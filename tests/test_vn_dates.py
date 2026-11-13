"""Vietnamese date parsing: vlkit.vn.parse_dates (day-first, quarters)."""
import pandas as pd

from vlkit.vn import parse_dates


def test_day_first():
    out = parse_dates(pd.Series(["01/02/2023", "15/03/2023", "31/12/2022"]))
    assert list(out) == [pd.Timestamp(2023, 2, 1), pd.Timestamp(2023, 3, 15), pd.Timestamp(2022, 12, 31)]


def test_iso_not_day_first():
    out = parse_dates(pd.Series(["2023-02-01", "2023-03-15"]))
    assert list(out) == [pd.Timestamp(2023, 2, 1), pd.Timestamp(2023, 3, 15)]


def test_quarters_vn_and_en():
    out = parse_dates(pd.Series(["Q1 2021", "Quý 2/2023", "2024 Q4"]))
    assert list(out) == [pd.Timestamp(2021, 1, 1), pd.Timestamp(2023, 4, 1), pd.Timestamp(2024, 10, 1)]


def test_non_dates_return_none():
    assert parse_dates(pd.Series(["abc", "def", "ghi"])) is None
    assert parse_dates(pd.Series([], dtype=object)) is None


def test_mostly_bad_dates_rejected():
    assert parse_dates(pd.Series(["01/02/2023", "hello", "world", "foo", "bar"])) is None
