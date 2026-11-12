"""Data profile: shape, missingness, distributions, cardinality, quality issues and caveats."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import r


def profile(df: pd.DataFrame, roles: dict, numeric_reports: dict, outlier_counts: dict) -> dict:
    n = len(df)
    cols = []
    issues = []
    for c in df.columns:
        if c.startswith("_"):
            continue
        s = df[c]
        miss = float(s.isna().mean())
        info = {"name": c, "role": roles.get(c, "?"), "dtype": str(s.dtype), "missing_pct": r(miss * 100), "unique": int(s.nunique(dropna=True))}
        if pd.api.types.is_numeric_dtype(s) and roles.get(c) in ("numeric", "time", "id"):
            d = s.dropna()
            if len(d):
                info.update({"mean": r(d.mean()), "median": r(d.median()), "std": r(d.std()), "min": r(d.min()), "p05": r(d.quantile(0.05)),
                             "p95": r(d.quantile(0.95)), "max": r(d.max()), "skew": r(d.skew()), "zeros_pct": r((d == 0).mean() * 100),
                             "negative_pct": r((d < 0).mean() * 100), "outliers": int(outlier_counts.get(c, 0))})
                hist, edges = np.histogram(d.clip(d.quantile(0.01), d.quantile(0.99)), bins=20)
                info["hist"] = {"counts": hist.tolist(), "edges": [r(e) for e in edges]}
        elif pd.api.types.is_datetime64_any_dtype(s):
            d = s.dropna()
            if len(d):
                info.update({"min": str(d.min().date()), "max": str(d.max().date())})
        else:
            vc = s.astype(str).where(s.notna()).value_counts().head(8)
            info["top_values"] = [{"value": k, "count": int(v)} for k, v in vc.items()]
        if c in numeric_reports:
            info["parsing"] = numeric_reports[c]
        cols.append(info)
        if miss > 0.3:
            issues.append({"severity": "high" if miss > 0.6 else "medium", "column": c, "issue": f"{miss:.0%} missing values"})
        if roles.get(c) == "constant":
            issues.append({"severity": "low", "column": c, "issue": "constant column (no information)"})
        if info.get("negative_pct") and info["negative_pct"] > 0 and any(w in c.lower() for w in ["area", "dien", "diện", "price", "gia", "giá", "population", "dân"]):
            issues.append({"severity": "medium", "column": c, "issue": f"{info['negative_pct']}% negative values in a quantity that should be positive"})
        if info.get("skew") and abs(info["skew"]) > 5:
            issues.append({"severity": "low", "column": c, "issue": f"heavily skewed (skew {info['skew']}); use medians/log scale"})
        if c in numeric_reports and numeric_reports[c].get("failed"):
            issues.append({"severity": "low", "column": c, "issue": f"{numeric_reports[c]['failed']} values could not be parsed as numbers"})
    total_missing = float(df[[c for c in df.columns if not c.startswith('_')]].isna().mean().mean())
    return {"rows": n, "columns": len(cols), "missing_overall_pct": r(total_missing * 100),
            "roles": {k: sum(1 for c in cols if c["role"] == k) for k in sorted({c["role"] for c in cols})},
            "column_profiles": cols, "issues": issues,
            "outlier_rows_pct": r(float(df["_outlier_any"].mean()) * 100) if "_outlier_any" in df else 0}


def caveats(prof: dict, domain_caveats: list[str], time_col: str | None, n: int) -> list[str]:
    out = ["Observational data: relationships reported are associations, not causal effects."]
    out += domain_caveats
    hi = [i for i in prof["issues"] if i["severity"] in ("high", "medium")]
    if hi:
        out.append(f"{len(hi)} column(s) have notable data-quality issues (e.g. {hi[0]['column']}: {hi[0]['issue']}); results using them are less reliable.")
    if prof.get("outlier_rows_pct", 0) > 1:
        out.append(f"{prof['outlier_rows_pct']}% of rows contain extreme values; they are flagged, not removed, and robust statistics are used.")
    if not time_col:
        out.append("No time dimension detected: findings describe one snapshot and say nothing about trends.")
    if n < 200:
        out.append(f"Small sample (n={n}): statistical power is limited and effect estimates are noisy.")
    out.append("Multiple comparisons: many tests are run; treat p-values near 0.05 as exploratory.")
    return out
