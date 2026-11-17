"""Transform step 1: data quality — profile bronze, clean to silver, score before/after.

Checks (as taught in the DE workshop): missing values, duplicates (full row + candidate key), outliers
(robust z / IQR, flagged, never deleted), wrong types (numbers stored as text), impossible negatives,
constant columns. Every change is written to a cleaning log so judges can audit it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..loader import clean
from ..vn import ascii_key, canonical_districts, is_district_column, normalize_province, parse_numeric_series, to_new_province

NONNEG_HINTS = ["gia", "price", "dien tich", "area", "so luong", "count", "dan so", "population", "doanh thu",
                "revenue", "chi", "thu", "budget", "ngan sach", "luong", "salary", "tuoi", "age"]
META_COLS = {"_row_hash", "_src", "_ingested_at", "_outlier_any"}


def profile_quality(df: pd.DataFrame, key: list[str] | None = None) -> dict:
    cols = [c for c in df.columns if c not in META_COLS]
    d = df[cols].copy()
    for c in d.columns:  # blank strings are missing values too (common in API/CSV exports)
        if d[c].dtype == object or pd.api.types.is_string_dtype(d[c]):
            d[c] = d[c].astype(object).mask(d[c].astype(str).str.strip().isin(["", "nan", "None", "NULL", "N/A", "-"]) | d[c].isna())
    n = max(len(d), 1)
    per_col, issues, invalid = {}, [], 0
    for c in cols:
        s = d[c]
        miss = float(s.isna().mean())
        info = {"dtype": str(s.dtype), "missing_pct": round(100 * miss, 2), "distinct": int(s.nunique(dropna=True))}
        if (s.dtype == object or pd.api.types.is_string_dtype(s)) and s.notna().any():
            parsed, _rep = parse_numeric_series(s)        # VN formats: "4,5 tỷ", "15 tr/m²", "1.200.000đ"
            if parsed is not None:
                bad = int((parsed.isna() & s.notna()).sum())
                info.update({"numeric_as_text": True, "invalid_values": bad})
                invalid += bad
                issues.append({"type": "wrong_type", "column": c, "detail": "numbers stored as text",
                               "unparseable": bad})
        if pd.api.types.is_numeric_dtype(s) and s.notna().sum() > 10:
            x = s.dropna().astype(float)
            q1, q3 = np.percentile(x, [25, 75])
            iqr = q3 - q1
            out = int(((x < q1 - 3 * iqr) | (x > q3 + 3 * iqr)).sum()) if iqr > 0 else 0
            info.update({"min": float(x.min()), "max": float(x.max()), "outliers_3iqr": out})
            if out:
                issues.append({"type": "outlier", "column": c, "count": out})
            if any(h in ascii_key(c) for h in NONNEG_HINTS) and (x < 0).any():
                k = int((x < 0).sum())
                info["negatives"] = k
                issues.append({"type": "impossible_negative", "column": c, "count": k})
        if miss > 0:
            issues.append({"type": "missing", "column": c, "pct": round(100 * miss, 2)})
        if info["distinct"] <= 1 and n > 1:
            issues.append({"type": "constant", "column": c})
        per_col[c] = info
    dup_rows = int(d.astype(str).duplicated().sum()) if len(d) else 0
    if dup_rows:
        issues.append({"type": "duplicate_rows", "count": dup_rows})
    key = key or guess_key(d)
    dup_key = int(d.duplicated(subset=key).sum()) if key else None
    if dup_key:
        issues.append({"type": "duplicate_key", "key": key, "count": dup_key})
    cells = n * max(len(cols), 1)
    miss_cells = int(d.isna().sum().sum())
    score = 100.0
    score -= 40 * (miss_cells + invalid) / cells
    score -= 25 * dup_rows / n
    score -= 15 * sum(1 for i in issues if i["type"] == "wrong_type") / max(len(cols), 1)
    score -= 10 * sum(i.get("count", 0) for i in issues if i["type"] == "outlier") / cells
    score -= 10 * sum(1 for i in issues if i["type"] in ("impossible_negative", "constant")) / max(len(cols), 1)
    return {"rows": int(len(d)), "cols": len(cols), "missing_cells": miss_cells, "invalid_cells": invalid, "duplicate_rows": dup_rows,
            "candidate_key": key, "duplicate_keys": dup_key, "score": round(max(score, 0), 1),
            "columns": per_col, "issues": issues}


def guess_key(df: pd.DataFrame) -> list[str] | None:
    """Smallest column set (≤2) that is unique: ids first, then (entity, time) pairs."""
    n = len(df)
    if n == 0:
        return None
    named = [c for c in df.columns if any(t in ascii_key(c).split() for t in ("id", "ma", "code", "ticker", "symbol"))]
    for c in named + list(df.columns):
        if df[c].notna().all() and df[c].nunique() == n:
            return [c]
    cands = [c for c in df.columns if 1 < df[c].nunique() < n]
    for i, a in enumerate(cands[:12]):
        for b in cands[i + 1:12]:
            if not df[[a, b]].duplicated().any() and df[[a, b]].notna().all().all():
                return [a, b]
    return None


def to_silver(df_bronze: pd.DataFrame, impute: str | None = None) -> tuple[pd.DataFrame, dict, list[str]]:
    """Clean bronze → silver. impute: None (keep NaN, default — honest) | 'median' (numeric median + flag col)."""
    raw = df_bronze.drop(columns=[c for c in df_bronze.columns if c in ("_row_hash", "_ingested_at")], errors="ignore")
    src = raw.pop("_src") if "_src" in raw.columns else None
    log: list[str] = []
    dist_cols = {c: lvl for c in raw.columns if not str(c).startswith("_")
                 and (lvl := is_district_column(str(c), raw[c] if raw[c].dtype == object or pd.api.types.is_string_dtype(raw[c]) else None))}
    res = clean(raw, log)
    df = res.df
    roles = res.roles
    kept = res.source.get("kept_index")
    # districts / wards: normalised from the RAW spelling (clean() strips "Quận"/"Huyện" prefixes, which would turn
    # "Quận 1" into "1"), aligned to the surviving rows, kept next to the original column
    for c, lvl in dist_cols.items():
        if c not in df.columns or kept is None or pd.api.types.is_datetime64_any_dtype(df[c]):
            continue
        if roles.get(c) in ("numeric", "time") and lvl != "district":
            continue
        if any(str(x).endswith("__province") for x in df.columns if str(x).startswith(f"{c}__")):
            continue   # values were actually provinces
        disp, key = canonical_districts(raw[c].loc[kept].reset_index(drop=True), "Quận" if lvl == "district" else "Phường")
        if key.notna().mean() < 0.5 * max(raw[c].notna().mean(), 1e-9):
            continue
        df[f"{c}__district"], df[f"{c}__district_key"] = disp.to_numpy(), key.to_numpy()
        roles[f"{c}__district"], roles[f"{c}__district_key"] = "geo", "geo_key"
        roles[c] = "geo_raw"
        log.append(f"'{c}': {lvl} names normalised ({key.nunique()} units; prefixes Quận/Huyện/Q./TP. stripped, "
                   f"accent-insensitive key) → '{c}__district' + '{c}__district_key'")
    for c in [c for c, r in roles.items() if r == "numeric"]:
        if any(h in ascii_key(c) for h in NONNEG_HINTS):
            neg = df[c] < 0
            if neg.any():
                df.loc[neg, c] = np.nan
                log.append(f"'{c}': {int(neg.sum())} impossible negative values → NaN")
    if impute == "median":
        for c in [c for c, r in roles.items() if r == "numeric"]:
            m = df[c].isna()
            if 0 < m.mean() <= 0.3:
                df[f"{c}__imputed"] = m
                df[c] = df[c].fillna(df[c].median())
                log.append(f"'{c}': imputed {int(m.sum())} missing with median; flag column '{c}__imputed'")
    if src is not None:
        df["_src"] = src.iloc[0] if len(src) else None
    return df, roles, log


def _rollup_provinces(silver: pd.DataFrame, config: dict, log: list[str]) -> tuple[pd.DataFrame, dict]:
    keys = ["province", "year"]
    measures = [c for c in config["sum"] if c in silver]
    if set(keys) - set(silver) or not measures:
        raise ValueError("province_rollup requires province, year and at least one additive measure")
    frame = silver[keys + measures].copy()
    province = frame["province"].map(lambda name: to_new_province(normalize_province(name)))
    invalid = province.isna() | frame["year"].isna()
    if invalid.any():
        samples = frame.loc[invalid, "province"].dropna().unique()[:5].tolist()
        log.append(f"province_rollup: {int(invalid.sum())} rows without a valid province/year excluded; examples: {samples!r}")
    frame["province"] = province
    grouped = frame.loc[~invalid].groupby(keys)[measures]
    rolled = grouped.sum(min_count=1).where(grouped.count().eq(grouped.size(), axis=0)).reset_index()
    log.append(f"province_rollup: {len(silver)} → {len(rolled)} rows at the 34-province × year grain; boundary break in 2025")
    roles = {"province": "geo", "year": "time", **dict.fromkeys(measures, "numeric")}
    for metric, (numerator, denominator) in config.get("ratios", {}).items():
        if numerator not in rolled or denominator not in rolled:
            log.append(f"{metric}: missing source columns {', '.join(c for c in (numerator, denominator) if c not in rolled)}")
            continue
        denom = rolled[denominator].where(rolled[denominator].ne(0))
        rolled[metric] = rolled[numerator] / denom
        roles[metric] = "numeric"
        log.append(f"{metric} = Σ{numerator} / Σ{denominator}")
    return rolled, roles


def quality_step(bronze: pd.DataFrame, impute: str | None = None, province_rollup: dict | None = None) -> dict:
    before = profile_quality(bronze)
    silver, roles, log = to_silver(bronze, impute=impute)
    if province_rollup:
        silver, roles = _rollup_provinces(silver, province_rollup, log)
    after = profile_quality(silver.drop(columns=[c for c in silver.columns if c.endswith("__imputed")]))
    return {"silver": silver, "roles": roles,
            "report": {"before": before, "after": after, "cleaning_log": log,
                       "score_before": before["score"], "score_after": after["score"]}}
