"""Finding the quarterly financial-statement PDFs: investor-relations pages, exchange disclosure pages, an agent.

Three link sources, cheapest first: a page the machine can read (the PDF hrefs are in the HTML), the HOSE
disclosure register already landed by the extra run, and the TinyFish agent for pages that only render their
document list in JavaScript. Every discovered link keeps where it came from; a quarter with no link stays
missing rather than being guessed from a name pattern.

The catalogue below holds the public investor-relations statement page of each large bank (checked 20/11/2026).
A page that cannot be reached is reported by the caller, not retried forever.
"""

import re
from urllib.parse import urljoin

import pandas as pd

CATALOGUE = {
    "VCB": "https://www.vietcombank.com.vn/vi-VN/Nha-dau-tu/Bao-cao-tai-chinh",
    "BID": "https://www.bidv.com.vn/vn/nha-dau-tu/bao-cao-tai-chinh",
    "CTG": "https://investor.vietinbank.vn/vi/bao-cao-tai-chinh",
    "TCB": "https://techcombank.com/nha-dau-tu/thong-tin-tai-chinh/bao-cao-tai-chinh-vas",
    "MBB": "https://www.mbbank.com.vn/investor/bao-cao-tai-chinh",
    "ACB": "https://investor.acb.com.vn/vi/bao-cao-tai-chinh",
    "VPB": "https://investor.vpbank.com.vn/vi/bao-cao-tai-chinh",
    "STB": "https://www.sacombank.com.vn/nha-dau-tu/bao-cao-tai-chinh.html",
}
COLUMNS = ["bank", "period", "statement_type", "url", "found_by", "found_at", "http_status"]
VIETSTOCK = "https://static2.vietstock.vn/data/{exchange}/{year}/BCTC/VN/{folder}/{ticker}_Baocaotaichinh_{label}_{year}_{kind}.pdf"
EXCHANGES = ("HOSE", "HNX", "UPCOM")          # probe order: the exchange the bank is listed on is usually HOSE
QUARTER_KINDS = (("consolidated", "Hopnhat"), ("separate", "Congtyme"), ("separate", "Rieng"))
ANNUAL_KINDS = (("consolidated", "Hopnhat"), ("separate", "Rieng"))
PDF = re.compile(r'(?:https?://[^\s"\'<>]+|/[^\s"\'<>]+?)\.pdf', re.I)
YEAR = re.compile(r"(20[12][0-9])")
QUARTER_WORDS = [(r"quy\s*4|quy\s*iv|q\s*4|ky\s*4", 4), (r"quy\s*3|quy\s*iii|q\s*3|ky\s*3", 3),
                 (r"quy\s*2|quy\s*ii|q\s*2|ky\s*2", 2), (r"quy\s*1|quy\s*i|q\s*1|ky\s*1", 1)]
FROM_TEXT = [(r"hop\s*nhat|consolidated", "consolidated"), (r"rieng|separate", "separate")]


def period_in(text):
    """('2024Q3') from a file name or tab label, or None when the text names no year+quarter."""
    from ...vn import ascii_key

    key = ascii_key(text or "")
    year = YEAR.search(key)
    if year is None:
        return None
    for pattern, quarter in QUARTER_WORDS:
        if re.search(pattern, key):
            return f"{year.group(1)}Q{quarter}"
    return None


def statement_type_of(text):
    """'consolidated' / 'separate' from a file name or label; 'unknown' when it says neither."""
    from ...vn import ascii_key

    key = ascii_key(text or "")
    for pattern, kind in FROM_TEXT:
        if re.search(pattern, key):
            return kind
    return "unknown"


def pdfs_in(html, base):
    """Absolute PDF URLs linked from an HTML page (relative links resolved against `base`)."""
    found = []
    for match in PDF.finditer(html or ""):
        url = match.group().replace("&amp;", "&")
        found.append(url if url.lower().startswith("http") else urljoin(base, url))
    return sorted(set(found))


def rows_from_page(bank, html, page_url, found_by="html", found_at=None):
    """Rows for every PDF whose name or link text names a year and a quarter."""
    rows = []
    for url in pdfs_in(html, page_url):
        period = period_in(url)
        if period is None:
            continue
        rows.append({"bank": bank, "period": period, "statement_type": statement_type_of(url),
                     "url": url, "found_by": found_by, "found_at": found_at})
    return rows


def rows_from_agent(bank, records, found_at=None, found_by="tinyfish"):
    """Rows from a TinyFish agent result: records already carry period + pdf_url + statement_type."""
    rows = []
    for record in records or []:
        url = str(record.get("pdf_url") or "").strip()
        period = period_in(str(record.get("period") or "")) or period_in(url)
        if not url.lower().startswith("http") or period is None:
            continue
        kind = str(record.get("statement_type") or "unknown")
        rows.append({"bank": bank, "period": period,
                     "statement_type": kind if kind in ("consolidated", "separate") else statement_type_of(url),
                     "url": url, "found_by": found_by, "found_at": found_at})
    return rows


QUARTER_URL = ("https://static2.vietstock.vn/data/{exchange}/{year}/BCTC/VN/QUY%20{quarter}/"
               "{ticker}_Baocaotaichinh_Q{quarter}_{year}_{kind}.pdf")
ANNUAL_URL = "https://static2.vietstock.vn/data/{exchange}/{year}/BCTC/VN/NAM/{name}"


def vietstock_quarter_urls(ticker, period, exchange="HOSE"):
    """[(url, statement_type)] for one bank-quarter: consolidated first, then the two separate-statement names."""
    year, quarter = str(period)[:4], str(period)[-1]
    return [(QUARTER_URL.format(exchange=exchange, year=year, quarter=quarter, ticker=ticker, kind=kind),
             statement_type) for statement_type, kind in QUARTER_KINDS]


def vietstock_annual_urls(ticker, year, exchange="HOSE"):
    """[(url, statement_type)] candidates for the audited annual statement: three NAM file namings.

    The folder is known ("NAM"); which naming Vietstock uses is not, so all three are probed and the log keeps
    the answer (a 404 stays in the probe row, so a later run can drop the namings that never exist).
    """
    out = []
    for statement_type, kind in ANNUAL_KINDS:
        for name in (f"{ticker}_Baocaotaichinh_{year}_{kind}", f"{ticker}_Baocaotaichinh_NAM_{year}_{kind}",
                     f"{ticker}_Baocaotaichinh_{year}_NAM_{kind}"):
            out.append((ANNUAL_URL.format(exchange=exchange, year=year, name=name + ".pdf"), statement_type))
    return out


def probe_statement(probe, ticker, period, found_at=None, exchanges=EXCHANGES, separate=True):
    """(probes, hits) for one bank-quarter; every HEAD is kept, a miss stays in the log as a 404.

    `probe` is a callable url -> (http_status, content_type). The consolidated statement is looked for first,
    across the exchanges in order, and the search stops at the first exchange where something answered; the
    separate-statement names are then probed in that same exchange. A normal bank-quarter costs two HEADs.
    """
    probes = []
    for exchange in exchanges:
        answered = False
        for url, statement_type in vietstock_quarter_urls(ticker, period, exchange):
            status, content_type = probe(url)
            hit = status == 200 and "pdf" in str(content_type).lower()
            probes.append({"bank": ticker, "period": period, "statement_type": statement_type, "url": url,
                           "found_by": "vietstock_static", "found_at": found_at, "http_status": status})
            if hit:
                answered = True
                if statement_type == "consolidated":
                    continue            # keep probing the two separate namings in the exchange that answered
                if separate:
                    continue
        if answered:
            break
    return probes, [row for row in probes if row["http_status"] == 200]


def hits_only(frame):
    """The links that answered 200 (a probe log and a link register are the same table, one column apart)."""
    if frame is None or not len(frame) or "http_status" not in frame:
        return frame
    return frame[frame["http_status"].isna() | (frame["http_status"] == 200)]


def prefer_consolidated(rows):
    """One link per (bank, period): the consolidated statement wins, then the earliest found link."""
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    frame = pd.DataFrame(rows).reindex(columns=COLUMNS)
    order = {"consolidated": 0, "unknown": 1, "separate": 2}
    frame["_order"] = frame["statement_type"].map(order).fillna(3)
    frame = frame.sort_values(["bank", "period", "_order", "url"]).drop_duplicates(["bank", "period"], keep="first")
    return frame.drop(columns="_order").sort_values(["bank", "period"], ignore_index=True)


def agent_schema():
    return {
        "type": "object",
        "properties": {
            "bank": {"type": "string"},
            "statements": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "period": {"type": "string"},
                    "statement_type": {"type": "string", "enum": ["consolidated", "separate", "unknown"]},
                    "pdf_url": {"type": "string"},
                    "published_date": {"type": "string"},
                    "period_label": {"type": "string"},
                },
                "required": ["period", "pdf_url"],
            }},
        },
        "required": ["statements"],
    }


def agent_goal(bank):
    return f"""This is {bank}'s investor-relations page for financial statements (bao cao tai chinh).
Open the page, expand every year/quarter tab or accordion, and collect the direct links to the QUARTERLY
financial statement files of 2021 to now. Prefer the CONSOLIDATED (hop nhat) statement and also list the SEPARATE
(rieng) one when the page offers both. For each file: period as YYYYQn taken from the tab label or the file name,
statement_type consolidated|separate|unknown, pdf_url = the absolute URL of the file itself (not a viewer page),
published_date YYYY-MM-DD when printed. Never invent a link: leave out a quarter the page does not list. If no file
link can be seen, return statements: [] and describe what you saw."""
