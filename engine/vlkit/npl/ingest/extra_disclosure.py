"""Actual publication dates of the banks' quarterly financial statements, from HOSE's public news feeds.

The exchange publishes disclosures as RSS feeds under api.hsx.vn. The register keeps only items whose
title names a listed bank ticker and a quarterly financial statement; every other disclosure is dropped.
Coverage is reported as-is: a quarter with no matching item simply stays missing, nothing is inferred.
"""

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from xml.etree import ElementTree

import pandas as pd

from .extra_landing import FetchError, land, write_silver

FEED_INDEX = "https://api.hsx.vn/n/api/v1/News/NewsFeed"
COLUMNS = ["ticker", "period", "published_at", "url"]
STATEMENT = re.compile(r"báo cáo tài chính|bao cao tai chinh", re.I)
QUARTER = re.compile(r"quý\s*(I{1,3}V?|IV|[1-4])|(?:\bQ)([1-4])\b", re.I)
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4}


def period_of(title, year):
    """Quarter label ('2024Q3') from a disclosure title, or None when the title names no quarter."""
    match = QUARTER.search(title)
    if match is None or not year:
        return None
    token = (match.group(1) or match.group(2) or "").lower()
    quarter = ROMAN.get(token) or (int(token) if token.isdigit() else None)
    return f"{year}Q{quarter}" if quarter else None


def parse_feed(xml, tickers):
    """Rows (ticker, period, published_at, url) for quarterly financial-statement disclosures."""
    root = ElementTree.fromstring(xml if isinstance(xml, (str, bytes)) else xml.read())
    rows = {}
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        stamp = (item.findtext("pubDate") or "").strip()
        upper = title.upper()
        ticker = next((code for code in tickers if re.search(rf"\b{code}\b", upper)), None)
        if not ticker or not STATEMENT.search(title):
            continue
        try:
            published = parsedate_to_datetime(stamp).astimezone(timezone.utc).date().isoformat()
        except (TypeError, ValueError):
            continue
        period = period_of(title, published[:4])
        if period is None:
            continue
        rows.setdefault((ticker, period), {"ticker": ticker, "period": period,
                                           "published_at": published, "url": link})
    return pd.DataFrame(list(rows.values()), columns=COLUMNS).sort_values(
        ["ticker", "period"], ignore_index=True)


def feeds(index_xml, base=FEED_INDEX):
    """Feed URLs advertised by the HOSE RSS index (title + absolute link)."""
    root = ElementTree.fromstring(index_xml if isinstance(index_xml, (str, bytes)) else index_xml.read())
    found = []
    for item in root.iter("item"):
        link = urljoin(base, (item.findtext("link") or "").strip())
        if link and link != base:
            found.append((item.findtext("title") or "", link))
    return [link for _, link in found]


def run(lake, fetcher, run_id, tickers):
    errors, frames, advertised = {}, [], 0
    try:
        index = fetcher.get(FEED_INDEX)
    except FetchError as exc:
        errors["index"] = str(exc)[:160]
        index = None
    if index is not None:
        land(lake, run_id, "disclosure", "index", index.content, "xml", {"url": FEED_INDEX})
        found = feeds(index.content, FEED_INDEX)
        advertised = len(found)
        for url in found[:20]:
            try:
                response = fetcher.get(url)
            except FetchError as exc:
                errors[url] = str(exc)[:120]
                continue
            land(lake, run_id, "disclosure", url, response.content, "xml", {"url": url, "feed": True})
            try:
                frames.append(parse_feed(response.content, tickers))
            except ElementTree.ParseError:
                errors[url] = "not RSS"
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    if len(frame):
        frame = frame.drop_duplicates(["ticker", "period"], keep="last").sort_values(
            ["ticker", "period"], ignore_index=True)
    write_silver(lake, "disclosure_dates.csv", frame, {"feeds": len(frames)})
    stats = {"rows": len(frame), "tickers_covered": int(frame["ticker"].nunique()) if len(frame) else 0,
             "periods": sorted(frame["period"].unique())[:3] + sorted(frame["period"].unique())[-1:]
             if len(frame) else [], "feeds_read": len(frames), "feeds_advertised": advertised}
    if errors:
        stats["errors"] = dict(list(errors.items())[:6])
    return frame, stats
