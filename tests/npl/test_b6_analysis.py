import numpy as np
import pandas as pd
import pytest

from vlkit.npl.real_context import mechanism, policy_context
from vlkit.npl.real_models import decision_rule, market_study, seasonal_expectation
from test_real_pipeline import silver


def test_expected_change_excludes_its_own_bank_quarter():
    panel = pd.DataFrame({
        "bank_code": ["A"] * 8 + ["B"] * 8,
        "quarter": [1, 2, 3, 4] * 4,
        "d_npl_pct": [1., 2., 3., 4.] * 2 + [2., 3., 4., 5.] * 2,
    })
    panel.loc[3, "d_npl_pct"] = 104
    expected = seasonal_expectation(panel)
    assert expected.iloc[3] == pytest.approx(4.)
    assert expected.iloc[0] != pytest.approx(1.)


def test_market_uses_report_date_for_one_bank_and_runs_joint_deadline_fit(silver):
    from vlkit.npl.real_data import clean_calendar, clean_market, clean_quarters, read_silver

    tables = read_silver(silver)
    panel, _ = clean_quarters(tables["bank_quarter"])
    market = clean_market(tables, panel.bank_code.unique())
    calendar = clean_calendar(tables["report_calendar"].loc[lambda rows: rows.period.ne("2023Q4")])
    disclosure = pd.DataFrame({
        "ticker": ["BIDV", "BID", "CTG"],
        "period": ["2023Q4", "2023Q4", "2023Q4"],
        "published_at": ["2024-01-13", "2024-01-16", "2023-12-29"],
        "url": ["https://test.com/first", "https://test.com/later", "https://test.com/invalid"],
    })
    result, events = market_study(panel, market, calendar, disclosure)
    rows = events.set_index(["bank_code", "period"])
    assert rows.loc[("BID", "2023Q4"), "event_date"] == pd.Timestamp("2024-01-15")
    assert rows.loc[("BID", "2023Q4"), "deadline_event_date"] == pd.Timestamp("2024-01-30")
    assert rows.loc[("CTG", "2023Q4"), "anchor_source"] == "deadline"
    assert result["coverage"]["actual_date_n"] == 1
    assert result["regressions"]["actual_dates"]["n"] == 1
    for variant in ("reported_or_deadline", "deadline_only"):
        terms = result["regressions"][variant]["terms"]
        assert set(terms) == {"expected_d_npl_pct", "surprise_d_npl_pct"}
        assert all(term["ci95"] and 0 < term["wild_p"] <= 1 for term in terms.values())


def test_decision_backtest_is_prior_only_and_matches_the_next_q1():
    periods = pd.period_range("2021Q1", "2025Q1", freq="Q")
    panel = pd.DataFrame({
        "bank_code": ["A"] * len(periods),
        "period": periods.astype(str),
        "quarter": periods.quarter,
        "year": periods.year,
        "d_npl_pct": np.array([.4, 0., 0., -.4] * 4 + [.5]),
    })
    panel.loc[panel.period.eq("2024Q4"), "d_npl_pct"] = -2.4
    result, rows = decision_rule(panel)
    q4 = rows.loc[rows.period.eq("2024Q4")].iloc[0]
    assert q4.expected_change_pp == pytest.approx(-.4)
    assert q4.adjusted_change_pp == pytest.approx(-2.)
    assert q4.status == "improving" and q4.unusual
    assert result["q4_backtest"]["improving"]["reversals"] == 1
    assert result["q4_backtest"]["improving"]["ci95_wilson"] is not None
    assert result["q4_backtest"]["improving"]["ci95"] is None
    assert rows.loc[rows.period.eq("2021Q1"), "status"].item() == "unavailable"
    assert rows.loc[rows.period.eq("2023Q4"), "status"].item() == "within_normal_season"


def _oos_panel(contaminate_2025=False):
    periods = pd.period_range("2021Q1", "2024Q4", freq="Q")
    seasonal = {1: 0.5, 2: 0.0, 3: 0.0, 4: -0.5}
    rows = []
    for bank in "ABCD":
        for period in periods:
            rows.append(dict(bank_code=bank, period=str(period), quarter=int(period.quarter),
                             year=int(period.year), d_npl_pct=seasonal[period.quarter]))
    scored = {"A": -2.0, "B": -0.5, "C": 0.4, "D": -0.05}
    outcome = {"A": 1.0, "B": -0.2, "C": 0.5, "D": 0.3}
    for bank in "ABCD":
        for quarter in (1, 2, 3):
            value = 50.0 if contaminate_2025 and quarter == 2 else seasonal[quarter]
            rows.append(dict(bank_code=bank, period=f"2025Q{quarter}", quarter=quarter, year=2025, d_npl_pct=value))
        rows.append(dict(bank_code=bank, period="2025Q4", quarter=4, year=2025, d_npl_pct=scored[bank]))
        rows.append(dict(bank_code=bank, period="2026Q1", quarter=1, year=2026, d_npl_pct=outcome[bank]))
    return pd.DataFrame(rows)


def test_q4_oos_band_stops_at_2024q4_and_scores_only_2025q4_declines():
    clean = decision_rule(_oos_panel())[0]["q4_oos"]
    contaminated = decision_rule(_oos_panel(contaminate_2025=True))[0]["q4_oos"]
    assert clean["train_through"] == "2024Q4"
    assert clean["scored_period"] == "2025Q4"
    assert clean["outcome_period"] == "2026Q1"
    assert clean["improving"]["n"] == 1 and clean["improving"]["share_pct"] == 100
    assert clean["improving"]["ci95"] is None
    assert clean["within_normal_season"]["n"] == 1 and clean["within_normal_season"]["share_pct"] == 0
    assert clean["deteriorating"]["n"] == 1 and clean["deteriorating"]["reversals"] == 1
    assert clean["unusual"]["n"] == 2 and clean["unusual"]["share_pct"] == 100
    assert clean["unusual"]["ci95"] == pytest.approx([100, 100])
    assert clean["improving"]["n"] + clean["within_normal_season"]["n"] + clean["deteriorating"]["n"] == 3
    for label in ("improving", "deteriorating", "within_normal_season", "unusual"):
        assert contaminated[label]["n"] == clean[label]["n"]
        assert contaminated[label]["share_pct"] == clean[label]["share_pct"]
    assert "2024Q4" in clean["reading_vi"] and "2026Q1" in clean["reading_vi"]
    assert "2024Q4" in clean["reading_en"] and "2026Q1" in clean["reading_en"]


def test_mechanism_uses_contiguous_stocks_and_four_complete_writeoffs():
    fields = {"customer_loans": [100, 110, 120, 150, 150],
              "group2_loans": [5, 5, 6, 9, 8], "groups345_loans": [3, 4, 6, 5, 6],
              "writeoffs": [1, 2, 3, 6, 1]}
    periods = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q2"]
    notes = pd.DataFrame([
        dict(bank="BID", period=period, field=field, value_vnd_bn=value, basis="consolidated",
             grade="verified", page=5, source_url="https://test.com/notes.pdf")
        for field, values in fields.items() for period, value in zip(periods, values)
    ])
    notes.loc[len(notes)] = ["BID", "2024Q4", "writeoffs", 700, "consolidated", "contested", 5,
                             "https://test.com/notes.pdf"]
    result = mechanism(notes, None)
    rows = pd.DataFrame(result["quarterly"]).set_index("period")
    assert rows.loc["2024Q4", "npl_formation_bn"] == 5
    assert rows.loc["2024Q4", "group2_ratio_pct"] == 6
    assert rows.loc["2024Q4", "loan_growth_qoq_pct"] == pytest.approx(25.)
    assert pd.isna(rows.loc["2025Q2", "npl_formation_bn"])
    assert result["annual_writeoffs"][0]["q4_share_pct"] == 50
    assert result["coverage"]["banks"] == ["BID"]
    assert mechanism(None, None)["coverage"]["n"] == 0


def test_tcb_case_provision_use_is_not_a_quarterly_writeoff():
    case = pd.DataFrame([
        dict(quarter=period, metric=metric, value_bn_vnd=value, page=10,
             url=f"https://test.com/{period}.pdf")
        for period, loans, watch in [("2025Q3", 100, 5), ("2025Q4", 125, 10)]
        for metric, value in [("loans_customer_bn_vnd", loans), ("npl_group_2_watch", watch),
                              ("provision_used_writeoff_bn_vnd", -5)]
    ])
    result = mechanism(None, case)
    q4 = result["q4_windows"][-1]
    assert q4["bank_code"] == "TCB" and q4["period"] == "2025Q4"
    assert q4["group2_ratio_pct"] == 8
    assert q4["loan_growth_qoq_pct"] == 25
    assert pd.isna(q4["writeoffs"])
    assert result["annual_writeoffs"] == []


def test_context_uses_same_year_peers_and_estimates_q4_against_q1(silver):
    from vlkit.npl.real_data import clean_quarters

    panel, _ = clean_quarters(pd.read_parquet(silver / "bank_quarter.parquet"))
    wdi = pd.DataFrame({
        "iso3": ["VNM", "THA", "MYS", "THA", "USA"], "country": ["Viet Nam", "Thailand", "Malaysia", "Thailand", "US"],
        "year": [2022, 2022, 2022, 2023, 2022], "npl_to_gross_loans_pct": [2., 4., 2., 8., 50.],
    })
    legal = pd.DataFrame({"ref": ["06/2024/TT-NHNN", "03/2020/TT-NHNN"], "title": ["Gia hạn", "Sửa đổi"],
                          "effective_from": ["2024-07-01", "2020-05-17"], "effective_to": ["2024-12-31", "2023-05-24"],
                          "url": ["https://test.com/circular", "https://test.com/erroneous-circular"]})
    context = policy_context(panel, wdi, legal)
    row = context["wdi"]["by_year"][0]
    assert row["vietnam_npl_pct"] == 2 and row["asean_peer_median_pct"] == 3 and row["n_peers"] == 2
    assert len(context["wdi"]["observations"]) == 4
    first, extension = context["policy"]["timeline"]
    assert first["ref"] == "03/2021/TT-NHNN" and first["register_ref"] == "03/2020/TT-NHNN"
    assert extension["effective_from"] == "2024-06-18" and extension["restructuring_until"] == "2024-12-31"
    assert extension["register_effective_from"] == "2024-07-01"
    yearly = {row["year"]: row for row in context["policy"]["q4_by_year"]}
    assert yearly[2024]["terms"]["Q4"]["coefficient"] < -.5
    assert yearly[2024]["n"] == 16
    assert not yearly[2026]["terms"]
