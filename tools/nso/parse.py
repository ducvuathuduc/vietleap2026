"""Deterministic parser for NSO monthly socio-economic reports (no LLM, regex only).

The parser reads a saved report page, finds the article paragraphs that publish each indicator,
extracts the printed Vietnamese number and keeps the exact sentence as evidence.  A value that
is not printed in the report produces no row - the parser never interpolates or derives numbers.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from engine.vlkit.vn import clean_text, nfc, parse_vn_number

PARSER_VERSION = "nso-1.0.0"

COLUMNS = [
    "indicator_id",
    "period",
    "measure_type",
    "value",
    "unit",
    "source_url",
    "published_date",
    "evidence",
    "parser_version",
]

MEASURE_ORDER = ["month", "ytd", "pct_plan", "yoy", "mom", "avg_ytd"]
INDICATOR_ORDER = [
    "nsnn_thu",
    "nsnn_chi",
    "dtc_giai_ngan",
    "fdi_dang_ky",
    "fdi_thuc_hien",
    "cpi",
    "iip",
    "ban_le",
    "xuat_khau",
    "nhap_khau",
    "can_can_thuong_mai",
]

MONTH_WORD = {
    "một": 1,
    "hai": 2,
    "ba": 3,
    "tư": 4,
    "bốn": 4,
    "năm": 5,
    "sáu": 6,
    "bảy": 7,
    "tám": 8,
    "chín": 9,
    "mười": 10,
    "mười một": 11,
    "mười hai": 12,
}
_QUARTER = {"i": 1, "ii": 2, "iii": 3, "iv": 4}

_BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "header", "footer", "li", "ul", "ol",
    "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th", "table", "blockquote",
}
_ROMAN_ALT = "iv|iii|ii|i"
_MONTH_ALT = "mười một|mười hai|mười|một|hai|ba|tư|bốn|năm|sáu|bảy|tám|chín"
_MONTH_TOKEN = rf"(?:{_MONTH_ALT}|\d{{1,2}}(?:/\d{{4}})?)"
_MONTH_CLAUSE = rf"tháng\s+{_MONTH_TOKEN}(?:\s+năm\s+\d{{4}})?"


class _Blocks(HTMLParser):
    """Collect visible text as blocks; scripts/styles and tags are dropped."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.title_parts: list[str] = []
        self._buf: list[str] = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        elif tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title_parts.append(data)
        self._buf.append(data)

    def _flush(self):
        text = clean_text("".join(self._buf))
        self._buf = []
        if text:
            self.blocks.append(text)

    def close(self):
        super().close()
        self._flush()


def period_from_title(title: str) -> str:
    """Map a report title to the reporting month (YYYY-MM).

    Quarterly reports are mapped to the last month of the quarter (quý I -> 03).
    """
    text = nfc(title).lower()
    year_match = re.search(r"\b(20\d{2})\b", text)

    quarter = re.search(rf"quý\s+({_ROMAN_ALT}|\d)\b", text)
    if quarter and year_match:
        token = quarter.group(1)
        q = int(token) if token.isdigit() else _QUARTER[token]
        if not 1 <= q <= 4:
            raise ValueError(f"invalid quarter in title: {title!r}")
        return f"{year_match.group(1)}-{3 * q:02d}"

    month = re.search(rf"tháng\s+({_MONTH_ALT})\b", text)
    if month:
        if not year_match:
            raise ValueError(f"missing year in title: {title!r}")
        return f"{year_match.group(1)}-{MONTH_WORD[month.group(1)]:02d}"

    month = re.search(r"tháng\s+(\d{1,2})\s*/\s*(\d{4})", text)
    if month:
        return f"{int(month.group(2)):04d}-{int(month.group(1)):02d}"

    month = re.search(r"tháng\s+(\d{1,2})\s+năm\s+(\d{4})", text)
    if month:
        return f"{int(month.group(2)):04d}-{int(month.group(1)):02d}"

    raise ValueError(f"cannot derive reporting period from title: {title!r}")


def _published_date(blocks: list[str]) -> str:
    for block in blocks:
        match = re.search(r"Ngày đăng:\s*(\d{1,2})/(\d{1,2})/(\d{4})", block, re.I)
        if match:
            day, month, year = (int(x) for x in match.groups())
            return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    start = 0
    for match in re.finditer(r"\.\s+", text):
        end = match.start() + 1
        spans.append((start, end))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _evidence(text: str, pos: int) -> str:
    for start, end in _sentence_spans(text):
        if start <= pos < end:
            return clean_text(text[start:end])
    return clean_text(text)


def _signed(direction: str, raw: str) -> float:
    value = parse_vn_number(raw)[0]
    return -value if direction.lower().startswith("giảm") else value


def _balance_value(kind: str, raw: str) -> float:
    value = parse_vn_number(raw)[0]
    return -value if kind.lower().startswith("nhập") else value


class _Extractor:
    def __init__(self, paragraphs, period, source_url, published_date):
        self.paragraphs = paragraphs
        self.period = period
        self.source_url = source_url
        self.published_date = published_date
        self.rows = []

    def add(self, indicator, measure, value, unit, evidence):
        if value is None:
            return
        self.rows.append(
            {
                "indicator_id": indicator,
                "period": self.period,
                "measure_type": measure,
                "value": value,
                "unit": unit,
                "source_url": self.source_url,
                "published_date": self.published_date,
                "evidence": evidence,
                "parser_version": PARSER_VERSION,
            }
        )

    def find(self, pattern, start=0):
        regex = re.compile(pattern, re.I)
        for paragraph in self.paragraphs[start:]:
            if regex.search(paragraph):
                return paragraph
        return None

    # ------------------------------------------------------------------ budget
    def budget(self, indicator, anchor):
        paragraph = self.find(anchor)
        if not paragraph:
            return
        unit = "nghìn tỷ đồng"

        match = re.search(
            rf"(?:tháng\s+)?{_MONTH_TOKEN}\s+(?:(?:ước\s+)?đạt\s+){{1,2}}"
            rf"(?:gần\s+)?(\d[\d.,]*)\s+nghìn tỷ",
            paragraph,
            re.I,
        )
        if match:
            self.add(indicator, "month", parse_vn_number(match.group(1))[0], unit,
                     _evidence(paragraph, match.start(1)))

        match = re.search(
            r"(?:lũy kế|tính chung)[^.]*?(?:(?:ước\s+)?đạt\s+){1,2}(?:gần\s+)?(\d[\d.,]*)\s+nghìn tỷ",
            paragraph,
            re.I,
        )
        if match:
            self.add(indicator, "ytd", parse_vn_number(match.group(1))[0], unit,
                     _evidence(paragraph, match.start(1)))

        match = re.search(r"bằng\s+(\d[\d.,]*)\s*%\s*dự toán", paragraph, re.I)
        if match:
            self.add(indicator, "pct_plan", parse_vn_number(match.group(1))[0], "%",
                     _evidence(paragraph, match.start(1)))

        match = re.search(
            r"(tăng|giảm)\s+(\d[\d.,]*)\s*%\s+so với (?:cùng kỳ|năm trước)",
            paragraph,
            re.I,
        )
        if match:
            self.add(indicator, "yoy", _signed(match.group(1), match.group(2)), "%",
                     _evidence(paragraph, match.start(2)))

    # ------------------------------------------------------------------ investment
    def public_investment(self):
        indicator = "dtc_giai_ngan"
        paragraph = self.find(r"vốn đầu tư thực hiện từ nguồn ngân sách")
        if not paragraph:
            return
        unit = "nghìn tỷ đồng"

        match = re.search(
            rf"{_MONTH_CLAUSE}\s+(?:(?:ước\s+)?đạt\s+){{1,2}}(?:gần\s+)?(\d[\d.,]*)\s+nghìn tỷ",
            paragraph,
            re.I,
        )
        if match:
            self.add(indicator, "month", parse_vn_number(match.group(1))[0], unit,
                     _evidence(paragraph, match.start(1)))

        ytd_match = re.search(
            r"(?:tính chung|lũy kế)[^.]*?(?:(?:ước\s+)?đạt\s+){1,2}(?:gần\s+)?(\d[\d.,]*)\s+nghìn tỷ",
            paragraph,
            re.I,
        )
        if ytd_match:
            self.add(indicator, "ytd", parse_vn_number(ytd_match.group(1))[0], unit,
                     _evidence(paragraph, ytd_match.start(1)))

        match = re.search(r"bằng\s+(\d[\d.,]*)\s*%\s+kế hoạch", paragraph, re.I)
        if match:
            self.add(indicator, "pct_plan", parse_vn_number(match.group(1))[0], "%",
                     _evidence(paragraph, match.start(1)))

        # The month sentence has its own yoy (e.g. 2026-10: 23.7%); the published
        # cumulative yoy lives in the ytd sentence.  Prefer the ytd sentence when present.
        yoy_source = _evidence(paragraph, ytd_match.start(1)) if ytd_match else paragraph
        match = re.search(r"(tăng|giảm)\s+(\d[\d.,]*)\s*%\s+so với cùng kỳ", yoy_source, re.I)
        if match:
            self.add(indicator, "yoy", _signed(match.group(1), match.group(2)), "%",
                     _evidence(yoy_source, match.start(2)))

    def fdi(self):
        for indicator, anchor in (
            ("fdi_dang_ky", r"tổng vốn đầu tư nước ngoài đăng ký"),
            ("fdi_thuc_hien", r"vốn đầu tư (?:trực tiếp )?nước ngoài thực hiện"),
        ):
            paragraph = self.find(anchor)
            if not paragraph:
                continue
            unit = "tỷ USD"
            sentences = [clean_text(paragraph[s:e]) for s, e in _sentence_spans(paragraph)]
            sentence = next((s for s in sentences if re.search(anchor, s, re.I)), paragraph)
            match = re.search(
                r"đạt\s+(?:(?:gần|hơn)\s+)?(\d[\d.,]*)\s+tỷ USD", sentence, re.I
            )
            if match:
                self.add(indicator, "ytd", parse_vn_number(match.group(1))[0], unit,
                         _evidence(sentence, match.start(1)))
            match = re.search(r"(tăng|giảm)\s+(\d[\d.,]*)\s*%", sentence, re.I)
            if match:
                self.add(indicator, "yoy", _signed(match.group(1), match.group(2)), "%",
                         _evidence(sentence, match.start(2)))

    # ------------------------------------------------------------------ prices / industry
    def cpi(self):
        paragraph = self.find(r"chỉ số giá tiêu dùng\s*\(cpi\)")
        if not paragraph:
            return

        sentences = [clean_text(paragraph[s:e]) for s, e in _sentence_spans(paragraph)]
        month_sentence = next(
            (s for s in sentences if re.search(r"\bcpi\b", s, re.I) and re.search(r"tháng\s+", s, re.I)),
            "",
        )
        unit = "%"
        match = re.search(
            r"(tăng|giảm)\s+(?:nhẹ\s+)?(\d[\d.,]*)\s*%\s+so với tháng(?!\s*\d)",
            month_sentence,
            re.I,
        )
        if match:
            self.add("cpi", "mom", _signed(match.group(1), match.group(2)), unit,
                     _evidence(month_sentence, match.start(2)))

        yoy = re.search(r"(tăng|giảm)\s+(\d[\d.,]*)\s*%\s+so với cùng kỳ năm", paragraph, re.I)
        if not yoy:
            yoy = re.search(
                r"so với cùng kỳ năm(?:\s+\d{4}|\s+trước)[^.]*?"
                r"(tăng|giảm)\s+(\d[\d.,]*)\s*%",
                paragraph,
                re.I,
            )
        if not yoy:
            # Annual report: "So với tháng 12/2024, CPI tháng Mười Hai tăng X%".
            yoy = re.search(
                r"so với tháng \d{1,2}/\d{4}[^.]*?\bcpi\b[^.]*?"
                r"(tăng|giảm)\s+(\d[\d.,]*)\s*%",
                paragraph,
                re.I,
            )
        if yoy:
            self.add("cpi", "yoy", _signed(yoy.group(1), yoy.group(2)), unit,
                     _evidence(paragraph, yoy.start(2)))

        avg = re.search(
            r"bình quân[^.]*?cpi[^.]*?(tăng|giảm)\s+(\d[\d.,]*)\s*%",
            paragraph,
            re.I,
        )
        if not avg:
            # Annual report: "Tính chung cả năm 2024, CPI tăng X%".
            avg = re.search(
                r"(?:tính chung|bình quân)[^.]*?cpi[^.]*?"
                r"(tăng|giảm)\s+(\d[\d.,]*)\s*%",
                paragraph,
                re.I,
            )
        if avg:
            self.add("cpi", "avg_ytd", _signed(avg.group(1), avg.group(2)), unit,
                     _evidence(paragraph, avg.start(2)))

    def iip(self):
        paragraph = self.find(
            r"chỉ số sản xuất (?:toàn\s+)?(?:ngành\s+)?công nghiệp\s*\(iip\)\s+tháng"
        )
        if not paragraph:
            return

        sentences = [clean_text(paragraph[s:e]) for s, e in _sentence_spans(paragraph)]
        sentence = next(
            (s for s in sentences if re.search(r"\(iip\)\s+tháng", s, re.I)),
            "",
        )
        unit = "%"
        match = re.search(r"(tăng|giảm)\s+(\d[\d.,]*)\s*%\s+so với tháng trước", sentence, re.I)
        if match:
            self.add("iip", "mom", _signed(match.group(1), match.group(2)), unit,
                     _evidence(sentence, match.start(2)))
        match = re.search(r"(tăng|giảm)\s+(\d[\d.,]*)\s*%\s+so với cùng kỳ năm", sentence, re.I)
        if match:
            self.add("iip", "yoy", _signed(match.group(1), match.group(2)), unit,
                     _evidence(sentence, match.start(2)))

    # ------------------------------------------------------------------ retail
    def retail(self):
        paragraph = self.find(r"tổng mức bán lẻ hàng hóa")
        if not paragraph:
            return
        unit = "nghìn tỷ đồng"
        sentences = [clean_text(paragraph[s:e]) for s, e in _sentence_spans(paragraph)]
        month_sentence = next((s for s in sentences if re.search(r"tháng\s+", s, re.I)), "")
        ytd_sentence = next(
            (s for s in sentences if re.search(r"(tính chung|lũy kế)", s, re.I)
             and re.search(r"nghìn tỷ", s, re.I)),
            "",
        )

        match = re.search(
            rf"{_MONTH_CLAUSE}\s+(?:(?:ước\s+)?đạt\s+){{1,2}}(?:gần\s+)?(\d[\d.,]*)\s+nghìn tỷ",
            month_sentence,
            re.I,
        )
        if match:
            self.add("ban_le", "month", parse_vn_number(match.group(1))[0], unit,
                     _evidence(month_sentence, match.start(1)))

        match = re.search(
            r"(?:tính chung|lũy kế)[^.]*?(?:(?:ước\s+)?đạt\s+){1,2}(?:gần\s+)?(\d[\d.,]*)\s+nghìn tỷ",
            ytd_sentence,
            re.I,
        )
        if match:
            self.add("ban_le", "ytd", parse_vn_number(match.group(1))[0], unit,
                     _evidence(ytd_sentence, match.start(1)))

        match = re.search(r"(tăng|giảm)\s+(\d[\d.,]*)\s*%\s+so với tháng trước", month_sentence, re.I)
        if match:
            self.add("ban_le", "mom", _signed(match.group(1), match.group(2)), "%",
                     _evidence(month_sentence, match.start(2)))

        # Year-on-year: prefer the cumulative sentence (consistent with the other indicators).
        yoy_source = ytd_sentence or month_sentence
        match = re.search(
            r"(tăng|giảm)\s+(\d[\d.,]*)\s*%\s+so với (?:cùng kỳ|năm trước)",
            yoy_source,
            re.I,
        )
        if match:
            self.add("ban_le", "yoy", _signed(match.group(1), match.group(2)), "%",
                     _evidence(yoy_source, match.start(2)))

    # ------------------------------------------------------------------ trade
    def exports(self):
        paragraph = self.find(r"(?:kim ngạch )?xuất khẩu hàng hóa tháng")
        if not paragraph:
            return
        unit = "tỷ USD"
        match = re.search(
            rf"xuất khẩu hàng hóa\s+{_MONTH_CLAUSE}\s+"
            rf"(?:(?:(?:ước|sơ bộ)\s+)?đạt\s+){{1,2}}(\d[\d.,]*)\s+tỷ USD",
            paragraph,
            re.I,
        )
        if match:
            self.add("xuat_khau", "month", parse_vn_number(match.group(1))[0], unit,
                     _evidence(paragraph, match.start(1)))
        match = re.search(
            r"tính chung[^.]*?(?:kim ngạch xuất khẩu[^.]*?)?đạt\s+(\d[\d.,]*)\s+tỷ USD",
            paragraph,
            re.I,
        )
        if match:
            self.add("xuat_khau", "ytd", parse_vn_number(match.group(1))[0], unit,
                     _evidence(paragraph, match.start(1)))

    def imports(self):
        paragraph = self.find(
            rf"^[+\-–]?\s*(?:kim ngạch )?nhập khẩu hàng hóa(?:\s*:\s*kim ngạch "
            rf"nhập khẩu hàng hóa)?(?:\s+{_MONTH_CLAUSE})?\s+"
            r"(?:(?:(?:ước|sơ bộ)\s+)?đạt)\b"
        )
        if not paragraph:
            return
        unit = "tỷ USD"
        match = re.search(
            rf"nhập khẩu hàng hóa(?:\s+{_MONTH_CLAUSE})?\s+"
            rf"(?:(?:(?:ước|sơ bộ)\s+)?đạt\s+){{1,2}}(\d[\d.,]*)\s+tỷ USD",
            paragraph,
            re.I,
        )
        if match:
            self.add("nhap_khau", "month", parse_vn_number(match.group(1))[0], unit,
                     _evidence(paragraph, match.start(1)))
        match = re.search(
            r"tính chung[^.]*?(?:kim ngạch nhập khẩu[^.]*?)?đạt\s+(\d[\d.,]*)\s+tỷ USD",
            paragraph,
            re.I,
        )
        if match:
            self.add("nhap_khau", "ytd", parse_vn_number(match.group(1))[0], unit,
                     _evidence(paragraph, match.start(1)))

    def trade_balance(self):
        candidates = [
            p for p in self.paragraphs
            if re.search(r"cán cân thương mại hàng(?: hóa)?", p, re.I)
            and re.search(r"(?:xuất|nhập) siêu", p, re.I)
        ]
        if not candidates:
            return
        unit = "tỷ USD"
        period_month = int(self.period[5:])

        # Month: pick the clause whose printed month equals the report period.
        # 2024-04 revises March and gives April in the same sentence.
        for paragraph in candidates:
            match = None
            for candidate in re.finditer(
                rf"tháng\s+({_MONTH_ALT}|\d{{1,2}})(?:\s*/\s*\d{{4}})?[^.;]*?"
                r"(xuất siêu|nhập siêu)\s+(\d[\d.,]*)\s+tỷ USD",
                paragraph,
                re.I,
            ):
                token = " ".join(candidate.group(1).lower().split())
                month = int(token) if token.isdigit() else MONTH_WORD[token]
                if month == period_month:
                    match = candidate
                    break
            if match:
                value = _balance_value(match.group(2), match.group(3))
                self.add("can_can_thuong_mai", "month", value, unit,
                         _evidence(paragraph, match.start(3)))
                break

        # YTD: "tính chung ..." or a printed count such as "2 tháng đầu năm",
        # "chín tháng", "mười tháng".  Skip "sau chín tháng liên tiếp nhập siêu",
        # which is a duration, not the cumulative balance.
        marker_re = re.compile(
            r"(?:tính chung|"
            r"(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười(?:\s+(?:một|hai))?|\d{1,2})"
            r"\s+tháng(?:\s+đầu năm)?)",
            re.I,
        )
        value_re = re.compile(r"(xuất siêu|nhập siêu)\s+(\d[\d.,]*)\s+tỷ USD", re.I)
        for paragraph in candidates:
            added = False
            for start, end in _sentence_spans(paragraph):
                sentence = clean_text(paragraph[start:end])
                marker = marker_re.search(sentence)
                if not marker:
                    continue
                if sentence[:marker.start()].rstrip().lower().endswith("sau"):
                    continue
                match = value_re.search(sentence, marker.end())
                if match:
                    value = _balance_value(match.group(1), match.group(2))
                    self.add("can_can_thuong_mai", "ytd", value, unit,
                             _evidence(sentence, match.start(2)))
                    added = True
                    break
            if added:
                break


def parse_html(html: str, source_url: str = "") -> dict:
    """Parse one saved NSO report page. Returns period, published_date and long rows."""
    collector = _Blocks()
    collector.feed(html)
    collector.close()
    title = clean_text("".join(collector.title_parts))
    period = period_from_title(title)
    published = _published_date(collector.blocks)

    extractor = _Extractor(collector.blocks, period, source_url, published)
    extractor.budget("nsnn_thu", r"tổng thu ngân sách")
    extractor.budget("nsnn_chi", r"tổng chi ngân sách")
    extractor.public_investment()
    extractor.fdi()
    extractor.cpi()
    extractor.iip()
    extractor.retail()
    extractor.exports()
    extractor.imports()
    extractor.trade_balance()

    seen = set()
    for row in extractor.rows:
        key = (row["indicator_id"], row["measure_type"])
        if key in seen:
            raise ValueError(f"duplicate row for {key} in {source_url or title}")
        seen.add(key)

    extractor.rows.sort(
        key=lambda row: (
            INDICATOR_ORDER.index(row["indicator_id"]),
            MEASURE_ORDER.index(row["measure_type"]),
        )
    )
    return {
        "period": period,
        "published_date": published,
        "source_url": source_url,
        "rows": extractor.rows,
    }


def parse_file(path: str | Path, source_url: str = "") -> dict:
    html = Path(path).read_text(encoding="utf-8")
    return parse_html(html, source_url=source_url)
