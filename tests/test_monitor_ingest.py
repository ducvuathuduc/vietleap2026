import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from vlkit.de.warehouse import Warehouse


@pytest.fixture
def local_warehouse(tmp_path):
    wh = Warehouse(tmp_path / "warehouse.duckdb", tmp_path / "lake")
    yield wh
    wh.close()


def test_selects_latest_complete_fiinquant_landing(tmp_path):
    from vlkit.monitor.ingest import select_file

    folder = tmp_path / "bars"
    folder.mkdir()
    for filename, time in (("2026-11-19_zzz", "10:00:00"), ("2026-11-19_aaa", "11:00:00")):
        parquet = folder / f"{filename}.parquet"
        pd.DataFrame({"ticker": ["ACB"]}).to_parquet(parquet, index=False)
        parquet.with_suffix(".json").write_text(json.dumps({
            "fetched_at": f"2026-11-19T{time}+07:00",
            "sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(),
        }), encoding="utf-8")
    (folder / "2026-11-20_pending.parquet").touch()
    path, meta = select_file(folder / "*.parquet", paired=True)
    assert path.stem == "2026-11-19_aaa"
    assert meta["fetched_at"] == "2026-11-19T11:00:00+07:00"


def test_corrupt_landing_is_refused(tmp_path):
    from vlkit.monitor.ingest import select_file

    parquet = tmp_path / "bars.parquet"
    parquet.write_bytes(b"a partial write")
    parquet.with_suffix(".json").write_text(json.dumps({
        "fetched_at": "2026-11-19T11:00:00+07:00", "sha256": "invalid",
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        select_file(tmp_path / "*.parquet", paired=True)


def test_warehouse_bronze_is_incremental_without_stale_revisions(tmp_path, local_warehouse):
    from vlkit.monitor.ingest import land_source

    path = tmp_path / "landing.parquet"
    pd.DataFrame({"ticker": ["VCB", "ACB"], "value": [10.0, 20.0]}).to_parquet(path, index=False)
    provenance = {"kind": "file", "source": "fq_bars", "uri": str(path),
                  "fetched_at": "2026-11-19T11:00:00+07:00"}
    first = land_source(local_warehouse, "vm_fq_bars", path, provenance, "run1")
    second = land_source(local_warehouse, "vm_fq_bars", path, provenance, "run2")
    assert first == {"rows": 2, "changed": True}
    assert second == {"rows": 2, "changed": False}
    pd.DataFrame({"ticker": ["ACB"], "value": [21.0]}).to_parquet(path, index=False)
    third = land_source(local_warehouse, "vm_fq_bars", path, provenance, "run3")
    result = local_warehouse.read("bronze.vm_fq_bars")
    assert third == {"rows": 1, "changed": True}
    assert result[["ticker", "value", "_run_id"]].to_dict("records") == [
        {"ticker": "ACB", "value": 21.0, "_run_id": "run3"}]
    assert len(local_warehouse.con.execute("SELECT * FROM meta.lineage").fetchall()) == 2


def test_long_carriers_preserve_units_periods_and_evidence():
    from vlkit.monitor.ingest import normalize_long

    source = pd.DataFrame({
        "indicator_id": ["nsnn_thu", "nsnn_thu", "cpi"], "period": ["2026-10"] * 3,
        "measure_type": ["month", "pct_plan", "avg_ytd"], "value": [40, 105, 3.2],
        "unit": ["nghìn tỷ đồng", "%", "%"], "evidence": ["A", "B", "C"],
    })
    result = normalize_long(source, "nso", "run1")
    assert result["indicator_id"].tolist() == ["nsnn_thu_level", "nsnn_thu_pct_plan", "cpi_avg_ytd"]
    assert result["measure_type"].tolist() == ["level", "pct_plan", "ytd"]
    assert result["value"].tolist() == [40, 105, 3.2]
    assert result["geo_type"].tolist() == ["national"] * 3
    assert result["evidence"].tolist() == ["A", "B", "C"]


def test_transfer_inputs_keep_old_provinces_for_silver_lineage():
    from vlkit.monitor.ingest import normalize_transfers

    source = pd.DataFrame({"province": ["HÀ GIANG", "TUYÊN QUANG"], "year": [2025, 2025],
                           "earmarked_transfers": [2000, 3000]})
    result = normalize_transfers(source, "run1")
    assert result["geo"].tolist() == ["HÀ GIANG", "TUYÊN QUANG"]
    assert result["value"].tolist() == [2000, 3000]
    assert result["unit"].tolist() == ["triệu đồng", "triệu đồng"]
    assert set(result["indicator_id"]) == {"earmarked_transfers"}


def test_monitor_help_exposes_offline_mode():
    import subprocess
    import sys

    path = Path(__file__).absolute().parents[1] / "de.py"
    result = subprocess.run([sys.executable, str(path), "monitor", "--help"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0
    assert "--offline" in result.stdout


def test_registered_catalog_has_vietnamese_labels_and_canonical_units():
    from vlkit.monitor.ingest import read_yaml

    base = Path(__file__).absolute().parents[1] / "scenarios" / "vn_monitor"
    rows = read_yaml(base / "indicators.yaml")
    catalog = {item["id"]: item for item in rows}
    assert len(catalog) == len(rows)
    assert catalog["nsnn_thu_ytd"]["name_vi"] == "Thu ngân sách nhà nước lũy kế"
    assert catalog["nsnn_thu_ytd"]["unit"] == "nghìn tỷ đồng"
    assert catalog["earmarked_transfers"]["unit"] == "tỷ đồng"


def test_sources_keep_bronze_wdi_and_align_asean_and_optional_press(tmp_path, local_warehouse):
    import shutil

    from vlkit.monitor.ingest import ingest_sources, read_yaml

    root = Path(__file__).absolute().parents[1]
    fixtures = root / "tests" / "fixtures" / "vn_monitor"
    pack = root / "scenarios" / "vn_monitor"
    shutil.copy(fixtures / "ingest_wdi.csv", tmp_path / "wdi.csv")
    shutil.copy(fixtures / "ingest_press.csv", tmp_path / "press.csv")
    specs = [
        {"name": name, "kind": "file", "uri": f"{name}.csv", "source_id": name, "license": "fixture",
         "conform": {}, "grain_vi": "fixture", "optional": name != "wdi"}
        for name in ("wdi", "press", "nso")
    ]
    metadata = read_yaml(pack / "sources_meta.yaml")
    catalog = read_yaml(pack / "indicators.yaml")
    values, sources, loads, missing = ingest_sources(
        local_warehouse, tmp_path, specs, metadata, catalog, "fixture", offline=True,
    )
    assert missing == ["nso"]
    assert loads[0]["rows"] == 4
    assert set(values.loc[values.source_id.eq("wdi"), "geo"]) == {"VNM", "IDN"}
    assert set(values.loc[values.source_id.eq("press_mof"), "indicator_id"]) == {"nsnn_thu_ytd"}
    assert {source["id"] for source in sources} == {"wdi", "press_mof", "tcbs"}


def test_offline_monitor_rerun_has_unique_stable_model_counts(tmp_path):
    import shutil

    from vlkit.monitor.pipeline import run_monitor

    root = Path(__file__).absolute().parents[1]
    fixture = root / "tests" / "fixtures" / "vn_monitor" / "ingest_wdi.csv"
    practice = tmp_path / "data" / "practice"
    practice.mkdir(parents=True)
    shutil.copy(fixture, practice / "wdi_asia_fiscal_panel.csv")
    output = tmp_path / "out" / "vn_monitor"
    options = {"root": tmp_path, "scenario": root / "scenarios" / "vn_monitor", "offline": True}
    first = run_monitor(**options)
    second = run_monitor(**options)
    payload = json.loads((output / "monitor.json").read_text(encoding="utf-8"))
    names = [row["name"] for row in payload["model"]["tables"]]
    assert len(names) == len(set(names))
    assert len(first["missing"]) == 12
    assert first["rows"] == second["rows"]
    assert not first["fired"]
    assert payload["asean"]["gdp_per_capita_usd"]["vn_rank"] == 2
    assert (output / "csv" / "v_asean_rank.csv").is_file()
    assert (output / "eda.md").is_file()


def test_source_cutoff_compares_trading_dates_and_report_periods_chronologically():
    from vlkit.monitor.ingest import update_source

    found = {}
    fetched = "2026-11-19T14:42:00+07:00"
    for period in ("2026-11-18", "2026-Q3", "2026-11-19"):
        update_source(found, {"fiinquant": {}}, "fiinquant", fetched, period, 1)
    assert found["fiinquant"]["data_cutoff"] == "2026-11-19"
    assert found["fiinquant"]["rows"] == 3


def test_press_carrier_classifies_geography_and_preserves_evidence_status():
    from vlkit.monitor.ingest import normalize_long

    raw = pd.DataFrame({
        "indicator_id": ["bank_npl", "bank_npl", "dtc_giai_ngan", "re_new_supply"],
        "period": ["2026-Q3", "2026-Q3", "2026-10", "2026-Q3"],
        "measure_type": ["ratio", "ratio", "pct_plan", "level"],
        "value": [4.2, 2.1, 45, 500],
        "geo": ["ACB", "VNM", "Hà Nội", "Hà Nội"],
        "evidence_ok": [True, False, True, True],
        "extractor_version": ["v1"] * 4,
    })
    normalized = normalize_long(raw, "press", "run1")
    assert normalized["geo_type"].tolist() == ["ticker", "national", "province", "city"]
    assert normalized["evidence_ok"].tolist() == [True, False, True, True]
    assert normalized["parser_version"].tolist() == ["v1"] * 4
