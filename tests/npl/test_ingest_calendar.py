from datetime import date

from vlkit.npl.ingest.calendar import report_calendar


def test_calendar_deadline_is_20_days_after_quarter_end():
    frame = report_calendar(date(2021, 12, 31)).set_index("quarter")
    assert frame.loc["2021Q4", "quarter_end"] == "2021-12-31"
    assert frame.loc["2021Q4", "disclosure_deadline"] == "2022-01-20"


def test_calendar_cites_the_circular_in_force_at_each_quarter_end():
    frame = report_calendar(date(2026, 9, 30)).set_index("quarter")
    assert frame.loc["2021Q1", "circular"] == "Thông tư 155/2015/TT-BTC"
    assert frame.loc["2026Q3", "circular"] == "Thông tư 96/2024/TT-BTC"
    assert (frame["article"] == "Điều 14").all()
