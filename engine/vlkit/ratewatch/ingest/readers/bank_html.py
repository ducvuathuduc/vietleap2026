"""Bank HTML reader: a server-rendered ``<table>`` on the bank's own rate page.

Most Vietnamese bank rate pages inject the table with JavaScript, so this reader only fires where
``banks.yaml`` pins a table column (OCB's "Tiết kiệm Online" column, VietinBank's VND column). Without a hint
it returns nothing — guessing which column is the household rate is how wrong numbers get published.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser

from ..contract import normalise_row, parse_rate, parse_term

LICENCE = "public bank page (robots.txt allows /)"
_PDF_RE = re.compile(r'href="([^"]+\.pdf[^"#]*)"', re.I)
_PDF_SCORE = (("lai-suat", 3), ("lai_suat", 3), ("laisuat", 3), ("tiet-kiem", 2), ("tietkiem", 2),
              ("khcn", 2), ("ca-nhan", 1))


def find_pdf_links(html: str, base_url: str, limit: int = 3) -> list[str]:
    """Absolute PDF URLs on the page, rate sheets first (the bank's own "biểu lãi suất" file)."""
    def score(url: str) -> int:
        low = url.lower()
        return sum(weight for token, weight in _PDF_SCORE if token in low)

    links = [urljoin(base_url, raw) for raw in _PDF_RE.findall(html or "")]
    unique = list(dict.fromkeys(links))
    return sorted(unique, key=score, reverse=True)[:limit]


def _cells(row) -> list[str]:
    return [cell.text(strip=True) for cell in row.css("td,th")]


def parse_bank_html(html: str, *, bank_code: str, channel: str, tier: str = "", rate_column: int = 1,
                    run_id: str, observed_at: str, source_url: str, raw_sha256: str,
                    interest_basis: str = "at_maturity") -> list[dict]:
    if not html:
        return []
    tree = LexborHTMLParser(html)
    rows: list[dict] = []
    for table in tree.css("table"):
        body = table.css("tr")
        if len(body) < 3:
            continue
        parsed: list[dict] = []
        for tr in body:
            cells = _cells(tr)
            if len(cells) <= rate_column:
                continue
            term = parse_term(cells[0])
            rate = parse_rate(cells[rate_column])
            if term is None or rate is None:
                continue
            parsed.append(normalise_row({
                "run_id": run_id, "bank_code": bank_code, "term_months": term, "channel": channel,
                "tier": tier, "rate_pct": rate, "interest_basis": interest_basis,
                "sheet_date": None,           # these pages print no rate-sheet effective date
                "observed_at": observed_at, "reader": "bank_html", "source_url": source_url,
                "raw_sha256": raw_sha256,
            }))
        if len(parsed) >= 3:
            rows = parsed
            break
    return rows
