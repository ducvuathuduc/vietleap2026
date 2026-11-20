"""Harvest the five notes inputs (loans, groups 1-5, provision movement, write-offs) from statement PDFs.

One bank-quarter is: find the statement PDF, cache it in bronze (a URL is fetched once, ever), read every page
two ways (the cell grid and the plain text, or two vision prompts when the PDF is a scan), grade each number,
convert YTD flows to single-quarter values, run the three quality gates and write one long silver row per
number. Silver is incremental by watermark: a bank-quarter that is already graded verified or single is not
read again unless `refresh` is set, so the table can be filled bank by bank across many runs.
"""

from datetime import date
import hashlib
import json
from pathlib import Path
import time

import httpx
import pandas as pd

from .extra_landing import FetchError, read_silver, write_silver
from .files import atomic, now
from .notes_contract import FIELDS, SILVER_COLUMNS, grade, kind_of, to_quarterly, unit_scale
from .notes_gates import run_gates
from .notes_links import (CATALOGUE, COLUMNS as LINK_COLUMNS, agent_goal, agent_schema,
                          prefer_consolidated, rows_from_agent, rows_from_page)
from .notes_pages import has_text_layer, page_png, page_tables, page_texts, text_pages
from .notes_text import read_tables, read_text
from .notes_vision import VisionReader, read_page
from .runner import LAKE, ROOT
from .watermark import load, quarter_periods, save

LARGE = ("VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "STB")
SILVER = "notes_bank_quarter.parquet"
GATES = "notes_gate.csv"
LINKS = "notes_links.csv"
FIRST_QUARTER = "2021Q1"
STORE = "bronze/notes/store"
VISION_PAGE_CAP = 40
GRADE_ORDER = {"verified": 0, "single": 1, "contested": 2}
FETCH_ERRORS = (FetchError, httpx.HTTPError)   # the retry gave up, or the host answered 404/403


def digest(content):
    return hashlib.sha256(content).hexdigest()


def quarters(first=FIRST_QUARTER, last=None, lake=LAKE):
    """Every quarter from `first` to `last` (default: the latest period the vendor panel knows)."""
    last = last or latest_vendor_period(lake)
    return quarter_periods(first, last, None)


def notes_periods(spec, lake=LAKE):
    """['2021Q1', ..., last] from a 'first:last' string, or the full default range when `spec` is empty."""
    if not spec:
        return quarters(lake=lake)
    first, _, last = str(spec).partition(":")
    return quarters(first.strip(), (last or "").strip() or None, lake=lake)


def tinyfish_agent(bank, max_usd=2.0, deadline_s=300.0):
    """TinyFish records for one bank's JS-only statement page (empty when there is no page or no key)."""
    from ...de import tinyfish

    page = CATALOGUE.get(bank)
    if page is None:
        return []
    outcome = tinyfish.run_goal(page, agent_goal(bank), output_schema=agent_schema(), deadline_s=deadline_s,
                                max_usd=max_usd, source=f"notes-links-{bank}")
    return outcome.records


def latest_vendor_period(lake=LAKE):
    frame = read_silver(lake, "bank_quarter.parquet")
    return str(frame["period"].max()) if frame is not None and len(frame) else FIRST_QUARTER


def vendor_npl(lake=LAKE):
    """(bank, period) -> vendor NPL percent, for the third gate."""
    frame = read_silver(lake, "bank_quarter.parquet")
    if frame is None or "npl" not in frame:
        return {}
    return {(str(row.ticker), str(row.period)): float(row.npl) for row in frame.itertuples() if pd.notna(row.npl)}


def store_path(lake, url):
    return Path(lake) / STORE / f"{hashlib.sha1(url.encode()).hexdigest()[:16]}.pdf"


def cached_pdf(lake, fetcher, url, run_id):
    """PDF bytes for `url` from the bronze store, fetched at most once per URL across every run."""
    path = store_path(lake, url)
    meta_path = path.with_suffix(".meta.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return path.read_bytes(), {**meta, "cached": True}
    response = fetcher.get(url)
    content = response.content
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic(path, content)
    meta = {"url": url, "sha256": digest(content), "bytes": len(content), "run_id": run_id,
            "fetched_at": now().isoformat(timespec="seconds"), "cached": False}
    atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
    return content, meta


def collect(readings, bank, period, url, sha):
    """Silver rows for one bank-quarter: one row per field, graded over its readers."""
    by_field = {}
    for reading in readings:
        by_field.setdefault(reading["field"], []).append(reading)
    rows = []
    for field in FIELDS:
        found = by_field.get(field) or []
        value_grade, value = grade([(item["reader"], item["value_vnd_bn"]) for item in found])
        if value_grade is None:
            continue
        page = next((item["page"] for item in found if item["value_vnd_bn"] == value), found[0]["page"])
        rows.append({"bank": bank, "period": period, "field": field,
                     "basis": "point" if kind_of(field) == "balance" else "ytd",
                     "value_vnd_bn": value, "page": int(page), "source_url": url, "reader": ",".join(
                         sorted({item["reader"] for item in found})), "grade": value_grade,
                     "raw_sha256": sha})
    return rows


def read_pdf(content, vision=None, use_vision=True, page_cap=VISION_PAGE_CAP):
    """(readings, errors) for one PDF: the two text readers on a text layer, two vision prompts on a scan."""
    texts = page_texts(content)
    readings, errors = [], {}
    if has_text_layer(texts):
        scales = {index: unit_scale(text) for index, text in enumerate(texts, start=1)}
        for reader, values in (("text", read_text(texts)), ("table", read_tables(page_tables(content), scales))):
            for field, item in values.items():
                readings.append({"field": field, **item})
        if not readings:
            errors["text"] = f"text layer on {len(texts)} pages but no label matched"
        return readings, errors
    if not use_vision or vision is None:
        errors["scan"] = f"no text layer on {len(texts)} pages and the vision reader is off"
        return readings, errors
    for page in range(1, min(len(texts), page_cap) + 1):
        try:
            png = page_png(content, page)
        except Exception as exc:            # a broken page does not lose the rest of the statement
            errors[f"page {page}"] = f"render failed: {type(exc).__name__}"
            continue
        page_readings, page_errors = read_page(vision, png, page)
        readings.extend(page_readings)
        errors.update({f"page {page} {key}": value for key, value in page_errors.items()})
    return readings, errors


def harvest(lake, links, fetcher, run_id, vision=None, use_vision=True, refresh=False, existing=None,
            vendor=None):
    """Read every linked PDF and return (silver rows, gate table, stats). Never writes: the caller does."""
    lake = Path(lake)
    stats = {"linked": len(links), "fetched": 0, "cached": 0, "read": 0, "skipped_done": 0,
             "no_text_layer": 0, "vision_calls": 0}
    errors, rows = {}, []
    done = set()
    if existing is not None and len(existing) and not refresh:
        done = {(str(bank), str(period)) for bank, period in
                existing[existing["grade"].isin(["verified", "single"])][["bank", "period"]].values.tolist()}
    for link in links.to_dict("records") if len(links) else []:
        bank, period = str(link["bank"]), str(link["period"])
        if (bank, period) in done:
            stats["skipped_done"] += 1
            continue
        try:
            content, meta = cached_pdf(lake, fetcher, link["url"], run_id)
        except FETCH_ERRORS as exc:
            errors[f"{bank} {period}"] = str(exc)[:140]
            continue
        stats["cached" if meta.get("cached") else "fetched"] += 1
        calls_before = len(getattr(vision, "calls", []))
        try:
            readings, page_errors = read_pdf(content, vision=vision, use_vision=use_vision)
        except Exception as exc:            # an unreadable PDF is a logged outcome, never a crashed run
            errors[f"{bank} {period}"] = f"unreadable: {type(exc).__name__}: {str(exc)[:100]}"
            continue
        if page_errors:
            errors[f"{bank} {period}"] = dict(list(page_errors.items())[:4])
        stats["vision_calls"] += len(getattr(vision, "calls", [])) - calls_before
        rows.extend(collect(readings, bank, period, link["url"], meta["sha256"]))
        if readings:
            stats["read"] += 1
        else:
            stats["no_text_layer"] += 1
    frame = pd.DataFrame(rows, columns=SILVER_COLUMNS)
    if len(frame):
        frame = pd.DataFrame(to_quarterly(frame.to_dict("records")), columns=SILVER_COLUMNS)
        frame["value_vnd_bn"] = pd.to_numeric(frame["value_vnd_bn"])
        frame["page"] = pd.to_numeric(frame["page"])
    gates, gate_stats = run_gates(frame, vendor=vendor)
    stats["gates"] = gate_stats
    if errors:
        stats["errors"] = dict(list(errors.items())[:10])
    return frame, gates, stats


def merge_silver(existing, new):
    """Union by (bank, period, field, basis); the better grade wins, then the later row."""
    frames = [frame for frame in (existing, new) if frame is not None and len(frame)]
    if not frames:
        return pd.DataFrame(columns=SILVER_COLUMNS)
    merged = pd.concat(frames, ignore_index=True)
    merged["_grade"] = merged["grade"].map(GRADE_ORDER).fillna(3)
    merged = merged.sort_values(["bank", "period", "field", "basis", "_grade"], ascending=[True, True, True, True, False],
                                kind="mergesort")
    merged = merged.drop_duplicates(["bank", "period", "field", "basis"], keep="last").drop(columns="_grade")
    return merged.sort_values(["bank", "period", "field", "basis"], ignore_index=True)[SILVER_COLUMNS]


def links_from_sources(lake, banks, fetcher, run_id, agent=None, today=None):
    """Links from the saved register, then the readable IR pages, then the agent for pages that need it."""
    found = []
    saved = read_silver(lake, LINKS)
    if saved is not None and len(saved) and "bank" in saved:
        found.extend(saved[saved["bank"].isin(list(banks))].to_dict("records"))
    known = {(str(row["bank"]), str(row["period"])) for row in found}
    errors = {}
    for bank in banks:
        if any(row["bank"] == bank for row in found):
            continue
        page = CATALOGUE.get(bank)
        if page is None:
            errors[bank] = "no investor-relations page in the catalogue"
            continue
        try:
            html = fetcher.get(page).text
        except FETCH_ERRORS as exc:
            errors[bank] = str(exc)[:120]
            continue
        rows = [row for row in rows_from_page(bank, html, page, found_at=now().isoformat(timespec="seconds"))
                if (bank, row["period"]) not in known]
        found.extend(rows)
        if not rows and agent is not None:
            try:
                records = agent(bank)
            except Exception as exc:        # the agent's failure is a logged outcome
                errors[bank] = f"agent: {type(exc).__name__}: {str(exc)[:100]}"
                continue
            found.extend(rows_from_agent(bank, records, found_at=now().isoformat(timespec="seconds")))
    frame = prefer_consolidated(found)
    return frame[frame["bank"].isin(list(banks))] if len(frame) else frame, errors


def coverage(frame, banks=None, periods=None):
    """Bank x period -> (fields read, verified share) for the report and the run log."""
    if frame is None or not len(frame):
        return pd.DataFrame(columns=["bank", "period", "fields", "verified_share"])
    table = frame.groupby(["bank", "period"]).agg(
        fields=("field", "nunique"), verified=("grade", lambda s: int((s == "verified").sum())),
        rows=("field", "size")).reset_index()
    table["verified_share"] = (table["verified"] / table["rows"]).round(3)
    return table[["bank", "period", "fields", "verified_share"]]


def run_notes(lake=LAKE, banks=None, periods=None, fetcher=None, vision=None, use_vision=True, refresh=False,
              agent=None, links_only=False, today=None):
    """One notes run: discover links, read what is new, write silver + gates + run log + watermark."""
    started = time.monotonic()
    lake = Path(lake)
    run_id = "notes-" + now().strftime("%Y%m%dT%H%M%S")
    banks = list(banks or LARGE)
    periods = list(periods or quarters(lake=lake))
    from .extra_landing import Fetcher

    fetcher = fetcher or Fetcher(lake=lake, run_id=run_id)
    vision = vision if vision is not None else VisionReader()
    log = {"run_id": run_id, "started_at": now().isoformat(timespec="seconds"), "banks": banks,
           "periods": [periods[0], periods[-1]], "errors": {}, "datasets": {}}
    links, link_errors = links_from_sources(lake, banks, fetcher, run_id, agent=agent, today=today)
    if len(links):
        links = links[links["period"].isin(periods)]
        write_silver(lake, LINKS, links, {"rows": len(links)})
    log["links"] = {"rows": len(links), "banks": int(links["bank"].nunique()) if len(links) else 0,
                    "periods": int(links["period"].nunique()) if len(links) else 0}
    if link_errors:
        log["errors"]["links"] = dict(list(link_errors.items())[:10])
    if links_only:
        log["elapsed_s"] = round(time.monotonic() - started, 3)
        atomic(lake / "run_log" / f"{run_id}.json",
               json.dumps(log, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
        return log
    existing = read_silver(lake, SILVER)
    frame, gates, stats = harvest(lake, links, fetcher, run_id, vision=vision, use_vision=use_vision,
                                  refresh=refresh, existing=existing, vendor=vendor_npl(lake))
    merged = merge_silver(existing, frame)
    if len(merged):
        write_silver(lake, SILVER, merged, {"run_id": run_id})
    if len(gates):
        write_silver(lake, GATES, gates, {"run_id": run_id})
    if len(merged):                     # an empty run must not move (or invent) the watermark
        marks = load(lake / "state/watermarks.json")
        marks["notes_bank_quarter"] = str(merged["period"].max())
        marks["notes_bank_last"] = {bank: str(block["period"].max()) for bank, block in merged.groupby("bank")}
        save(lake / "state/watermarks.json", marks)
    log["datasets"]["notes"] = stats
    log["silver"] = {"rows": len(merged), "banks": int(merged["bank"].nunique()) if len(merged) else 0,
                     "periods": int(merged["period"].nunique()) if len(merged) else 0,
                     "verified_share": round(float((merged["grade"] == "verified").mean()), 4) if len(merged) else 0}
    log["coverage"] = coverage(frame).to_dict("records")[:40]
    log["spend_usd"] = {"openai": round(getattr(vision, "cost_usd", 0.0), 4)}
    log["http_calls"] = len(getattr(fetcher, "calls", []))
    log["elapsed_s"] = round(time.monotonic() - started, 3)
    atomic(lake / "run_log" / f"{run_id}.json",
           json.dumps(log, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    return log
