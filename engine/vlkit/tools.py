"""Analysis tools exposed to the AI agent (and reused by the API). Each tool takes the cleaned DataFrame + results
and JSON arguments, and returns a JSON-serialisable dict. Tools may attach `chart` (a chart spec the UI renders) and
`table` ({columns, rows}). The agent may only quote numbers that appear in these outputs."""
from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from . import stats
from .models import fit_drivers as _fit_drivers, what_if as _what_if
from .stats import r


class ToolError(ValueError):
    pass


class Context:
    """Per-dataset state shared by tool calls in one agent session (e.g. fitted models)."""

    def __init__(self, df: pd.DataFrame, results: dict, whatif: dict | None = None):
        self.df, self.results = df, results
        self.meta = results["meta"]
        self.models: dict[str, dict] = {}
        if whatif:
            self.models[whatif["target"]] = {"whatif": whatif, "target": whatif["target"]}

    def col(self, name: str | None, kind: str = "any") -> str:
        if name is None:
            raise ToolError("column name required")
        if name in self.df.columns:
            c = name
        else:
            from .vn import ascii_key
            m = [c for c in self.df.columns if ascii_key(c) == ascii_key(name)]
            if not m:
                raise ToolError(f"unknown column '{name}'. Available: {[c for c in self.df.columns if not c.startswith('_')]}")
            c = m[0]
        if kind == "numeric" and not pd.api.types.is_numeric_dtype(self.df[c]):
            raise ToolError(f"column '{c}' is not numeric")
        return c


def describe_dataset(ctx: Context) -> dict:
    m, prof = ctx.meta, ctx.results["profile"]
    cols = [{"name": c["name"], "role": c["role"], "missing_pct": c["missing_pct"], "unique": c["unique"],
             **({"median": c.get("median"), "min": c.get("min"), "max": c.get("max")} if "median" in c else {}),
             **({"top_values": [t["value"] for t in c.get("top_values", [])[:5]]} if "top_values" in c else {})}
            for c in prof["column_profiles"]]
    return {"rows": m["rows"], "domain": m["domain"], "default_target": m["target"], "time_col": m["time_col"], "geo_col": m["geo_col"],
            "columns": cols, "caveats": ctx.results["caveats"][:5], "quality_issues": prof["issues"][:8]}


def run_groupby(ctx: Context, by: str, metric: str | None = None, agg: str = "median", top: int = 15) -> dict:
    by = ctx.col(by)
    metric = ctx.col(metric or ctx.meta["target"], "numeric")
    if agg not in ("median", "mean", "sum", "count"):
        raise ToolError("agg must be median|mean|sum|count")
    res = stats.groupby_summary(ctx.df, by, metric, "n" if agg == "count" else agg, top=min(int(top), 30))
    key = "n" if agg == "count" else agg
    res["chart"] = {"kind": "bar", "x": [row[by] for row in res["rows"]], "series": [{"name": f"{agg} {metric}", "data": [row[key] for row in res["rows"]]}],
                    "x_label": by, "y_label": f"{agg} {metric}"}
    res["table"] = {"columns": [by, "n", "median", "mean", "sum"], "rows": [[row[by], row["n"], row["median"], row["mean"], row["sum"]] for row in res["rows"]]}
    return res


def run_stat_test(ctx: Context, x: str, y: str | None = None, test: str = "auto", groups: list[str] | None = None) -> dict:
    x = ctx.col(x)
    y = ctx.col(y or ctx.meta["target"])
    try:
        out = stats.stat_test(ctx.df, test, x, y, groups)
    except ValueError as e:
        raise ToolError(str(e))
    out.pop("medians", None) if out.get("test") == "kruskal+anova" and len(out.get("medians", {})) > 15 else None
    return out


def fit_drivers(ctx: Context, target: str | None = None, features: list[str] | None = None) -> dict:
    target = ctx.col(target or ctx.meta["target"], "numeric")
    roles = ctx.meta["roles"]
    if features:
        feats = [ctx.col(f) for f in features]
        nums = [f for f in feats if pd.api.types.is_numeric_dtype(ctx.df[f])]
        cats = [f for f in feats if f not in nums]
    else:
        nums = [c for c, rr in roles.items() if rr == "numeric" and c in ctx.df and c != target]
        cats = [c for c in ctx.meta.get("category_cols", []) if c in ctx.df][:3]
    m = _fit_drivers(ctx.df, target, nums, cats)
    if not m:
        raise ToolError("not enough data to fit a model")
    ctx.models[target] = m
    imp = m["importance"][:10]
    return {"target": target, "n": m["n"], "cv_r2": m["cv_r2"], "log_target": m["log_target"], "leakage_excluded": m["leakage_excluded"],
            "importance": imp, "coefficients": m["coefficients"][:10], "note": m["note"],
            "chart": {"kind": "hbar", "x": [i["feature"] for i in imp], "series": [{"name": "permutation importance", "data": [i["importance"] for i in imp]}],
                      "x_label": "feature", "y_label": "importance"}}


def forecast(ctx: Context, metric: str | None = None, time: str | None = None, horizon: int = 3, agg: str = "median") -> dict:
    t = ctx.col(time or ctx.meta.get("time_col"))
    metric = ctx.col(metric or ctx.meta["target"], "numeric")
    ts = stats.time_series(ctx.df, t, metric, agg=agg)
    periods = [p["period"] for p in ts["points"]]
    vals = [p["value"] for p in ts["points"]]
    fc = stats.forecast(periods, vals, horizon=int(horizon))
    tr = stats.trend_stats(periods, vals)
    if fc is None:
        raise ToolError(f"need ≥6 complete periods to forecast; got {len(vals)}")
    return {"metric": metric, "agg": agg, "freq": ts["freq"], "history": ts["points"][-24:], "trend": tr, **fc,
            "chart": {"kind": "line", "x": periods + [f"+{i + 1}" for i in range(int(horizon))],
                      "series": [{"name": "actual", "data": vals + [None] * int(horizon)},
                                 {"name": "forecast", "data": [None] * (len(vals) - 1) + [vals[-1]] + fc["forecast"]},
                                 {"name": "lower80", "data": [None] * len(vals) + fc["lower80"]},
                                 {"name": "upper80", "data": [None] * len(vals) + fc["upper80"]}],
                      "x_label": t, "y_label": metric}}


def what_if(ctx: Context, feature: str, pct_change: float, target: str | None = None) -> dict:
    target = ctx.col(target or ctx.meta["target"], "numeric")
    if target not in ctx.models:
        fit_drivers(ctx, target)
    try:
        out = _what_if(ctx.models[target], feature, float(pct_change))
    except (KeyError, ValueError) as e:
        raise ToolError(str(e))
    return out


def make_chart(ctx: Context, kind: str, x: str, y: str | None = None, agg: str = "median", limit: int = 20) -> dict:
    x = ctx.col(x)
    if kind in ("bar", "hbar"):
        g = run_groupby(ctx, x, y, agg, limit)
        return {"chart": {**g["chart"], "kind": kind}, "rows": g["rows"]}
    if kind == "line":
        y = ctx.col(y or ctx.meta["target"], "numeric")
        ts = stats.time_series(ctx.df, x, y, agg=agg)
        return {"points": ts["points"], "chart": {"kind": "line", "x": [p["period"] for p in ts["points"]],
                                                  "series": [{"name": f"{agg} {y}", "data": [p["value"] for p in ts["points"]]}], "x_label": x, "y_label": y}}
    if kind == "scatter":
        y = ctx.col(y or ctx.meta["target"], "numeric")
        d = ctx.df[[x, y]].dropna()
        d = d.sample(min(400, len(d)), random_state=0)
        rho = stats.stat_test(ctx.df, "spearman", x, y)
        return {"spearman": rho, "chart": {"kind": "scatter", "x": [r(v) for v in d[x]], "series": [{"name": y, "data": [r(v) for v in d[y]]}],
                                           "x_label": x, "y_label": y}}
    if kind == "hist":
        v = ctx.df[ctx.col(x, "numeric")].dropna()
        cnt, edges = np.histogram(v.clip(v.quantile(0.01), v.quantile(0.99)), bins=20)
        return {"chart": {"kind": "bar", "x": [r(e) for e in edges[:-1]], "series": [{"name": "count", "data": cnt.tolist()}], "x_label": x, "y_label": "count"}}
    raise ToolError("kind must be bar|hbar|line|scatter|hist")


def ranked_insights(ctx: Context, top_n: int = 5) -> dict:
    keep = ("id", "rank", "type", "title_en", "sentence_en", "sentence_vi", "test", "p_value", "effect", "score", "value", "chart")
    return {"insights": [{k: i.get(k) for k in keep} for i in ctx.results["insights"][: int(top_n)]],
            "recommendations": ctx.results["recommendations"][:5]}


TOOLS: dict[str, tuple[Callable[..., dict], dict]] = {
    "describe_dataset": (describe_dataset, {"description": "Columns, roles, missingness, default target/time/geo columns, caveats.", "parameters": {"type": "object", "properties": {}}}),
    "run_groupby": (run_groupby, {"description": "Aggregate a numeric metric by a category/geo/time column (median/mean/sum/count). Returns a table and a bar chart.",
                                  "parameters": {"type": "object", "properties": {"by": {"type": "string"}, "metric": {"type": "string"},
                                                 "agg": {"type": "string", "enum": ["median", "mean", "sum", "count"]}, "top": {"type": "integer"}}, "required": ["by"]}}),
    "run_stat_test": (run_stat_test, {"description": "Statistical test between x and y. auto picks: numeric×numeric→Spearman, 2 groups→Mann–Whitney, k groups→Kruskal–Wallis+ANOVA, cat×cat→chi².",
                                      "parameters": {"type": "object", "properties": {"x": {"type": "string"}, "y": {"type": "string"},
                                                     "test": {"type": "string", "enum": ["auto", "mannwhitney", "ttest", "kruskal", "anova", "spearman", "pearson", "chi2"]},
                                                     "groups": {"type": "array", "items": {"type": "string"}}}, "required": ["x"]}}),
    "fit_drivers": (fit_drivers, {"description": "Fit ridge + gradient boosting on the target; 5-fold CV R², permutation importance, bootstrapped coefficients.",
                                  "parameters": {"type": "object", "properties": {"target": {"type": "string"}, "features": {"type": "array", "items": {"type": "string"}}}}}),
    "forecast": (forecast, {"description": "Aggregate the metric over time and forecast with linear/ETS (chosen by holdout MAE), 80% interval.",
                            "parameters": {"type": "object", "properties": {"metric": {"type": "string"}, "time": {"type": "string"}, "horizon": {"type": "integer"},
                                                                             "agg": {"type": "string", "enum": ["median", "mean", "sum"]}}}}),
    "what_if": (what_if, {"description": "Model-based scenario: change a numeric feature by pct_change % → expected % change in target with bootstrap 90% interval.",
                          "parameters": {"type": "object", "properties": {"feature": {"type": "string"}, "pct_change": {"type": "number"}, "target": {"type": "string"}},
                                         "required": ["feature", "pct_change"]}}),
    "make_chart": (make_chart, {"description": "Build a chart for the UI: bar/hbar (y aggregated by x), line (y over time x), scatter (x vs y), hist (distribution of x).",
                                "parameters": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["bar", "hbar", "line", "scatter", "hist"]},
                                                                                 "x": {"type": "string"}, "y": {"type": "string"}, "agg": {"type": "string"}}, "required": ["kind", "x"]}}),
    "ranked_insights": (ranked_insights, {"description": "The rule-based insight engine's ranked insights (effect × significance × relevance) and recommendations.",
                                          "parameters": {"type": "object", "properties": {"top_n": {"type": "integer"}}}}),
}


def call(ctx: Context, name: str, args: dict[str, Any] | None) -> dict:
    if name not in TOOLS:
        raise ToolError(f"unknown tool {name}")
    fn = TOOLS[name][0]
    return fn(ctx, **(args or {}))


def openai_specs() -> list[dict]:
    return [{"type": "function", "function": {"name": n, **spec}} for n, (_, spec) in TOOLS.items()]
