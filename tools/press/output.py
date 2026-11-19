"""Long-format CSV writer + raw keeper for press/report targets (W2-PRESS).

Contract (brief W2-PRESS, "Output contract"):

data/raw/press/press_long.csv — one row per indicator/period/geo/source:
    indicator_id, period (YYYY-MM | YYYY-Qn | YYYY), measure_type (level|ytd|yoy|share|ratio|pct_plan),
    value, unit, geo (VNM | province name | bank ticker | city), source_id, source_url, published_date,
    evidence (exact sentence/table cell text containing the number), method (tinyfish|tinyfetch|pdf|scrape),
    evidence_ok (true|false|empty), extractor_version.

data/raw/press/sources_meta.csv — source_id, publisher, title_vi, url, method, license_note, robots_status, fetched_at.

Raw artifacts (run JSON / page markdown / PDF) kept under data/raw/press/raw/ with sha256 — see save_raw().
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KIT = Path(__file__).resolve().parents[2]
RAW_PRESS = KIT / "data" / "raw" / "press"
RAW_DIR = RAW_PRESS / "raw"
PRESS_LONG = RAW_PRESS / "press_long.csv"
SOURCES_META = RAW_PRESS / "sources_meta.csv"
RAW_MANIFEST = RAW_PRESS / "raw_manifest.jsonl"

LONG_COLUMNS = ["indicator_id", "period", "measure_type", "value", "unit", "geo", "source_id", "source_url",
                "published_date", "evidence", "method", "evidence_ok", "extractor_version"]
META_COLUMNS = ["source_id", "publisher", "title_vi", "url", "method", "license_note", "robots_status", "fetched_at"]
MEASURES = {"level", "ytd", "yoy", "share", "ratio", "pct_plan"}
METHODS = {"tinyfish", "tinyfetch", "pdf", "scrape"}
VERSION = "w2-press-v1"


def now_vi() -> str:
    return datetime.now(ZoneInfo("Asia/Saigon")).isoformat(timespec="seconds")


def _s(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def contract_row(*, indicator_id: str, source_id: str, source_url: str, method: str,
                 period=None, measure_type=None, value=None, unit=None, geo=None,
                 published_date=None, evidence=None, evidence_ok=None, extractor_version=VERSION) -> dict:
    """One press_long row (typed values; formatted at write time)."""
    if measure_type is not None and measure_type not in MEASURES:
        raise ValueError(f"bad measure_type {measure_type!r}")
    if method not in METHODS:
        raise ValueError(f"bad method {method!r}")
    row = {c: "" for c in LONG_COLUMNS}
    row["indicator_id"] = str(indicator_id)
    row["period"] = _s(period)
    row["measure_type"] = measure_type or ""
    row["value"] = _s(value)
    row["unit"] = _s(unit)
    row["geo"] = _s(geo)
    row["source_id"] = source_id
    row["source_url"] = source_url
    row["published_date"] = _s(published_date)
    row["evidence"] = evidence or ""
    row["method"] = method
    row["evidence_ok"] = "" if evidence_ok is None else ("true" if evidence_ok else "false")
    row["extractor_version"] = extractor_version
    return row


def row_key(row) -> tuple:
    return tuple(row.get(c, "") for c in ("indicator_id", "period", "measure_type", "geo", "source_id"))


def dedupe(rows) -> list[dict]:
    """Dedup on (indicator_id, period, measure_type, geo, source_id); returns rows sorted by the same key."""
    seen: set[tuple] = set()
    out = []
    for row in sorted(rows, key=lambda r: (row_key(r), r.get("value", ""), r.get("evidence", ""))):
        key = row_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def write_long_csv(path=PRESS_LONG, rows=None) -> int:
    rows = dedupe(rows or [])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LONG_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in LONG_COLUMNS})
    return len(rows)


def write_sources_meta_csv(path=SOURCES_META, meta=None) -> int:
    meta = sorted(meta or [], key=lambda r: r.get("source_id", ""))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=META_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in meta:
            writer.writerow({c: row.get(c, "") for c in META_COLUMNS})
    return len(meta)


def save_raw(name: str, data: bytes, ext: str) -> Path:
    """Write a raw artifact to data/raw/press/raw/<name>.<ext> and log its sha256 in raw_manifest.jsonl."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    p = RAW_DIR / f"{name}.{ext}"
    p.write_bytes(data)
    RAW_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    try:
        recorded = str(p.relative_to(KIT))
    except ValueError:
        recorded = str(p)
    with RAW_MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"name": name, "ext": ext, "path": recorded,
                             "sha256": hashlib.sha256(data).hexdigest(),
                             "bytes": len(data), "fetched_at": now_vi()}, ensure_ascii=False) + "\n")
    return p
