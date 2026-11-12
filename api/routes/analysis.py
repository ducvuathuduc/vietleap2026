"""Analysis endpoints: insights, time series, segments, drivers, what-if."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from vlkit import stats
from vlkit import tools as T

from ..schemas import WhatIfRequest
from ..store import Store, get_store
from .datasets import ds_or_404

router = APIRouter(prefix="/api/datasets/{ds_id}", tags=["analysis"])


@router.get("/insights")
def insights(ds_id: str, store: Store = Depends(get_store)):
    r = ds_or_404(store, ds_id).results
    return {"insights": r["insights"], "recommendations": r["recommendations"]}


@router.get("/timeseries")
def timeseries(ds_id: str, metric: str | None = None, agg: str = Query("median", pattern="^(median|mean|sum|count)$"),
               freq: str | None = Query(None, pattern="^(Y|Q|M|W|D)$"), group: str | None = None, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    meta = ds.results["meta"]
    t = meta.get("time_col")
    if not t:
        return {"time": None, "points": [], "metric": metric or meta["target"], "agg": agg, "freq": None}
    ctx = T.Context(ds.df, ds.results)
    try:
        m = ctx.col(metric or meta["target"], "numeric")
        g = ctx.col(group) if group else None
    except T.ToolError as e:
        raise HTTPException(422, str(e))
    out = stats.time_series(ds.df, t, m if agg != "count" else None, agg=agg if agg != "count" else "count", freq=freq, group=g)
    if ds.results.get("timeseries") and not group and m == meta["target"]:
        out["trend"] = ds.results["timeseries"].get("trend")
        out["forecast"] = ds.results["timeseries"].get("forecast")
    return out


@router.get("/segments")
def segments(ds_id: str, by: str | None = None, metric: str | None = None, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    meta = ds.results["meta"]
    ctx = T.Context(ds.df, ds.results)
    by = by or meta.get("geo_col") or (meta["category_cols"] or [None])[0]
    if not by:
        raise HTTPException(422, "no categorical column available")
    try:
        g = T.run_groupby(ctx, by, metric, "median", 25)
        test = T.run_stat_test(ctx, by, metric)
    except T.ToolError as e:
        raise HTTPException(422, str(e))
    return {"by": by, "metric": g["metric"], "groups": g["rows"], "groups_total": g["groups_total"], "test": test,
            "options": meta["category_cols"], "clusters": ds.results.get("segments")}


@router.get("/drivers")
def drivers(ds_id: str, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    d = ds.results.get("drivers")
    feats = []
    if ds.whatif:
        feats = [{"name": f["name"], "mean": f["mean"], "sd": f["sd"], "median": f.get("median")} for f in ds.whatif["features"] if f["numeric"]]
    return {"drivers": d, "whatif_features": feats, "target": ds.results["meta"]["target"]}


@router.post("/whatif")
def whatif(ds_id: str, req: WhatIfRequest, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    ctx = T.Context(ds.df, ds.results, ds.whatif)
    try:
        return T.what_if(ctx, req.feature, req.pct_change, req.target)
    except T.ToolError as e:
        raise HTTPException(422, str(e))


@router.get("/whatif/curve")
def whatif_curve(ds_id: str, feature: str, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    ctx = T.Context(ds.df, ds.results, ds.whatif)
    pts = []
    for p in range(-30, 31, 5):
        try:
            w = T.what_if(ctx, feature, p)
        except T.ToolError as e:
            raise HTTPException(422, str(e))
        pts.append({"pct": p, "change": w["target_change_pct"], "low": w["ci90_pct"][0], "high": w["ci90_pct"][1]})
    return {"feature": feature, "points": pts}
