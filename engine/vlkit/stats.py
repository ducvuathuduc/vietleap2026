"""Statistical building blocks. Every function returns plain JSON-serialisable dicts so the same code serves the
insight engine, the API and the AI agent's tools (the agent may only quote numbers these functions return)."""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd
from scipy import stats as ss

warnings.filterwarnings("ignore")

RNG = 42


def r(x, k=4):
    """Round for JSON; None for NaN/inf."""
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return x
    if math.isnan(xf) or math.isinf(xf):
        return None
    if xf == 0:
        return 0.0
    mag = int(math.floor(math.log10(abs(xf))))
    return round(xf, max(k - 1 - mag, 0)) if abs(xf) < 1e15 else xf


def sig_label(p):
    if p is None:
        return "n/a"
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


# ----------------------------------------------------------------------------- grouping

def top_levels(s: pd.Series, k: int = 15, min_n: int = 5) -> pd.Series:
    vc = s.value_counts()
    keep = vc[vc >= min_n].index[:k]
    return s.where(s.isin(keep), other=np.where(s.isna(), None, "Other"))


def groupby_summary(df: pd.DataFrame, by: str, metric: str, agg: str = "median", top: int = 15) -> dict:
    g = df[[by, metric]].dropna()
    if pd.api.types.is_datetime64_any_dtype(g[by]):
        g[by] = g[by].dt.to_period("M").astype(str)
    grp = g.groupby(by)[metric]
    tab = pd.DataFrame({"n": grp.size(), "mean": grp.mean(), "median": grp.median(), "sum": grp.sum(),
                        "std": grp.std()}).reset_index()
    tab = tab[tab["n"] >= 1].sort_values(agg if agg in tab else "median", ascending=False)
    total = len(tab)
    tab = tab.head(top)
    rows = [{by: str(row[by]), **{k: r(row[k]) for k in ["n", "mean", "median", "sum", "std"]}} for _, row in tab.iterrows()]
    return {"by": by, "metric": metric, "agg": agg, "groups_total": int(total), "rows": rows}


def compare_groups(df: pd.DataFrame, by: str, metric: str, min_n: int = 10, max_groups: int = 15) -> dict | None:
    """Omnibus test (Kruskal–Wallis + one-way ANOVA) and top-vs-bottom Mann–Whitney with effect sizes."""
    d = df[[by, metric]].dropna()
    if d.empty:
        return None
    d = d.assign(**{by: top_levels(d[by].astype(str), max_groups, min_n)})
    d = d[d[by] != "Other"]
    groups = {k: v[metric].values for k, v in d.groupby(by) if len(v) >= min_n}
    if len(groups) < 2:
        return None
    meds = {k: float(np.median(v)) for k, v in groups.items()}
    top_k = max(meds, key=meds.get)
    bot_k = min(meds, key=meds.get)
    arrays = list(groups.values())
    N = sum(len(a) for a in arrays)
    k = len(arrays)
    try:
        H, p_kw = ss.kruskal(*arrays)
    except ValueError:
        return None
    eps2 = max(0.0, (H - k + 1) / (N - k)) if N > k else None  # epsilon-squared
    F, p_anova = ss.f_oneway(*arrays)
    grand = np.concatenate(arrays)
    ss_b = sum(len(a) * (a.mean() - grand.mean()) ** 2 for a in arrays)
    ss_t = ((grand - grand.mean()) ** 2).sum()
    eta2 = ss_b / ss_t if ss_t > 0 else None
    a, b = groups[top_k], groups[bot_k]
    U, p_mw = ss.mannwhitneyu(a, b, alternative="two-sided")
    rbc = 1 - 2 * U / (len(a) * len(b))  # rank-biserial correlation
    rbc = -rbc  # positive when top > bottom
    t, p_t = ss.ttest_ind(a, b, equal_var=False)
    pooled = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2) if len(a) > 1 and len(b) > 1 else 0
    cohen_d = (a.mean() - b.mean()) / pooled if pooled else None
    ratio = meds[top_k] / meds[bot_k] if meds[bot_k] not in (0, None) else None
    return {
        "by": by, "metric": metric, "n": int(N), "k_groups": int(k),
        "kruskal": {"H": r(H), "p": r(p_kw), "epsilon2": r(eps2)},
        "anova": {"F": r(F), "p": r(p_anova), "eta2": r(eta2)},
        "top": {"group": str(top_k), "median": r(meds[top_k]), "n": int(len(a)), "mean": r(a.mean())},
        "bottom": {"group": str(bot_k), "median": r(meds[bot_k]), "n": int(len(b)), "mean": r(b.mean())},
        "top_vs_bottom": {"mannwhitney_U": r(U), "p": r(p_mw), "rank_biserial": r(rbc),
                          "welch_t": r(t), "welch_p": r(p_t), "cohen_d": r(cohen_d), "median_ratio": r(ratio)},
        "medians": {str(k): r(v) for k, v in sorted(meds.items(), key=lambda kv: -kv[1])},
        "overall_median": r(np.median(grand)),
    }


def stat_test(df: pd.DataFrame, test: str, x: str, y: str | None = None, groups: list[str] | None = None) -> dict:
    """Generic test entry point used by the agent. test ∈ {auto, mannwhitney, ttest, kruskal, anova, spearman, pearson, chi2}."""
    test = (test or "auto").lower()
    if y is None:
        raise ValueError("y is required")
    if test in ("spearman", "pearson") or (test == "auto" and pd.api.types.is_numeric_dtype(df[x]) and pd.api.types.is_numeric_dtype(df[y])):
        d = df[[x, y]].dropna()
        f = ss.pearsonr if test == "pearson" else ss.spearmanr
        rho, p = f(d[x], d[y])
        return {"test": "pearson" if test == "pearson" else "spearman", "x": x, "y": y, "n": int(len(d)), "r": r(rho), "p": r(p),
                "note": "association only, not causation"}
    if test == "chi2" or (test == "auto" and not pd.api.types.is_numeric_dtype(df[y])):
        ct = pd.crosstab(df[x], df[y])
        chi2, p, dof, _ = ss.chi2_contingency(ct)
        n = ct.values.sum()
        v = math.sqrt(chi2 / (n * (min(ct.shape) - 1))) if min(ct.shape) > 1 else None
        return {"test": "chi2", "x": x, "y": y, "n": int(n), "chi2": r(chi2), "dof": int(dof), "p": r(p), "cramers_v": r(v)}
    d = df[[x, y]].dropna()
    if groups:
        d = d[d[x].astype(str).isin([str(g) for g in groups])]
    if test in ("mannwhitney", "ttest") or (test == "auto" and d[x].nunique() == 2):
        lv = list(d[x].astype(str).value_counts().index[:2]) if not groups else [str(g) for g in groups[:2]]
        a = d[d[x].astype(str) == lv[0]][y].values
        b = d[d[x].astype(str) == lv[1]][y].values
        if test == "ttest":
            t, p = ss.ttest_ind(a, b, equal_var=False)
            pooled = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
            return {"test": "welch_t", "groups": lv, "n": [len(a), len(b)], "means": [r(a.mean()), r(b.mean())],
                    "t": r(t), "p": r(p), "cohen_d": r((a.mean() - b.mean()) / pooled if pooled else None)}
        U, p = ss.mannwhitneyu(a, b, alternative="two-sided")
        return {"test": "mann_whitney", "groups": lv, "n": [len(a), len(b)], "medians": [r(np.median(a)), r(np.median(b))],
                "U": r(U), "p": r(p), "rank_biserial": r(-(1 - 2 * U / (len(a) * len(b))))}
    res = compare_groups(d, x, y, min_n=3)
    if res is None:
        return {"error": "not enough data per group"}
    return {"test": "kruskal+anova", **res}


# ----------------------------------------------------------------------------- correlations

def correlations(df: pd.DataFrame, cols: list[str], target: str | None = None, max_cols: int = 15) -> dict:
    cols = [c for c in cols if df[c].nunique() > 2][:max_cols]
    if len(cols) < 2:
        return {"pairs": [], "matrix": {}}
    d = df[cols]
    rho = d.corr(method="spearman")
    pairs = []
    m = len(cols) * (len(cols) - 1) / 2
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            dd = d[[a, b]].dropna()
            if len(dd) < 10:
                continue
            rr, p = ss.spearmanr(dd[a], dd[b])
            pairs.append({"a": a, "b": b, "rho": r(rr), "p": r(p), "p_bonferroni": r(min(1.0, p * m)), "n": int(len(dd))})
    pairs.sort(key=lambda x: -abs(x["rho"] or 0))
    # partial correlation with the target controlling for the other variables (rank-based)
    partial = {}
    if target and target in cols and len(cols) >= 3:
        rk = d.dropna().rank()
        if len(rk) > len(cols) + 5:
            for c in cols:
                if c == target:
                    continue
                ctrl = [x for x in cols if x not in (c, target)]
                X = np.column_stack([np.ones(len(rk))] + [rk[x] for x in ctrl])
                ra = rk[c] - X @ np.linalg.lstsq(X, rk[c], rcond=None)[0]
                rb = rk[target] - X @ np.linalg.lstsq(X, rk[target], rcond=None)[0]
                pc = np.corrcoef(ra, rb)[0, 1]
                partial[c] = r(pc)
    return {"pairs": pairs, "matrix": {a: {b: r(rho.loc[a, b], 3) for b in cols} for a in cols}, "partial_with_target": partial}


# ----------------------------------------------------------------------------- concentration

def concentration(values: pd.Series, labels: pd.Series | None = None) -> dict | None:
    v = values.dropna()
    v = v[v > 0]
    if len(v) < 5:
        return None
    s = np.sort(v.values)[::-1]
    share = s / s.sum()
    n = len(s)
    top20 = share[: max(1, int(math.ceil(0.2 * n)))].sum()
    srt = np.sort(v.values)
    gini = (2 * np.sum((np.arange(1, n + 1)) * srt) / (n * srt.sum())) - (n + 1) / n
    hhi = float((share ** 2).sum() * 10000)
    out = {"n": int(n), "top20_share": r(top20), "gini": r(gini), "hhi": r(hhi)}
    if labels is not None:
        lab = labels.loc[v.sort_values(ascending=False).index].astype(str).tolist()[:10]
        out["top_labels"] = lab
        out["top_shares"] = [r(x) for x in share[:10]]
    return out


# ----------------------------------------------------------------------------- time series

def choose_freq(t: pd.Series) -> str:
    t = t.dropna()
    if t.empty:
        return "Y"
    if pd.api.types.is_numeric_dtype(t):
        return "Y"
    u = pd.Series(t.unique())
    if len(u) >= 2 and (u.dt.day == 1).all() and u.dt.month.isin([1, 4, 7, 10]).all():
        return "Y" if u.dt.month.eq(1).all() else "Q"
    span_days = (t.max() - t.min()).days
    if span_days > 365 * 4:
        return "Y"
    if span_days > 365 * 1.5:
        return "Q"
    if span_days > 60:
        return "M"
    return "W"


def time_series(df: pd.DataFrame, time_col: str, metric: str | None, agg: str = "median", freq: str | None = None,
                group: str | None = None) -> dict:
    d = df[[time_col] + ([metric] if metric else []) + ([group] if group else [])].dropna(subset=[time_col])
    t = d[time_col]
    freq = freq or choose_freq(t)
    if pd.api.types.is_numeric_dtype(t):
        key = t.astype(int).astype(str)
    else:
        key = t.dt.to_period(freq).astype(str)
    d = d.assign(_p=key)
    keys = ["_p"] + ([group] if group else [])
    if metric:
        g = d.groupby(keys)[metric].agg(agg if agg != "count" else "size")
    else:
        g = d.groupby(keys).size()
    cnt = d.groupby(keys).size()
    out = g.reset_index().rename(columns={"_p": "period", 0: "value", metric or 0: "value"})
    out.columns = ["period"] + ([group] if group else []) + ["value"]
    out["n"] = cnt.values
    return {"time": time_col, "metric": metric, "agg": agg, "freq": freq,
            "points": [{k: (r(v) if k in ("value",) else (int(v) if k == "n" else str(v))) for k, v in row.items()} for row in out.to_dict("records")]}


def trend_stats(periods: list[str], values: list[float]) -> dict | None:
    y = np.array([v for v in values if v is not None], dtype=float)
    if len(y) < 4:
        return None
    x = np.arange(len(y))
    lr = ss.linregress(x, y)
    rho, p_rho = ss.spearmanr(x, y)
    first, last = y[0], y[-1]
    cagr = (last / first) ** (1 / (len(y) - 1)) - 1 if first > 0 and last > 0 else None
    last_growth = (y[-1] / y[-2] - 1) if y[-2] not in (0,) else None
    # single structural break: best split by SSE of two linear fits; F-test vs one line (Chow)
    best = None
    sse_full = ((y - (lr.intercept + lr.slope * x)) ** 2).sum()
    for b in range(3, len(y) - 2):
        s1 = ss.linregress(x[:b], y[:b]); s2 = ss.linregress(x[b:], y[b:])
        sse = ((y[:b] - (s1.intercept + s1.slope * x[:b])) ** 2).sum() + ((y[b:] - (s2.intercept + s2.slope * x[b:])) ** 2).sum()
        if best is None or sse < best[1]:
            best = (b, sse, s1.slope, s2.slope)
    brk = None
    if best and len(y) >= 8:
        kpar = 2
        F = ((sse_full - best[1]) / kpar) / (best[1] / (len(y) - 2 * kpar)) if best[1] > 0 else None
        pF = 1 - ss.f.cdf(F, kpar, len(y) - 2 * kpar) if F is not None else None
        brk = {"at": periods[best[0]], "slope_before": r(best[2]), "slope_after": r(best[3]), "F": r(F), "p": r(pF)}
    # anomalies: robust z of first differences
    anomalies = []
    if len(y) >= 6:
        resid = y - (lr.intercept + lr.slope * x)
        med = np.median(resid); mad = np.median(np.abs(resid - med)) * 1.4826
        if mad > 0:
            z = (resid - med) / mad
            anomalies = [{"period": periods[i], "value": r(y[i]), "robust_z": r(z[i])} for i in np.where(np.abs(z) > 3)[0]]
    return {"n_periods": int(len(y)), "first": r(first), "last": r(last), "total_change_pct": r((last / first - 1) * 100) if first else None,
            "cagr_pct": r(cagr * 100) if cagr is not None else None, "last_period_growth_pct": r(last_growth * 100) if last_growth is not None else None,
            "slope_per_period": r(lr.slope), "slope_p": r(lr.pvalue), "r2": r(lr.rvalue ** 2), "spearman_rho": r(rho), "spearman_p": r(p_rho),
            "break": brk, "anomalies": anomalies}


def forecast(periods: list[str], values: list[float], horizon: int = 3) -> dict | None:
    y = np.array(values, dtype=float)
    if len(y) < 6 or np.isnan(y).any():
        return None
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    n_test = max(1, int(round(len(y) * 0.2)))
    train, test = y[:-n_test], y[-n_test:]
    res = {}
    # linear
    x = np.arange(len(train))
    lr = ss.linregress(x, train)
    pred_lin = lr.intercept + lr.slope * np.arange(len(train), len(y))
    res["linear"] = float(np.mean(np.abs(pred_lin - test)))
    try:
        ets = ExponentialSmoothing(train, trend="add", initialization_method="estimated").fit()
        res["ets"] = float(np.mean(np.abs(ets.forecast(n_test) - test)))
    except Exception:
        pass
    best = min(res, key=res.get)
    xf = np.arange(len(y))
    if best == "ets":
        m = ExponentialSmoothing(y, trend="add", initialization_method="estimated").fit()
        fc = m.forecast(horizon)
        resid = y - m.fittedvalues
    else:
        lr = ss.linregress(xf, y)
        fc = lr.intercept + lr.slope * np.arange(len(y), len(y) + horizon)
        resid = y - (lr.intercept + lr.slope * xf)
    sd = float(np.std(resid, ddof=1))
    z = 1.2816  # 80% interval
    lo = [fc[i] - z * sd * math.sqrt(1 + i * 0.5) for i in range(horizon)]
    hi = [fc[i] + z * sd * math.sqrt(1 + i * 0.5) for i in range(horizon)]
    return {"model": best, "holdout_mae": {k: r(v) for k, v in res.items()}, "horizon": horizon,
            "forecast": [r(v) for v in fc], "lower80": [r(v) for v in lo], "upper80": [r(v) for v in hi],
            "note": "simple univariate extrapolation; assumes the recent pattern continues"}


# ----------------------------------------------------------------------------- segmentation

def segment(df: pd.DataFrame, cols: list[str], kmax: int = 6, sample: int = 5000) -> dict | None:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler
    cols = [c for c in cols if df[c].nunique() > 5][:8]
    if len(cols) < 2:
        return None
    d = df[cols].dropna()
    if len(d) < 30:
        return None
    X = d.copy()
    logged = []
    for c in cols:
        if (X[c] > 0).all() and X[c].skew() > 1:
            X[c] = np.log1p(X[c]); logged.append(c)
    Xs = StandardScaler().fit_transform(X)
    Xs = np.clip(Xs, -5, 5)
    idx = np.random.default_rng(RNG).choice(len(Xs), min(sample, len(Xs)), replace=False)
    best = None
    for k in range(2, kmax + 1):
        km = KMeans(k, n_init=3, random_state=RNG).fit(Xs[idx])
        if np.bincount(km.labels_).min() < 0.05 * len(idx):
            continue  # a 'segment' of <5% is an outlier group, not a segment
        sc = silhouette_score(Xs[idx], km.labels_, sample_size=min(2000, len(idx)), random_state=RNG)
        if best is None or sc > best[1]:
            best = (k, sc)
    if best is None:
        return None
    km = KMeans(best[0], n_init=5, random_state=RNG).fit(Xs[idx])
    lab = km.predict(Xs)
    prof = []
    overall = d.median()
    for k in range(best[0]):
        part = d[lab == k]
        med = part.median()
        zdiff = ((X[lab == k].mean() - X.mean()) / X.std()).sort_values(key=abs, ascending=False)
        prof.append({"cluster": int(k), "size": int(len(part)), "share": r(len(part) / len(d)),
                     "medians": {c: r(med[c]) for c in cols},
                     "distinctive": [{"feature": f, "z": r(z), "median": r(med[f]), "overall_median": r(overall[f])} for f, z in zdiff.head(3).items()]})
    prof.sort(key=lambda p: -p["size"])
    labels = pd.Series(lab, index=d.index)
    return {"k": int(best[0]), "silhouette": r(best[1]), "features": cols, "log_transformed": logged,
            "profiles": prof, "_labels": labels}
