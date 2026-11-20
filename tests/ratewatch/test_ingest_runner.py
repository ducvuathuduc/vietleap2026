"""Runner: bronze + silver + run log, offline replay, idempotency, unchanged sheet, robots skip."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from vlkit.ratewatch.ingest.contract import SILVER_COLUMNS
from vlkit.ratewatch.ingest.http import FetchError, retry_call
from vlkit.ratewatch.ingest.runner import run_ingest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ratewatch"
ROOT = Path(__file__).resolve().parents[2]
BANKS = ROOT / "scenarios" / "ratewatch" / "banks.yaml"
AGG_URL = "https://laisuattietkiem.vn/"
OCB_URL = "https://ocb.com.vn/vi/cong-cu/lai-suat"
HDB_URL = "https://hdbank.com.vn/vi/ca-nhan/tiet-kiem/lai-suat"
SEEN = "2026-11-20T13:30:00+07:00"


def save_object(root: Path, source: str, run_id: str, name: str, data: bytes, url: str, method: str) -> None:
    folder = root / source / run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    (folder / f"{name}.meta.json").write_text(json.dumps({
        "url": url, "fetched_at": "2026-11-20T13:30:00+07:00", "status": 200,
        "sha256": hashlib.sha256(data).hexdigest(), "run_id": run_id, "robots_allowed": True,
        "licence": "public page, reference use", "method": method, "usd_cost": 0.0,
    }), encoding="utf-8")


@pytest.fixture
def offline(tmp_path):
    root = tmp_path / "offline"
    save_object(root, "aggregator", "rw-20261120T1300", "index.html",
                (FIXTURES / "aggregator_20261120.html").read_bytes(), AGG_URL, "aggregator")
    save_object(root, "bank_html", "rw-20261120T1300", "OCB.html",
                (FIXTURES / "html" / "OCB_20261120.html").read_bytes(), OCB_URL, "bank_html")
    save_object(root, "tinyfish", "rw-20261120T1300", "HDB.json",
                (FIXTURES / "tinyfish" / "HDBank_20261120.json").read_bytes(), HDB_URL, "tinyfish")
    return root


def run(tmp_path, offline, run_id="rw-20261120T1400"):
    return run_ingest(run_id=run_id, out=tmp_path / "lake", banks_path=BANKS, offline=offline,
                      observed_at=SEEN)


def test_offline_replay_writes_bronze_silver_and_run_log(tmp_path, offline):
    result = run(tmp_path, offline)
    silver = tmp_path / "lake" / "silver" / "rw-20261120T1400"
    assert (silver / "rates.parquet").is_file() and (silver / "rates.csv").is_file()
    frame = pd.read_parquet(silver / "rates.parquet")
    assert list(frame.columns) == SILVER_COLUMNS
    assert set(frame.reader) == {"aggregator", "bank_html", "tinyfish"}
    assert "HDB" in set(frame.bank_code) and "OCB" in set(frame.bank_code)
    assert result.log["run_id"] == "rw-20261120T1400"
    assert result.log["records"] == len(frame)
    assert {"started_at", "finished_at", "seconds", "usd", "errors", "banks"} <= set(result.log)
    assert result.log["banks"]["NCB"]["status"] == "unreadable"
    assert "NCB" not in set(frame.bank_code)
    for meta_path in (tmp_path / "lake" / "bronze").rglob("*.meta.json"):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert {"url", "fetched_at", "status", "sha256", "run_id", "robots_allowed", "licence",
                "method", "usd_cost"} <= set(meta)


def test_running_twice_produces_the_same_silver(tmp_path, offline):
    first = run(tmp_path, offline)
    second = run(tmp_path, offline, run_id="rw-20261120T1500")
    keep = [c for c in SILVER_COLUMNS if c not in ("run_id", "observed_at")]
    pd.testing.assert_frame_equal(first.silver[keep].reset_index(drop=True),
                                  second.silver[keep].reset_index(drop=True))


def test_unchanged_sheet_is_reused_not_reparsed(tmp_path, offline):
    run(tmp_path, offline)
    second = run(tmp_path, offline, run_id="rw-20261120T1500")
    assert second.log["banks"]["OCB"]["unchanged"] is True
    assert second.log["banks"]["OCB"]["rows"] > 0
    assert second.log["banks"]["HDB"]["unchanged"] is True


def test_same_run_id_overwrites_the_same_objects(tmp_path, offline):
    first = run(tmp_path, offline)
    second = run(tmp_path, offline)
    folders = sorted(p.name for p in (tmp_path / "lake" / "silver").iterdir())
    assert folders == ["rw-20261120T1400"]
    assert (tmp_path / "lake" / "silver" / "rw-20261120T1400" / "rates.csv").is_file()
    pd.testing.assert_frame_equal(first.silver, second.silver)


def test_robots_denied_bank_is_skipped(tmp_path, monkeypatch):
    from vlkit.ratewatch.ingest import runner
    from vlkit.ratewatch.ingest.http import Response

    class FakeHttp:
        def __init__(self):
            self.calls = []

        def get(self, url, **kw):
            self.calls.append(url)
            assert url.startswith(AGG_URL), f"robots-denied host was fetched: {url}"
            return Response(url=url, status=200,
                            content=(FIXTURES / "aggregator_20261120.html").read_bytes())

    http = FakeHttp()
    monkeypatch.setattr(runner, "robots_allowed", lambda url, **kw: url.startswith(AGG_URL))
    result = run_ingest(run_id="rw-20261120T1400", out=tmp_path / "lake", banks_path=BANKS,
                        offline=None, observed_at=SEEN, http=http, allow_agents=False)
    assert set(http.calls) == {AGG_URL}
    assert result.log["banks"]["OCB"]["status"] == "skipped_robots"
    assert result.silver[(result.silver.bank_code == "OCB") & (result.silver.reader == "bank_html")].empty


def test_retry_call_uses_exponential_backoff():
    sleeps, attempts = [], []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise FetchError("temporary")
        return "ok"

    assert retry_call(flaky, attempts=3, base_delay=1.0, sleep=sleeps.append) == "ok"
    assert len(attempts) == 3 and sleeps == [1.0, 2.0]

    def broken():
        raise FetchError("permanent")

    with pytest.raises(FetchError):
        retry_call(broken, attempts=3, base_delay=1.0, sleep=sleeps.append)
