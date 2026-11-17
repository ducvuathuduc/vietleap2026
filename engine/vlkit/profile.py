"""Data profile: shape, missingness, distributions, cardinality, quality issues and caveats."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import fmt
from .i18n import LANGS, t
from .stats import r


def _issue(severity: str, column: str, key: str, **values) -> dict:
    """A quality issue in both languages (issue = EN, issue_vi = VI); numeric values get the language's decimal mark."""
    def text(lang: str) -> str:
        return t(lang, key, **{k: v if isinstance(v, str) else fmt.dec(v, lang) for k, v in values.items()})
    return {"severity": severity, "column": column, "issue": text("en"), "issue_vi": text("vi")}


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
            issues.append(_issue("high" if miss > 0.6 else "medium", c, "issue_missing", pct=f"{miss:.0%}"))
        if roles.get(c) == "constant":
            issues.append(_issue("low", c, "issue_constant"))
        neg = info.get("negative_pct")
        if neg and neg > 0 and any(w in c.lower() for w in ["area", "dien", "diện", "price", "gia", "giá", "population", "dân"]):
            issues.append(_issue("medium", c, "issue_negative", pct=neg))
        skew = info.get("skew")
        if skew and abs(skew) > 5:
            issues.append(_issue("low", c, "issue_skew", skew=skew))
        if c in numeric_reports and numeric_reports[c].get("failed"):
            issues.append(_issue("low", c, "issue_unparsed", n=numeric_reports[c]["failed"]))
    total_missing = float(df[[c for c in df.columns if not c.startswith('_')]].isna().mean().mean())
    return {"rows": n, "columns": len(cols), "missing_overall_pct": r(total_missing * 100),
            "roles": {k: sum(1 for c in cols if c["role"] == k) for k in sorted({c["role"] for c in cols})},
            "column_profiles": cols, "issues": issues,
            "outlier_rows_pct": r(float(df["_outlier_any"].mean()) * 100) if "_outlier_any" in df else 0}


def _caveat_lines(lang: str, prof: dict, domain_caveats: list[dict[str, str]], time_col: str | None, n: int) -> list[str]:
    out = [t(lang, "cav_causal")] + [c[lang] for c in domain_caveats]
    hi = [i for i in prof["issues"] if i["severity"] in ("high", "medium")]
    if hi:
        issue = hi[0].get("issue_vi") if lang == "vi" else None
        out.append(t(lang, "cav_quality", n=len(hi), column=hi[0]["column"], issue=issue or hi[0]["issue"]))
    if prof.get("outlier_rows_pct", 0) > 1:
        out.append(t(lang, "cav_outliers", pct=fmt.dec(prof["outlier_rows_pct"], lang)))
    if not time_col:
        out.append(t(lang, "cav_no_time"))
    if n < 200:
        out.append(t(lang, "cav_small_n", n=n))
    out.append(t(lang, "cav_multiple"))
    return out


def caveats(prof: dict, domain_caveats: list[dict[str, str]], time_col: str | None, n: int) -> dict[str, list[str]]:
    """Caveats as parallel lists {"en": [...], "vi": [...]}: same order, same numbers; the causal caveat first."""
    return {lang: _caveat_lines(lang, prof, domain_caveats, time_col, n) for lang in LANGS}
