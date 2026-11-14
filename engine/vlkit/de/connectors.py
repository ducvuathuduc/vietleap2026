"""Ingestion connectors — the five source types from the VietLeap DE workshop plus CV.

    file    csv/tsv/txt/xlsx/xls/json/jsonl/parquet/zip (encoding + delimiter sniffing, title rows skipped)
    api     REST JSON: paging (page / offset / next-link / World Bank), retry with backoff on 429/5xx,
            honours Retry-After, rate limit, on-disk cache (re-runs during the contest cost no quota)
    sql     any SQLAlchemy URL (sqlite / postgresql / mysql ...) — Python's "JDBC"; SELECT only, chunked
    scrape  HTML tables or CSS-selector records; robots.txt respected, polite delay, identifiable UA;
            Playwright only when options.render_js is true. Never bypasses captchas or logins.
    social  RSS/Atom feeds (news, YouTube channel feeds, subreddit .rss) and optional Google Trends
    cv      a counts CSV produced by scenarios/cv_counting/count.py (or the video itself → runs it)
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import re
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd

from .sources import IngestResult, Source, make_provenance

UA = "VietLeapInsightKit/1.0 (student hackathon research; contact: vietleap2026 participant)"
CACHE = Path(__file__).resolve().parents[3] / "data" / "cache"


# ----------------------------------------------------------------------------- file

def ingest_file(src: Source) -> IngestResult:
    from ..loader import read_any

    p = Path(src.uri)
    if not p.exists():
        raise FileNotFoundError(src.uri)
    frames: dict[str, pd.DataFrame] = {}
    log: list[str] = []
    if p.suffix.lower() == ".zip":
        tmp = CACHE / "unzipped" / p.stem
        tmp.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(p) as z:
            z.extractall(tmp)
        for f in sorted(tmp.rglob("*")):
            if f.suffix.lower() in (".csv", ".tsv", ".txt", ".xlsx", ".xls", ".json", ".jsonl", ".parquet"):
                frames[_tname(f.stem)] = read_any(f, log=log)
    elif p.suffix.lower() in (".xlsx", ".xls", ".xlsm") and src.options.get("all_sheets", True):
        xl = pd.ExcelFile(p)
        if len(xl.sheet_names) == 1 or src.options.get("sheet"):
            frames[src.name] = read_any(p, sheet=src.options.get("sheet"), log=log)
        else:
            for sh in xl.sheet_names:
                try:
                    frames[f"{src.name}__{_tname(sh)}"] = read_any(p, sheet=sh, log=log)
                except ValueError:
                    log.append(f"sheet {sh}: empty")
    elif p.suffix.lower() == ".jsonl":
        frames[src.name] = pd.read_json(p, lines=True)
    else:
        frames[src.name] = read_any(p, log=log)
    return IngestResult(src, frames, make_provenance(src, frames, read_log=log, bytes=p.stat().st_size))


# ----------------------------------------------------------------------------- api

def _cache_key(url: str, params: dict) -> Path:
    h = hashlib.sha1((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:20]
    return CACHE / "api" / f"{h}.json"


def _get_json(client, url: str, params: dict, min_interval: float, use_cache: bool):
    from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential
    import httpx

    ck = _cache_key(url, params)
    if use_cache and ck.exists():
        return json.loads(ck.read_text(encoding="utf-8")), True

    def _retryable(e):
        return isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (429, 500, 502, 503, 504) \
            or isinstance(e, httpx.TransportError)

    @retry(retry=retry_if_exception(_retryable), wait=wait_exponential(multiplier=1, min=1, max=30),
           stop=stop_after_attempt(5), reraise=True)
    def _do():
        r = client.get(url, params=params)
        if r.status_code == 429 and "retry-after" in r.headers:
            try:
                time.sleep(min(60, float(r.headers["retry-after"])))
            except ValueError:
                pass
        r.raise_for_status()
        return r.json()

    data = _do()
    time.sleep(min_interval)
    ck.parent.mkdir(parents=True, exist_ok=True)
    ck.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data, False


def _dig(obj, path: str | None):
    if not path:
        return obj
    for part in str(path).split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj.get(part)
        if obj is None:
            return []
    return obj


def ingest_api(src: Source, client=None) -> IngestResult:
    """options: params, headers, records_path ("data.items" / "1"), paging (none|page|offset|next|worldbank),
    page_param, size_param, page_size, max_pages, rate_per_sec, cache (default true), auth_env (env var name
    holding a bearer token — never hard-code keys)."""
    import os
    import httpx

    o = src.options
    headers = {"User-Agent": UA, **o.get("headers", {})}
    if o.get("auth_env") and os.environ.get(o["auth_env"]):
        headers["Authorization"] = f"Bearer {os.environ[o['auth_env']]}"
    own = client is None
    client = client or httpx.Client(headers=headers, timeout=30, follow_redirects=True)
    paging, params = o.get("paging", "none"), dict(o.get("params", {}))
    min_interval = 1.0 / float(o.get("rate_per_sec", 2))
    max_pages, size = int(o.get("max_pages", 50)), int(o.get("page_size", 100))
    rows, pages, cached_pages, url = [], 0, 0, src.uri
    try:
        while url and pages < max_pages:
            data, cached = _get_json(client, url, params, min_interval, o.get("cache", True))
            pages += 1
            cached_pages += cached
            recs = _dig(data, o.get("records_path"))
            if isinstance(recs, dict):
                recs = [recs]
            rows.extend(recs or [])
            if paging == "worldbank":            # [ {page, pages, ...}, [records] ]
                meta = data[0] if isinstance(data, list) and data else {}
                if int(meta.get("page", 1)) >= int(meta.get("pages", 1)):
                    break
                params["page"] = int(meta.get("page", 1)) + 1
            elif paging == "page":
                if not recs or len(recs) < size:
                    break
                params[o.get("page_param", "page")] = params.get(o.get("page_param", "page"), 1) + 1
                params[o.get("size_param", "per_page")] = size
            elif paging == "offset":
                if not recs or len(recs) < size:
                    break
                params[o.get("page_param", "offset")] = params.get(o.get("page_param", "offset"), 0) + size
                params[o.get("size_param", "limit")] = size
            elif paging == "next":
                nxt = _dig(data, o.get("next_path", "next"))
                url, params = (nxt if isinstance(nxt, str) and nxt else None), {}
            else:
                break
    finally:
        if own:
            client.close()
    df = pd.json_normalize(rows, sep="__") if rows else pd.DataFrame()
    frames = {src.name: df}
    return IngestResult(src, frames, make_provenance(src, frames, pages=pages, cached_pages=cached_pages))


# ----------------------------------------------------------------------------- sql

_WRITE = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|merge|replace)\b", re.I)


def ingest_sql(src: Source) -> IngestResult:
    """uri: SQLAlchemy URL. options: query (SELECT ...) or tables: [..], chunksize."""
    from sqlalchemy import create_engine, inspect, text

    eng = create_engine(src.uri)
    o, frames = src.options, {}
    queries = {}
    if o.get("query"):
        queries[src.name] = o["query"]
    for t in o.get("tables") or ([] if o.get("query") else inspect(eng).get_table_names()):
        queries[f"{src.name}__{_tname(t)}"] = f'SELECT * FROM "{t}"'
    with eng.connect() as con:
        for name, q in queries.items():
            if _WRITE.search(q):
                raise PermissionError(f"read-only connector: refused query for {name}")
            chunks = pd.read_sql(text(q), con, chunksize=int(o.get("chunksize", 50_000)))
            frames[name] = pd.concat(list(chunks), ignore_index=True)
    eng.dispose()
    safe_uri = re.sub(r"//[^@/]+@", "//***@", src.uri)  # never store credentials in provenance
    prov = make_provenance(src, frames, queries=queries)
    prov["uri"] = safe_uri
    return IngestResult(src, frames, prov)


# ----------------------------------------------------------------------------- scrape

def robots_allows(url: str, client=None) -> bool:
    u = urlparse(url)
    rp = RobotFileParser()
    try:
        import httpx
        r = (client or httpx).get(f"{u.scheme}://{u.netloc}/robots.txt", headers={"User-Agent": UA}, timeout=10)
        if r.status_code >= 400:
            return True
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, url)
    except Exception:
        return True


def _html_tables(html: str) -> list[pd.DataFrame]:
    try:
        return pd.read_html(io.StringIO(html))
    except ValueError:
        return []


def ingest_scrape(src: Source, client=None) -> IngestResult:
    """options: urls (list, else [uri]), table_index (int|'all'|'largest', default largest), or records: {item: css, fields: {col: css}},
    next_css (pagination link), max_pages, delay [min,max], render_js (Playwright)."""
    import httpx

    o = src.options
    urls = list(o.get("urls") or [src.uri])
    lo, hi = o.get("delay", [1.0, 3.0])
    own = client is None
    client = client or httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
    frames, visited, skipped = {}, [], []
    recs: list[dict] = []
    try:
        pages = 0
        while urls and pages < int(o.get("max_pages", 20)):
            url = urls.pop(0)
            if not robots_allows(url, client):
                skipped.append(url)
                continue
            html = _render(url) if o.get("render_js") else client.get(url).text
            visited.append(url)
            pages += 1
            if "records" in o:
                from selectolax.parser import HTMLParser
                tree = HTMLParser(html)
                for node in tree.css(o["records"]["item"]):
                    row = {}
                    for col, sel in o["records"]["fields"].items():
                        attr = None
                        if "@" in sel:
                            sel, attr = sel.split("@", 1)
                        n = node.css_first(sel) if sel else node
                        row[col] = (n.attributes.get(attr) if attr else n.text(strip=True)) if n else None
                    row["_page"] = url
                    recs.append(row)
                if o.get("next_css"):
                    n = tree.css_first(o["next_css"])
                    if n and n.attributes.get("href"):
                        urls.append(urljoin(url, n.attributes["href"]))
            else:
                tabs = _html_tables(html)
                idx = o.get("table_index", "largest")
                if idx == "largest" and tabs:
                    pick = [max(range(len(tabs)), key=lambda i: tabs[i].size)]
                else:
                    pick = range(len(tabs)) if idx == "all" else [int(idx)]
                for i in pick:
                    if i < len(tabs):
                        key = src.name if len(pick) == 1 and len(visited) == 1 else f"{src.name}__p{len(visited)}_t{i}"
                        frames[key] = tabs[i]
            if urls:
                time.sleep(random.uniform(lo, hi))
    finally:
        if own:
            client.close()
    if recs:
        frames[src.name] = pd.DataFrame(recs)
    return IngestResult(src, frames, make_provenance(src, frames, visited=visited, robots_disallowed=skipped))


def _render(url: str) -> str:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=UA)
        pg.goto(url, wait_until="networkidle", timeout=45_000)
        html = pg.content()
        b.close()
    return html


# ----------------------------------------------------------------------------- social listening

def ingest_social(src: Source) -> IngestResult:
    """uri: an RSS/Atom feed, or 'trends:<kw1>|<kw2>' (needs pytrends; Google rate-limits hard).
    options.feeds: extra feed URLs. Output: one row per post (title, summary, published, link, feed)."""
    if src.uri.startswith("trends:"):
        from pytrends.request import TrendReq  # optional dependency
        kws = src.uri.split(":", 1)[1].split("|")
        py = TrendReq(hl="vi-VN", tz=-420)
        py.build_payload(kws, geo=src.options.get("geo", "VN"), timeframe=src.options.get("timeframe", "today 12-m"))
        df = py.interest_over_time().reset_index()
        frames = {src.name: df}
        return IngestResult(src, frames, make_provenance(src, frames, note="Google Trends index 0-100 within request"))
    import feedparser
    rows = []
    for feed_url in [src.uri, *src.options.get("feeds", [])]:
        f = feedparser.parse(feed_url, agent=UA)
        for e in f.entries:
            rows.append({"feed": feed_url, "title": e.get("title"), "summary": re.sub("<[^>]+>", " ", e.get("summary", "") or "").strip(),
                         "published": e.get("published") or e.get("updated"), "link": e.get("link"),
                         "author": e.get("author")})
    frames = {src.name: pd.DataFrame(rows)}
    return IngestResult(src, frames, make_provenance(src, frames))


# ----------------------------------------------------------------------------- cv

def ingest_cv(src: Source) -> IngestResult:
    """uri: counts CSV from scenarios/cv_counting/count.py, or a video file (then count.py is run first)."""
    p = Path(src.uri)
    if p.suffix.lower() in (".mp4", ".avi", ".mov", ".mkv"):
        import subprocess, sys
        out = CACHE / "cv" / f"{p.stem}_counts.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        script = Path(__file__).resolve().parents[3] / "scenarios" / "cv_counting" / "count.py"
        args = [sys.executable, str(script), "--video", str(p), "--out", str(out)]
        for k, v in src.options.items():
            args += [f"--{k}", str(v)]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:  # e.g. 2 = ultralytics/supervision not installed (count.py explains how to fix)
            raise RuntimeError(f"count.py failed (exit {r.returncode}): {(r.stderr or r.stdout).strip()[-800:]}")
        p = out
    frames = {src.name: pd.read_csv(p)}
    return IngestResult(src, frames, make_provenance(src, frames))


# ----------------------------------------------------------------------------- dispatch

CONNECTORS = {"file": ingest_file, "api": ingest_api, "sql": ingest_sql, "scrape": ingest_scrape,
              "social": ingest_social, "cv": ingest_cv}


def ingest(src: Source) -> IngestResult:
    return CONNECTORS[src.kind](src)


def _tname(s: str) -> str:
    from ..vn import ascii_key
    return re.sub(r"[^a-z0-9]+", "_", ascii_key(str(s))).strip("_")[:48] or "t"
