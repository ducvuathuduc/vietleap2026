"""Harvest the five notes inputs (loans, groups 1-5, provision movement, write-offs) from statement PDFs.

One bank-quarter is: find the statement PDF, cache it in bronze (a URL is fetched once, ever), read every page
two ways (the cell grid and the plain text, or two vision prompts when the PDF is a scan), grade each number,
convert YTD flows to single-quarter values, run the three quality gates and write one long silver row per
number. Silver is incremental by watermark: a bank-quarter that is already graded verified or single is not
read again unless `refresh` is set, so the table can be filled bank by bank across many runs.
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import threading
import time

import httpx
import pandas as pd

from .extra_landing import FetchError, read_silver, write_silver
from .files import atomic, now
from .notes_text import signed
from .notes_contract import GROUP_FIELDS, NPL_FIELDS

PROVISION_MOVEMENT_LITE = ("provision_opening", "provision_charge", "provision_used_writeoff")
from .notes_contract import (FIELDS, SILVER_COLUMNS, agreement, grade, kind_of, to_quarterly,
                             unit_scale)
from .notes_gates import GATE_COLUMNS, GROUP_TOL, ROLLFORWARD_TOL, run_gates
from .notes_links import (CATALOGUE, COLUMNS as LINK_COLUMNS, agent_goal, agent_schema, hits_only,
                          prefer_consolidated, probe_statement, rows_from_agent, rows_from_page,
                          vietstock_annual_urls)
from .notes_pages import (fast_page_texts, has_text_layer, page_png, page_tables, page_texts, render_pages,
                          render_strip, text_pages)
from .notes_text import read_tables, read_text
from .notes_vision import (LOCATE_PROMPT, LOCATE_SCHEMA, MODEL_A, MODEL_LOCATE, VisionError,
                          VisionReader, pages_from_locate, read_page)
from .runner import LAKE, ROOT
from .watermark import load, quarter_periods, save

LARGE = ("VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "STB")
SILVER = "notes_bank_quarter.parquet"
GATES = "notes_gate.csv"
LINKS = "notes_links.csv"
FIRST_QUARTER = "2021Q1"
STORE = "bronze/notes/store"
VISION_PAGE_CAP = 90
STRIP = 6                      # pages per locator image (a legible thumbnail grid: 0.7 scale, 3x2 tiles)
STRIP_SCALE = 0.7
PAGES_PER_STATEMENT = 8        # pages given to the two readers: classification, provision movement, balance sheet
PAGE_WORKERS = int(os.getenv("NOTES_PAGE_WORKERS", "3"))   # pages read in parallel (6 vision calls at a time overall)
VISION_BUDGET_USD = 40.0
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
    """(bank, period) -> vendor NPL in percent, for the third gate.

    The vendor stores the ratio as a fraction (VCB 2026Q3 = 0.007058), so a value at or below 1 is multiplied by
    100. A vendor column that already prints percent would exceed 1 everywhere and is left alone.
    """
    frame = read_silver(lake, "bank_quarter.parquet")
    if frame is None or "npl" not in frame:
        return {}
    values = pd.to_numeric(frame["npl"], errors="coerce")
    scale = 100.0 if values.dropna().le(1).all() else 1.0
    return {(str(row.ticker), str(row.period)): float(row.npl) * scale
            for row in frame.itertuples() if pd.notna(row.npl)}


def store_path(lake, url):
    return Path(lake) / STORE / f"{hashlib.sha1(url.encode()).hexdigest()[:16]}.pdf"


STORE_LOCK = threading.Lock()


def cached_pdf(lake, fetcher, url, run_id):
    """PDF bytes for `url` from the bronze store, fetched at most once per URL across every run."""
    path = store_path(lake, url)
    meta_path = path.with_suffix(".meta.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return path.read_bytes(), {**meta, "cached": True}
    response = fetcher.get(url)
    content = response.content
    with STORE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic(path, content)
        meta = {"url": url, "sha256": digest(content), "bytes": len(content), "run_id": run_id,
                "fetched_at": now().isoformat(timespec="seconds"), "cached": False}
        atomic(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
    return content, meta


def _candidates(readings):
    """field -> [{grade, value, page, readers}] with one entry per (field, page), graded over that page's readers."""
    by_page = {}
    for reading in readings:
        by_page.setdefault((reading["field"], int(reading["page"])), []).append(reading)
    per_field = {}
    for (field, page), found in by_page.items():
        value_grade, value = grade([(item["reader"], signed(field, item["value_vnd_bn"])) for item in found])
        if value_grade is None:
            continue
        per_field.setdefault(field, []).append({"grade": value_grade, "value": value, "page": page,
                                                "readers": sorted({item["reader"] for item in found})})
    for entries in per_field.values():
        entries.sort(key=lambda item: (GRADE_ORDER[item["grade"]], -item["page"]))
    return per_field


def _group_sums(per_field):
    """[(page, sum of groups 1-5 on that page)] for every page that carries all five groups."""
    pages = {}
    for field in GROUP_FIELDS:
        for entry in per_field.get(field) or []:
            pages.setdefault(entry["page"], {})[field] = entry["value"]
    return [(page, sum(values.values())) for page, values in pages.items() if len(values) == len(GROUP_FIELDS)]


COVERAGE_RANGE = (0.05, 20.0)     # a loan-loss provision balance between 5% and 2000% of the NPL it covers


def _npl_total(per_field):
    """The NPL (groups 3-5) total on the page that carries the most of them, or 0 when the notes are missing."""
    pages = {}
    for field in NPL_FIELDS:
        for entry in per_field.get(field) or []:
            pages.setdefault(entry["page"], {})[field] = entry["value"]
    if not pages:
        return 0.0
    _, values = max(pages.items(), key=lambda item: len(item[1]))
    return sum(values.values())


def _coherent(loans, total, tolerance):
    if not total:
        return False
    return abs(loans - total) / abs(total) <= tolerance


def choose(per_field):
    """One entry per field, chosen so the gates can pass on numbers read from the same page set.

    A statement shows the same quantity on several pages (balance sheet, note, maturity table) and only one of
    them is the note the gate compares against, so the choice is driven by the gates themselves: loans must agree
    with a page that carries all five groups, the provision closing must close a page's roll-forward, and the
    groups/opening/charge/used come from the page that made the check pass. A field with no coherent partner keeps
    its best-graded candidate, and the grade is never upgraded by the choice: it stays what the readers gave.
    """
    chosen = {}
    sums = _group_sums(per_field)
    loans_entries = per_field.get("loans_customer") or []
    best = None
    for total_page, total in sums:
        for entry in loans_entries:
            if _coherent(entry["value"], total, GROUP_TOL) and (best is None or
                                                                GRADE_ORDER[entry["grade"]] < GRADE_ORDER[best[0]["grade"]]):
                best = (entry, total_page, total)
    if best is not None:
        entry, total_page, total = best
        chosen["loans_customer"] = entry
        for field in GROUP_FIELDS:
            match = next(item for item in per_field[field] if item["page"] == total_page)
            chosen[field] = match
    group_pages = {}
    for field in GROUP_FIELDS:
        for entry in per_field.get(field) or []:
            group_pages.setdefault(entry["page"], {})[field] = entry
    if group_pages:
        page, entries = max(group_pages.items(), key=lambda item: (len(item[1]), -item[0]))
        for field, entry in entries.items():
            chosen.setdefault(field, entry)          # the five groups always come from ONE page
    npl_total = _npl_total(per_field)
    closing_entries = per_field.get("provision_closing") or []
    rejected_pages = set()
    if npl_total > 0:
        plausible = [entry for entry in closing_entries
                     if COVERAGE_RANGE[0] <= entry["value"] / npl_total <= COVERAGE_RANGE[1]]
        rejected_pages = {entry["page"] for entry in closing_entries if entry not in plausible}
        closing_entries = plausible or closing_entries
    fallback_closing = closing_entries[0] if closing_entries else None
    movement = None
    for closing in closing_entries:
        page = closing["page"]
        parts = {}
        for field in PROVISION_MOVEMENT_LITE:
            match = next((item for item in per_field.get(field) or [] if item["page"] == page), None)
            if match is not None:
                parts[field] = match
        if len(parts) < 3:
            continue
        expected = parts["provision_opening"]["value"] + parts["provision_charge"]["value"] \
            - parts["provision_used_writeoff"]["value"]
        if _coherent(expected, closing["value"], ROLLFORWARD_TOL):
            movement = (page, parts, closing)
            break
    if movement is not None:
        page, parts, closing = movement
        chosen["provision_closing"] = closing
        chosen.update(parts)
    if "provision_closing" not in chosen and fallback_closing is not None:
        chosen["provision_closing"] = fallback_closing
    for field in FIELDS:
        if field in chosen:
            continue
        entries = per_field.get(field) or []
        if entries:
            chosen[field] = entries[0]
    for field in PROVISION_MOVEMENT_LITE:       # a movement table with a unit slip is not half-emitted
        if field in chosen and chosen[field]["page"] in rejected_pages:
            del chosen[field]
    return chosen


def collect(readings, bank, period, url, sha, statement_type="unknown"):
    """Silver rows for one bank-quarter: one row per field, graded page by page and chosen coherently (see choose)."""
    per_field = _candidates(readings)
    chosen = choose(per_field)
    rows = []
    for field in FIELDS:
        entry = chosen.get(field)
        if entry is None:
            continue
        rows.append({"bank": bank, "period": period, "field": field,
                     "basis": "point" if kind_of(field) == "balance" else "ytd",
                     "value_vnd_bn": entry["value"], "page": entry["page"], "source_url": url,
                     "statement_type": statement_type, "reader": ",".join(entry["readers"]),
                     "grade": entry["grade"], "raw_sha256": sha})
    rows.extend(_derived_npl(rows, bank, period, url, sha, statement_type))
    return rows


def _derived_npl(rows, bank, period, url, sha, statement_type="unknown"):
    """The groups 3-5 total the downstream ratios need: the arithmetic sum of three rows on one page.

    It is a derived row and says so (reader "derived"), keeps the page of its parts, and can only be as good as its
    worst part. A group missing from that page means no derived total at all.
    """
    parts = {row["field"]: row for row in rows if row["field"] in NPL_FIELDS}
    if len(parts) != len(NPL_FIELDS) or len({row["page"] for row in parts.values()}) != 1:
        return []
    grade_rank = max(GRADE_ORDER[row["grade"]] for row in parts.values())
    grade_name = next(name for name, rank in GRADE_ORDER.items() if rank == grade_rank)
    page = next(iter(parts.values()))["page"]
    return [{"bank": bank, "period": period, "field": "groups_3_5", "basis": "point",
             "value_vnd_bn": round(sum(row["value_vnd_bn"] for row in parts.values()), 6), "page": page,
             "source_url": url, "statement_type": statement_type, "reader": "derived", "grade": grade_name,
             "raw_sha256": sha}]


def locate_table_pages(content, vision, total, page_cap=VISION_PAGE_CAP, model=None):
    """(pages, errors) that hold the classification note, the provision movement or the balance sheet.

    Cheap by design: six legible page thumbnails per vision call, each stamped with its own page number, so a
    90-page scan costs about fifteen small calls instead of ninety full-page ones.
    """
    pages = list(range(1, min(total, page_cap) + 1))
    wanted, errors = [], {}
    for start in range(0, len(pages), STRIP):
        chunk = pages[start:start + STRIP]
        try:
            strip = render_strip(content, chunk, scale=STRIP_SCALE, per_row=4)   # 4 per row keeps the cached strips reusable
            payload = vision.read(strip, LOCATE_PROMPT, model or MODEL_LOCATE, schema=LOCATE_SCHEMA)
        except VisionError as exc:
            errors[f"locate {chunk[0]}-{chunk[-1]}"] = str(exc)[:140]
            continue
        classification, provision, balance = pages_from_locate(payload, allowed=chunk)
        for group in (sorted(classification), sorted(provision), sorted(balance)):
            wanted.extend(page for page in group if page not in wanted)
    return wanted[:PAGES_PER_STATEMENT], errors


def read_pdf(content, vision=None, use_vision=True, page_cap=VISION_PAGE_CAP, locate=True):
    """(readings, errors) for one PDF: the two text readers on a text layer, two vision prompts on a scan."""
    texts = fast_page_texts(content)       # PDFium: the same text, an order of magnitude faster than pdfplumber
    readings, errors = [], {}
    if has_text_layer(texts):
        found = read_text(texts)
        pages = sorted({item["page"] for item in found.values()})
        scales = {index: unit_scale(text) for index, text in enumerate(texts, start=1)}
        tables = page_tables(content, only=pages) if pages else []
        for reader, values in (("text", found), ("table", read_tables(tables, scales))):
            for field, item in values.items():
                readings.append({"field": field, **item})
        if not readings:
            errors["text"] = f"text layer on {len(texts)} pages but no label matched"
        return readings, errors
    if not use_vision or vision is None:
        errors["scan"] = f"no text layer on {len(texts)} pages and the vision reader is off"
        return readings, errors
    if locate:
        pages, locate_errors = locate_table_pages(content, vision, len(texts), page_cap=page_cap)
        errors.update(locate_errors)
        if not pages:
            errors.setdefault("scan", f"locator found no table page in {len(texts)} pages")
            return readings, errors
    else:
        pages = list(range(1, min(len(texts), page_cap) + 1))
    try:
        images = render_pages(content, pages, scale=2.0)
    except Exception as exc:               # a broken render does not lose the rest of the statement
        return readings, {**errors, "render": f"{type(exc).__name__}: {str(exc)[:100]}"}
    def one(page):
        return page, read_page(vision, images.get(page, b""), page)
    with ThreadPoolExecutor(max_workers=PAGE_WORKERS) as pool:
        for page, (page_readings, page_errors) in pool.map(one, pages):
            readings.extend(page_readings)
            errors.update({f"page {page} {key}": value for key, value in page_errors.items()})
    return readings, errors


def read_one(lake, fetcher, run_id, link, vision, use_vision, locate, budget_usd):
    """One bank-quarter: cached PDF -> readings (text layer, or locator + two vision reads) -> silver rows."""
    bank, period = str(link["bank"]), str(link["period"])
    out = {"bank": bank, "period": period, "rows": [], "errors": {},
           "stats": {"fetched": 0, "cached": 0, "read": 0, "no_text_layer": 0, "vision_calls": 0}}
    if vision is not None and getattr(vision, "cost_usd", 0.0) >= float(budget_usd):
        out["errors"]["budget"] = f"vision spend {vision.cost_usd:.2f} USD reached the {budget_usd:.0f} USD budget"
        return out
    try:
        content, meta = cached_pdf(lake, fetcher, link["url"], run_id)
    except FETCH_ERRORS as exc:
        out["errors"]["fetch"] = str(exc)[:140]
        return out
    out["stats"]["cached" if meta.get("cached") else "fetched"] = 1
    calls_before = len(getattr(vision, "calls", []))
    try:
        readings, page_errors = read_pdf(content, vision=vision, use_vision=use_vision, locate=locate)
    except Exception as exc:            # an unreadable PDF is a logged outcome, never a crashed run
        out["errors"]["unreadable"] = f"{type(exc).__name__}: {str(exc)[:100]}"
        return out
    out["stats"]["vision_calls"] = len(getattr(vision, "calls", [])) - calls_before
    if page_errors:
        out["errors"]["pages"] = dict(list(page_errors.items())[:4])
    out["rows"] = collect(readings, bank, period, link["url"], meta["sha256"],
                          statement_type=str(link.get("statement_type") or "unknown"))
    if readings:
        out["stats"]["read"] = 1
    else:
        out["stats"]["no_text_layer"] = 1
    return out


def harvest(lake, links, fetcher, run_id, vision=None, use_vision=True, refresh=False, existing=None,
            vendor=None, workers=1, fragment=None, budget_usd=VISION_BUDGET_USD, locate=True):
    """Read every linked PDF and return (silver rows, gate table, stats). Never writes silver: the caller does."""
    lake = Path(lake)
    stats = {"linked": len(links), "fetched": 0, "cached": 0, "read": 0, "skipped_done": 0,
             "no_text_layer": 0, "vision_calls": 0, "budget_stop": 0}
    done = set()
    if existing is not None and len(existing) and not refresh:
        done = {(str(bank), str(period)) for bank, period in
                existing[existing["grade"].isin(["verified", "single"])][["bank", "period"]].values.tolist()}
    jobs = []
    for link in links.to_dict("records") if len(links) else []:
        if (str(link["bank"]), str(link["period"])) in done:
            stats["skipped_done"] += 1
            continue
        jobs.append(link)
    reader = lambda job: read_one(lake, fetcher, run_id, job, vision, use_vision, locate, budget_usd)
    if workers and int(workers) > 1 and len(jobs) > 1:
        with ThreadPoolExecutor(max_workers=int(workers)) as pool:
            results = list(pool.map(reader, jobs))
    else:
        results = [reader(job) for job in jobs]
    errors, rows = {}, []
    for result in results:
        rows.extend(result["rows"])
        for key, value in result["stats"].items():
            stats[key] = stats.get(key, 0) + value
        if result["errors"]:
            errors[f"{result['bank']} {result['period']}"] = result["errors"]
            if "budget" in result["errors"]:
                stats["budget_stop"] += 1
    frame = pd.DataFrame(rows, columns=SILVER_COLUMNS)
    if len(frame):
        frame = pd.DataFrame(to_quarterly(frame.to_dict("records")), columns=SILVER_COLUMNS)
        frame["value_vnd_bn"] = pd.to_numeric(frame["value_vnd_bn"])
        frame["page"] = pd.to_numeric(frame["page"])
    gates, gate_stats = run_gates(frame, vendor=vendor)
    stats["gates"] = gate_stats
    if errors:
        stats["errors"] = dict(list(errors.items())[:10])
    if fragment is not None:
        path = Path(fragment)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic(path, json.dumps({"rows": frame.to_dict("records"), "gates": gates.to_dict("records"),
                                 "stats": stats}, ensure_ascii=False, default=str).encode("utf-8"))
    return frame, gates, stats


def vietstock_probe(sleep=time.sleep, spacing=1.0, client=None, timeout=40.0):
    """HEAD probe of the Vietstock static host, one request a second (its robots.txt answers 404: no restriction)."""
    http = client or httpx.Client(timeout=timeout, follow_redirects=True,
                                  headers={"User-Agent": "VietLeapInsightKit/1.0 (NPL research)"})

    def probe(url):
        sleep(spacing)
        try:
            response = http.head(url)
            if response.status_code in (405, 501):
                response = http.get(url, headers={"Range": "bytes=0-1"})
        except httpx.HTTPError:
            return 0, ""
        return response.status_code, response.headers.get("content-type", "")
    return probe


def discover(lake, banks, periods, probe, run_id, separate=True, annual_years=(), found_at=None):
    """Probe Vietstock static for every bank-quarter and merge the probe log into silver/notes_links.csv.

    Every HEAD is recorded, hits and 404s alike, so a later run knows which namings exist. A bank-quarter that
    already has a 200 consolidated link from this source is not probed again.
    """
    lake = Path(lake)
    existing = read_silver(lake, LINKS)
    rows = existing.to_dict("records") if existing is not None and len(existing) else []
    known = {(row.get("bank"), row.get("period"), row.get("url")) for row in rows}
    probed = hits = 0
    found_at = found_at or now().isoformat(timespec="seconds")
    for bank in banks:
        for period in periods:
            already = any(row.get("bank") == bank and row.get("period") == period
                          and row.get("found_by") == "vietstock_static"
                          and row.get("statement_type") == "consolidated"
                          and str(row.get("http_status")) in ("200", "nan", "None") for row in rows)
            if already:
                continue
            probes, found = probe_statement(probe, bank, period, found_at=found_at, separate=separate)
            probed += len(probes)
            hits += len(found)
            for row in probes:
                if (row["bank"], row["period"], row["url"]) not in known:
                    rows.append(row)
                    known.add((row["bank"], row["period"], row["url"]))
        for year in annual_years:
            for url, statement_type in vietstock_annual_urls(bank, year):
                if (bank, str(year), url) in known:
                    continue
                status, content_type = probe(url)
                probed += 1
                rows.append({"bank": bank, "period": f"{year}FY", "statement_type": statement_type, "url": url,
                             "found_by": "vietstock_static", "found_at": found_at, "http_status": status})
                known.add((bank, str(year), url))
                hits += 1 if status == 200 and "pdf" in str(content_type).lower() else 0
    frame = pd.DataFrame(rows).reindex(columns=LINK_COLUMNS)
    frame = frame.drop_duplicates(["bank", "period", "statement_type", "url"], keep="last")
    stats = {"probes": probed, "hits": hits, "rows": len(frame),
             "banks": int(frame["bank"].nunique()) if len(frame) else 0}
    write_silver(lake, LINKS, frame, {"run_id": run_id, **stats})
    return frame, stats


def merge_fragment_dir(lake, folder, run_id):
    """Merge every fragment JSON in `folder` into silver + gates + watermark, and return the run log dict.

    The parallel readers write fragments (rows + gates + stats) so no two of them ever touch the silver table;
    this is the single writer that folds their work together, keeping the better grade per bank-quarter-field.
    """
    lake = Path(lake)
    folder = Path(folder)
    paths = sorted(folder.glob("*.json")) if folder.exists() else []
    frame, gates = merge_fragments(paths)
    existing = read_silver(lake, SILVER)
    merged = merge_silver(existing, frame)
    if len(merged):
        write_silver(lake, SILVER, merged, {"run_id": run_id, "fragments": [path.name for path in paths]})
    if len(gates):
        write_silver(lake, GATES, gates, {"run_id": run_id})
    if len(merged):
        marks = load(lake / "state/watermarks.json")
        marks["notes_bank_quarter"] = str(merged["period"].max())
        marks["notes_bank_last"] = {bank: str(block["period"].max()) for bank, block in merged.groupby("bank")}
        save(lake / "state/watermarks.json", marks)
    stats = {"fragments": len(paths), "rows": len(frame), "gates": len(gates)}
    return {"run_id": run_id, "datasets": {"notes_merge": stats},
            "silver": {"rows": len(merged), "banks": int(merged["bank"].nunique()) if len(merged) else 0,
                       "periods": int(merged["period"].nunique()) if len(merged) else 0,
                       "verified_share": round(float((merged["grade"] == "verified").mean()), 4) if len(merged) else 0},
            "coverage": coverage(frame).to_dict("records")}


def merge_fragments(paths):
    """(silver rows, gate rows) from the per-group fragments the parallel readers wrote."""
    rows, gates = [], []
    for path in paths:
        if not Path(path).exists():
            continue
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        rows.extend(payload.get("rows") or [])
        gates.extend(payload.get("gates") or [])
    frame = pd.DataFrame(rows).reindex(columns=SILVER_COLUMNS) if rows else pd.DataFrame(columns=SILVER_COLUMNS)
    gate_frame = pd.DataFrame(gates).reindex(columns=GATE_COLUMNS) if gates else pd.DataFrame(columns=GATE_COLUMNS)
    return frame, gate_frame


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


def links_from_sources(lake, banks, periods, fetcher, run_id, agent=None, today=None):
    """Links from the saved register (Veitstock hits), then readable IR pages, then the agent for the JS pages.

    The register is written by `discover`; a bank it already covers is not scraped again, so the expensive
    sources only run for the banks Vietstock re-hosts nothing for.
    """
    saved = read_silver(lake, LINKS)
    found = []
    if saved is not None and len(saved) and "bank" in saved:
        usable = hits_only(saved)
        found.extend(usable[usable["bank"].isin(list(banks))].to_dict("records"))
    covered = {row["bank"] for row in found}
    errors = {}
    for bank in banks:
        if bank in covered:
            continue
        page = CATALOGUE.get(bank)
        if page is None:
            errors[bank] = "no link in the register and no investor-relations page in the catalogue"
            continue
        try:
            html = fetcher.get(page).text
        except FETCH_ERRORS as exc:
            errors[bank] = str(exc)[:120]
            continue
        rows = rows_from_page(bank, html, page, found_at=now().isoformat(timespec="seconds"))
        found.extend(rows)
        if not rows and agent is not None:
            try:
                records = agent(bank)
            except Exception as exc:        # the agent's failure is a logged outcome
                errors[bank] = f"agent: {type(exc).__name__}: {str(exc)[:100]}"
                continue
            found.extend(rows_from_agent(bank, records, found_at=now().isoformat(timespec="seconds")))
    frame = prefer_consolidated(found)
    if len(frame):
        frame["http_status"] = 200
    return frame, errors


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
              agent=None, links_only=False, today=None, discover_only=False, probe=None, separate=False,
              annual_years=(), workers=1, budget_usd=VISION_BUDGET_USD, fragment=None):
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
    if discover_only:
        registry, stats = discover(lake, banks, periods, probe or vietstock_probe(), run_id, separate=separate,
                                   annual_years=annual_years)
        log["datasets"]["links"] = stats
        log["links"] = {"rows": len(registry), "banks": int(registry["bank"].nunique()) if len(registry) else 0,
                        "periods": int(registry["period"].nunique()) if len(registry) else 0}
        log["elapsed_s"] = round(time.monotonic() - started, 3)
        atomic(lake / "run_log" / f"{run_id}.json",
               json.dumps(log, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
        return log
    links, link_errors = links_from_sources(lake, banks, periods, fetcher, run_id, agent=agent, today=today)
    if len(links):
        links = links[links["period"].isin(periods)]
    log["links"] = {"rows": len(links), "banks": int(links["bank"].nunique()) if len(links) else 0,
                    "periods": int(links["period"].nunique()) if len(links) else 0}
    if link_errors:
        log["errors"]["links"] = dict(list(link_errors.items())[:10])
    if links_only:
        log["elapsed_s"] = round(time.monotonic() - started, 3)
        atomic(lake / "run_log" / f"{run_id}.json",
               json.dumps(log, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
        return log
    existing = read_silver(lake, SILVER) if fragment is None else None
    frame, gates, stats = harvest(lake, links, fetcher, run_id, vision=vision, use_vision=use_vision,
                                 refresh=refresh, existing=existing, vendor=vendor_npl(lake), workers=workers,
                                 fragment=fragment, budget_usd=budget_usd)
    log["datasets"]["notes"] = stats
    log["spend_usd"] = {"openai": round(getattr(vision, "cost_usd", 0.0), 4)}
    if fragment is not None:
        log["fragment"] = str(fragment)
        log["elapsed_s"] = round(time.monotonic() - started, 3)
        atomic(lake / "run_log" / f"{run_id}.json",
               json.dumps(log, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
        return log
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
    log["silver"] = {"rows": len(merged), "banks": int(merged["bank"].nunique()) if len(merged) else 0,
                     "periods": int(merged["period"].nunique()) if len(merged) else 0,
                     "verified_share": round(float((merged["grade"] == "verified").mean()), 4) if len(merged) else 0}
    log["coverage"] = coverage(frame).to_dict("records")[:60]
    log["http_calls"] = len(getattr(fetcher, "calls", []))
    log["elapsed_s"] = round(time.monotonic() - started, 3)
    atomic(lake / "run_log" / f"{run_id}.json",
           json.dumps(log, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    return log
