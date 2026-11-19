"""SBV credit-by-sector static scraper.

Fetches https://sbv.gov.vn/du-no-tin-dung-doi-voi-nen-kt-dttktt, keeps the raw page,
parses the two published snapshot tables with pandas and writes a long CSV.

Usage: python tools/sbv/extract.py [--refresh]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from lxml import html as lxml_html

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.vlkit.vn import parse_vn_number

PAGE_URL = "https://sbv.gov.vn/du-no-tin-dung-doi-voi-nen-kt-dttktt"
ROBOTS_URL = "https://sbv.gov.vn/robots.txt"
USER_AGENT = "vietleap-research/0.1 (SBV credit statistics extractor; +https://github.com/vietleap)"
DELAY = 2.0
RETRIES = 3

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "raw" / "sbv"
CSV_NAME = "sbv_credit_by_sector.csv"
RAW_NAME = "credit_by_sector"
ROBOTS_RECORD = "_robots.json"

COLUMNS = [
    "period",
    "sector",
    "balance_bn_vnd",
    "growth_vs_prev_year_end_pct",
    "comparison_base",
    "source_url",
    "evidence",
]

CAPTION_RE = re.compile(
    r"\((?:Tháng|THÁNG)\s*(\d{1,2})\s*(?:Năm|năm)\s*(\d{4})\)", re.I
)

_last_request_at = 0.0


class RobotsDenied(RuntimeError):
    pass


class FetchError(RuntimeError):
    pass


def _throttle(delay: float, sleep) -> None:
    global _last_request_at
    if delay > 0:
        wait = delay - (time.monotonic() - _last_request_at)
        if wait > 0:
            sleep(wait)


def fetch_url(
    url: str,
    *,
    opener=urllib.request.urlopen,
    retries: int = RETRIES,
    sleep=time.sleep,
    delay: float = DELAY,
    timeout: int = 60,
) -> bytes:
    global _last_request_at
    last_error: Exception | None = None
    for attempt in range(retries):
        _throttle(delay, sleep)
        _last_request_at = time.monotonic()
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with opener(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt + 1 < retries:
                sleep(2**attempt)
    raise FetchError(f"GET {url} failed after {retries} attempts: {last_error}") from last_error


def check_robots(
    *,
    out_dir: Path | str = OUT_DIR,
    opener=urllib.request.urlopen,
    sleep=time.sleep,
    delay: float = DELAY,
) -> bool:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = fetch_url(ROBOTS_URL, opener=opener, retries=2, sleep=sleep, delay=delay)
    robots = urllib.robotparser.RobotFileParser()
    robots.parse(body.decode("utf-8", errors="replace").splitlines())
    allowed = robots.can_fetch(USER_AGENT, PAGE_URL)
    record = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "robots_url": ROBOTS_URL,
        "user_agent": USER_AGENT,
        "allowed": allowed,
        "crawl_delay": robots.crawl_delay(USER_AGENT),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    (out_dir / ROBOTS_RECORD).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not allowed:
        raise RobotsDenied(f"robots.txt at {ROBOTS_URL} does not allow {PAGE_URL}")
    return True


def _caption(table) -> tuple[str, str, str] | None:
    """Find the (Tháng X Năm YYYY) caption around a table, including its wrapper."""
    node = table
    for _ in range(4):
        if node is None:
            break
        text = node.text_content() if hasattr(node, "text_content") else ""
        match = CAPTION_RE.search(text)
        if match:
            return match.group(1), match.group(2), match.group(0)
        node = node.getparent()
    return None


def _normalise_table(df: pd.DataFrame) -> pd.DataFrame | None:
    """Turn either a clean header table or an SBV jrPage table into STT/Chỉ tiêu/Số dư/Tốc độ."""
    df = df.copy()
    names = [str(c).strip() for c in df.columns]
    if not (any(name == "STT" for name in names) and any("Chỉ tiêu" in name for name in names)):
        header_idx = None
        for i in range(min(len(df), 10)):
            cells = [str(value).strip() for value in df.iloc[i].tolist()]
            if cells and cells[0] == "STT" and any("Chỉ tiêu" in cell for cell in cells):
                header_idx = i
                break
        if header_idx is None:
            return None
        header = [str(value).strip() for value in df.iloc[header_idx].tolist()]
        df = df.iloc[header_idx + 1 :].copy()
        df.columns = header

    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, [name not in ("", "nan") for name in df.columns]]
    sector_col = next((c for c in df.columns if "Chỉ tiêu" in c), None)
    balance_col = next((c for c in df.columns if "Số dư" in c), None)
    growth_col = next((c for c in df.columns if "Tốc" in c and "%" in c), None)
    if not (sector_col and balance_col and growth_col):
        return None
    return df[[sector_col, balance_col, growth_col]]


def _to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in ("nan", "-", "--"):
        return None
    return parse_vn_number(text)[0]


def _clean_sector(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    text = re.sub(r"^[-\u2013\u2014]\s*", "", text)
    if not text or text.lower().startswith("ghi chú"):
        return None
    return text


def _comparison_base(header: str) -> str:
    match = re.search(r"so với\s+cuối năm\s+(.+?)\s*\(%\)", header, re.I)
    if match:
        return f"so với cuối năm {match.group(1).strip()}"
    return re.sub(r"\s+", " ", header).strip()


def parse_html(html: str, source_url: str = PAGE_URL) -> list[dict]:
    doc = lxml_html.fromstring(html)
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for table in doc.xpath("//table"):
        if not table.text_content().strip():
            continue
        caption = _caption(table)
        if caption is None:
            continue
        month, year, caption_text = caption
        try:
            parsed = pd.read_html(
                io.StringIO(lxml_html.tostring(table, encoding="unicode")),
                thousands=".",
                decimal=",",
            )
        except (ValueError, ImportError):
            continue
        if not parsed:
            continue
        df = _normalise_table(parsed[0])
        if df is None:
            continue
        sector_col, balance_col, growth_col = df.columns
        period = f"{int(year):04d}-{int(month):02d}"
        base = _comparison_base(str(growth_col))

        for _, record in df.iterrows():
            sector = _clean_sector(record[sector_col])
            balance = _to_float(record[balance_col])
            growth = _to_float(record[growth_col])
            if sector is None or balance is None or growth is None:
                continue
            key = (period, sector)
            if key in seen:
                continue
            seen.add(key)
            evidence = (
                f"{period} {caption_text} | {sector} | {balance:,.0f} tỷ đồng | "
                f"{growth:.2f}% ({base})"
            )
            rows.append(
                {
                    "period": period,
                    "sector": sector,
                    "balance_bn_vnd": balance,
                    "growth_vs_prev_year_end_pct": growth,
                    "comparison_base": base,
                    "source_url": source_url,
                    "evidence": evidence,
                }
            )

    if not rows:
        raise ValueError("no credit-by-sector rows found in page")
    return rows


def parse_file(path: str | Path, source_url: str = PAGE_URL) -> list[dict]:
    return parse_html(Path(path).read_text(encoding="utf-8"), source_url=source_url)


def write_csv(rows: list[dict], out_dir: Path | str = OUT_DIR) -> None:
    path = Path(out_dir) / CSV_NAME
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _cache_valid(raw: Path, sha: Path) -> bool:
    if not raw.exists():
        return False
    if not sha.exists():
        return True
    return sha.read_text(encoding="utf-8").strip() == hashlib.sha256(raw.read_bytes()).hexdigest()


def _cache_write(raw: Path, sha: Path, body: bytes) -> None:
    raw.write_bytes(body)
    sha.write_text(hashlib.sha256(body).hexdigest() + "\n", encoding="utf-8")


def run(
    *,
    refresh: bool = False,
    out_dir: Path | str = OUT_DIR,
    fetch_fn=None,
    robots_fn=None,
    sleep=time.sleep,
    delay: float = DELAY,
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if robots_fn is None:
        def robots_fn():
            return check_robots(out_dir=out_dir, sleep=sleep, delay=delay)

    robots_fn()
    raw = out_dir / f"{RAW_NAME}.html"
    sha = out_dir / f"{RAW_NAME}.html.sha256"
    fetched: list[str] = []
    cached: list[str] = []

    if not refresh and _cache_valid(raw, sha):
        body = raw.read_bytes()
        cached.append(RAW_NAME)
    else:
        body = (fetch_fn or (lambda url: fetch_url(url, sleep=sleep, delay=delay)))(PAGE_URL)
        _cache_write(raw, sha, body)
        fetched.append(RAW_NAME)

    rows = parse_html(body.decode("utf-8", errors="replace"), source_url=PAGE_URL)
    write_csv(rows, out_dir)
    return {"rows": len(rows), "fetched": fetched, "cached": cached}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-fetch the cached page")
    args = parser.parse_args(argv)
    summary = run(refresh=args.refresh)
    print(
        f"SBV: {summary['rows']} rows, {len(summary['fetched'])} fetched, "
        f"{len(summary['cached'])} cached"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
