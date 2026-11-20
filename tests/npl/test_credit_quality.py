import json
import os
import subprocess
import sys

import duckdb
import numpy as np
import pandas as pd
import pytest

from vlkit.npl.model import build_signals, calibrate_npl, derive_credit_quality
from vlkit.npl.pipeline import run_pipeline
from vlkit.npl.regression import run_regressions


@pytest.fixture
def silver(kit_root):
    return kit_root / "tests/fixtures/npl/SYNTHETIC_credit_quality.csv"


def credit_rows(silver):
    rows = pd.read_csv(silver).iloc[:3].copy()
    rows[["loans_vnd_bn", "group2_vnd_bn", "npl_vnd_bn",
          "provision_vnd_bn", "writeoff_vnd_bn"]] = [
        [100, 5, 10, 20, 1], [125, 10, 8, 12, 3], [125, 11, 7, 7, 7],
    ]
    rows["writeoff_basis"] = ["ytd", "quarter", "ytd"]
    return rows


def test_hand_calculated_formulas(silver):
    _, q2, q3 = derive_credit_quality(credit_rows(silver)).to_dict("records")
    expected = {
        "npl_ratio": .064, "g2_ratio": .08, "coverage": 1.5,
        "broad_problem_ratio": .144, "writeoff_q_vnd_bn": 3,
        "writeoff_ratio": .03, "writeoff_ratio_annualised": .12,
        "npl_formation": .01, "npl_numerator_effect": -.02,
        "npl_loan_growth_effect": -.016, "delta_npl_ratio": -.036,
        "loan_growth": .25, "lagged_coverage": 2, "delta_g2_ratio": .03,
    }
    assert {field: q2[field] for field in expected} == pytest.approx(expected)
    assert q3["writeoff_q_vnd_bn"] == 3
    assert q3["npl_formation"] == pytest.approx(.016)


def test_no_cross_basis_or_gap_lags_and_ytd_resets(silver):
    rows = credit_rows(silver)
    rows["period"] = ["2025Q2", "2025Q4", "2026Q1"]
    rows["basis"] = ["separate", "consolidated", "separate"]
    result = derive_credit_quality(rows).set_index("period")
    assert result["delta_npl_ratio"].isna().all()
    assert result["writeoff_ratio"].isna().all()
    assert pd.isna(result.at["2025Q2", "writeoff_q_vnd_bn"])
    assert result.at["2026Q1", "writeoff_q_vnd_bn"] == 7


@pytest.mark.parametrize(("field", "value", "message"), [
    ("loans_vnd_bn", 14, "loan balance"),
    ("provision_vnd_bn", -1, "provision_vnd_bn"),
    ("writeoff_vnd_bn", float("inf"), "writeoff_vnd_bn"),
    ("period", "2025Q5", "period"),
    ("basis", "mixed", "basis"),
    ("writeoff_basis", "annual", "writeoff_basis"),
])
def test_invalid_silver_cells_fail_gate(silver, field, value, message):
    rows = credit_rows(silver)
    rows[field] = rows[field].astype(object)
    rows.loc[0, field] = value
    with pytest.raises(ValueError, match=message):
        derive_credit_quality(rows)


def test_missing_inputs_and_zero_denominators_are_distinct(silver):
    rows = credit_rows(silver)
    rows.loc[0, ["npl_vnd_bn", "group2_vnd_bn", "source_url"]] = [0, None, None]
    result = derive_credit_quality(rows).iloc[0]
    assert result["missing_fields"] == ["group2_vnd_bn", "source_url"]
    assert result["npl_ratio"] == 0
    assert pd.isna(result["coverage"])
    assert pd.isna(result["broad_problem_ratio"])


def test_duplicate_grain_and_falling_ytd_fail_gate(silver):
    rows = credit_rows(silver)
    with pytest.raises(ValueError, match="duplicate"):
        derive_credit_quality(pd.concat([rows, rows]))
    rows.loc[2, "writeoff_vnd_bn"] = 2
    with pytest.raises(ValueError, match="write-off"):
        derive_credit_quality(rows)


def test_calibration_is_keyed_by_bank_period_basis_and_uses_runtime_tolerance(silver):
    credit = derive_credit_quality(credit_rows(silver))
    reference = {("VCB", "2025Q2", "consolidated"): .066}
    assert calibrate_npl(credit, reference, tolerance=.003).iloc[0]["difference"] == pytest.approx(.002)
    with pytest.raises(ValueError, match="FiinQuant"):
        calibrate_npl(credit, reference, tolerance=.001)


@pytest.mark.parametrize(("changes", "thresholds", "expected"), [
    ([.01, .01, -.1, .02], {}, ["S1", "S2", "S3", "S4"]),
    ([-.01, 0, 0, 0], {}, ["S5"]),
    ([-.01, None, 0, 0], {}, []),
    ([.01, .01, -.1, .02], {"g2": .015}, ["S2", "S3", "S4"]),
    ([.01, .01, -.1, .02], {"npl": .02}, []),
])
def test_signals_and_thresholds(changes, thresholds, expected):
    credit = pd.DataFrame([
        dict(bank_code="VCB", period="2025Q2", basis="consolidated", delta_npl_ratio=-.01,
             delta_g2_ratio=changes[0], delta_writeoff_ratio=changes[1],
             delta_coverage=changes[2], delta_npl_formation=changes[3]),
    ])
    signals = build_signals(credit, thresholds=thresholds)
    assert signals["signal"].tolist() == expected
    assert signals["sentence_vi"].str.endswith(".").all()
    assert signals["sentence_en"].str.endswith(".").all()


def test_regression_recovers_known_panel_slopes_and_checks_each_bank():
    rng = np.random.default_rng(17)
    rows = []
    for bank in range(8):
        for _ in range(5):
            w, g2, growth, cover = rng.uniform(0, 1, 4)
            rows.append(dict(bank_code=f"B{bank}", basis="consolidated",
                             delta_npl_ratio=(bank - 2*w + 3*g2 + growth - cover) / 100,
                             writeoff_ratio=w, delta_g2_ratio=g2, loan_growth=growth, lagged_coverage=cover))
    result = run_regressions(pd.DataFrame(rows))
    fixed = result["fixed_effects"]
    assert fixed["n"] == result["pooled"]["n"] == 40
    assert fixed["r2"] == pytest.approx(1)
    assert fixed["covariance"] == "cluster_bank"
    assert fixed["n_banks"] == 8
    slope = fixed["coefficients"]["writeoff_ratio"]
    assert slope["estimate"] == pytest.approx(-2)
    assert slope["ci_95"] == pytest.approx([-2, -2])
    assert result["pooled"]["r2"] < fixed["r2"]
    assert set(result["leave_one_bank_out"]) == {f"B{bank}" for bank in range(8)}
    assert all(fit["n"] == 35 for fit in result["leave_one_bank_out"].values())
    assert "40" in result["sample_note"]["en"]


def test_cli_writes_star_schema_and_serving_artifacts(silver, kit_root, tmp_path):
    output = tmp_path / "gold"
    run = subprocess.run(
        [sys.executable, "-m", "vlkit.npl.pipeline", "--silver", str(silver), "--out", str(output)],
        env={**os.environ, "PYTHONPATH": str(kit_root / "engine")}, capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stderr
    assert {path.name for path in output.iterdir()} == {
        "npl.duckdb", "signals.csv", "regression.json", "data_dictionary.md", "erd.mmd",
    }
    with duckdb.connect(str(output / "npl.duckdb"), read_only=True) as con:
        assert con.execute("select count(*) from gold.fact_credit_quality").fetchone() == (48,)
        assert con.execute("select count(*) from gold.dim_bank").fetchone() == (8,)
        assert con.execute("select count(*) from gold.dim_period where is_quarter_end").fetchone() == (6,)
        assert con.execute("select count(*) from gold.dim_source").fetchone() == (48,)
        assert con.execute("select count(*) from gold.v_credit_quality where missing_fields = []").fetchone() == (48,)
        assert con.execute("select count(*) from gold.v_signal").fetchone()[0] == len(pd.read_csv(output / "signals.csv"))
    result = json.loads((output / "regression.json").read_text(encoding="utf-8"))
    assert result["fixed_effects"]["n"] == 40
    assert result["fixed_effects"]["coefficients"]["loan_growth"]["ci_95"][0] is not None


def test_parquet_and_reporting_basis_selection(silver, tmp_path):
    consolidated = credit_rows(silver)
    separate = consolidated.assign(basis="separate", npl_vnd_bn=[3, 4, 5])
    path = tmp_path / "silver.parquet"
    with duckdb.connect() as con:
        con.from_df(pd.concat([consolidated, separate])).write_parquet(str(path))
    output = tmp_path / "gold"
    run_pipeline(path, output, basis="separate")
    with duckdb.connect(str(output / "npl.duckdb"), read_only=True) as con:
        assert con.execute("select count(*) from gold.fact_credit_quality").fetchone() == (6,)
        assert con.execute("select count(*) from gold.v_signal").fetchone() == (0,)
    assert json.loads((output / "regression.json").read_text())["basis"] == "separate"
