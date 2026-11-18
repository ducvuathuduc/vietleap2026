"""Analysis endpoints: insights, time series, segments, drivers, what-if."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from vlkit import stats
from vlkit import tools as T

from ..schemas import SavedScenario, SaveScenarioBody, WhatIfScenarioResult, WhatIfRequest, WhatIfScenarioRequest
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


@router.get("/geo")
def geo(ds_id: str, metric: str | None = None, agg: str = Query("median", pattern="^(median|mean|sum|count)$"),
        store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    ctx = T.Context(ds.df, ds.results)
    try:
        return T.run_geo(ctx, metric, agg)
    except T.ToolError as e:
        raise HTTPException(422, str(e))


@router.get("/drivers")
def drivers(ds_id: str, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    d = ds.results.get("drivers")
    feats = []
    if ds.whatif:
        feats = [{"name": f["name"], "mean": f["mean"], "sd": f["sd"], "median": f.get("median"),
                  "min": f.get("min"), "max": f.get("max")} for f in ds.whatif["features"] if f["numeric"]]
    return {"drivers": d, "whatif_features": feats, "target": ds.results["meta"]["target"]}


@router.post("/whatif")
def whatif(ds_id: str, req: WhatIfRequest, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    ctx = T.Context(ds.df, ds.results, ds.whatif)
    try:
        return T.what_if(ctx, req.feature, req.pct_change, req.target)
    except T.ToolError as e:
        raise HTTPException(422, str(e))


@router.post("/whatif/scenario", response_model=WhatIfScenarioResult)
def whatif_scenario(ds_id: str, req: WhatIfScenarioRequest, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    ctx = T.Context(ds.df, ds.results, ds.whatif)
    try:
        return T.what_if_multi(ctx, [c.model_dump() for c in req.changes], req.target)
    except T.ToolError as e:
        raise HTTPException(422, str(e))


def _scenarios_path(ds_path: Path) -> Path:
    return ds_path / "scenarios.json"


def _read_scenarios(ds_path: Path) -> list[dict]:
    p = _scenarios_path(ds_path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data[:4] if isinstance(data, list) else []
    except Exception:
        return []


@router.get("/whatif/scenarios", response_model=list[SavedScenario])
def list_whatif_scenarios(ds_id: str, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    return _read_scenarios(ds.path)


@router.post("/whatif/scenarios", response_model=list[SavedScenario])
def save_whatif_scenario(ds_id: str, body: SaveScenarioBody, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    name = body.name.strip()
    if not name or len(name) > 60:
        raise HTTPException(422, "Tên kịch bản phải có 1–60 ký tự.")
    items = _read_scenarios(ds.path)
    if len(items) >= 4 and not any(x.get("name") == name for x in items):
        raise HTTPException(409, "Đã đạt tối đa 4 kịch bản lưu cho deck.")
    ctx = T.Context(ds.df, ds.results, ds.whatif)
    try:
        result = T.what_if_multi(ctx, [c.model_dump() for c in body.request.changes], body.request.target)
    except T.ToolError as e:
        raise HTTPException(422, str(e))
    next_items = [x for x in items if x.get("name") != name] + [
        {"name": name, "request": body.request.model_dump(), "result": result}
    ]
    next_items = next_items[:4]
    _scenarios_path(ds.path).write_text(json.dumps(next_items, ensure_ascii=False, indent=2), encoding="utf-8")
    return next_items


@router.delete("/whatif/scenarios", response_model=list[SavedScenario])
def delete_whatif_scenario(ds_id: str, name: str, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    items = [x for x in _read_scenarios(ds.path) if x.get("name") != name]
    _scenarios_path(ds.path).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return items


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
