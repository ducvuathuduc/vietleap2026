import numpy as np
import pandas as pd
import pytest

from vlkit.npl.market_model import (
    asof_rows,
    ceiling_note,
    monthly_asof_features,
    npl_band,
    publication_dates,
    walk_forward_predictions,
    walk_forward_splits,
)


@pytest.mark.parametrize(
    ("value", "band"),
    [
        (0.0, "lt1"),
        (0.99, "lt1"),
        (1.0, "b1_2"),
        (1.99, "b1_2"),
        (2.0, "b2_3"),
        (2.99, "b2_3"),
        (3.0, "ge3"),
        (3.5, "ge3"),
    ],
)
def test_band_edges(value, band):
    assert npl_band(value) == band


def test_asof_alignment_never_uses_a_quarter_before_its_deadline():
    calendar = pd.DataFrame({
        "period": ["2024Q3", "2024Q4"],
        "deadline": ["2024-10-21", "2025-01-20"],
    })
    sessions = pd.to_datetime([
        "2024-10-21", "2024-10-22", "2025-01-20", "2025-01-21", "2025-01-22",
    ])
    public = publication_dates(calendar, sessions)
    assert public.loc[public.period.eq("2024Q4"), "first_public_date"].iloc[0] == pd.Timestamp("2025-01-21")
    panel = pd.DataFrame({
        "bank_code": ["AAA", "AAA", "BBB", "BBB"],
        "period": ["2024Q3", "2024Q4", "2024Q3", "2024Q4"],
        "npl_pct": [1.1, 99.0, 1.4, 99.0],
        "coverage_lag": [50.0, 50.0, 40.0, 40.0],
        "loan_growth": [10.0, 10.0, 12.0, 12.0],
    })
    on_deadline = asof_rows(panel, public, "2025-01-20")
    assert set(on_deadline.period) == {"2024Q3"}
    assert on_deadline.npl_pct.max() < 3
    after = asof_rows(panel, public, "2025-01-21")
    assert set(after.period) == {"2024Q4"}

    features = monthly_asof_features(panel, public, [pd.Timestamp("2025-01-20")])
    assert features.loc[0, "median_npl"] == pytest.approx(1.25)
    assert features.loc[0, "share_ge3"] == 0
    assert (features["max_period"] < "2024Q4").all()


def test_url_encoding_is_not_cited_as_a_3_percent_ceiling():
    legal = pd.DataFrame({
        "ref": ["02/2013/TT-NHNN"],
        "title": ["Thông tư 02/2013/TT-NHNN"],
        "what_changes": ["mức trích lập 0/5/20/50/100% và nợ xấu = nhóm 3-5"],
        "url": ["https://example.test/tim-kiem.htm?keyword=02%2F2013%2FTT-NHNN"],
    })
    note = ceiling_note(legal)
    assert note["cited"] is False
    assert note["rows"] == []


def test_walk_forward_never_trains_on_the_forecast_month_or_later():
    months = [f"{year}-{month:02d}" for year in range(2021, 2026) for month in range(1, 13)]
    months = [month for month in months if "2021-02" <= month <= "2025-03"]
    splits = list(walk_forward_splits(months, train_start="2021-02", test_start="2025-01"))
    assert [month for month, _train in splits] == ["2025-01", "2025-02", "2025-03"]
    assert splits[0][1][0] == "2021-02"
    assert splits[0][1][-1] == "2024-12"
    for forecast, train in splits:
        assert forecast not in train
        assert all(month < forecast for month in train)

    rng = np.random.default_rng(0)
    frame = pd.DataFrame({
        "month": months,
        "ret": rng.normal(size=len(months)),
        "npl": rng.normal(size=len(months)),
        "lag_ret": rng.normal(size=len(months)),
    })
    out = walk_forward_predictions(frame, ["npl", "lag_ret"], train_start="2021-02", test_start="2025-01")
    assert list(out["month"]) == ["2025-01", "2025-02", "2025-03"]
    assert (out["train_max"] < out["month"]).all()
    assert out.loc[out.month.eq("2025-01"), "train_max"].item() == "2024-12"
    assert out.loc[out.month.eq("2025-02"), "train_max"].item() == "2025-01"
    assert out["predicted"].notna().all()
