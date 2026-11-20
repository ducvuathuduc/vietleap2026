"""Statutory disclosure calendar for listed banks' quarterly financial statements."""

import calendar
from datetime import date, timedelta

import pandas as pd

CIRCULAR = "Thông tư 96/2024/TT-BTC"
ARTICLE = "Điều 14"
PREDECESSOR, EFFECTIVE = "Thông tư 155/2015/TT-BTC", date(2024, 5, 13)
RULE = ("Công ty đại chúng, tổ chức niêm yết công bố báo cáo tài chính quý trong thời hạn 20 ngày "
        "kể từ ngày kết thúc quý (kế thừa Thông tư 155/2015/TT-BTC Điều 14)")
DAYS = 20


def quarter_end(year, quarter):
    month = quarter * 3
    return date(year, month, calendar.monthrange(year, month)[1])


def report_calendar(latest):
    rows = []
    for year in range(2021, latest.year + 1):
        for quarter in (1, 2, 3, 4):
            end = quarter_end(year, quarter)
            if end > latest:
                continue
            rows.append({
                "quarter": f"{year}Q{quarter}", "quarter_end": end.isoformat(),
                "disclosure_deadline": (end + timedelta(days=DAYS)).isoformat(),
                "days_after_quarter_end": DAYS,
                "circular": CIRCULAR if end >= EFFECTIVE else PREDECESSOR,
                "article": ARTICLE, "rule": RULE,
            })
    return pd.DataFrame(rows, columns=["quarter", "quarter_end", "disclosure_deadline",
                                       "days_after_quarter_end", "circular", "article", "rule"])
