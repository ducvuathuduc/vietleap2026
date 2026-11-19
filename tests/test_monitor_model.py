import pandas as pd
import pytest

from vlkit.de.warehouse import Warehouse


@pytest.fixture
def warehouse(tmp_path):
    wh = Warehouse(tmp_path / "monitor.duckdb", tmp_path / "lake")
    yield wh
    wh.close()


def _land(wh, name, rows):
    frame = pd.DataFrame(rows).assign(
        _src="fiinquant", _run_id="landing", _row_hash=[str(i) for i in range(len(rows))]
    )
    wh.write("bronze", f"vm_fq_{name}", frame, parquet=False)


def _build(wh, rows=(), catalog=()):
    from vlkit.monitor.model import build_model

    return build_model(wh, pd.DataFrame(rows), list(catalog), [
        {"id": "fiinquant", "publisher": "FiinGroup", "method": "api"},
        {"id": "nso", "publisher": "Cục Thống kê", "method": "scrape"},
    ], "model-test")


def test_silver_keeps_bad_and_superseded_bars_and_gold_uses_latest(warehouse):
    template = dict(ticker="VCB", timestamp="2025-02-03 00:00", open=11, low=10,
                    high=13, close=12, volume=100, value=1200, fb=50, fs=30, fn=20)
    rows = [
        template | {"close": 11, "_ingested_at": "2025-02-03T18:00:00+07:00"},
        template | {"_ingested_at": "2025-02-04T08:00:00+07:00"},
        template | {"timestamp": "2025-02-04 00:00", "low": 14, "fn": 25},
        template | {"timestamp": "not a date", "volume": "unavailable"},
    ]
    _land(warehouse, "bars", rows)
    result = _build(warehouse)

    assert warehouse.con.execute("SELECT count(*) FROM silver.vm_fq_bars").fetchone() == (4,)
    assert warehouse.con.execute("""
        SELECT dq_flags FROM silver.vm_fq_bars ORDER BY _row_hash
    """).fetchall() == [
        (["duplicate"],), ([],), (["ohlc_bounds", "foreign_balance"],),
        (["type_error", "missing"],),
    ]
    assert warehouse.con.execute("""
        SELECT close, fn, price_basis FROM gold.fact_security_daily ORDER BY date
    """).fetchall() == [(12.0, 20.0, "adjusted"), (12.0, 25.0, "adjusted")]
    quality = next(row for row in result["quality"] if row["source_id"] == "fiinquant")
    assert quality["rows"] == 4
    assert quality["flags"]["ohlc_bounds"] == 1
    profile = next(row for row in result["profiles"] if row["table"] == "silver.vm_fq_bars")
    assert profile["missing"]["date"] == 1
    assert profile["duplicates"] == 1


def test_indicator_units_imputation_geographies_and_idempotency(warehouse):
    rows = [
        {"period": "2025-01", "value": 1, "unit": "nghìn tỷ đồng"},
        {"period": "2025-02", "value": None, "unit": "tỷ đồng"},
        {"period": "2025-03", "value": 3000, "unit": "tỷ đồng"},
        {"period": "2025-05", "value": 2900, "unit": "tỷ đồng"},
        {"period": "2025-01", "value": 500, "unit": "tỷ đồng",
         "geo_type": "province", "geo": "ha_noi"},
        {"period": "2025-02", "value": None, "unit": "tỷ đồng",
         "geo_type": "province", "geo": "ha_noi"},
        {"period": "2026-01", "value": 800, "unit": "tỷ đồng"},
    ]
    defaults = dict(indicator_id="nsnn_thu_ytd", geo_type="national", geo="",
                    measure_type="ytd", source_id="nso", run_id="upstream")
    observations = [defaults | row for row in rows]
    catalog = [dict(id="nsnn_thu_ytd", sector="public_finance", name_vi="Thu ngân sách",
                    frequency="monthly", measure_type="ytd", unit="tỷ đồng", source_id="nso")]
    before = _build(warehouse, observations, catalog)
    after = _build(warehouse, observations, catalog)

    assert before["tables"] == after["tables"]
    assert warehouse.con.execute("""
        SELECT period, value, is_imputed, dq_flags FROM gold.fact_indicator
        WHERE geo_type='national' ORDER BY period
    """).fetchall() == [
        ("2025-01", 1000.0, False, ["unit_normalized"]),
        ("2025-02", pytest.approx(2050.8474576271187), True, ["missing", "imputed"]),
        ("2025-03", 3000.0, False, []),
        ("2025-05", 2900.0, False, ["ytd_decrease"]),
        ("2026-01", 800.0, False, []),
    ]
    assert warehouse.con.execute("""
        SELECT f.value, g.name_vi, g.region FROM gold.fact_indicator f
        JOIN gold.dim_geo g USING (geo_key) WHERE f.period='2025-02' AND f.geo_type='province'
    """).fetchone() == (None, "Hà Nội", "Đồng bằng sông Hồng")
    assert warehouse.con.execute("SELECT count(*) FROM gold.dim_geo WHERE geo_type='province'").fetchone() == (34,)
    assert warehouse.con.execute("""
        SELECT count(*) FROM meta.lineage
        WHERE from_node='silver.vm_observations' AND to_node='gold.fact_indicator'
    """).fetchone() == (1,)
    profile = next(row for row in after["profiles"] if row["source_id"] == "nso")
    assert profile["time_gap_count"] == 8


def test_breadth_uses_consecutive_hose_sessions_and_preserves_vendor_snapshot(warehouse):
    _land(warehouse, "roster", [
        {"ticker": "VCB", "exchangeCode": "HOSE", "snapshot_date": "2025-02-04",
         "organizationName": "Vietcombank", "icbNameL2": "BANKS_L2"},
        {"ticker": "ACB", "exchangeCode": "HOSE", "snapshot_date": "2025-02-04",
         "organizationName": "Á Châu", "icbNameL2": "BANKS_L2"},
        {"ticker": "SHS", "exchangeCode": "HNX", "snapshot_date": "2025-02-04"},
    ])
    _land(warehouse, "bars", [
        dict(ticker=ticker, timestamp=f"2025-02-0{day}", open=price, low=price,
             high=price, close=price, volume=100, value=100 * price)
        for ticker, quotes in {
            "VNINDEX": [(3, 1000), (4, 1020), (5, 1050)],
            "VCB": [(3, 100), (4, 101), (5, 102)],
            "ACB": [(3, 25), (5, 27)],
            "SHS": [(3, 20), (4, 22), (5, 24)],
        }.items()
        for day, price in quotes
    ])
    _land(warehouse, "breadth", [
        dict(comGroupCode="VNINDEX", tradingDate="2025-02-05", kind="summary",
             totalStockUpPrice=2, totalStockDownPrice=3, totalStockNoChangePrice=4),
    ])
    result = _build(warehouse)

    assert warehouse.con.execute("""
        SELECT date::VARCHAR, advancers, decliners, unchanged, vendor_advancers
        FROM gold.fact_market_breadth_daily ORDER BY date
    """).fetchall() == [("2025-02-04", 1, 0, 0, None), ("2025-02-05", 1, 0, 0, 2)]
    assert warehouse.con.execute("""
        SELECT is_trading_day FROM gold.dim_date WHERE date = DATE '2025-02-04'
    """).fetchone() == (True,)
    assert "gold.v_capital_market_daily" in result["views"]


def test_bank_ratios_convert_vendor_fractions_and_absent_sources_build_empty_gold(warehouse):
    _land(warehouse, "bank_ratios", [{
        "ticker": "BID", "year": 2025, "quarter": 1,
        "ratios.AssetQualityComponent.ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans": .018,
        "ratios.AssetQualityComponent.LoanLossReservesToNPLs": 1.2,
        "ratios.LiquidityAndAssetsComponent.LDRPercentage": .85,
        "ratios.ProfitabilityComponent.NIM": .0225,
        "ratios.ValuationRatios.PriceToBook": 1.75,
    }])
    _build(warehouse)

    assert warehouse.con.execute("""
        SELECT ticker, period, nim, pb, npl_proxy, coverage, ldr FROM gold.fact_bank_ratio_quarter
    """).fetchone() == ("BID", "2025-Q1", 2.25, 1.75, pytest.approx(1.8), 120, 85)
    assert warehouse.con.execute("SELECT count(*) FROM gold.fact_valuation_daily").fetchone() == (0,)
    assert warehouse.con.execute("SELECT count(*) FROM gold.fact_indicator").fetchone() == (0,)


def test_transfers_sum_distinct_pre_merger_provinces_after_latest_revision(warehouse):
    defaults = dict(indicator_id="transfer", period="2024", unit="triệu đồng",
                    geo_type="province", measure_type="level", source_id="transfers")
    observations = [
        defaults | dict(geo="HÀ GIANG", value=4000, published_date="2025-01-01"),
        defaults | dict(geo="Hà Giang", value=5000, published_date="2025-01-02"),
        defaults | dict(geo="Tuyên Quang", value=6000, published_date="2025-01-01"),
    ]
    catalog = [dict(id="transfer", sector="province", unit="tỷ đồng",
                    frequency="annual", measure_type="level", source_id="transfers")]
    _build(warehouse, observations, catalog)

    assert warehouse.con.execute("SELECT count(*) FROM silver.vm_observations").fetchone() == (3,)
    assert warehouse.con.execute("""
        SELECT geo, value, constituent_count, dq_flags FROM gold.fact_indicator
    """).fetchall() == [("tuyen_quang", 11, 2, ["category_normalized", "unit_normalized"])]


def test_business_validation_checks_components_and_keeps_over_plan_values(warehouse):
    defaults = dict(period="2025-08", geo="", geo_type="national", source_id="nso")
    measures = {
        "fdi_dang_ky_ytd": (35, "triệu USD", "ytd"),
        "fdi_cap_moi_ytd": (10, "triệu USD", "ytd"),
        "fdi_dieu_chinh_ytd": (10, "triệu USD", "ytd"),
        "fdi_gop_von_ytd": (10, "triệu USD", "ytd"),
        "execution_pct_plan": (115, "%", "pct_plan"),
        "invalid_share": (105, "%", "share"),
    }
    observations = [defaults | dict(indicator_id=key, value=value, unit=unit, measure_type=measure)
                    for key, (value, unit, measure) in measures.items()]
    catalog = [dict(id=key, unit=unit, measure_type=measure, frequency="monthly")
               for key, (_, unit, measure) in measures.items()]
    _build(warehouse, observations, catalog)

    assert warehouse.con.execute("""
        SELECT indicator_id, dq_flags FROM gold.fact_indicator WHERE len(dq_flags) > 0
        ORDER BY indicator_id
    """).fetchall() == [("fdi_dang_ky_ytd", ["parts_balance"]), ("invalid_share", ["share_range"])]


def test_bank_view_distinguishes_reported_npl_from_vendor_proxy(warehouse):
    _land(warehouse, "bank_ratios", [{
        "ticker": "BID", "year": 2025, "quarter": 1,
        "ratios.AssetQualityComponent.ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans": .018,
    }])
    observations = [{
        "indicator_id": "bank_npl", "period": "2025-Q1", "value": 2.5, "unit": "%",
        "geo": "bid", "geo_type": "ticker", "source_id": "tcbs", "measure_type": "ratio",
    }]
    catalog = [dict(id="bank_npl", sector="banking", frequency="quarterly", unit="%",
                    source_id="tcbs", measure_type="ratio")]
    _build(warehouse, observations, catalog)

    assert warehouse.con.execute("""
        SELECT ticker, npl_proxy, bank_npl, npl_source_id FROM gold.v_bank_health_quarter
    """).fetchall() == [("BID", pytest.approx(1.8), 2.5, "tcbs")]


def test_iqr_outlier_stays_in_gold_during_flat_baseline(warehouse):
    observations = [
        dict(indicator_id="level", period=f"2025-{n:02}", value=90 if n == 8 else 10,
             unit="tỷ đồng", geo="", geo_type="national", source_id="nso", measure_type="level")
        for n in range(1, 9)
    ]
    catalog = [dict(id="level", sector="macro", frequency="monthly", unit="tỷ đồng",
                    measure_type="level", source_id="nso")]
    result = _build(warehouse, observations, catalog)

    assert warehouse.con.execute("""
        SELECT period, value, is_invalid FROM gold.fact_indicator WHERE is_outlier
    """).fetchall() == [("2025-08", 90, False)]
    assert result["profiles"][0]["outliers"] == 1


def test_unverified_evidence_stays_in_silver_and_cannot_supersede_verified_data(warehouse):
    common = dict(indicator_id="bank_npl", period="2026-Q3", geo="ACB", geo_type="ticker",
                  unit="%", measure_type="ratio", source_id="nso")
    _build(warehouse, [
        dict(common, value=3, published_date="2026-10-01", evidence_ok=True),
        dict(common, value=5, published_date="2026-10-02", evidence_ok=False),
        dict(common, geo="VCB", value=6, published_date="2026-10-02", evidence_ok=False),
    ])
    silver = warehouse.read("silver.vm_observations")
    assert len(silver) == 3
    assert silver.loc[silver.value.eq(5), "dq_flags"].iloc[0].tolist() == ["duplicate", "unverified_evidence"]
    gold = warehouse.read("gold.fact_indicator").set_index("geo")
    assert gold.loc["ACB", "value"] == 3
    assert gold.loc["VCB", "is_invalid"]
