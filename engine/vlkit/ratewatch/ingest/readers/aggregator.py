"""Aggregator reader: the server-rendered laisuattietkiem.vn table (22 banks x 2 channels x 8 terms).

This is the breadth reader, not a bank: ``source_url`` is the aggregator page that was actually read and the
reader name is ``aggregator``, so T2 can grade it against a bank's own sheet.
"""
from __future__ import annotations

import re

from ..banks import aggregator_index, code_for_aggregator_name
from ..contract import normalise_row, parse_rate, parse_vi_date, parse_term

AGGREGATOR_URL = "https://laisuattietkiem.vn/"
LICENCE = "public comparison table, reference use (robots.txt allows /)"
_BLOCK_SPLIT = '<td class="order-cell" rowspan="2">'
_NAME_RE = re.compile(r'class="bank-cell-name">([^<]+)<')
_CHANNEL_RE = re.compile(r'class="channel-cell">([^<]+)<')
_CELL_RE = re.compile(r'<td class="rate-cell[^"]*">(.*?)</td>', re.S)
_CURRENT_RE = re.compile(r'class="rate-current">([\d.,]+)%')
_TERM_RE = re.compile(r"<th[^>]*>\s*(\d{1,2})\s*th[áa]ng\s*</th>", re.I)
_STAMP_RE = re.compile(r'id="dataStripDate">([^<]+)<')
_UPDATED_RE = re.compile(r"Cập nhật lúc:[^<]{0,40}?(\d{1,2}[/.]\d{1,2}[/.]20\d\d)")


def parse_aggregator_terms(html: str) -> list[int]:
    """Term columns, in header order (the site's 8 columns, not a hard-coded list)."""
    terms = []
    for raw in _TERM_RE.findall(html):
        term = parse_term(f"{raw} tháng")
        if term:
            terms.append(term)
    return terms


def parse_aggregator_sheet_date(html: str):
    stamp = _STAMP_RE.search(html)
    if stamp:
        return parse_vi_date(stamp.group(1))
    updated = _UPDATED_RE.search(html)
    return parse_vi_date(updated.group(1)) if updated else None


def parse_aggregator_html(html: str, *, url: str, run_id: str, observed_at: str, raw_sha256: str,
                          banks) -> list[dict]:
    index = aggregator_index(banks)
    terms = parse_aggregator_terms(html)
    sheet_date = parse_aggregator_sheet_date(html)
    rows: list[dict] = []
    if not terms:
        return rows
    for block in html.split(_BLOCK_SPLIT)[1:]:
        name = _NAME_RE.search(block)
        if not name:
            continue
        code = code_for_aggregator_name(name.group(1), index)
        if not code:
            continue
        channels = _CHANNEL_RE.findall(block)
        cells = _CELL_RE.findall(block)
        for position, label in enumerate(channels[:2]):
            channel = "online" if "online" in label.lower() else "counter"
            for term, cell in zip(terms, cells[position * len(terms):(position + 1) * len(terms)]):
                current = _CURRENT_RE.search(cell)
                rate = parse_rate(current.group(1) + "%") if current else None
                if rate is None:
                    continue
                rows.append(normalise_row({
                    "run_id": run_id, "bank_code": code, "term_months": term, "channel": channel,
                    "tier": "", "rate_pct": rate, "interest_basis": "at_maturity",
                    "sheet_date": sheet_date, "observed_at": observed_at, "reader": "aggregator",
                    "source_url": url, "raw_sha256": raw_sha256,
                }))
    return rows
