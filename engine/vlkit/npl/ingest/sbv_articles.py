"""Read the SBV monthly credit and deposit articles the NPL context series uses."""
import json
import re

from ...vn import ascii_key


def _number(text, *, integral=False):
    value = re.sub(r"\s*\(\*\)$", "", text.strip()).replace(" ", "").rstrip("%*")
    if value in {"", "-", "–", "—"}:
        return None
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif integral:
        value = value.replace(".", "")
    return float(value)


def _field_value(value):
    if isinstance(value, list):
        return _field_value(value[0]) if value else None
    if isinstance(value, dict):
        for key in ("content", "value", "name", "data", "vi_VN"):
            if (nested := _field_value(value.get(key))) not in (None, ""):
                return nested
        return None
    return value


def _monthly_number(value, *, amount=False):
    if isinstance(value, (int, float)) or value is None:
        return value
    value = "".join(str(value).split()).rstrip("%")
    if not value or value in {"-", "–", "—"}:
        return None
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    if "," in value and "." in value and value.rindex(".") > value.rindex(","):
        return float(value.replace(",", ""))
    thousands = amount and bool(re.fullmatch(r"-?\d{1,3}(\.\d{3})+", value))
    return _number(value, integral=thousands)


def parse_monthly(content, series):
    body = json.loads(content)
    articles = body["articles"]
    matches = {}
    credit = series == "sbv_credit"
    for article in articles:
        if str(article.get("status", 0)) not in {"0", "approved", "published"}:
            continue
        fields = article.get("fields") or {}
        fields = {key: _field_value(value) for key, value in fields.items()}
        date_field = "Date62813077" if credit else "Date00760329"
        observed = str(article.get(date_field) or fields.get(date_field) or "")[:10]
        title = article.get("title") or ""
        if isinstance(title, dict):
            title = title.get("vi_VN", "")
        period = re.search(r"thang\s*(\d{1,2})\s*(?:(?:nam\s*)?(20\d{2}))?", ascii_key(title))
        year = period[2] if period else None
        if period and 1 <= int(period[1]) <= 12 and (year or observed[:4].isdigit()):
            month = f"{year or observed[:4]}-{int(period[1]):02}"
        elif re.match(r"20\d{2}-\d{2}-\d{2}", observed):
            month = observed[:7]
        else:
            continue

        def value(key, *, amount=False):
            return _monthly_number(fields.get(key), amount=amount)

        try:
            if credit:
                total = value("soDuTongCong", amount=True)
                if total is None:
                    continue
                result = dict(credit_bn=total, credit_growth_ytd_pct=value("tocDoTangGiamTongCong"))
                agriculture, industry, construction, trade, transport, other = [
                    value(key, amount=True) for key in (
                        "soDuNongNghiep", "soDuCongNghiep", "soDuXayDung", "soDuHoatDongThuongMai",
                        "soDuVanTaiVaVienThong", "soDuCacHoatDongDichVuKhac",
                    )
                ]
                combined_industry = value("soDuCongNghiepVaXayDung", amount=True)
                combined_trade = value("soDuHoatDongThuongMaiVanTaiVaVienThong", amount=True)
                parts = [
                    agriculture, industry + construction if None not in (industry, construction) else combined_industry,
                    trade + transport if None not in (trade, transport) else combined_trade, other,
                ]
                if None not in parts:
                    result.update(total_bn=total, parts_bn=sum(parts))
            else:
                households = value("soDuTienGuiCuaDanCu", amount=True)
                if households is None:
                    continue
                result = dict(
                    household_deposits_bn=households, deposit_growth_ytd_pct=value("tocDoTangGiamTienGuiCuaDanCu"),
                    organization_deposits_bn=value("soDuTienGuiCuaCacTCKT", amount=True),
                    methodology_break=month >= "2025-10",
                )
        except ValueError:
            continue
        result.update(article_id=str(article.get("id") or article.get("articleId") or ""),
                      source_date_field=observed or None)
        rank = (observed.startswith(month), str(article.get("dateModified") or article.get("modifiedDate") or ""),
                float(article.get("version") or 0), result["article_id"])
        if month not in matches or rank > matches[month][0]:
            matches[month] = (rank, dict(month=month, **result))
    return [result for _, result in sorted(matches.values(), key=lambda item: item[1]["month"])]
