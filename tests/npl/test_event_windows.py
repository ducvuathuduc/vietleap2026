import numpy as np
import pandas as pd
import pytest

from vlkit.npl.disclosure_dates import assess_last_modified
from vlkit.npl.event_windows import event_cars, placebo_dates, window_study, windows_overlap


def _market(dates, shock_at):
    rng = np.random.default_rng(4)
    index = rng.normal(0, 1, len(dates))
    stock = 0.2 + 1.1 * index
    stock[shock_at] += 5
    other = 0.1 + 0.8 * index
    frame = pd.DataFrame({
        "date": list(dates) * 3,
        "bank_code": ["VNINDEX"] * len(dates) + ["AAA"] * len(dates) + ["BBB"] * len(dates),
        "return_pct": np.r_[index, stock, other],
    })
    return frame


def test_estimation_window_does_not_overlap_any_reported_event_window():
    assert windows_overlap((-120, -21), (-1, 1)) is False
    assert windows_overlap((-120, -21), (-1, 5)) is False
    assert windows_overlap((-120, -21), (-10, 10)) is False
    assert windows_overlap((-30, -5), (-10, 10)) is True
    dates = pd.bdate_range("2022-01-03", periods=250)
    market = _market(dates, 180)
    anchors = pd.DataFrame({
        "bank_code": ["AAA", "BBB"], "event_date": [dates[180], dates[180]],
        "period": ["2023Q4", "2023Q4"], "quarter": [4, 4],
        "d_npl_pct": [-0.4, 0.3], "surprise_d_npl_pct": [-0.2, 0.2],
    })
    cars = event_cars(market, anchors, (-120, -21), (-1, 1))
    assert cars.loc[cars.bank_code.eq("AAA"), "car_pct"].item() == pytest.approx(5, abs=0.6)
    with pytest.raises(ValueError):
        event_cars(market, anchors, (-30, -5), (-10, 10))


def test_placebo_dates_never_equal_event_dates():
    dates = pd.bdate_range("2020-01-02", periods=300)
    market = _market(dates, 200)
    events = pd.DataFrame({
        "bank_code": ["AAA", "AAA", "BBB"],
        "event_date": [dates[200], dates[220], dates[210]],
    })
    picked = placebo_dates(market, events, draws=25, seed=20261120)
    assert len(picked) == 25 * 2
    overlap = picked.merge(events, on=["bank_code", "event_date"])
    assert overlap.empty
    study_events = events.assign(period="2024Q2", quarter=2, d_npl_pct=[-0.2, 0.1, -0.3],
                                 surprise_d_npl_pct=[-0.1, 0.1, -0.2], deadline=events.event_date,
                                 published_at=pd.NaT)
    result = window_study(market, study_events, draws=15, reps=40)
    assert result["estimation"] == [-120, -21]
    assert set(result["clocks"]["deadline"]["windows"]) == {"m1_p1", "m1_p5", "m10_p10"}
    assert result["clocks"]["actual"]["unavailable_reason"] == "no_valid_disclosure_dates"
    assert "2.8" in result["reading_en"] and result["reading_vi"]


def test_power_for_the_deadline_slope_ignores_the_actual_date_car():
    from vlkit.npl.event_windows import _legacy_power
    rows = []
    for bank in range(4):
        for step in range(6):
            rows.append({
                "bank_code": f"B{bank}", "car_pct": 40.0, "deadline_car_pct": step / 10,
                "expected_d_npl_pct": 0.1, "surprise_d_npl_pct": float(step),
            })
    frame = pd.DataFrame(rows)
    frame.loc[frame.index % 2 == 0, "deadline_car_pct"] = np.nan
    power = _legacy_power(frame, {"coefficient": -1.2, "se": 0.2, "p": 0.01, "wild_p": 0.264}, reps=30)
    assert power["n"] == 12
    assert power["wild_p"] == 0.264


def test_last_modified_inside_the_filing_window_is_kept_and_a_single_stamp_is_not():
    periods = ["2024Q1", "2024Q2", "2024Q3", "2024Q4"]
    ends = pd.PeriodIndex(periods, freq="Q").to_timestamp(how="end").normalize()
    calendar = pd.DataFrame({"period": periods, "deadline": ends + pd.Timedelta(days=30)})
    rows = []
    for bank in range(8):
        for period, end in zip(periods, ends):
            rows.append(dict(ticker=f"B{bank}", period=period,
                             published_at=end + pd.Timedelta(days=12 + bank),
                             url="https://example.test/a.pdf"))
    good = pd.DataFrame(rows)
    kept = assess_last_modified(good, calendar)
    assert kept["plausible"] is True
    assert kept["frame"]["valid"].all()
    bad = good.copy()
    bad["published_at"] = pd.Timestamp("2020-01-15")
    rejected = assess_last_modified(bad, calendar)
    assert rejected["plausible"] is False
    assert not rejected["frame"]["valid"].any()
