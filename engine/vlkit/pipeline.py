"""End-to-end pipeline: load → clean → domain pack → profile → insights → decisions → outputs."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import domains, fmt, insights as ins_mod, stats
from .decision import recommend
from .loader import load_and_clean
from .profile import caveats as mk_caveats, profile as mk_profile
from scipy.stats import trim_mean

from .vn import ascii_key, slug


class NpEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (pd.Timestamp,)):
            return str(o)
        if isinstance(o, set):
            return list(o)
        return super().default(o)


def dump(obj, path: Path):
    path.write_text(json.dumps(obj, cls=NpEncoder, ensure_ascii=False, indent=1), encoding="utf-8")


def _resolve(df, name):
    if name is None:
        return None
    if name in df.columns:
        return name
    k = ascii_key(name)
    for c in df.columns:
        if ascii_key(c) == k:
            return c
    raise KeyError(f"column '{name}' not found. Columns: {list(df.columns)}")


def pick_time(df, roles):
    cands = [c for c, r in roles.items() if r == "time"]
    if not cands:
        return None
    return max(cands, key=lambda c: (df[c].notna().mean(), df[c].nunique()))


def pick_geo(df, roles):
    cands = [c for c, r in roles.items() if r == "geo" and 2 <= df[c].nunique() <= 100 and not c.endswith("__province_2025")]
    if not cands:
        return None
    # prefer normalised provinces, then moderate cardinality and completeness
    return max(cands, key=lambda c: (c.endswith("__province"), df[c].notna().mean() > 0.7, -abs(df[c].nunique() - 20)))


def pick_target(df, roles, domain_info):
    pm = domain_info.get("primary_metric")
    if pm and pm in df and df[pm].notna().mean() > 0.3:
        return pm
    nums = [c for c, r in roles.items() if r == "numeric" and df[c].notna().mean() > 0.5]
    if not nums:
        raise ValueError("No numeric column available as a target; pass --target")
    prio = ["price", "gia", "revenue", "doanh thu", "profit", "loi nhuan", "gdp", "value", "gia tri", "amount", "so tien", "total", "tong"]
    for p in prio:
        for c in nums:
            if p in ascii_key(c):
                return c
    return max(nums, key=lambda c: df[c].notna().mean() * np.log1p(df[c].nunique()))


def build_kpis(df, target, time_col, ts, prof, insights, domain_info):
    k = []
    n = len(df)
    cover = ""
    if time_col is not None:
        t = df[time_col].dropna()
        if len(t):
            lo, hi = (int(t.min()), int(t.max())) if pd.api.types.is_numeric_dtype(t) else (str(t.min().date()), str(t.max().date()))
            cover = f"{lo} → {hi}"
    k.append({"label": "Records analysed", "label_vi": "Số bản ghi", "value": f"{n:,}", "raw": n, "delta_pct": None,
              "footer": cover or f"{prof['columns']} columns", "description": f"{prof['columns']} columns after cleaning"})
    med = float(df[target].median())
    delta = None
    foot = "across all records"
    if ts and ts.get("points") and len(ts["points"]) >= 2:
        a, b = ts["points"][-2]["value"], ts["points"][-1]["value"]
        if a:
            delta = (b / a - 1) * 100
            foot = f"{ts['points'][-1]['period']} vs {ts['points'][-2]['period']}"
    k.append({"label": f"Median {target}", "label_vi": f"Trung vị {target}", "value": fmt.num(med, target), "raw": med,
              "delta_pct": stats.r(delta), "footer": foot, "description": f"5%-trimmed mean {fmt.num(trim_mean(df[target].dropna(), 0.05), target)}"})
    gap = next((i for i in insights if i["type"] == "segment_gap"), None)
    top = insights[0] if insights else None
    if gap and gap["value"].get("ratio"):
        ev = gap["evidence"]
        k.append({"label": f"Spread across {ev['by']}", "label_vi": f"Chênh lệch theo {ev['by']}", "value": f"{gap['value']['ratio']:.2f}×",
                  "raw": gap["value"]["ratio"], "delta_pct": None, "footer": f"{ev['top']['group']} vs {ev['bottom']['group']}",
                  "description": f"Kruskal–Wallis {fmt.p(ev['kruskal']['p'])}, ε²={ev['kruskal']['epsilon2']}"})
    elif top:
        k.append({"label": "Top insight", "label_vi": "Phát hiện #1", "value": str(top["value"]) if not isinstance(top["value"], dict) else f"{top['effect']}",
                  "raw": top["effect"], "delta_pct": None, "footer": top["title_en"], "description": f"{top['test']}, {fmt.p(top['p_value'])}"})
    complete = 100 - (prof["missing_overall_pct"] or 0)
    k.append({"label": "Data completeness", "label_vi": "Độ đầy đủ dữ liệu", "value": f"{complete:.1f}%", "raw": complete,
              "delta_pct": None, "footer": f"{len(prof['issues'])} quality flags", "description": f"{prof['outlier_rows_pct']}% rows with extreme values"})
    return k


def run(path: str | Path, out_root: str | Path = "out", target: str | None = None, time_col: str | None = None,
        geo_col: str | None = None, domain: str = "auto", sheet: str | None = None, transpose: bool | None = None,
        name: str | None = None, reports: bool = True, max_insights: int = 12) -> dict:
    t0 = time.time()
    timings = {}
    path = Path(path)
    name = name or slug(path.stem)[:60]
    out = Path(out_root) / name
    (out / "charts").mkdir(parents=True, exist_ok=True)
    cr = load_and_clean(path, sheet=sheet, transpose=transpose)
    df, roles, log = cr.df, cr.roles, cr.log
    timings["load_clean_s"] = round(time.time() - t0, 2)
    dom, dom_scores = domains.detect_domain(list(df.columns)) if domain == "auto" else (domain, {})
    dinfo = domains.apply_domain(dom, df, roles, log)
    time_col = _resolve(df, time_col) or pick_time(df, roles)
    geo_col = _resolve(df, geo_col) or pick_geo(df, roles)
    target = _resolve(df, target) or pick_target(df, roles, dinfo)
    roles[target] = "numeric"
    if dom == "property":
        # avoid algebraic leakage: price = ppm2 × area
        dinfo["exclude_from_drivers"] = [c for c in [dinfo.get("price"), "price_total_vnd", "price_per_m2", dinfo.get("price_per_m2")] if c and c != target]
        dinfo["skip_segments"] = ["price_segment"]  # built from price itself → tautological vs price targets
    # alias columns (1:1 with another category, e.g. country ↔ iso3) add nothing; exclude from analysis
    catc = [c for c, r in roles.items() if r in ("category", "geo") and 2 <= df[c].nunique() <= 500]
    for i, a in enumerate(catc):
        for b in catc[i + 1:]:
            if roles.get(b) == "alias" or roles.get(a) == "alias":
                continue
            pair = df[[a, b]].dropna()
            if len(pair) and pair[a].nunique() == pair[b].nunique() and pair.groupby(a)[b].nunique().max() == 1:
                keep, drop = (a, b) if a in (geo_col, time_col) or b not in (geo_col,) else (b, a)
                roles[drop] = "alias"
                log.append(f"'{drop}' is a 1:1 alias of '{keep}'; excluded from analysis")
    # leakage guard: never explain the target with its own ingredients (e.g. ROE = profit / equity)
    ingr = dinfo.get("ingredients", {})
    banned = set(ingr.get(target, [])) - set(dinfo.get("keep_ingredients", []))
    derived_from_banned = [m for m, parts in ingr.items() if m != target and set(parts) & (banned | {target})]
    dinfo["exclude_from_drivers"] = sorted(set(dinfo.get("exclude_from_drivers", [])) | banned | set(derived_from_banned))
    if dinfo["exclude_from_drivers"]:
        log.append(f"leakage guard: excluded {dinfo['exclude_from_drivers']} from drivers/correlations of '{target}' (algebraic ingredients)")
    t1 = time.time()
    prof = mk_profile(df, roles, cr.numeric_reports, cr.source.get("outlier_counts", {}))
    cav = mk_caveats(prof, domains.CAVEATS.get(dom, []), time_col, len(df))
    timings["profile_s"] = round(time.time() - t1, 2)
    t2 = time.time()
    insights, extras = ins_mod.generate(df, roles, target, time_col, geo_col, dinfo, max_insights=max_insights)
    timings["insights_s"] = round(time.time() - t2, 2)
    recs = recommend(insights, dom, target, extras.get("drivers"))
    seg = extras.get("segments")
    if seg is not None:
        labels = seg.pop("labels_index")
        df["_segment"] = labels.reindex(df.index)
    drivers = extras.get("drivers")
    whatif = drivers.pop("whatif") if drivers else None
    ts = extras.get("timeseries")
    kpis = build_kpis(df, target, time_col, ts, prof, insights, dinfo)
    # persist
    df.to_parquet(out / "clean.parquet", index=False)
    df.head(5000).to_csv(out / "clean_sample.csv", index=False, encoding="utf-8-sig")
    meta = {"name": name, "source_file": path.name, "domain": dom, "domain_scores": dom_scores, "target": target, "time_col": time_col,
            "geo_col": geo_col, "rows": len(df), "columns": int(df.shape[1]), "roles": roles,
            "domain_metrics": dinfo.get("metrics", []), "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "category_cols": [c for c, r in roles.items() if r in ("category", "geo") and 2 <= df[c].nunique() <= 60]}
    results = {"meta": meta, "cleaning_log": log, "profile": prof, "caveats": cav, "kpis": kpis, "timeseries": ts,
               "insights": insights, "recommendations": recs, "drivers": drivers, "segments": seg,
               "correlations": extras.get("correlations")}
    if whatif:
        dump(whatif, out / "whatif.json")
    if reports:
        t3 = time.time()
        from . import report
        files = report.build_all(results, df, whatif, out)
        results["files"] = files
        timings["reports_s"] = round(time.time() - t3, 2)
    timings["total_s"] = round(time.time() - t0, 2)
    results["timings"] = timings
    dump(results, out / "results.json")
    return results
