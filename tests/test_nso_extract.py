import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools.nso import extract

FIX = Path(__file__).parent / "fixtures" / "nso"
URL = "https://www.nso.gov.vn/bai-top/2026/11/bao-cao-thang-muoi/"


class Resp:
    def __init__(self, body: bytes):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_parse_listing_resolves_urls_and_periods():
    html = """
    <div class="archive-container">
    <p><a href="https://www.nso.gov.vn/bai-top/2026/11/bao-cao-thang-muoi/"></p>
    <section class="item">
    <h3>Báo cáo tình hình kinh tế - xã hội tháng Mười và 10 tháng năm 2026</h3>
    <p><span class="archive-issue-date">Ngày đăng: 03/11/2026</span></p>
    </section>
    <p></a></p>
    <p><a href="/tin-tuc-thong-ke/2026/10/bao-cao-quy-iii/"></p>
    <section class="item">
    <h3>Báo cáo tình hình kinh tế - xã hội quý III và 9 tháng năm 2026</h3>
    </section>
    <p></a></p>
    </div>
    """
    entries = extract.parse_listing(html, "https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/")
    assert [e["period"] for e in entries] == ["2026-10", "2026-09"]
    assert entries[0]["url"] == URL
    assert entries[1]["url"] == "https://www.nso.gov.vn/tin-tuc-thong-ke/2026/10/bao-cao-quy-iii/"
    assert "tháng Mười" in entries[0]["title"]


def test_select_targets_uses_watermark_plus_last_two():
    periods = ["2024-01", "2024-02", "2026-08", "2026-09", "2026-10"]
    assert extract.select_targets(periods, None) == set(periods)
    assert extract.select_targets(periods, "2026-08") == {"2026-09", "2026-10"}
    assert extract.select_targets(periods, "2026-10") == {"2026-09", "2026-10"}
    assert extract.select_targets(periods, "2024-01") == {"2024-02", "2026-08", "2026-09", "2026-10"}


def test_robots_denied_is_recorded_and_raises(tmp_path):
    def opener(request, timeout=60):
        return Resp(b"User-agent: *\nDisallow: /\n")

    with pytest.raises(extract.RobotsDenied):
        extract.check_robots(
            robots_url="https://www.nso.gov.vn/robots.txt",
            out_dir=tmp_path,
            opener=opener,
            sleep=lambda _s: None,
            delay=0,
        )
    record = json.loads((tmp_path / "_robots.json").read_text(encoding="utf-8"))
    assert record["allowed"] is False
    assert record["robots_url"] == "https://www.nso.gov.vn/robots.txt"


def test_robots_allowed_is_recorded(tmp_path):
    def opener(request, timeout=60):
        return Resp(b"User-agent: *\nAllow: /\nCrawl-delay: 3\n")

    assert extract.check_robots(
        robots_url="https://www.nso.gov.vn/robots.txt",
        out_dir=tmp_path,
        opener=opener,
        sleep=lambda _s: None,
        delay=0,
    )
    record = json.loads((tmp_path / "_robots.json").read_text(encoding="utf-8"))
    assert record["allowed"] is True
    assert record["crawl_delay"] == 3


def test_fetch_retries_with_backoff():
    calls = []
    sleeps = []

    def opener(request, timeout=60):
        calls.append(request.full_url)
        if len(calls) < 3:
            raise OSError("temporary")
        return Resp(b"ok")

    body = extract.fetch_url(
        "https://www.nso.gov.vn/x",
        opener=opener,
        retries=3,
        sleep=sleeps.append,
        delay=0,
    )
    assert body == b"ok"
    assert len(calls) == 3
    assert sleeps == [1, 2]


def test_run_is_idempotent_and_uses_cache(tmp_path):
    fixture = (FIX / "nso_2026-10.html").read_bytes()
    fetched = []

    def fake_discover():
        return {
            "2026-10": {
                "url": URL,
                "title": "Báo cáo tình hình kinh tế - xã hội tháng Mười và 10 tháng năm 2026",
            }
        }

    def fake_fetch(url):
        fetched.append(url)
        return fixture

    summary = extract.run(
        out_dir=tmp_path,
        discover_fn=fake_discover,
        fetch_fn=fake_fetch,
        robots_fn=lambda **kwargs: True,
        sleep=lambda _s: None,
        delay=0,
    )
    assert summary["errors"] == []
    assert summary["fetched"] == ["2026-10"]
    assert summary["rows"] == 31
    assert fetched == [URL]

    raw = tmp_path / "2026-10.html"
    assert raw.read_bytes() == fixture
    assert (tmp_path / "2026-10.html.sha256").read_text().strip() == hashlib.sha256(fixture).hexdigest()

    first = (tmp_path / "nso_monthly_long.csv").read_text(encoding="utf-8")
    summary2 = extract.run(
        out_dir=tmp_path,
        discover_fn=fake_discover,
        fetch_fn=fake_fetch,
        robots_fn=lambda **kwargs: True,
        sleep=lambda _s: None,
        delay=0,
    )
    second = (tmp_path / "nso_monthly_long.csv").read_text(encoding="utf-8")

    assert summary2["cached"] == ["2026-10"]
    assert fetched == [URL], "second run must not hit the network"
    assert first == second
    with open(tmp_path / "nso_monthly_long.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 31
    keys = [(r["indicator_id"], r["period"], r["measure_type"]) for r in rows]
    assert len(keys) == len(set(keys))


def test_run_refresh_refetches_cache(tmp_path):
    fixture = (FIX / "nso_2026-10.html").read_bytes()
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return fixture

    kwargs = dict(
        out_dir=tmp_path,
        discover_fn=lambda: {"2026-10": {"url": URL, "title": "Báo cáo tháng Mười và 10 tháng năm 2026"}},
        fetch_fn=fake_fetch,
        robots_fn=lambda **kwargs: True,
        sleep=lambda _s: None,
        delay=0,
    )
    extract.run(**kwargs)
    extract.run(refresh=True, **kwargs)
    assert calls == [URL, URL]


def test_coverage_matrix_has_every_indicator_and_period(tmp_path):
    rows = [
        {
            "indicator_id": "nsnn_thu",
            "period": "2026-10",
            "measure_type": "month",
            "value": 1.0,
            "unit": "nghìn tỷ đồng",
            "source_url": "",
            "published_date": "",
            "evidence": "",
            "parser_version": "x",
        }
    ]
    coverage = extract.coverage_rows(rows, ["2026-09", "2026-10"])
    assert len(coverage) == len(extract.parse.INDICATOR_ORDER) * 2
    found = {(r["indicator_id"], r["period"]): r for r in coverage}
    assert found[("nsnn_thu", "2026-10")]["n_measures"] == 1
    assert found[("nsnn_thu", "2026-10")]["measures"] == "month"
    assert found[("nsnn_thu", "2026-09")]["n_measures"] == 0
    assert found[("cpi", "2026-10")]["n_measures"] == 0
