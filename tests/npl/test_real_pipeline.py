"""D2 panel, inference, event alignment and publication checks."""
import json

import duckdb
import numpy as np
import pandas as pd
import pytest

from vlkit.npl.pipeline import main
from vlkit.npl.real_data import clean_calendar, clean_quarters
from vlkit.npl.real_models import QUARTER_TERMS, _fit, _quarters, event_paths, linkage, seasonal_models


def test_cleaning_preserves_missing_and_breaks_nonconsecutive_changes():
    frame = pd.DataFrame({
        "ticker": [" BIDV ", "BID", "BID", "BID", "BID"],
        "period": ["2021Q1", "2021Q1", "2021Q3", "2021Q4", "2022Q1"],
        "npl_pct": [1.234, 1.234, 2.0, None, -.001],
        "coverage_pct": [100.235, 100.235, -.001, 120, 119],
    })
    panel, log = clean_quarters(frame)
    assert panel.bank_code.tolist() == ["BID"] * 4
    assert panel.ownership.eq("state").all()
    assert panel.npl_pct.iloc[0] == 1.23
    assert panel.npl_pct.isna().sum() == 2
    assert panel.d_npl_pct.isna().all()
    assert panel.coverage_pct.isna().sum() == 1
    assert len(log) == 7
    assert [(entry["before"], entry["after"]) for entry in log][2] == (5, 4)



def test_m5_screening_fits_quarterly_mechanisms_and_preserves_gaps(silver):
    panel, _ = clean_quarters(pd.read_parquet(silver / "bank_quarter.parquet"))
    rng = np.random.default_rng(23)
    amounts = panel[["bank_code", "period"]].copy()
    q4 = panel.quarter.eq(4)
    amounts["customer_loans"] = 1000 + rng.normal(0, 20, len(panel)) + 50 * q4
    amounts["group2_loans"] = 20 + rng.normal(0, 2, len(panel)) + 10 * q4
    amounts["groups345_loans"] = 15 + rng.normal(0, 1, len(panel))
    amounts["provision_balance"] = 10 + rng.normal(0, 1, len(panel)) + 3 * q4
    amounts["writeoffs"] = 3 + rng.normal(0, .3, len(panel)) + 2 * q4
    gap = amounts.bank_code.eq("VCB") & amounts.period.eq("2024Q3")
    fits = linkage(panel, amounts.loc[~gap])["screening_seasonal"]
    assert set(fits) == {"d_group2_ratio_pct", "d_broad_problem_ratio_pct", "loan_growth_qoq_pct",
                         "writeoff_ratio_pct", "d_provision_ratio_pct"}
    assert fits["d_group2_ratio_pct"]["n"] == len(panel) - 8 - 2
    for fit in fits.values():
        term = fit["terms"]["Q4"]
        assert fit["clusters"] == 8 and term["coefficient"] > 0
        assert term["ci95"] and term["p"] is not None and term["wild_p"] is not None
        assert fit["reading_vi"] and fit["reading_en"] and fit["what_this_does_not_show"]


def test_vendor_fractions_outliers_and_calendar_provenance():
    raw = pd.DataFrame({
        "ticker": ["VCB"] * 8,
        "period": pd.period_range("2021Q1", "2022Q4", freq="Q").astype(str),
        "npl": [.01234] * 7 + [.08],
        "coverage": [1.01235] * 8,
        "ldr": [.75] * 8,
        "roa": [.02] * 8,
        "nim": [.03] * 8,
        "loan_growth": [.1] * 8,
    })
    panel, _ = clean_quarters(raw)
    assert panel.npl_pct.tolist() == [1.23] * 7 + [8.]
    assert panel.npl_pct_iqr_flag.tolist() == [False] * 7 + [True]
    assert panel.coverage_pct.iloc[0] == 101.24
    assert panel.loan_growth_yoy_pct.iloc[0] == 10

    calendar = clean_calendar(pd.DataFrame({
        "quarter": ["2021Q1"], "quarter_end": ["2021-03-31"],
        "disclosure_deadline": ["2021-04-20"], "circular": ["Silver citation"],
    }))
    assert calendar.deadline.item() == pd.Timestamp("2021-04-30")
    assert calendar.silver_deadline.item() == pd.Timestamp("2021-04-20")
    assert calendar.silver_circular.item() == "Silver citation"

def test_market_model_uses_prior_window_and_full_event_window():
    dates = pd.bdate_range("2023-01-02", periods=300)
    rng = np.random.default_rng(52)
    index = rng.normal(0, 0.01, len(dates))
    stocks = 0.001 + 1.4 * index
    stocks[260] += 0.05
    market = pd.DataFrame({"date": list(dates) * 2, "bank_code": ["VNINDEX"] * 300 + ["AAA"] * 300,
                           "return_pct": np.r_[index, stocks] * 100})
    calendar = pd.DataFrame({"period": ["2023Q4", "2024Q1"],
                             "deadline": [dates[260], dates[-2]]})
    paths = event_paths(market, calendar)
    assert len(paths) == 21
    assert paths.period.unique().tolist() == ["2023Q4"]
    assert paths.loc[paths.day.eq(-1), "car_pct"].item() == pytest.approx(0)
    assert paths.car_pct.iloc[-1] == pytest.approx(5)


@pytest.fixture
def silver(tmp_path):
    rng = np.random.default_rng(1318)
    periods = pd.period_range("2021Q1", "2026Q3", freq="Q")
    tickers = ["BID", "CTG", "VCB", "TCB", "MBB", "ACB", "STB", "VPB"]
    quarters = []
    for index, ticker in enumerate(tickers):
        level = 1 + index / 4
        for period in periods:
            level += {1: .29, 2: .05, 3: .01, 4: -.35}[period.quarter] + rng.normal(0, .04)
            quarters.append(dict(ticker=ticker, period=str(period), basis="consolidated", npl_pct=level,
                                 coverage_pct=rng.normal(120, 8), ldr_pct=rng.normal(75, 4),
                                 roa_pct=rng.normal(1, .1), nim_pct=rng.normal(3, .15),
                                 loan_growth_yoy_pct=rng.normal(12, 2)))
    panel = pd.DataFrame(quarters)
    panel.to_parquet(tmp_path / "bank_quarter.parquet")
    panel[panel.period.str.endswith("Q4")].assign(
        period=lambda frame: frame.period.str[:4]
    ).to_parquet(tmp_path / "bank_annual.parquet")
    dates = pd.bdate_range("2019-01-01", "2026-11-19")
    prices = pd.DataFrame([dict(ticker=ticker, date=date, close=price)
                           for ticker in [*tickers, "VNINDEX"]
                           for date, price in zip(dates, 100 * np.exp(rng.normal(0, .008, len(dates)).cumsum()))])
    prices.to_parquet(tmp_path / "price_daily.parquet")
    daily = prices.loc[prices.ticker.eq("VCB"), ["ticker", "date"]]
    daily.assign(pe=8., pb=1.4).to_parquet(tmp_path / "valuation_daily.parquet")
    daily.assign(net_value=1.).to_parquet(tmp_path / "foreign_daily.parquet")
    ends = periods.to_timestamp(how="end").normalize()
    pd.DataFrame({"period": periods.astype(str), "quarter_end": ends,
                  "deadline": ends + pd.Timedelta(days=30)}).to_csv(tmp_path / "report_calendar.csv", index=False)
    return tmp_path


def test_bootstrap_repeats_and_detects_q4_drop(silver):
    panel, _ = clean_quarters(pd.read_parquet(silver / "bank_quarter.parquet"))
    first, fitted = seasonal_models(panel)
    second, _ = seasonal_models(panel)
    q4 = first["baseline"]["terms"]["Q4"]
    assert q4["coefficient"] < -0.5
    assert 0 < q4["wild_p"] < 0.05
    assert first["by_ownership"]["state"]["terms"]["Q4"]["wild_p"] > .15
    assert first["baseline"]["terms"] == second["baseline"]["terms"]
    assert fitted.notna().sum() == 8 * 22


def test_wild_bootstrap_counts_ties_with_three_clusters():
    rng = np.random.default_rng(0)
    panel = _quarters(pd.DataFrame({
        "bank_code": np.repeat(["VCB", "BID", "CTG"], 20),
        "quarter": np.tile(np.arange(1, 5), 15),
        "d_npl_pct": np.tile([.25, .01, .02, -.33], 15) + rng.normal(0, .1, 60),
    }))
    model, _ = _fit(panel, "d_npl_pct", QUARTER_TERMS, bank=True, bootstrap=True)
    # The two equal-sign draws reproduce the observed t statistic up to roundoff.
    assert model["terms"]["Q4"]["wild_p"] > .15


def test_real_cli_publishes_models_and_gold(silver):
    out = silver / "gold"
    main(["--real", str(silver), "--out", str(out)])
    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert set(results) == {f"M{i}" for i in range(1, 8)} | {"decoder"}
    assert all(results[f"M{i}"]["reading"] and results[f"M{i}"]["what_this_does_not_show"] for i in range(1, 8))
    assert len(results["decoder"]["rows"]) == 184
    assert len(results["decoder"]["focus"]) == 48
    assert results["decoder"]["regression"]["fiinquant"]["available"]["n"] == 176
    assert sum(row["n"] for row in results["M3"]["by_year"]) == 40
    assert results["M6"]["regressions"]["reported_or_deadline"]["n"] > 100
    assert results["M6"]["coverage"]["actual_date_n"] == 0
    assert results["M6"]["regressions"]["reported_or_deadline"] == results["M6"]["regressions"]["deadline_only"]
    assert results["M3"]["summary"]["mean_next_q1_change_pp"] > 0
    assert results["M3"]["summary"]["share_pct"] > 0
    assert "partial persistence" in results["M3"]["reading_en"]
    assert "decision_rule" in results["M7"]
    assert results["M7"]["decision_rule"]["q4_backtest"]["unusual"]["ci95"] is not None
    assert len(results["M1"]["findings"]) <= 6
    assert "notes_bank_quarter" in (out / "cleaning_log.md").read_text(encoding="utf-8")
    assert results["M7"]["backtest"]["n"] == 56
    assert results["M7"]["train_n"] == 8 * 15
    assert results["M7"]["backtest"]["mae_difference_vs"]["naive"]["ci95"][1] < 0
    assert results["M7"]["forecast_2026Q4"][0]["upper80"] > results["M7"]["forecast_2026Q4"][0]["lower80"]
    assert len(results["M7"]["forecast_2026Q4"]) == 8
    assert len(list(out.glob("*.png"))) == 4
    with duckdb.connect(str(out / "gold.duckdb"), read_only=True) as db:
        assert db.execute("select count(*) from fact_bank_quarter").fetchone() == (184,)
        assert db.execute("select count(*) from fact_report_event").fetchone() == (184,)
        assert db.execute("select count(*) from fact_bank_market_day where return_pct is not null").fetchone()[0] > 0
