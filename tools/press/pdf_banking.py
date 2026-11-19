"""TCBS Banking Sector 3Q/2026 PDF: appendix bank table + sector aggregates."""
from __future__ import annotations

import re
from datetime import datetime

from .output import contract_row
from .tf_rows import find_snippet, to_number

PDF_URL = "https://www.tcbs.com.vn/wp-content/uploads/2026/11/20261116_Banking_Sector_Earnings_Update_Q3_2026.pdf"
PERIOD = "2026-Q3"
PUBLISHED = "2026-11-16"

BANK_COLUMNS = [
    ("total_assets", "bank_total_assets", "vnd_trn", "level"),
    ("credit_ytd", "bank_credit_ytd", "%", "ytd"),
    ("deposits_ytd", "bank_deposits_ytd", "%", "ytd"),
    ("npat_3q", "bank_npat_3q", "vnd_bn", "level"),
    ("npat_3q_yoy", "bank_npat_3q_yoy", "%", "yoy"),
    ("npat_9m", "bank_npat_9m", "vnd_bn", "level"),
    ("npat_9m_yoy", "bank_npat_9m_yoy", "%", "yoy"),
    ("nim", "bank_nim", "%", "ratio"),
    ("cir", "bank_cir", "%", "ratio"),
    ("roe_3q", "bank_roe_3q", "%", "ratio"),
    ("npl", "bank_npl", "%", "share"),
    ("npl_coverage", "bank_npl_coverage", "%", "ratio"),
    ("casa", "bank_casa", "%", "share"),
]
_TICKER_LINE = re.compile(r"^([A-Z]{3})\s+((?:[+\-]?[\d.,]+%?\s+){12}[+\-]?[\d.,]+%?)\s*$")

SECTOR_SPECS = [
    ("bank_sector_npl", r"NPL ratio edged up to ([\d.]+)%", "share", "%"),
    ("bank_sector_npl_group2", r"group-2 loans rose.{0,120}?to ([\d.]+)%", "share", "%"),
    ("bank_sector_npl_coverage", r"coverage fell to a series-low ([\d.]+)%", "ratio", "%"),
    ("bank_sector_nim", r"pulling NIM down to ([\d.]+)%", "ratio", "%"),
    ("bank_sector_cof", r"cost of funds rose to ([\d.]+)%", "ratio", "%"),
    ("bank_sector_casa", r"CASA slipped to ([\d.]+)%", "share", "%"),
    ("bank_sector_pb", r"Aggregate P/B is ([\d.]+)x", "ratio", "x"),
    ("bank_sector_roe", r"trailing ROE holds at ([\d.]+)%", "ratio", "%"),
    ("bank_sector_npat_3q", r"Net profit reached VND ([\d,]+) bn in 3Q", "level", "vnd_bn"),
    ("bank_sector_npat_3q_yoy", r"Net profit reached VND [\d,]+ bn in 3Q, up ([\d.]+)% YoY", "yoy", "%"),
    ("bank_sector_npat_9m", r"earned VND ([\d,]+) bn", "level", "vnd_bn"),
    ("bank_sector_npat_9m_yoy", r"earned VND [\d,]+ bn \(\+([\d.]+)%\)", "yoy", "%"),
    ("bank_sector_credit_yoy", r"loans rose ([\d.]+)% YoY", "yoy", "%"),
]
_BLOCK = re.compile(
    r"TOTAL ASSETS\s+OUTSTANDING CREDIT\s+CUSTOMER DEPOSITS\s+EQUITY\s*\n"
    r"([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*\n"
    r"VND trn[^\n]*?\+([\d.]+)% YTD[^\n]*?\+([\d.]+)% YTD[^\n]*?\+([\d.]+)% YTD[^\n]*?\+([\d.]+)% YTD"
)
BLOCK_COLUMNS = [
    ("bank_sector_total_assets", 1, "level", "vnd_trn"),
    ("bank_sector_credit", 2, "level", "vnd_trn"),
    ("bank_sector_deposits", 3, "level", "vnd_trn"),
    ("bank_sector_equity", 4, "level", "vnd_trn"),
    ("bank_sector_total_assets_ytd", 5, "ytd", "%"),
    ("bank_sector_credit_ytd", 6, "ytd", "%"),
    ("bank_sector_deposits_ytd", 7, "ytd", "%"),
    ("bank_sector_equity_ytd", 8, "ytd", "%"),
]


def _line_at(text: str, pos: int, width: int = 400) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    end = len(text) if end < 0 else end
    return text[start:end].strip()[:width]


def parse_appendix(text: str) -> list[dict]:
    """The 26-bank appendix table (BANK + 13 numeric columns) from one or more pages of text."""
    banks = []
    for line in str(text).splitlines():
        match = _TICKER_LINE.match(line.strip())
        if not match:
            continue
        tokens = match.group(2).split()
        if len(tokens) != 13:
            continue
        values = [to_number(token, ".") for token in tokens]
        if any(v is None for v in values):
            continue
        bank = {"ticker": match.group(1), "evidence": line.strip()}
        bank.update({name: value for (name, _, _, _), value in zip(BANK_COLUMNS, values)})
        banks.append(bank)
    return banks


def bank_rows(banks, *, source_id: str, url: str = PDF_URL, published_date: str = PUBLISHED,
              period: str = PERIOD, method: str = "pdf") -> list[dict]:
    rows = []
    for bank in banks:
        for key, indicator_id, unit, measure_type in BANK_COLUMNS:
            value = bank[key]
            rows.append(contract_row(
                indicator_id=indicator_id, period=period, measure_type=measure_type, value=value,
                unit=unit, geo=bank["ticker"], source_id=source_id, source_url=url,
                published_date=published_date, evidence=bank["evidence"], evidence_ok=True, method=method,
            ))
    return rows


def sector_rows(text: str, *, source_id: str, url: str = PDF_URL, published_date: str = PUBLISHED,
                period: str = PERIOD, method: str = "pdf") -> list[dict]:
    rows = []
    block = _BLOCK.search(text)
    if block:
        for indicator_id, group, measure_type, unit in BLOCK_COLUMNS:
            value = to_number(block.group(group), ".")
            rows.append(contract_row(
                indicator_id=indicator_id, period=period, measure_type=measure_type, value=value, unit=unit,
                geo="VNM", source_id=source_id, source_url=url, published_date=published_date,
                evidence=_line_at(text, block.start(group)), evidence_ok=True, method=method,
            ))
    for indicator_id, pattern, measure_type, unit in SECTOR_SPECS:
        match = re.search(pattern, text, re.S)
        if not match:
            continue
        value = to_number(match.group(1), ".")
        rows.append(contract_row(
            indicator_id=indicator_id, period=period, measure_type=measure_type, value=value, unit=unit,
            geo="VNM", source_id=source_id, source_url=url, published_date=published_date,
            evidence=_line_at(text, match.start()), evidence_ok=bool(find_snippet(text, value)), method=method,
        ))
    return rows


def pdf_text(path) -> str:
    """All page text of a PDF (pdfplumber, no OCR)."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n\f\n".join((page.extract_text() or "") for page in pdf.pages)


def extract(path, *, source_id: str = "tcbs_banking_q3_2026", url: str = PDF_URL,
            published_date: str = PUBLISHED, period: str = PERIOD) -> tuple[list[dict], dict]:
    text = pdf_text(path)
    banks = parse_appendix(text)
    rows = bank_rows(banks, source_id=source_id, url=url, published_date=published_date, period=period)
    rows += sector_rows(text, source_id=source_id, url=url, published_date=published_date, period=period)
    fetched = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    info = {"banks": len(banks), "pages_text": len(text), "file_date": fetched}
    return rows, info
