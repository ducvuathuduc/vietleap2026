"""Vietnamese display labels for machine-readable monitor periods."""
import re

from .. import fmt


def period_vi(period: str, *, cumulative: bool = False) -> str:
    parts = str(period).split("-")
    if len(parts) == 3:
        year, month, day = parts
        return f"{day}/{month}/{year}"
    if len(parts) == 2:
        year, part = parts
        if part.startswith("Q"):
            return f"quý {('I', 'II', 'III', 'IV')[int(part[1:]) - 1]}/{year}"
        return f"{int(part)} tháng {year}" if cumulative else f"tháng {int(part)}/{year}"
    return f"năm {period}"


def localize_periods(text: str) -> str:
    return re.sub(
        r"(?:kỳ |quý |ngày )?(?<!\w)\d{4}-(?:Q[1-4]|\d{2}(?:-\d{2})?)(?!\w)",
        lambda match: period_vi(match.group().split()[-1]),
        text,
    )


def percentile_vi(value: float, years: int) -> str:
    if value < 2:
        return f"thuộc nhóm thấp nhất trong {years} năm"
    return f"ở phân vị {fmt.fixed(value, 0, lang='vi')}/100 so với {years} năm"


def decimal_vi(value: float, places: int = 1) -> str:
    whole, comma, fraction = fmt.fixed(abs(value), places, lang="vi").partition(",")
    return ("-" if value < 0 else "") + fmt.count(whole, lang="vi") + comma + fraction
