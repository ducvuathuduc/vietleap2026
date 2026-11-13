"""Transform step 1: data quality — profile bronze, clean to silver, score before/after.

Checks (as taught in the DE workshop): missing values, duplicates (full row + candidate key), outliers
(robust z / IQR, flagged, never deleted), wrong types (numbers stored as text), impossible negatives,
constant columns. Every change is written to a cleaning log so judges can audit it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..loader import clean
from ..vn import ascii_key, parse_numeric_series

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
    res = clean(raw, log)
    df = res.df
    roles = res.roles
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


def quality_step(bronze: pd.DataFrame, impute: str | None = None) -> dict:
    before = profile_quality(bronze)
    silver, roles, log = to_silver(bronze, impute=impute)
    after = profile_quality(silver.drop(columns=[c for c in silver.columns if c.endswith("__imputed")]))
    return {"silver": silver, "roles": roles,
            "report": {"before": before, "after": after, "cleaning_log": log,
                       "score_before": before["score"], "score_after": after["score"]}}
