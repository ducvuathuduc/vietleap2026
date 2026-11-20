import json
from datetime import datetime
from pathlib import Path
from shutil import copyfile

import pytest

from vlkit.ratewatch import pipeline
from vlkit.ratewatch.snapshot import publish, validate_snapshot
from vlkit.ratewatch.warehouse import transform

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/ratewatch/t2"


def test_optional_ingest_failure_still_publishes_with_source_status(tmp_path, monkeypatch):
    def fetch(url):
        if url.endswith("l%C3%A3i-su%E1%BA%A5t1"):
            return ("<p>Ngày áp dụng: 18/11/2026</p><table>"
                    "<tr><td>Qua đêm</td><td>4,47</td><td>863.715,0</td></tr></table>").encode()
        raise RuntimeError("Nguồn tạm thời gián đoạn")

    def fiin():
        raise RuntimeError("Vendor unavailable")

    monkeypatch.setattr(pipeline, "PublicHttp", lambda session: fetch)
    monkeypatch.setattr(pipeline, "fiin_provider", lambda *args: fiin)
    lake = tmp_path / "lake"
    rate_silver = lake / "silver/rw-20261120T1230/rates.csv"
    rate_silver.parent.mkdir(parents=True)
    copyfile(FIXTURE / "rates.csv", rate_silver)
    nonrate = lake / "silver/nonrate"
    nonrate.mkdir()
    copyfile(FIXTURE / "nonrate/omo.json", nonrate / "omo.json")
    output, path = tmp_path / "out", tmp_path / "snapshot.json"
    args = ["--non-rate-only", "--lake", str(lake), "--banks", str(FIXTURE / "banks.yaml"),
            "--out", str(output), "--snapshot", str(path), "--as-of", "2026-11-20T16:00:00+07:00"]
    assert pipeline.main(["--stage", "ingest", *args]) == 2
    log = json.loads(next((lake / "run_log").glob("*-nonrate.json")).read_text(encoding="utf-8"))
    assert "Nguồn tạm thời gián đoạn" in log["errors"]["omo"]
    assert pipeline.main(["--stage", "transform", *args]) == 0
    assert pipeline.main(["--stage", "publish", *args]) == 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    status = payload["meta"]["source_status"]
    assert status["interbank"]["status"] == "ok"
    assert status["omo"]["status"] == "error"
    assert status["omo"]["latest_period"] == "2026-11-19"
    assert status["omo"]["observed_at"] == "2026-11-20T12:45:00+07:00"
    assert payload["market"]["omo"][0]["volume_bn"] == 2244.48
    warning = next(gate for gate in payload["meta"]["quality"] if gate["id"] == "optional_sources")
    assert warning["status"] == "warn"
    assert "Nguồn tạm thời gián đoạn" in warning["detail"]
    assert pipeline.main(["--stage", "all", *args]) == 2
    assert path.is_file()


def test_publish_geo_cli_copies_contract_d(tmp_path):
    provinces = [
        dict(pcode=f"VN{i:02}", name_vi=f"Tỉnh {i}", name_en=f"Province {i}", branches_total=0,
             branches_by_bank={}, branch_source="OSM Overpass", population=100,
             population_period="2024", deposits_bn=None, credit_bn=None, deposit_period=None,
             deposit_source=None, best_counter_12m=None)
        for i in range(1, 35)
    ]
    geo = {"provinces": provinces, "boundary": "web/public/geo/vn-34.geo.json",
           "attribution": "Ranh giới: GSO/OCHA COD-AB v02 (CC BY-IGO) · Bao gồm Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa)."}
    geo_path, snapshot_path = tmp_path / "geography.json", tmp_path / "snapshot.json"
    geo_path.write_text(json.dumps(geo), encoding="utf-8")
    args = ["--fixture", str(FIXTURE), "--out", str(tmp_path / "out"), "--snapshot", str(snapshot_path),
            "--as-of", "2026-11-20T13:00:00+07:00"]
    assert pipeline.main(["--stage", "transform", *args]) == 0
    assert pipeline.main(["--stage", "publish", "--geo", str(geo_path), *args]) == 0
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["geo"] == geo


def test_publish_validates_and_preserves_previous_file_on_gate_failure(tmp_path):
    db = tmp_path / "ratewatch.duckdb"
    destination = tmp_path / "seed/snapshot.json"
    output = tmp_path / "public"
    transform(db, [FIXTURE / "rates.csv"], FIXTURE / "banks.yaml", list((FIXTURE / "nonrate").glob("*.json")))
    publish(db, destination, output, now=datetime.fromisoformat("2026-11-20T13:00:00+07:00"))
    original = destination.read_bytes()
    payload = json.loads(original)
    validate_snapshot(payload)
    assert payload["banks"][0]["rates"][0]["grade"] == "contested"
    assert len(payload["banks"][0]["rates"][0]["readers"]) == 2
    assert payload["market"]["ceiling_stats"]["quotes_1_5m"] == 0
    assert payload["market"]["central_fx"] == [{"date": "2026-11-20", "vnd_per_usd": 25659}]
    assert payload["macro"]["cpi_yoy"] == [{"month": "2026-10", "pct": 5.09}]
    assert payload["macro"]["sbv_monthly"][0]["credit_growth_ytd_pct"] == 10.19
    assert list((output / "archive").glob("*.csv"))
    assert (output / "eda.svg").is_file()
    with pytest.raises(ValueError, match="freshness"):
        publish(db, destination, output, now=datetime.fromisoformat("2027-01-01T13:00:00+07:00"))
    assert destination.read_bytes() == original
