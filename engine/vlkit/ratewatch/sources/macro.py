"""Parse the SBV releases and the NSO CPI index."""
import json
import re
from datetime import date
from urllib.parse import urljoin, urlsplit, quote

from lxml import html

from ...vn import ascii_key

SBV = "https://sbv.gov.vn"
NSO = "https://www.nso.gov.vn/cpi-vi/"
DATE = r"(\d{1,2})(?:[/.-]|\s+tháng\s+)(\d{1,2})(?:[/.-]|\s+năm\s+)(20\d{2})"
CPI_PERIOD = re.compile(r"Kỳ tham chiếu\s*:?\s*(?:tháng\s+)?(1[0-2]|0?[1-9])/(20\d{2})", re.I)
TENORS = {"qua dem", "1 tuan", "2 tuan", "1 thang", "3 thang", "6 thang", "9 thang"}


def _dom(content):
    return html.fromstring(content.decode("utf-8-sig"))


def _text(element):
    return " ".join(element.text_content().split())


def _number(text, *, integral=False):
    value = re.sub(r"\s*\(\*\)$", "", text.strip()).replace(" ", "").rstrip("%*")
    if value in {"", "-", "–", "—"}:
        return None
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif integral:
        value = value.replace(".", "")
    return float(value)


def _iso_date(match):
    day, month, year = map(int, match.groups())
    return date(year, month, day).isoformat()


def _table_rows(content, header):
    root = _dom(content)
    for table in root.xpath("//table"):
        entries = []
        for row in table.xpath(".//tr"):
            cells = [_text(cell) for cell in row.xpath("./td|./th")]
            if cells:
                entries.append(cells)
        if any(header(ascii_key(cells[0])) for cells in entries):
            date_elements = table.xpath(
                "ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' ls01-wrap ')][1]"
                "/div[contains(concat(' ', normalize-space(@class), ' '), ' ls01-date ')]"
            )
            captions = [_text(element) for element in date_elements or table.xpath(
                "./caption|preceding::*[self::h2 or self::h3 or self::p or self::strong]"
            )]
            leading = [" ".join(row) for row in entries if not any("tham chiếu" in cell.lower() for cell in row)]
            dates = [match for text in reversed(captions) if (match := re.search(DATE, text))]
            dates = [match for text in leading if (match := re.search(DATE, text))] + dates
            if not dates:
                raise ValueError("Bảng NHNN thiếu ngày quan sát")
            return _iso_date(dates[0]), entries
    return None, []


def parse_interbank(content):
    day, entries = _table_rows(content, lambda title: title.rstrip("*").strip() in TENORS)
    rows = []
    references = [match for cells in entries for cell in cells
                  if "tham chiếu" in cell.lower() and (match := re.search(DATE, cell))]
    for cells in entries:
        tenor = ascii_key(cells[0]).strip()
        if tenor not in TENORS or len(cells) < 3:
            continue
        rate, volume = _number(cells[1]), _number(cells[2], integral=True)
        if rate is not None and ("*" not in cells[1] or len(references) == 1):
            row_day = _iso_date(references[0]) if "*" in cells[1] else day
            rows.append(dict(date=row_day, tenor=cells[0].strip(" *"), rate_pct=rate, volume_bn=volume))
    return rows


def parse_omo(content):
    def operation(title):
        return title.startswith(("mua ky han", "ban ky han", "ban han", "phat hanh tin phieu"))

    day, entries = _table_rows(content, operation)
    rows = []
    totals = []
    current_operation = None
    for cells in entries:
        title = ascii_key(cells[0])
        if title.startswith(("tong", "cong")) and len(cells) >= 3:
            total = _number(cells[-2], integral=True)
            if total is not None:
                totals.append(total)
        if operation(title):
            current_operation = cells[0]
        if len(cells) >= 6 and operation(title):
            match = re.fullmatch(r"(\d+)(?:\s*ngày)?", cells[1], re.I)
        else:
            match = re.fullmatch(r"ky han (\d+) ngay", title)
        if match and current_operation and len(cells) >= 4:
            rows.append(dict(date=day, operation=current_operation, tenor_days=int(match[1]),
                             volume_bn=_number(cells[-2], integral=True), rate_pct=_number(cells[-1]),
                             auction=len(rows) + 1))
    if rows and len(totals) == 1 and all(row["volume_bn"] is not None for row in rows):
        rows[0].update(total_bn=totals[0], parts_bn=sum(row["volume_bn"] for row in rows))
    return rows


def parse_fx(content):
    text = _text(_dom(content))
    for match in re.finditer(r"tỷ giá trung tâm", text, re.I):
        excerpt = text[match.end():match.end() + 300]
        day = re.search(DATE, excerpt)
        rate = re.search(r"(\d{2}[., ]\d{3}|\d{5})\s*(?:VND|đồng)\b", excerpt, re.I)
        if day and rate:
            return [dict(date=_iso_date(day), vnd_per_usd=int(re.sub(r"\D", "", rate[1])))]
    return []


def parse_cpi(content):
    root = _dom(content)
    period = CPI_PERIOD.search(_text(root))
    if period is None:
        return []
    for paragraph in root.xpath("//p"):
        text = _text(paragraph)
        if not re.match(r"(Chỉ số giá tiêu dùng(?:\s*\(CPI\))?|CPI)\b", text, re.I):
            continue
        latest = re.search(r"(tăng|giảm)\s+(\d+(?:[,.]\d+)?)\s*%\s*so với cùng kỳ năm (?:trước|20\d{2})", text, re.I)
        if latest:
            value = _number(latest[2])
            return [dict(month=f"{period[2]}-{int(period[1]):02}", pct=value if latest[1].lower() == "tăng" else -value)]
    return []


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


def daily_provider(fetch, series, slug, parse):
    url = SBV + "/vi/" + quote(slug)

    def read():
        yield series, url, fetch(url), parse

    read.__name__ = series
    return read


def monthly_provider(fetch, series, today):
    structure = "10034332" if series == "sbv_credit" else "10038520"
    url = f"{SBV}/o/article/v1.0/articles?scopeKey=20117&contentStructureId={structure}&pageSize=100"
    if series == "sbv_credit":
        condition = f"status eq 0 and Date62813077 ne '' and Date62813077 ge '2010-01-01' and Date62813077 le '{today}'"
        url += "&filter=" + quote(condition)

    def read():
        yield series, url, fetch(url), lambda raw: parse_monthly(raw, series)

    read.__name__ = series
    return read


def cpi_provider(fetch, watermark=None):
    def cpi():
        raw = fetch(NSO)
        yield "cpi_index", NSO, raw, []
        selected = {}
        root = _dom(raw)
        entries = [(_text(link), link.get("href")) for link in root.xpath("//a[@href]")]
        for item in root.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' archive-container ')]//section"):
            # The release's anchor may close before the section after HTML recovery.
            links = item.xpath("ancestor::a[1]/@href | preceding-sibling::*[1][self::p]/a/@href")
            if links:
                entries.append((_text(item), links[0]))
        for title, href in entries:
            period = CPI_PERIOD.search(title)
            if period and ascii_key(title).startswith("chi so gia tieu dung"):
                month = f"{period[2]}-{int(period[1]):02}"
                if watermark and month < watermark:
                    continue
                url = urljoin(NSO, href)
                parts = urlsplit(url)
                if parts.scheme == "https" and parts.netloc == urlsplit(NSO).netloc:
                    selected.setdefault(month, url)
        if not selected:
            raise ValueError("Không tìm thấy bản tin CPI mới trong danh mục")
        for month in sorted(selected):
            url = selected[month]
            yield "cpi", url, fetch(url), parse_cpi

    return cpi
