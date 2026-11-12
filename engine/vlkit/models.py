"""Driver models (regularised linear + gradient boosting with permutation importance) and the what-if calculator.

The what-if uses a bootstrapped Ridge model on standardised features so that its uncertainty is explicit and the
whole calculator can be serialised to JSON (used by the API, static HTML dashboard and the AI agent)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import RNG, r


def _design(df: pd.DataFrame, target: str, numeric: list[str], categorical: list[str], max_levels: int = 15):
    cols = [c for c in numeric if c != target and df[c].notna().mean() > 0.5 and df[c].nunique() > 2]
    d = df[[target] + cols + categorical].dropna(subset=[target])
    for c in cols:
        d[c] = d[c].fillna(d[c].median())
    X = d[cols].copy()
    for c in categorical:
        top = d[c].astype(str).value_counts().index[:max_levels]
        for lv in top[1:]:  # first level = reference
            X[f"{c}={lv}"] = (d[c].astype(str) == lv).astype(float)
    return X, d[target].astype(float), cols


def leakage_filter(df: pd.DataFrame, target: str, cols: list[str], thr: float = 0.97) -> tuple[list[str], list[str]]:
    keep, dropped = [], []
    for c in cols:
        dd = df[[c, target]].dropna()
        if len(dd) > 10 and abs(dd[c].corr(dd[target], method="spearman")) >= thr:
            dropped.append(c)
        else:
            keep.append(c)
    return keep, dropped


def fit_drivers(df: pd.DataFrame, target: str, numeric: list[str], categorical: list[str] | None = None,
                n_boot: int = 200, max_rows: int = 20000, exclude: list[str] | None = None) -> dict | None:
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.inspection import permutation_importance
    from sklearn.linear_model import Ridge, RidgeCV
    from sklearn.model_selection import KFold, cross_val_score, train_test_split
    categorical = [c for c in (categorical or []) if 2 <= df[c].nunique() <= 40][:3]
    numeric = [c for c in numeric if c != target and c not in (exclude or [])]
    numeric, leaked = leakage_filter(df, target, numeric)
    if not numeric and not categorical:
        return None
    d = df.sample(min(len(df), max_rows), random_state=RNG) if len(df) > max_rows else df
    X, y, num_used = _design(d, target, numeric, categorical)
    if len(y) < 30 or X.shape[1] == 0:
        return None
    log_target = bool((y > 0).all() and y.skew() > 1)
    yt = np.log(y) if log_target else y
    mu, sd = X.mean(), X.std().replace(0, 1)
    Xs = (X - mu) / sd
    cv = KFold(5, shuffle=True, random_state=RNG)
    ridge = RidgeCV(alphas=np.logspace(-3, 3, 13)).fit(Xs, yt)
    r2_lin = cross_val_score(Ridge(alpha=ridge.alpha_), Xs, yt, cv=cv, scoring="r2")
    gb = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.08, random_state=RNG)
    r2_gb = cross_val_score(gb, X, yt, cv=cv, scoring="r2")
    Xtr, Xte, ytr, yte = train_test_split(X, yt, test_size=0.25, random_state=RNG)
    gb.fit(Xtr, ytr)
    pi = permutation_importance(gb, Xte, yte, n_repeats=5, random_state=RNG)
    imp = sorted(({"feature": f, "importance": r(m), "std": r(s)} for f, m, s in zip(X.columns, pi.importances_mean, pi.importances_std)),
                 key=lambda x: -(x["importance"] or 0))
    # bootstrap ridge for uncertainty
    rng = np.random.default_rng(RNG)
    B = []
    Xv, yv = Xs.values, yt.values
    for _ in range(n_boot):
        ii = rng.integers(0, len(yv), len(yv))
        B.append(Ridge(alpha=ridge.alpha_).fit(Xv[ii], yv[ii]).coef_)
    B = np.array(B)
    coefs = []
    for j, f in enumerate(X.columns):
        lo, hi = np.percentile(B[:, j], [5, 95])
        coefs.append({"feature": f, "coef_std": r(ridge.coef_[j]), "ci90": [r(lo), r(hi)],
                      "direction": "+" if ridge.coef_[j] > 0 else "-", "stable": bool(lo * hi > 0)})
    coefs.sort(key=lambda c: -abs(c["coef_std"] or 0))
    whatif = {
        "target": target, "log_target": log_target, "target_mean": r(float(y.mean())), "target_median": r(float(y.median())),
        "intercept": r(float(ridge.intercept_)), "alpha": r(float(ridge.alpha_)),
        "features": [{"name": f, "mean": r(float(mu[f])), "sd": r(float(sd[f])), "median": r(float(X[f].median())),
                      "beta": float(ridge.coef_[j]), "boot": [float(b) for b in B[:, j]], "numeric": f in num_used}
                     for j, f in enumerate(X.columns)],
    }
    return {
        "target": target, "n": int(len(y)), "features": list(X.columns), "leakage_excluded": leaked,
        "log_target": log_target,
        "cv_r2": {"ridge_mean": r(r2_lin.mean()), "ridge_std": r(r2_lin.std()), "gb_mean": r(r2_gb.mean()), "gb_std": r(r2_gb.std())},
        "importance": imp, "coefficients": coefs, "whatif": whatif,
        "note": "Associations from observational data; coefficients are conditional on the other features and are not causal effects.",
    }


def what_if(model: dict, feature: str, pct_change: float) -> dict:
    """Change `feature` by pct_change % for every row → expected change in target (bootstrap 90% interval)."""
    wi = model["whatif"] if "whatif" in model else model
    f = next((x for x in wi["features"] if x["name"] == feature), None)
    if f is None:
        raise KeyError(f"feature '{feature}' not in model; available: {[x['name'] for x in wi['features']]}")
    if not f.get("numeric", True):
        raise ValueError("what-if % change only applies to numeric features")
    dx = f["mean"] * pct_change / 100.0
    dz = dx / f["sd"] if f["sd"] else 0.0
    boot = np.array(f["boot"]) * dz
    point = f["beta"] * dz
    base = wi["target_mean"]
    if wi["log_target"]:
        pct = (np.exp(point) - 1) * 100
        lo, hi = np.percentile((np.exp(boot) - 1) * 100, [5, 95])
    else:
        pct = point / base * 100 if base else None
        lo, hi = np.percentile(boot / base * 100, [5, 95]) if base else (None, None)
    return {"feature": feature, "pct_change": pct_change, "target": wi["target"],
            "target_change_pct": r(pct), "ci90_pct": [r(lo), r(hi)],
            "target_change_abs": r(base * pct / 100) if base and pct is not None else None,
            "baseline_target_mean": r(base),
            "interpretation": "model-based association holding other features fixed; not a causal guarantee"}
