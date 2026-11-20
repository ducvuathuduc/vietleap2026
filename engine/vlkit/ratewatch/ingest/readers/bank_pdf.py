"""Bank PDF reader: term lines of the bank's own sheet, with the column pinned by ``banks.yaml``.

Every Vietnamese rate PDF we could read prints one term per line (``1 tháng 4,50% 4,49% ...``) and several
columns (money tiers / interest-payment methods). A parser cannot know which column is the household counter
rate, so the column index, channel and tier come from the bank's config and are written into the silver row.
Corporate sheets are refused: they are a different product and must never be published as household rates.
"""
from __future__ import annotations

import io
import re

from ..contract import normalise_row, parse_rate, parse_term, parse_vi_date
from ....vn import ascii_key

LICENCE = "public PDF rate sheet (robots.txt allows /)"
_HEADER_RE = re.compile(r"(?:hi[ệe]u l[ựu]c|áp d[ụu]ng|kể từ)[^\n]{0,45}", re.I)
_TERM_PREFIX_RE = re.compile(
    r"^\s*(?:Từ\s+)?\d{1,2}(?:\s*đến\s*(?:dưới\s*)?\d{1,2})?\s*(?:tháng|thang)\b", re.I)
_CELL_RE = re.compile(r"-|\d{1,2}[.,]\d{1,2}\s*%?|\d{1,2}\s*%")
_SPLIT_START_RE = re.compile(r"^Từ\s+(\d{1,2})\s+đến$", re.I)
_SPLIT_END_RE = re.compile(r"^dưới\s+\d{1,2}\s+tháng", re.I)


def is_household_sheet(text: str) -> bool:
    """False for a corporate (doanh nghiệp) sheet; True when the sheet says individual or does not say."""
    key = ascii_key(text[:4000])
    return not ("doanh nghiep" in key and "ca nhan" not in key)


def extract_pdf_text(content: bytes) -> str:
    """pdfplumber text of the first pages; empty string for a scan (nothing to read, do not guess)."""
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages[:6])
    except Exception:                     # noqa: BLE001 - a broken PDF is "unreadable", not a crash
        return ""


def join_split_terms(text: str) -> str:
    """Some sheets wrap a term label around its numbers: ``Từ 1 đến`` / values / ``dưới 2 tháng``."""
    lines = text.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        start = _SPLIT_START_RE.match(lines[index].strip())
        if start and index + 2 < len(lines) and _SPLIT_END_RE.match(lines[index + 2].strip()):
            values, end = lines[index + 1].strip(), lines[index + 2].strip()
            out.append(f"Từ {start.group(1)} đến {end} {values}")
            index += 3
            continue
        out.append(lines[index].strip())
        index += 1
    return "\n".join(out)


def parse_pdf_text(text: str, *, bank_code: str, channel: str, tier: str = "", rate_column: int = 0,
                   run_id: str, observed_at: str, source_url: str, raw_sha256: str,
                   interest_basis: str = "at_maturity") -> list[dict]:
    if not text or not is_household_sheet(text):
        return []
    header_lines = "\n".join(text.splitlines()[:6])
    sheet_date = next((parsed for parsed in (parse_vi_date(match.group(0))
                                            for match in _HEADER_RE.finditer(header_lines))
                       if parsed is not None), None)
    rows: list[dict] = []
    for line in join_split_terms(text).splitlines():
        prefix = _TERM_PREFIX_RE.match(line)
        if not prefix:
            continue
        term = parse_term(prefix.group(0))
        if term is None:
            continue
        cells = _CELL_RE.findall(line[prefix.end():])
        if len(cells) <= rate_column:
            continue
        rate = parse_rate(cells[rate_column])
        if rate is None:
            continue
        rows.append(normalise_row({
            "run_id": run_id, "bank_code": bank_code, "term_months": term, "channel": channel,
            "tier": tier, "rate_pct": rate, "interest_basis": interest_basis,
            "sheet_date": sheet_date, "observed_at": observed_at, "reader": "bank_pdf",
            "source_url": source_url, "raw_sha256": raw_sha256,
        }))
    return rows
