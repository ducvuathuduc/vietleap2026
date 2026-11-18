"""Unit tests for mentor cleaning rules: interpolate per ticker, dedupe keep='last', flag outliers never delete."""
from __future__ import annotations

import pandas as pd


def test_interpolate_per_ticker_does_not_leak_across_tickers():
    from vlkit.de.quality import to_silver

    df = pd.DataFrame({
        "ticker": ["FPT", "FPT", "FPT", "VNM", "VNM", "VNM"],
        "year": [2021, 2023, 2022, 2021, 2022, 2023],
        "revenue": [100.0, 300.0, None, 500.0, None, 900.0],
    })
    silver, _roles, log = to_silver(df, impute="interpolate", ticker_col="ticker", time_col="year")

    fpt_2022 = silver.loc[(silver["ticker"] == "FPT") & (silver["year"] == 2022), "revenue"].iloc[0]
    vnm_2022 = silver.loc[(silver["ticker"] == "VNM") & (silver["year"] == 2022), "revenue"].iloc[0]
    assert fpt_2022 == 200.0
    assert vnm_2022 == 700.0
    assert "revenue__imputed" in silver.columns
    assert int(silver["revenue__imputed"].sum()) == 2
    assert any("interpolated" in msg for msg in log)


def test_dedupe_keep_last_preserves_latest_record():
    from vlkit.de.quality import to_silver

    df = pd.DataFrame({
        "ticker": ["FPT", "FPT", "VNM"],
        "year": [2024, 2024, 2024],
        "close_price": [90.0, 105.0, 70.0],
    })
    silver, _roles, log = to_silver(df, key=["ticker", "year"], dedupe_keep="last")
    assert len(silver) == 2
    fpt_price = silver.loc[silver["ticker"] == "FPT", "close_price"].iloc[0]
    assert fpt_price == 105.0
    assert any("keep=last" in msg for msg in log)


def test_outliers_are_flagged_never_deleted():
    from vlkit.de.quality import to_silver

    vals = [10.0, 11.0, 12.0, 10.5, 11.5, 12.5, 10.2, 11.8, 12.1, 10.9, 9999.0]
    df = pd.DataFrame({"ticker": [f"T{i}" for i in range(len(vals))], "metric": vals})
    silver, roles, log = to_silver(df)
    assert len(silver) == len(vals)
    assert "_outlier_any" in silver.columns
    assert roles["_outlier_any"] == "flag"
    assert bool(silver.loc[silver["metric"] == 9999.0, "_outlier_any"].iloc[0]) is True
    assert any("kept, not deleted" in msg for msg in log)
