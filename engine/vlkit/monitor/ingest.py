"""Resolve versioned exports and register their raw records in the existing warehouse."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import yaml

from ..de.sources import TZ, now_iso
from ..de.warehouse import ident
from ..vn import ascii_key


DATASET = "vn_monitor"
OBS_COLUMNS = ["indicator_id", "period", "geo", "geo_type", "value", "unit", "measure_type",
               "source_id", "source_url", "published_date", "evidence", "parser_version", "run_id", "evidence_ok"]
TRANSFER_COLUMNS = ("earmarked_transfers", "earmarked_capex", "earmarked_current", "earmarked_programs")
ASEAN_PANEL = frozenset("BRN KHM IDN LAO MYS MMR PHL SGP THA VNM".split())
PERIOD = re.compile(r"^\d{4}(?:-(?:0[1-9]|1[0-2])(?:-\d{2})?|-Q[1-4])?$")


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def checksum(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def select_file(pattern, *, paired=False):
    """Choose a complete landing pair by fetch time, or the last ordinary file by name."""
    files = sorted(pattern.parent.glob(pattern.name))
    if not paired:
        return (files[-1], {}) if files else (None, {})
    pairs = [
        (p, json.loads(p.with_suffix(".json").read_text(encoding="utf-8")))
        for p in files if p.with_suffix(".json").is_file()
    ]
    if not pairs:
        return None, {}
    path, meta = max(pairs, key=lambda pair: (datetime.fromisoformat(pair[1]["fetched_at"]), pair[0].name))
    if checksum(path) != meta.get("sha256"):
        raise ValueError(f"SHA-256 không khớp cho tệp nguồn {path.name}")
    return path, meta


def literal(text):
    return "'" + str(text).replace("'", "''") + "'"


def land_source(wh, name, path, provenance, run_id, *, frame=None):
    """Replace revised cumulative snapshots, skip content-identical loads."""
    signature = provenance.get("sha256") or checksum(path)
    provenance = {**provenance, "sha256": signature}
    fq = f"bronze.{ident(name)}"
    previous = wh.con.execute(
        """SELECT json_extract_string(provenance, '$.sha256') FROM meta.sources
           WHERE dataset = ? AND source = ? ORDER BY rowid DESC LIMIT 1""", [DATASET, name],
    ).fetchall()
    if previous and previous[0][0] == signature and wh.exists("bronze", name):
        return {"rows": wh.con.execute(f"SELECT count(*) FROM {fq}").fetchone()[0], "changed": False}

    if frame is not None:
        stats = wh.write_bronze(DATASET, name, frame.assign(_run_id=run_id), provenance)
        return {"rows": stats["rows"], "changed": True}

    # Keep the largest Parquet input columnar through the ordinary bronze namespace.
    wh.con.execute(
        f"""CREATE OR REPLACE TABLE {fq} AS
            SELECT raw.*, ?::VARCHAR AS _run_id, ?::VARCHAR AS _src, ?::VARCHAR AS _ingested_at,
                   hash(raw)::VARCHAR AS _row_hash
            FROM read_parquet(?) raw""",
        [run_id, provenance["source"], provenance["fetched_at"], str(path)],
    )
    target = wh.lake / "bronze" / f"{name}.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    wh.con.execute(f"COPY {fq} TO {literal(target.as_posix())} (FORMAT parquet)")
    rows = wh.con.execute(f"SELECT count(*) FROM {fq}").fetchone()[0]
    wh.con.execute("INSERT INTO meta.sources VALUES (?,?,?,?,?,?)", [
        DATASET, name, provenance["kind"], str(path), provenance["fetched_at"],
        json.dumps(provenance, ensure_ascii=False),
    ])
    wh.lineage(DATASET, f"source:{provenance['source']}", f"bronze.{name}", "ingest")
    return {"rows": rows, "changed": True}


def slug(value):
    return re.sub(r"[^a-z0-9]+", "_", ascii_key(str(value))).strip("_")


def observations(frame, source_id, run_id, geo_type="national", measure_type="level"):
    result = frame.copy()
    defaults = {"geo": "", "geo_type": geo_type, "measure_type": measure_type, "unit": "",
                "source_id": source_id, "source_url": "", "published_date": "", "evidence": "",
                "parser_version": ""}
    for field, default in defaults.items():
        result[field] = result[field].fillna(default) if field in result else default
    result["run_id"] = run_id
    return result.reindex(columns=OBS_COLUMNS)


def normalize_long(raw, source_id, run_id, catalog=()):
    """Use the common source handoff without converting numbers before silver."""
    frame = raw.copy()
    suffix = frame["measure_type"].replace({"month": "level"})
    canonical = frame["indicator_id"] + "_" + suffix
    if source_id == "nso":
        frame["indicator_id"] = canonical
    else:
        candidates = {entry["id"] for entry in catalog if entry.get("base_id")}
        frame["indicator_id"] = frame["indicator_id"].where(~canonical.isin(candidates), canonical)
    frame["measure_type"] = frame["measure_type"].replace({"month": "level", "avg_ytd": "ytd"})
    if source_id == "press":
        indicator = frame["indicator_id"]
        fdi_amount = indicator.isin(["fdi_province", "fdi_partner"]) & frame["measure_type"].eq("level")
        if "extractor_version" in frame and "parser_version" not in frame:
            frame = frame.rename(columns={"extractor_version": "parser_version"})
        if "geo" in frame and "geo_type" not in frame:
            labels = frame["geo"].fillna("").str.strip()
            local = ~labels.str.upper().isin(["", "VNM"])
            indicator = frame["indicator_id"]
            frame["geo_type"] = "national"
            frame.loc[local & indicator.str.startswith("bank_"), "geo_type"] = "ticker"
            frame.loc[local & indicator.str.startswith(("dtc_", "fdi_")), "geo_type"] = "province"
            frame.loc[local & indicator.str.startswith("dtc_ministry_"), "geo_type"] = "ministry"
            frame.loc[local & indicator.eq("fdi_partner"), "geo_type"] = "partner"
            frame.loc[local & (indicator.str.startswith(("re_", "apartment_", "landed_home_"))
                               | indicator.isin(["mortgage_rate", "deposit_rate_12m"])), "geo_type"] = "city"
        frame["indicator_id"] = indicator.replace({
            "bank_npl_coverage": "bank_coverage",
            "bank_sector_credit_ytd": "credit_ytd",
            "bank_sector_deposits_ytd": "deposit_ytd",
        })
        supply = indicator.eq("apartment_new_supply") & frame["measure_type"].eq("level")
        frame.loc[supply, "indicator_id"] = "re_new_supply"
        if "unit" in frame:
            frame.loc[supply & frame["unit"].eq("can"), "unit"] = "căn"
            margin = indicator.eq("margin_debt") & frame["measure_type"].eq("level")
            frame.loc[margin & frame["unit"].eq("nghin_ty_vnd"), "unit"] = "nghìn tỷ đồng"
        frame.loc[fdi_amount, ["indicator_id", "measure_type"]] = ["fdi_dang_ky", "ytd"]
        frame.loc[indicator.eq("bank_npl"), "measure_type"] = "ratio"
        if "period" in frame:
            sector_ytd = indicator.isin(["bank_sector_credit_ytd", "bank_sector_deposits_ytd"])
            frame.loc[sector_ytd, "period"] = frame.loc[sector_ytd, "period"].str.replace(
                r"-Q([1-4])$", lambda match: f"-{int(match[1]) * 3:02d}", regex=True,
            )
        frame = _press_absorption(frame)
        if {"source_id", "geo_type"} <= set(frame):
            # The rate in the HCMC article is a benchmark from commercial banks.
            benchmark = frame["source_id"].eq("realtique_cbre_hcm_q3_2026") & frame["indicator_id"].eq("mortgage_rate")
            frame.loc[benchmark, ["geo", "geo_type"]] = ["VNM", "national"]
    if "geo" not in frame:
        for field, kind in (("province", "province"), ("province_code", "province"), ("ticker", "ticker"),
                            ("ministry", "ministry"), ("partner", "partner"), ("iso3", "country")):
            if field in frame:
                if "geo" not in frame:
                    frame["geo"] = ""
                if "geo_type" not in frame:
                    frame["geo_type"] = "national"
                present = frame[field].notna() & frame["geo"].eq("")
                frame.loc[present, "geo"] = frame.loc[present, field].astype(str)
                frame.loc[present, "geo_type"] = kind
    return observations(frame, source_id, run_id)


def _press_absorption(frame):
    """Publish the catalog's percent from same-source, same-city apartment counts."""
    if not {"evidence_ok", "evidence", "period", "geo", "source_id", "value"} <= set(frame):
        return frame
    verified = frame.loc[frame["measure_type"].eq("level") & frame["evidence_ok"].astype(str).str.lower().eq("true")]
    key = ["period", "geo", "source_id"]
    rates = verified.loc[verified["indicator_id"].eq("mortgage_rate"), key].drop_duplicates()
    supply = verified.loc[verified["indicator_id"].eq("re_new_supply") & verified["unit"].eq("căn"),
                          key + ["value", "evidence"]]
    sales = verified.loc[verified["indicator_id"].eq("apartment_absorption") & verified["unit"].isin(["can", "căn"])]
    matched = sales.merge(supply, on=key, suffixes=("", "_supply")).merge(rates, on=key)
    sold = pd.to_numeric(matched["value"], errors="coerce")
    offered = pd.to_numeric(matched["value_supply"], errors="coerce")
    valid = sold.ge(0) & offered.gt(0)
    if not valid.any():
        return frame
    matched = matched.loc[valid].assign(
        indicator_id="re_absorption", unit="%", value=(100 * sold[valid] / offered[valid]),
        evidence=matched.loc[valid, "evidence"] + " | " + matched.loc[valid, "evidence_supply"],
    )
    return pd.concat([frame, matched[frame.columns]], ignore_index=True)


def normalize_transfers(raw, run_id):
    frame = raw.rename(columns={"province": "geo", "year": "period"})
    columns = [c for c in TRANSFER_COLUMNS if c in frame]
    frame = frame.melt(["geo", "period"], columns, var_name="indicator_id")
    frame["period"] = frame["period"].astype(str)
    frame["unit"] = "triệu đồng"
    frame["source_url"] = frame["period"].map({
        "2024": "https://vanban.chinhphu.vn/?docid=209069&pageid=27160",
        "2025": "https://vanban.chinhphu.vn/?docid=211922&pageid=27160",
    })
    return observations(frame, "transfers", run_id, "province")


def normalize_wdi(raw, catalog, run_id):
    fields = {entry["id"]: entry["unit"] for entry in catalog if entry["source_id"] == "wdi"}
    columns = [c for c in fields if c in raw]
    frame = raw.loc[raw["iso3"].isin(ASEAN_PANEL)].rename(columns={"iso3": "geo", "year": "period"})
    frame = frame.melt(["geo", "period"], columns, var_name="indicator_id")
    frame["period"] = frame["period"].astype(str)
    frame["unit"] = frame["indicator_id"].map(fields)
    return observations(frame, "wdi", run_id, "country")


def normalize_sbv(raw, run_id):
    if "indicator_id" in raw:
        return normalize_long(raw, "sbv", run_id)
    frame = raw.assign(geo=raw["sector"].map(slug), geo_type="industry")
    total = frame["geo"].eq("tong_cong")
    frame.loc[total, ["geo", "geo_type"]] = ["", "national"]
    frame = frame.rename(columns={"balance_bn_vnd": "sbv_credit_balance",
                                  "growth_vs_prev_year_end_pct": "credit_ytd"})
    frame = frame.melt(["period", "geo", "geo_type", "source_url", "evidence"],
                       ["sbv_credit_balance", "credit_ytd"], var_name="indicator_id")
    growth = frame["indicator_id"].eq("credit_ytd")
    frame["unit"] = growth.map({True: "%", False: "tỷ đồng"})
    frame["measure_type"] = growth.map({True: "ytd", False: "level"})
    return observations(frame, "sbv", run_id)


def fq_cutoff(wh, name, dataset):
    columns = {"roster": "snapshot_date", "breadth": "tradingDate", "vn30_weights": "snapshot_date"}
    column = ident(columns.get(dataset, "timestamp"))
    query = ("max(printf('%04d-Q%d', year, quarter))" if dataset == "bank_ratios"
             else f"max(substr(CAST({column} AS VARCHAR), 1, 10))")
    return wh.con.execute(f"SELECT {query} FROM bronze.{ident(name)}").fetchone()[0]


def file_time(path):
    return datetime.fromtimestamp(path.stat().st_mtime, TZ).isoformat(timespec="seconds")


def period_end(period):
    if period is None or not PERIOD.fullmatch(period):
        return None
    year = int(period[:4])
    try:
        if len(period) == 10:
            return date.fromisoformat(period)
        month = 12 if len(period) == 4 else int(period[-1]) * 3 if "-Q" in period else int(period[-2:])
        return date(year, month, monthrange(year, month)[1])
    except ValueError:
        return None


def ingest_sources(wh, root, specs, source_meta, catalog, run_id, *, offline=False):
    loaded, missing, frames, by_source = [], [], [], {}
    press_meta = _press_collection_metadata(root)
    for spec in specs:
        name = spec["name"]
        started = now_iso()
        pattern = root / spec["uri"]
        fq_dataset = spec.get("vendor_dataset")
        if spec["kind"] != "file":
            raise ValueError(f"Nguồn {name} cần tệp landing cho chế độ {'offline' if offline else 'monitor'}")
        if fq_dataset:
            path, meta = select_file(pattern, paired=True)
            paths = [path] if path is not None else []
        else:
            paths = sorted(pattern.parent.glob(pattern.name))
            meta = {}
        if not paths:
            if not spec.get("optional"):
                raise FileNotFoundError(f"Thiếu nguồn {name}: {pattern}")
            missing.append(name)
            wh.log_run(run_id, DATASET, f"ingest:{name}", "skipped", started, {"reason": "landing absent"})
            continue
        source_id = spec["source_id"]
        for index, path in enumerate(paths):
            table = f"vm_{name}" if index == 0 else f"vm_{name}_{index + 1}"
            fetched = meta.get("fetched_at") or file_time(path)
            provenance = {
                **meta, "kind": spec["kind"], "source": name, "uri": str(path),
                "fetched_at": fetched, "license_note": spec["license"], "conform": spec["conform"],
            }
            raw = None if fq_dataset else pd.read_csv(path, encoding="utf-8-sig")
            stats = land_source(wh, table, path, provenance, run_id, frame=raw)
            loaded.append({"name": f"bronze.{table}", "layer": "bronze", "rows": stats["rows"],
                           "grain_vi": spec["grain_vi"]})
            wh.log_run(run_id, DATASET, f"ingest:{name}", "ok", started, stats)
            if fq_dataset:
                cutoff = fq_cutoff(wh, table, fq_dataset)
                update_source(by_source, source_meta, source_id, fetched, cutoff, stats["rows"])
                continue
            if name == "wdi":
                normalized = normalize_wdi(raw, catalog, run_id)
            elif name == "transfers":
                normalized = normalize_transfers(raw, run_id)
            elif name == "sbv":
                normalized = normalize_sbv(raw, run_id)
            else:
                normalized = normalize_long(raw, source_id, run_id, catalog)
            frames.append(normalized)
            for sid, frame in normalized.groupby("source_id"):
                periods = {label: end for label in frame["period"].unique()
                           if (end := period_end(str(label))) is not None}
                if not periods:
                    continue
                if sid not in source_meta:
                    urls = frame["source_url"].dropna()
                    source_meta[sid] = {**source_meta[source_id], "publisher": sid.upper(),
                                        "url": next((u for u in urls if u.startswith(("https://", "http://"))),
                                                    source_meta[source_id]["url"])}
                cutoff = max(periods, key=lambda label: (periods[label], len(label)))
                if sid in press_meta and source_id == "press":
                    metadata, collected_at = press_meta[sid]
                    source_meta[sid] = {**source_meta[sid], **metadata}
                    update_source(by_source, source_meta, sid, collected_at, cutoff, int(raw["source_id"].eq(sid).sum()))
                else:
                    update_source(by_source, source_meta, sid, fetched, cutoff, len(frame))
    for feed in _rss_collection_sources(root):
        by_source[feed["id"]] = feed
    observed = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=OBS_COLUMNS)
    return observed, list(by_source.values()), loaded, missing


def _press_collection_metadata(root):
    path = root / "data/raw/press/sources_meta.csv"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        return {row["source_id"]: ({
            "publisher": row["publisher"], "title_vi": row["title_vi"], "url": row["url"],
            "method": {"tinyfetch": "scrape", "rss": "social"}.get(row["method"], row["method"]),
            "license": row["license_note"], "robots": row["robots_status"],
        }, row["fetched_at"]) for row in csv.DictReader(file)}


def _rss_collection_sources(root):
    """Register the saved news enrichment without adding articles to financial facts."""
    from time import strftime

    import feedparser

    directory = root / "data/raw/press/raw"
    for source_id, publisher, url in (
        ("vnexpress_kinh_doanh", "VnExpress", "https://vnexpress.net/rss/kinh-doanh.rss"),
        ("cafef_thi_truong", "CafeF", "https://cafef.vn/thi-truong-chung-khoan.rss"),
    ):
        path = directory / f"{source_id}_rss.xml"
        if not path.is_file():
            continue
        dates = [stamp for entry in feedparser.parse(path.read_bytes()).entries
                 if (stamp := entry.get("published_parsed") or entry.get("updated_parsed"))]
        if dates:
            yield {"id": source_id, "publisher": publisher, "title_vi": f"Tin kinh doanh · {publisher}",
                   "url": url, "method": "social", "license": "RSS công khai, chỉ dùng tiêu đề và tóm tắt.",
                   "fetched_at": file_time(path), "data_cutoff": strftime("%Y-%m-%d", max(dates)), "rows": len(dates)}


def update_source(found, metadata, source_id, fetched, cutoff, rows):
    end = period_end(cutoff)
    if end is None:
        return
    current = found.setdefault(source_id, dict(metadata[source_id], id=source_id, fetched_at=fetched,
                                               data_cutoff=cutoff, rows=0))
    prior = current["data_cutoff"]
    if (end, len(cutoff)) > (period_end(prior), len(prior)):
        current["data_cutoff"] = cutoff
    current["fetched_at"] = max(current["fetched_at"], fetched)
    current["rows"] += rows
