"""TCB case: loans, NPL by group, provision balance and provision used for write-offs, with page numbers.

The statements are PDFs on TCB's investor page. Extraction works on the page texts so it can be tested
without a PDF: every value carries the page it was read from, and a metric that is absent stays absent.
"""

import io
import re

import pandas as pd

from .extra_landing import FetchError, land, write_silver

PAGE = ("https://techcombank.com/nha-dau-tu/thong-tin-tai-chinh/bao-cao-tai-chinh-vas"
        "?year={year}&quarter={quarter}")
QUARTERS = ["2024Q3", "2024Q4", "2025Q1", "2025Q3", "2025Q4", "2026Q1"]
COLUMNS = ["quarter", "metric", "value_bn_vnd", "page", "url"]
GROUPS = {
    "npl_group_1_current": r"Nợ đủ tiêu chuẩn",
    "npl_group_2_watch": r"Nợ cần chú ý",
    "npl_group_3_substandard": r"Nợ dưới tiêu chuẩn",
    "npl_group_4_doubtful": r"Nợ nghi ngờ",
    "npl_group_5_loss": r"Nợ có khả năng mất vốn",
}
METRICS = {"loans_customer_bn_vnd": r"Cho vay khách hàng",
           "provision_balance_bn_vnd": r"Dự phòng rủi ro cho vay khách hàng",
           "provision_used_writeoff_bn_vnd": r"(?:Số sử dụng trong kỳ|Dự phòng đã sử dụng để xử lý rủi ro|"
                                             r"Xử lý nợ|Dùng để xử lý nợ)"}
NUMBER = re.compile(r"\(?-?[\d.,]{3,}\)?")


def _number(text):
    value = text.strip().strip("()").replace(".", "").replace(",", ".")
    try:
        number = float(value)
    except ValueError:
        return None
    return -number if text.strip().startswith("(") else number


def page_value(text, label):
    """First number on the same line as `label` (TCB prints '<label>  <number>')."""
    for line in text.splitlines():
        match = re.search(label, line, re.I)
        if match is None:
            continue
        number = NUMBER.search(line[match.end():])
        if number:
            value = _number(number.group())
            if value is not None:
                return value
    return None


def parse_pages(pages, quarter, url=None):
    """Read the case metrics from a list of page texts; the page number is 1-based."""
    rows = []
    for index, text in enumerate(pages, start=1):
        for metric, label in {**GROUPS, **METRICS}.items():
            value = page_value(text, label)
            if value is None or any(row["metric"] == metric for row in rows):
                continue
            rows.append({"quarter": quarter, "metric": metric, "value_bn_vnd": value, "page": index,
                         "url": url})
    return pd.DataFrame(rows, columns=COLUMNS)


def urls_of(html, base=""):
    found = re.findall(r'(?:https?://[^\s"\'<>]+|/[^\s"\'<>]+)\.pdf', html)
    return sorted({part if part.startswith("http") else base.rstrip("/") + part for part in found})


def pdf_pages(content):
    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return [(page.extract_text() or "") for page in pdf.pages]


def run(lake, fetcher, run_id, quarters=QUARTERS):
    frames, errors = [], {}
    for quarter in quarters:
        year, number = int(quarter[:4]), int(quarter[-1])
        page = PAGE.format(year=year, quarter=number)
        try:
            response = fetcher.get(page)
        except FetchError as exc:
            errors[quarter] = str(exc)[:120]
            continue
        land(lake, run_id, "tcb", f"{quarter}-page", response.content, "html", {"url": page})
        pdfs = urls_of(response.text, page)
        for pdf_url in pdfs[:2]:
            try:
                pdf = fetcher.get(pdf_url)
            except FetchError as exc:
                errors[f"{quarter} {pdf_url}"] = str(exc)[:120]
                continue
            land(lake, run_id, "tcb", f"{quarter}-{pdf_url[-40:]}", pdf.content, "pdf", {"url": pdf_url})
            try:
                frames.append(parse_pages(pdf_pages(pdf.content), quarter, pdf_url))
            except Exception as exc:  # a scanned PDF has no text layer: say so, do not guess
                errors[f"{quarter} {pdf_url}"] = f"no text layer: {type(exc).__name__}"
        if not pdfs:
            errors[quarter] = "no statement PDF linked on the investor page"
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    if len(frame):
        frame = frame.sort_values(["quarter", "metric"], ignore_index=True)
    write_silver(lake, "case_tcb.csv", frame, {"quarters": quarters})
    stats = {"rows": len(frame), "quarters_with_rows": int(frame["quarter"].nunique()) if len(frame) else 0,
             "metrics": sorted(frame["metric"].unique()) if len(frame) else []}
    if errors:
        stats["errors"] = errors
    return frame, stats
