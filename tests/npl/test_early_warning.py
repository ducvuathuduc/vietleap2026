"""Early-warning panel timing, quarterly flows and paired validation."""

import numpy as np
import pandas as pd
import pytest

from vlkit.npl.early_warning import (
    SPECIFICATIONS, _max_vif, build_warning_panel, compare_forecasts, holdout_predictions, temporal_split,
)


def _panel(periods, values, bank="A"):
    return pd.DataFrame({"bank_code": bank, "period": periods, "npl_pct": values, "coverage_pct": 100.0})


def test_horizons_use_exact_quarters_and_the_event_checks_all_four_future_quarters():
    complete = _panel(pd.period_range("2024Q1", "2025Q1", freq="Q").astype(str), [1., 1.6, 1.2, .8, .9])
    frame = build_warning_panel(complete, None).set_index("period")
    assert frame.at["2024Q1", "change_h1"] == pytest.approx(.6)
    assert frame.at["2024Q1", "change_h4"] == pytest.approx(-.1)
    assert frame.at["2024Q1", "rise_in_four"] == 1
    assert pd.isna(frame.at["2024Q2", "rise_in_four"])
    gap = build_warning_panel(complete.loc[complete.period.ne("2024Q2")], None).set_index("period")
    assert pd.isna(gap.at["2024Q1", "change_h1"])
    assert pd.isna(gap.at["2024Q1", "rise_in_four"])
    assert gap.at["2024Q1", "change_h4"] == pytest.approx(-.1)
    assert pd.isna(gap.at["2024Q3", "lagged_coverage_pct"])


def test_predictors_only_use_quarter_anchored_flows_and_opening_loans():
    panel = _panel(["2024Q1", "2024Q2", "2024Q3"], [2., 2.2, 2.4])
    rows = [
        ("2024Q1", "loans_customer", "point", 1000),
        ("2024Q2", "loans_customer", "point", 1200),
        ("2024Q3", "loans_customer", "point", 1400),
        ("2024Q2", "provision_expense", "quarterly", -11),
        ("2024Q2", "provision_expense", "ytd", -999),
        ("2024Q3", "provision_expense", "ytd", -27),
        ("2024Q2", "provision_closing", "point", -30),
        ("2024Q2", "group_2_watch", "point", 20),
        ("2024Q2", "group_3_substandard", "point", 15),
        ("2024Q2", "group_4_doubtful", "point", 5),
        ("2024Q2", "group_5_loss", "point", 10),
    ]
    screening = pd.DataFrame(rows, columns=["period", "field", "flow_basis", "value_vnd_bn"]).assign(bank="A")
    frame = build_warning_panel(panel, screening).set_index("period")
    assert frame.at["2024Q2", "credit_cost_pct"] == pytest.approx(1.)
    assert pd.isna(frame.at["2024Q3", "credit_cost_pct"])
    assert frame.at["2024Q2", "provisions_to_loans_pct"] == pytest.approx(2.5)
    assert frame.at["2024Q2", "loan_growth_qoq_pct"] == pytest.approx(20.)
    assert frame.at["2024Q2", "broad_problem_pct"] == pytest.approx(100 * 50 / 1200)
    assert frame.at["2024Q2", "severity_pct"] == pytest.approx(100 / 3)


def _forecast_fixture():
    rng = np.random.default_rng(60)
    dates = pd.period_range("2020Q1", "2027Q3", freq="Q")
    rows = []
    for bank in "ABCD":
        for time in dates:
            risk, npl = rng.normal(), rng.normal()
            rows.append({
                "bank_code": bank, "period": str(time), "quarter_id": time.ordinal,
                "npl_pct": npl, "group2_pct": risk,
                "change_h1": .8 * risk + .1 * npl + rng.normal(0, .05),
            })
    return pd.DataFrame(rows)


def test_training_labels_end_by_cutoff_and_predictions_ignore_holdout_outcomes():
    frame = _forecast_fixture()
    predictors = {"npl_only": ("npl_pct",), "npl_group2": ("npl_pct", "group2_pct")}
    train, test = temporal_split(frame, "change_h1", 1)
    assert train.period.max() == "2024Q3"
    assert test.period.min() == "2025Q1"
    _, scored, predictions = holdout_predictions(frame, "change_h1", 1, predictors)
    changed = frame.copy()
    changed.loc[changed.period.ge("2024Q4"), "change_h1"] += 1000
    _, changed_test, unchanged_predictions = holdout_predictions(changed, "change_h1", 1, predictors)
    assert scored.period.tolist() == changed_test.period.tolist()
    for name in predictors:
        np.testing.assert_array_equal(predictions[name], unchanged_predictions[name])


def test_cluster_bootstrap_is_reproducible_on_a_matched_holdout():
    frame = _forecast_fixture()
    predictors = {"npl_only": ("npl_pct",), "npl_group2": ("npl_pct", "group2_pct")}
    first = compare_forecasts(frame, "change_h1", 1, predictors, reps=59)
    second = compare_forecasts(frame, "change_h1", 1, predictors, reps=59)
    assert first == second
    assert first["fits"]["npl_group2"]["mae"]["estimate"] < first["fits"]["npl_only"]["mae"]["estimate"]
    assert first["gains_vs_npl"]["npl_group2"]["mae"]["ci95"][0] > 0


def test_binary_holdout_uses_auc_and_brier_on_the_same_events():
    frame = _forecast_fixture()
    frame["rise_in_four"] = frame.group2_pct.gt(0).astype(float)
    predictors = {"npl_only": ("npl_pct",), "npl_group2": ("npl_pct", "group2_pct")}
    result = compare_forecasts(frame, "rise_in_four", 4, predictors, reps=59)
    assert result["last_training_origin"] == "2023Q4"
    assert result["last_training_label"] == "2024Q4"
    assert result["fits"]["npl_group2"]["auc"]["estimate"] > result["fits"]["npl_only"]["auc"]["estimate"]
    assert result["fits"]["npl_group2"]["brier"]["estimate"] < result["fits"]["npl_only"]["brier"]["estimate"]
    assert result["gains_vs_npl"]["npl_group2"]["brier"]["ci95"][0] > 0


def test_full_predictors_omit_the_constructed_broad_problem_ratio():
    assert "broad_problem_pct" not in SPECIFICATIONS["full"]
    rng = np.random.default_rng(4)
    frame = pd.DataFrame({name: rng.normal(size=40) for name in SPECIFICATIONS["full"]})
    frame["broad_problem_pct"] = frame.npl_pct + frame.group2_pct
    assert _max_vif(frame, ("npl_pct", "group2_pct", "broad_problem_pct")) > 100
    assert _max_vif(frame, SPECIFICATIONS["npl_only"]) == 1
    assert _max_vif(frame, SPECIFICATIONS["full"]) < 5
