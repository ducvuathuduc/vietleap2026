"""Golden rule values on small, already conformed facts."""
import json

import pandas as pd
import pytest


def evaluate(frames, catalog=()):
    from vlkit.monitor.rules import evaluate as run

    evaluation = run(frames, list(catalog))
    json.dumps(evaluation, allow_nan=False)
    return evaluation


def observation(indicator, period, value, measure="level", unit="%", geo="VNM", geo_type="country", source="nso"):
    return {
        "indicator_id": indicator, "period": period, "value": value, "measure_type": measure,
        "unit": unit, "geo": geo, "geo_type": geo_type, "source_id": source,
    }


def outcome(evaluation, rule):
    return next(row for row in evaluation["results"] if row["id"] == rule)


def test_budget_execution_uses_same_month_and_flags_pace_gap():
    rows = [
        observation("nsnn_thu_pct_plan", "2026-09", 82, "pct_plan"),
        observation("nsnn_chi_pct_plan", "2026-09", 60.5, "pct_plan"),
        observation("nsnn_thu_pct_plan", "2026-10", 90, "pct_plan"),
    ]
    rule = outcome(evaluate({"observations": pd.DataFrame(rows)}), "BR-PF1")
    assert (rule["value"], rule["status"], rule["period"], rule["source_id"]) == (21.5, "fired", "2026-09", "nso")
    assert "21,5" in rule["sentence_vi"]


def test_public_investment_compares_pace_and_lists_units_below_mean():
    rows = [
        observation("dtc_giai_ngan_pct_plan", "2026-09", 55, "pct_plan"),
        observation("dtc_giai_ngan_pct_plan", "2026-09", 62, "pct_plan", geo="central", geo_type="central"),
        observation("dtc_giai_ngan_pct_plan", "2026-09", 52, "pct_plan", geo="local", geo_type="local"),
        observation("dtc_giai_ngan_pct_plan", "2026-09", 45, "pct_plan", geo="hue", geo_type="province"),
        observation("dtc_giai_ngan_pct_plan", "2026-09", 56, "pct_plan", geo="hanoi", geo_type="province"),
    ]
    evaluation = evaluate({"observations": pd.DataFrame(rows)})
    rule = outcome(evaluation, "BR-PF2")
    assert (rule["value"], rule["status"]) == (-20, "fired")
    assert rule["metrics"]["central_local_gap"] == 10
    assert evaluation["tables"]["public_finance"][0]["rows"] == [
        {"geo": "hue", "name": "hue", "kind": "Tỉnh, thành phố", "rate": 45.0, "gap": -10.0, "period": "2026-09"},
    ]


def test_fdi_realisation_and_growth_compare_aligned_ytd_values():
    rows = [
        observation("fdi_dang_ky_ytd", "2026-09", 400, "ytd", "triệu USD"),
        observation("fdi_thuc_hien_ytd", "2026-09", 260, "ytd", "triệu USD"),
        observation("fdi_dang_ky_yoy", "2026-09", 45, "yoy"),
        observation("fdi_thuc_hien_yoy", "2026-09", 10, "yoy"),
    ]
    rule = outcome(evaluate({"observations": pd.DataFrame(rows)}), "BR-FDI1")
    assert (rule["value"], rule["status"], rule["metrics"]["yoy_gap"]) == (65, "fired", 35)


def test_fdi_concentration_uses_one_period_and_computes_both_hhi():
    rows = [
        observation("fdi_dang_ky_ytd", "2026-09", value, "ytd", "triệu USD", geo, geo_type)
        for geo, geo_type, value in [
            ("a", "province", 40), ("b", "province", 30), ("c", "province", 20), ("d", "province", 10),
            ("partner_a", "partner", 75), ("partner_b", "partner", 25),
        ]
    ]
    rule = outcome(evaluate({"observations": pd.DataFrame(rows)}), "BR-FDI2")
    assert rule["value"] == 90
    assert rule["metrics"] == {"province_hhi": pytest.approx(0.30), "partner_hhi": pytest.approx(0.625)}


def test_partner_only_covers_partner_hhi_without_inventing_a_province_statistic():
    rows = [
        observation("fdi_dang_ky_ytd", "2026-09", amount, "ytd", "triệu USD", geo, "partner")
        for geo, amount in [("partner_a", 75), ("partner_b", 25)]
    ]
    rule = outcome(evaluate({"observations": pd.DataFrame(rows)}), "BR-FDI2")
    assert rule["status"] == "evaluated"
    assert rule["value"] == pytest.approx(0.625)
    assert rule["metrics"]["province_hhi"] is None


def test_credit_deposit_gap_requires_comparable_ytd_growth():
    rows = [
        observation("credit_ytd", "2026-09", 9, "ytd", source="sbv"),
        observation("deposit_ytd", "2026-09", 7.5, "ytd", source="sbv"),
        observation("deposit_ytd", "2026-10", 8, "yoy", source="sbv"),
    ]
    rule = outcome(evaluate({"observations": pd.DataFrame(rows)}), "BR-BK1")
    assert (rule["value"], rule["status"], rule["period"]) == (1.5, "fired", "2026-09")


def test_bank_asset_quality_uses_verified_npl_and_same_quarter_coverage():
    bank = pd.DataFrame([
        {"ticker": "AAA", "period": "2026-Q2", "nim": 2, "pb": 1, "npl_proxy": 9, "coverage": 85},
        {"ticker": "BBB", "period": "2026-Q2", "nim": 3, "pb": 2, "npl_proxy": 6, "coverage": 85},
        {"ticker": "CCC", "period": "2026-Q2", "nim": 4, "pb": 3, "npl_proxy": 6, "coverage": 85},
    ])
    observations = pd.DataFrame([
        observation("bank_npl", "2026-Q2", 3.5, "ratio", "%", "AAA", "ticker", "tcbs"),
        observation("bank_coverage", "2026-Q2", 95, "ratio", "%", "AAA", "ticker", "tcbs"),
        observation("bank_group2", "2026-Q2", 4, "ratio", "%", "AAA", "bank", "tcbs"),
        observation("bank_npl", "2026-Q1", 6, "ratio", "%", "BBB", "bank", "tcbs"),
    ])
    evaluation = evaluate({"observations": observations, "bank": bank})
    rule = outcome(evaluation, "BR-BK2")
    assert (rule["value"], rule["status"], rule["source_id"]) == (3.5, "fired", "tcbs")
    league = {row["ticker"]: row for row in evaluation["tables"]["banking"][0]["rows"]}
    assert league["AAA"]["group2"] == 4
    assert [league[ticker]["nim_tier"] for ticker in ("AAA", "BBB", "CCC")] == [1, 2, 3]
    assert [league[ticker]["pb_tier"] for ticker in ("AAA", "BBB", "CCC")] == [1, 2, 3]
    assert league["BBB"]["npl"] is None and league["BBB"]["alert"] is None
    assert outcome(evaluate({"bank": bank}), "BR-BK2")["status"] == "not evaluated"


def test_banks_valuation_uses_only_its_own_history_and_keeps_roe():
    dates = pd.date_range("2020-10-01", "2025-10-01", freq="MS")
    rows = [
        {"ticker": ticker, "scope": "sector", "date": day, "pb": n if ticker == "BANKS_L2" else n + 100}
        for ticker in ("BANKS_L2", "OTHER_L2")
        for n, day in enumerate(dates, 1)
    ]
    rows[-1]["pb"] = 1
    rows[len(dates) - 1]["roe"] = 12.5
    evaluation = evaluate({"valuation": pd.DataFrame(rows)})
    rule = outcome(evaluation, "BR-BK3")
    assert (rule["value"], rule["metrics"]["roe"], rule["period"]) == (100, 12.5, "2025-10-01")
    assert {row["ticker"]: row["pb_pctile"] for row in evaluation["tables"]["banking"][0]["rows"]} == {
        "BANKS_L2": 100.0, "OTHER_L2": 0.0,
    }


def test_liquidity_breadth_and_drawdown_have_independent_denominators():
    dates = pd.bdate_range("2024-09-02", periods=290)
    market = pd.DataFrame({
        "date": dates, "trading_value": [10] * 270 + [30] * 20,
        "close": [100] * 289 + [90], "advancers": 60, "decliners": 30, "unchanged": 10,
    })
    evaluation = evaluate({"market": market})
    rule = outcome(evaluation, "BR-CM1")
    assert (rule["value"], rule["metrics"]["median_1y"], rule["metrics"]["pctile"], rule["metrics"]["breadth"]) == (
        30, 10, 100, 60,
    )
    derived = {row["indicator_id"]: row["value"] for row in evaluation["derived"] if row["period"] == rule["period"]}
    assert derived["vnindex_drawdown"] == pytest.approx(-10)


def test_index_pe_and_pb_percentiles_compare_vnindex_to_itself():
    dates = pd.date_range("2020-10-01", "2025-10-01", freq="MS")
    valuation = pd.DataFrame({
        "date": dates, "ticker": "VNINDEX", "scope": "index", "pe": [10] * 60 + [20],
        "pb": [3] * 60 + [2],
    })
    evaluation = evaluate({"valuation": valuation})
    latest = {row["indicator_id"]: row["value"] for row in evaluation["derived"] if row["period"] == "2025-10-01"}
    assert latest == {"vnindex_pe_pctile": 100, "vnindex_pb_pctile": 0}


def test_foreign_flows_sum_complete_windows_and_rank_sector_net_sell():
    dates = pd.bdate_range("2026-01-01", periods=60)
    market = pd.DataFrame({"date": dates, "foreign_net": [3] * 40 + [-4] * 20})
    foreign = pd.DataFrame([
        {"date": day, "icb_l2": sector, "foreign_net": amount}
        for day in dates
        for sector, amount in [("BANKS_L2", -3), ("REAL_ESTATE_L2", -1)]
    ])
    evaluation = evaluate({"market": market, "foreign": foreign})
    rule = outcome(evaluation, "BR-CM2")
    assert (rule["value"], rule["metrics"]["net_60d"], rule["metrics"]["streak"]) == (-80, 40, -20)
    assert evaluation["tables"]["capital_market"][0]["rows"][0]["icb_l2"] == "BANKS_L2"
    assert evaluation["tables"]["capital_market"][0]["rows"][0]["net_60d"] == -180


def test_leverage_diverges_from_average_trading_value_in_same_quarters():
    dates = pd.bdate_range("2026-01-01", "2026-06-30")
    market = pd.DataFrame({"date": dates, "trading_value": [100 if day.month < 4 else 80 for day in dates]})
    debt = pd.DataFrame([
        observation("margin_debt", "2026-Q1", 100, unit="tỷ đồng", source="press"),
        observation("margin_debt", "2026-Q2", 125, unit="tỷ đồng", source="press"),
    ])
    rule = outcome(evaluate({"market": market, "observations": debt}), "BR-CM3")
    assert (rule["value"], rule["status"], rule["metrics"]["liquidity_growth"]) == (25, "fired", pytest.approx(-20))


def test_real_estate_aligns_supply_absorption_and_mortgage_periods():
    rows = [
        observation("re_absorption", "2026-Q2", 120, unit="căn", source="press"),
        observation("re_new_supply", "2026-Q2", 200, unit="căn", source="press"),
        observation("mortgage_rate", "2026-Q1", 7, "ratio", source="press"),
        observation("mortgage_rate", "2026-Q2", 8.5, "ratio", source="press"),
        observation("mortgage_rate", "2026-Q3", 9, "ratio", source="press"),
    ]
    rule = outcome(evaluate({"observations": pd.DataFrame(rows)}), "BR-RE1")
    assert (rule["value"], rule["period"], rule["metrics"]["mortgage_gap"]) == (60, "2026-Q2", 1.5)
    assert "rổ" in rule["caveat_vi"].casefold()


def test_asean_rank_uses_latest_common_year_and_declared_direction():
    rows = [
        observation("tax_revenue_pct_gdp", period, value, "ratio", "%", geo, "country", "wdi")
        for geo, period, value in [
            ("VNM", "2024", 15), ("THA", "2024", 21), ("IDN", "2024", 9), ("MYS", "2024", 11),
            ("VNM", "2025", 60), ("THA", "2025", 50), ("BGD", "2024", 100),
        ]
    ]
    evaluation = evaluate({"observations": pd.DataFrame(rows)}, [{"id": "tax_revenue_pct_gdp", "higher_is_better": False}])
    compare = evaluation["asean"]["tax_revenue_pct_gdp"]
    assert (compare["year"], compare["vn_rank"], compare["n"], compare["median"]) == (2024, 3, 4, 13)
    assert outcome(evaluation, "BR-AS1")["value"] == 2


def test_province_uses_published_cut_points_as_well_as_observed_range():
    rows = [
        observation("earmarked_transfers", "2025", value, unit="tỷ đồng", geo=geo, geo_type="province", source="transfers")
        for geo, value in zip("abcde", [10, 20, 30, 40, 50])
    ]
    evaluation = evaluate({"observations": pd.DataFrame(rows)})
    province = evaluation["province"]
    assert [row["group"] for row in province["rows"]] == [1, 2, 3, 4, 5]
    assert province["groups"][0]["max"] == 18
    assert province["stats"]["earmarked_transfers"] == {"median": 30.0, "min": 10.0, "max": 50.0, "n": 5}
    assert outcome(evaluation, "BR-PV1")["value"] == 30


def test_heatmap_only_ranks_complete_calendar_windows_and_centers_ties():
    periods = pd.period_range("2025-01", periods=14, freq="M")
    rows = [
        observation("fdi_dang_ky_yoy", str(period), value, "yoy")
        for period, value in zip(periods, [2] * 12 + [None, 4])
    ]
    evaluation = evaluate({"observations": pd.DataFrame(rows)}, [
        {"id": "fdi_dang_ky_yoy", "sector": "fdi", "frequency": "monthly", "source_id": "nso"},
    ])
    cells = evaluation["heatmap"]["fdi"][0]["cells"]
    assert cells[11:] == [
        {"period": "2025-12", "value": 2.0, "pctile": 50.0},
        {"period": "2026-01", "value": None, "pctile": None},
        {"period": "2026-02", "value": 4.0, "pctile": None},
    ]
    assert outcome(evaluation, "HM1")["status"] == "evaluated"


def test_missing_inputs_are_explicit_and_yield_no_synthetic_values():
    evaluation = evaluate({})
    assert len(evaluation["rules"]) == len(evaluation["results"]) == 14
    assert all(result["status"] == "not evaluated" and "value" not in result for result in evaluation["results"])
    assert all(not rule["fired"] for rule in evaluation["rules"])
    assert not evaluation["derived"]


def test_flagged_input_never_enters_an_execution_alert():
    rows = [
        observation("nsnn_thu_pct_plan", "2026-09", 90, "pct_plan"),
        observation("nsnn_chi_pct_plan", "2026-09", 60, "pct_plan") | {"is_imputed": True},
    ]
    rule = outcome(evaluate({"observations": pd.DataFrame(rows)}), "BR-PF1")
    assert rule["status"] == "not evaluated"


def test_real_estate_aligns_city_supply_with_absorption_and_national_rate():
    rows = [
        observation("re_absorption", "2026-Q2", 120, unit="căn", geo="HÀ NỘI", geo_type="city", source="press"),
        observation("re_new_supply", "2026-Q2", 200, unit="căn", geo="HÀ NỘI", geo_type="city", source="press"),
        observation("mortgage_rate", "2026-Q2", 8.5, "ratio", source="press"),
    ]
    rule = outcome(evaluate({"observations": pd.DataFrame(rows)}), "BR-RE1")
    assert rule["value"] == 60
    assert "HÀ NỘI" in rule["sentence_vi"]
