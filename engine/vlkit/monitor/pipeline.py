"""Run the monitor recipes through the shared warehouse and publish serving files."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import pandas as pd

from ..de.lineage import lineage_graph, lineage_mermaid
from ..de.modeling import erd
from ..de.sources import now_iso
from ..de.warehouse import Warehouse, ident
from .ingest import DATASET, OBS_COLUMNS, ingest_sources, literal, read_yaml


ROOT = Path(__file__).absolute().parents[3]
CONTRACT = ROOT / "specs" / "001-vietleap-insight-kit" / "contracts" / "monitor.schema.json"


def analysis_frames(wh):
    market = wh.con.execute("""
        WITH bars AS (
            SELECT date,
                   sum(value) FILTER (WHERE NOT is_index AND NOT is_invalid) / 1e9 AS trading_value,
                   sum(fn) FILTER (WHERE NOT is_index AND NOT is_invalid) / 1e9 AS foreign_net,
                   max(close) FILTER (WHERE upper(ticker)='VNINDEX' AND NOT is_invalid) AS close
            FROM gold.fact_security_daily GROUP BY date
        ), valuation AS (
            SELECT date, pe, pb FROM gold.fact_valuation_daily
            WHERE scope='index' AND upper(ticker)='VNINDEX'
        )
        SELECT b.*, a.advancers, a.decliners, a.unchanged, v.pe, v.pb
        FROM bars b LEFT JOIN gold.fact_market_breadth_daily a USING (date)
        LEFT JOIN valuation v USING (date) ORDER BY date
    """).df()
    foreign = wh.con.execute("""
        SELECT date, icb_l2, sum(fn) / 1e9 AS foreign_net
        FROM gold.fact_security_daily
        WHERE NOT is_index AND NOT is_invalid AND date IS NOT NULL AND fn IS NOT NULL
        GROUP BY date, icb_l2 ORDER BY date, icb_l2
    """).df()
    valuation = wh.con.execute("""
        SELECT ticker, date, scope, pe, pb FROM gold.fact_valuation_daily
        WHERE scope IN ('index','sector') ORDER BY date, scope, ticker
    """).df()
    return {
        "observations": wh.read("gold.fact_indicator"),
        "market": market,
        "foreign": foreign,
        "valuation": valuation,
        "bank": wh.read("gold.fact_bank_ratio_quarter"),
        "geo": wh.read("gold.dim_geo"),
    }


def market_observations(market, run_id):
    frame = market[["date", "close", "pe", "pb"]].dropna(subset=["date"]).rename(
        columns={"date": "period", "close": "vnindex_close", "pe": "vnindex_pe", "pb": "vnindex_pb"})
    frame["period"] = frame["period"].astype(str).str.slice(0, 10)
    data = frame.melt("period", var_name="indicator_id").dropna(subset=["value"])
    prices = data["indicator_id"].eq("vnindex_close")
    data["unit"] = prices.map({True: "điểm", False: "lần"})
    data["measure_type"] = prices.map({True: "index", False: "ratio"})
    data = data.assign(geo="", geo_type="national", source_id="fiinquant", run_id=run_id)
    return data.reindex(columns=OBS_COLUMNS)


def export_views(wh, names):
    def export(name, path):
        schema, view = name.split(".", 1)
        wh.con.execute(f"COPY {ident(schema)}.{ident(view)} TO {literal(path.as_posix())} (HEADER, DELIMITER ',')")

    return {name.split(".", 1)[1]: lambda path, name=name: export(name, path) for name in names}


def run_monitor(*, root=ROOT, output=None, scenario=None, offline=False, deck=False):
    from .model import build_model
    from .rules import evaluate
    from .writer import write_monitor

    root = Path(root)
    output = Path(output or root / "out" / DATASET)
    scenario = Path(scenario or root / "scenarios" / DATASET)
    catalog = read_yaml(scenario / "indicators.yaml")
    sources_meta = read_yaml(scenario / "sources_meta.yaml")
    specs = read_yaml(scenario / "sources.yaml")["sources"]
    run_id, started, timer = uuid.uuid4().hex[:12], now_iso(), time.perf_counter()
    wh = Warehouse(root / "data" / "warehouse.duckdb", root / "data" / "lake")
    try:
        observations, sources, bronze, missing = ingest_sources(
            wh, root, specs, sources_meta, catalog, run_id, offline=offline)
        model = build_model(wh, observations, catalog, sources, run_id)
        model["tables"] = list({table["name"]: table for table in [*model["tables"], *bronze]}.values())
        data = analysis_frames(wh)
        evaluation = evaluate(data, catalog)
        serving = pd.concat([data["observations"], market_observations(data["market"], run_id)], ignore_index=True)
        gold = [record["name"] for record in model["tables"] if record["layer"] == "gold"]
        diagram = erd(wh, gold)
        payload = write_monitor(output, CONTRACT, catalog, sources, serving, evaluation, model,
                                diagram, export_views(wh, model["views"]), deck=deck)
        for view in model["views"]:
            wh.lineage(DATASET, view, "serving:monitor.json", "publish")
        graph = lineage_graph(wh, DATASET)
        (output / "lineage.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        (output / "lineage.mmd").write_text(lineage_mermaid(graph), encoding="utf-8")
        layer_rows = {layer: sum(table["rows"] for table in model["tables"] if table["layer"] == layer)
                      for layer in ("bronze", "silver", "gold")}
        summary = {
            "run_id": run_id, "rows": layer_rows, "fired": [rule["id"] for rule in payload["rules"] if rule["fired"]],
            "missing": missing, "files": sorted(str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()),
            "duration_s": round(time.perf_counter() - timer, 3),
        }
        wh.log_run(run_id, DATASET, "monitor", "ok", started, summary)
        return summary
    except Exception as error:
        wh.log_run(run_id, DATASET, "monitor", "failed", started, {"type": type(error).__name__})
        raise
    finally:
        wh.close()
