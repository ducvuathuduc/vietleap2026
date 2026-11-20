"""Snapshot contract and release-gate tests."""

import json
from pathlib import Path

import jsonschema
import pandas as pd
import pytest

from vlkit.npl.real_pipeline import run_real
from vlkit.npl.real_data import clean_quarters
from vlkit.npl.snapshot import build_snapshot, main
from vlkit.npl.snapshot_metrics import dashboard_metrics
from test_real_pipeline import silver


@pytest.fixture
def snapshot_inputs(silver):
    output = silver / "analytics"
    run_real(silver, output)
    return output / "results.json", output / "gold.duckdb", silver


def test_public_snapshot_matches_schema_and_results(snapshot_inputs, monkeypatch, tmp_path):
    monkeypatch.delenv("NPL_PUBLISH_BANK_SERIES", raising=False)
    results_path, gold, silver = snapshot_inputs
    out = tmp_path / "seed" / "snapshot.json"
    main(["--results", str(results_path), "--gold", str(gold), "--silver", str(silver), "--out", str(out)])
    payload = json.loads(out.read_bytes())
    results = json.loads(results_path.read_bytes())
    schema_path = Path(__file__).resolve().parents[2] / "engine/vlkit/npl/schema/snapshot.schema.json"
    schema = json.loads(schema_path.read_bytes())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(payload, schema, format_checker=jsonschema.FormatChecker())

    baseline = results["M2"]["baseline"]
    q4 = baseline["terms"]["Q4"]
    benchmark = payload["kpis"]["benchmark"]
    assert benchmark["q4_coef_pp"] == q4["coefficient"]
    assert benchmark["n"] == baseline["n"]
    assert f"{abs(q4['coefficient']):.2f}" in payload["headline"]["en"]
    assert f"{abs(q4['coefficient']):.2f}".replace(".", ",") in payload["headline"]["vi"]
    assert str(baseline["n"]) in payload["headline"]["vi"]
    assert all(period in payload["headline"]["en"] for period in baseline["period"])
    assert payload["kpis"]["trend"]["down_then_up"] == [
        {key: row[key] for key in ("year", "n", "share_pct")} for row in results["M3"]["by_year"]
    ]
    assert payload["meta"]["publish_bank_series"] is True
    assert 1 <= len(payload["findings"]) <= 6
    assert payload["findings"] == results["M1"]["findings"]
    assert payload["decoder"] == results["decoder"]
    assert len(payload["decoder"]["rows"]) == 184
    assert len(payload["decoder"]["focus"]) == 48
    assert payload["market"]["coverage"]["actual_date_n"] == 0
    assert payload["decision_rule"]["q4_backtest"]
    assert payload["banks"][0]["latest"]["decision"]["status"] in {
        "within_normal_season", "improving", "deteriorating", "unavailable",
    }
    fields = {"period", "npl_pct", "coverage_pct", "ldr_pct", "nim_pct", "loan_growth_pct"}
    assert all(bank["series"] and all(set(point) == fields for point in bank["series"]) for bank in payload["banks"])
    assert any("Nguồn: FiinQuant (FiinGroup)" in item["text_vi"] for item in payload["legal"])
    payload["meta"]["publish_bank_series"] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)
    assert "d_roa_pct" not in payload["linkage"]["seasonal"]
    assert "d_roa_pct" not in payload["linkage"]["correlation"]
    assert "d_roa_pct" not in results["M5"]["seasonal"]
    assert "dashboard" in results["M1"]
    assert "TCB" in next(gate["detail"] for gate in payload["meta"]["quality"] if gate["id"] == "calibration")
    assert list(out.parent.iterdir()) == [out]


def test_only_zero_disables_publication_and_older_results_are_supported(snapshot_inputs, monkeypatch):
    results_path, gold, silver = snapshot_inputs
    results = json.loads(results_path.read_bytes())
    results["M1"].pop("dashboard")
    results["M5"]["seasonal"]["d_roa_pct"] = {"n": 0, "clusters": 0, "terms": {}}
    results_path.write_text(json.dumps(results), encoding="utf-8")

    monkeypatch.setenv("NPL_PUBLISH_BANK_SERIES", "0")
    hidden = build_snapshot(results_path, gold, silver)
    assert hidden["meta"]["publish_bank_series"] is False
    assert all("series" not in bank for bank in hidden["banks"])
    for collection in ("rows", "focus"):
        assert all(row["npl_ratio"] is None and row["coverage"] is None and row["lagged_coverage"] is None
                   and row["nim"] is None and row["loan_growth"] is None for row in hidden["decoder"][collection])
        assert any(row["delta_npl_ratio"] is not None for row in hidden["decoder"][collection])

    monkeypatch.setenv("NPL_PUBLISH_BANK_SERIES", "true")
    published = build_snapshot(results_path, gold, silver)
    assert published["meta"]["publish_bank_series"] is True
    assert all(bank["series"] for bank in published["banks"])
    assert "d_roa_pct" not in published["linkage"]["seasonal"]
    assert published["series"] == hidden["series"]


def test_metrics_require_consecutive_quarters_and_report_signal_availability():
    panel = pd.DataFrame({
        "bank_code": ["A"] * 5 + ["B"] * 4,
        "basis": "consolidated",
        "period": ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1",
                   "2024Q1", "2024Q3", "2024Q4", "2025Q1"],
        "npl_pct": [1., 2., 3., 2., 4., 9., 8., 7., 6.],
        "coverage_pct": [100., 100., 100., 90., 90., 90., 90., 90., 91.],
        "d_npl_pct": [None, 1., 1., -1., 2., None, None, -1., -1.],
        "d_coverage_pct": [None, 0., 0., -10., 0., None, None, 0., 1.],
        "adjusted_d_npl_pct": [None, 1., 1., -1., .5, None, None, -1., -.5],
    })
    data = dashboard_metrics(panel)
    bank = data["banks"]["A"]
    assert data["npl_4q_avg_median_pct"] == 2.75
    assert bank["down_then_up_years"] == 1
    assert bank["years"] == 1
    assert bank["latest"]["adjusted_change_pp"] == .5
    assert [(value["id"], value["period"]) for value in bank["signals"]] == [("S3", "2024Q4")]
    assert data["signal_availability"]["S1"]["eligible"] == 0
    assert data["signal_availability"]["S3"]["eligible"] == 6


def test_available_group2_change_survives_cleaning_and_fires_s1():
    source = pd.DataFrame({
        "ticker": ["A", "A", "A"],
        "period": ["2024Q1", "2024Q2", "2024Q4"],
        "npl_pct": [4., 3., 2.],
        "delta_g2_ratio": [None, .01, .02],
    })
    panel, _ = clean_quarters(source)
    assert panel.loc[panel.period.eq("2024Q4"), "delta_g2_ratio"].isna().all()
    summary = dashboard_metrics(panel.assign(adjusted_d_npl_pct=panel.d_npl_pct))
    assert summary["signal_availability"]["S1"] == {"eligible": 1, "missing": [], "fired": 1}
