"""Tests for Gap #3: time-gap detection and 3-period moving average (MA3)."""
import pandas as pd


def test_detect_time_gaps_monthly_quarterly_yearly():
    from vlkit.stats import detect_time_gaps

    m = detect_time_gaps(["2024-01", "2024-02", "2024-05", "2024-06"])
    assert m["count"] == 2
    assert m["samples"] == ["2024-03", "2024-04"]
    assert m["expected_periods"] == 6
    assert m["pct_missing"] == 33.3

    q = detect_time_gaps(["2024-Q1", "2024-Q2", "2024-Q4"], freq="Q")
    assert q["count"] == 1
    assert q["samples"] == ["2024-Q3"]

    y = detect_time_gaps(["2020", "2021", "2022"], freq="Y")
    assert y["count"] == 0


def test_moving_average_ma3_and_timeseries():
    from vlkit.stats import moving_average, time_series

    assert moving_average([10.0, 20.0, 30.0, 40.0], window=3) == [None, None, 20.0, 30.0]

    df = pd.DataFrame({
        "month": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-04-01", "2024-05-01"]),
        "cpi": [3.1, 3.3, 3.9, 4.1],
    })
    ts = time_series(df, "month", "cpi", agg="mean", freq="M")
    assert ts["gaps"]["count"] == 1
    assert ts["gaps"]["samples"] == ["2024-03"]
    assert ts["points"][0]["ma3"] is None
    assert ts["points"][2]["ma3"] is not None


def test_profile_emits_bilingual_time_gap_issue():
    from vlkit.profile import profile

    df = pd.DataFrame({
        "nam": [2020, 2021, 2024],
        "gdp": [100.0, 110.0, 130.0],
    })
    prof = profile(df, {"nam": "time", "gdp": "numeric"}, {}, {})
    gap_issues = [i for i in prof["issues"] if i["column"] == "nam"]
    assert gap_issues
    assert "missing time period" in gap_issues[0]["issue"]
    assert "thiếu" in gap_issues[0]["issue_vi"]
