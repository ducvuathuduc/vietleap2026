"""Reviewer checks on seasonal contrasts, matched rebounds and multiplicity."""

import numpy as np
import pandas as pd
import pytest

from vlkit.npl.real_data import clean_quarters
from vlkit.npl.seasonal_review import (
    add_rebound_baseline, adjust_pvalues, loan_size_subgroups, policy_robustness, rebound_baselines,
    seasonal_hypotheses,
)


@pytest.fixture
def panel():
    rng = np.random.default_rng(37)
    periods = pd.period_range("2021Q1", "2026Q1", freq="Q")
    effect = {1: .4, 2: .1, 3: .2, 4: -.4}
    return pd.DataFrame([
        dict(bank_code=bank, period=str(period), quarter=period.quarter, year=period.year,
             quarter_id=period.year * 4 + period.quarter,
             d_npl_pct=effect[period.quarter] + offset / 100 + rng.normal(0, .08))
        for offset, bank in enumerate("ABCDEFGH") for period in periods
    ])


def test_directional_quarter_contrasts_and_joint_test(panel):
    tests = seasonal_hypotheses(panel)["tests"]
    expected = {"q4_below_zero": -.365, "q1_above_zero": .435,
                "q4_vs_q2_q3": -.55, "q4_vs_q1_q3": -.633}
    for key, value in expected.items():
        row = tests[key]
        assert row["coefficient"] == pytest.approx(value, abs=.04)
        assert row["ci95"][0] < row["coefficient"] < row["ci95"][1]
        assert row["clusters"] == 8 and row["p"] < .05 and row["wild_p"] < .05
    joint = tests["joint_quarters"]
    assert joint["df_num"] == 3 and joint["df_den"] == 7 and joint["p"] < .05 and joint["wild_p"] < .05
    assert set(joint["simultaneous_ci95"]) == {"Q2", "Q3", "Q4"}


def test_rebound_signs_use_published_precision_before_display_rounding():
    vendor = pd.DataFrame({"ticker": ["A"] * 3, "period": ["2024Q3", "2024Q4", "2025Q1"],
                           "npl": [.01230, .01229, .01231]})
    precise, _ = clean_quarters(vendor, round_digits=None)
    rates = rebound_baselines(precise)
    assert rates["q4_fell"]["n"] == rates["q4_fell"]["rises"] == 1
    assert rates["q4_not_fell"]["n"] == 0


def test_rebound_pairs_compare_falls_and_nonfalls_and_never_cross_gaps(panel):
    changed = panel.copy()
    changed.loc[changed.bank_code.isin(["A", "B"]) & changed.quarter.eq(4), "d_npl_pct"] = 0.
    changed.loc[changed.bank_code.eq("A") & changed.period.eq("2025Q1"), "d_npl_pct"] = -.1
    changed.loc[changed.bank_code.eq("C") & changed.period.eq("2025Q3"), "d_npl_pct"] = -.2
    changed = changed.loc[~(changed.bank_code.eq("A") & changed.period.eq("2026Q1"))]
    block = rebound_baselines(changed)
    assert block["q4_fell"]["n"] == 30
    assert block["q4_not_fell"]["n"] == 9
    assert block["q4_fell"]["rises"] == 30
    assert block["q4_not_fell"]["rises"] == 8
    assert block["other_quarter_fell"]["n"] >= 1
    assert block["q4_large_fall"]["n"] + block["q4_small_fall"]["n"] == 30

    rule = {"q4_backtest": {"within_normal_season": {}}, "q4_oos": {
        "scored_period": "2025Q4", "within_normal_season": {"n": 6, "reversals": 6},
    }}
    decisions = changed.assign(adjusted_change_pp=0., status="within_normal_season", unusual=False)
    add_rebound_baseline(rule, changed, decisions, block)
    full = rule["q4_backtest"]["within_normal_season"]
    assert full["q1_rises"] == 38 and full["baseline_q1_rise_pct"] == pytest.approx(100 * 38 / 39)
    assert rule["q4_oos"]["within_normal_season"]["q1_rises"] == 6
    assert rule["q4_oos"]["q1_rise_baseline"]["n"] == 7


def test_loan_split_and_quarter_end_policy_dates(panel):
    sizes = pd.DataFrame({"bank_code": list("ABCDEFGH"), "customer_loans": range(10, 90, 10)})
    groups = loan_size_subgroups(panel, sizes)
    assert groups["median_customer_loans_bn"] == 45
    assert groups["small"]["clusters"] == groups["large"]["clusters"] == 4
    assert groups["large"]["terms"]["Q4"]["wild_p"] is not None
    register = pd.DataFrame([
        {"ref": "14/2021/TT-NHNN", "effective_from": "2021-09-17", "effective_to": "2023-05-24", "url": "https://example.test/14"},
        {"ref": "02/2023/TT-NHNN", "effective_from": "2023-05-24", "effective_to": "2024-07-01", "url": "https://example.test/02"},
        {"ref": "06/2024/TT-NHNN", "effective_from": "2024-07-01", "effective_to": "2024-12-31", "url": "https://example.test/06"},
    ])
    policy = policy_robustness(panel, register)
    flags = policy["quarter_regime"]
    assert [flags[p] for p in ("2021Q2", "2021Q3", "2022Q2", "2022Q3", "2023Q1", "2023Q2", "2024Q4", "2025Q1")] == [
        False, True, True, False, False, True, True, False,
    ]
    assert policy["drop_2024"]["n"] == len(panel) - 32
    assert policy["interaction"]["inside"]["ci95"] and policy["interaction"]["difference"]["wild_p"] is not None


def test_bh_collects_numeric_inference_in_nested_model_paths():
    result = adjust_pvalues({"M2": {"h1": {"p": .02, "wild_p": .04}},
                             "M6": {"placebos": [{"empirical_p": .025}, {"p": None}]},
                             "M8": {"dm": {"p": .1}}, "M1": {"p": .01}})
    rows = {row["test_id"]: row for row in result["rows"]}
    assert list(rows) == ["M2.h1", "M6.placebos[0].empirical", "M8.dm"]
    assert rows["M2.h1"]["raw_p"] == .02 and rows["M2.h1"]["wild_p"] == .04
    assert rows["M2.h1"]["bh_adjusted"] == pytest.approx(4 * .04 / 3)
    assert rows["M2.h1"]["raw_p_bh_adjusted"] == pytest.approx(.05)
    assert rows["M6.placebos[0].empirical"]["bh_adjusted"] == pytest.approx(.05)
    assert rows["M8.dm"]["bh_adjusted"] == pytest.approx(.1)
