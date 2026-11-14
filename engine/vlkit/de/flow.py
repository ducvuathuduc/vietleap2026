"""Orchestrator: Ingestion → Storage (bronze) → Transform (silver + gold models) → Serving (insight engine).

    python de.py run   scenarios/demo_sources.yaml          # many sources from YAML
    python de.py file  data/practice/hanoi_housing_2020.csv # one file, same pipeline

Outputs under out/<dataset>/: pipeline.json (everything the dashboard needs), quality.json, lineage.json,
lineage.mmd, models/*.sql + *.mmd, provenance.json; warehouse tables in data/warehouse.duckdb, Parquet in
data/lake/. With serve=True the existing insight engine (vlkit.pipeline) then runs on the chosen gold OBT.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

from ..vn import ascii_key
from .conformed import build_conformed
from .connectors import ingest
from .lineage import lineage_graph, lineage_mermaid
from .modeling import build_models, erd
from .quality import quality_step
from .sources import Source, now_iso
from .warehouse import KIT, Warehouse, ident


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", ascii_key(s)).strip("_")[:40] or "ds"


def _dump(obj, p: Path):
    from ..pipeline import NpEncoder
    p.write_text(json.dumps(obj, cls=NpEncoder, ensure_ascii=False, indent=1), encoding="utf-8")


def run_flow(dataset: str, sources: list[Source], out_root: str | Path | None = None, wh: Warehouse | None = None,
             impute: str | None = None, primary: str | None = None, serve: bool = False,
             serve_kwargs: dict | None = None, keys: dict | None = None) -> dict:
    ds = slugify(dataset)
    out = Path(out_root or KIT / "out") / ds
    out.mkdir(parents=True, exist_ok=True)
    own = wh is None
    wh = wh or Warehouse()
    run_id, timings, steps = uuid.uuid4().hex[:8], {}, []
    try:
        # ---------------- Ingestion → bronze
        t0, bronze, provenance, conform_of = time.time(), [], [], {}
        for src in sources:
            st = now_iso()
            try:
                res = ingest(src)
            except Exception as e:  # one broken source must not kill the run
                wh.log_run(run_id, ds, f"ingest:{src.name}", "failed", st, {"error": repr(e)})
                steps.append({"step": f"ingest:{src.name}", "status": "failed", "error": repr(e)})
                continue
            provenance.append(res.provenance)
            for name, df in res.frames.items():
                if df is None or df.empty:
                    continue
                tname = f"{ds}__{slugify(name)}"
                wh.write_bronze(ds, tname, df, {**res.provenance, "source": src.name})
                bronze.append(f"bronze.{tname}")
                conform_of[f"silver.{tname}"] = src.conform
            wh.log_run(run_id, ds, f"ingest:{src.name}", "ok", st, {"tables": list(res.frames)})
            steps.append({"step": f"ingest:{src.name}", "status": "ok", "tables": list(res.frames)})
        timings["ingest"] = round(time.time() - t0, 2)
        if not bronze:
            raise RuntimeError("no source produced data")

        # ---------------- Transform 1: quality → silver
        t0, silver, quality, roles_of = time.time(), [], {}, {}
        for b in bronze:
            st = now_iso()
            q = quality_step(wh.read(b), impute=impute)
            name = b.split(".", 1)[1]
            wh.write("silver", name, q["silver"])
            wh.lineage(ds, b, f"silver.{name}", "clean")
            wh.save_quality(ds, f"silver.{name}", q["report"])
            quality[f"silver.{name}"] = q["report"]
            roles_of[f"silver.{name}"] = q["roles"]
            silver.append(f"silver.{name}")
            wh.log_run(run_id, ds, f"clean:{name}", "ok", st, {"score_before": q["report"]["score_before"],
                                                               "score_after": q["report"]["score_after"]})
        timings["clean"] = round(time.time() - t0, 2)

        # ---------------- Transform 2: models on the primary silver table (largest unless told)
        t0 = time.time()
        main = f"silver.{ds}__{slugify(primary)}" if primary else max(silver, key=lambda t: quality[t]["after"]["rows"])
        models = build_models(wh, ds, main, roles_of[main], out_dir=out)
        timings["model"] = round(time.time() - t0, 2)

        # ---------------- Transform 3: conformed dimensions + integrated OBT across sources (≥2 tables sharing a key)
        t0, conformed = time.time(), None
        if len(silver) >= 2:
            st = now_iso()
            try:
                conformed = build_conformed(wh, ds, silver, roles_of, main, keys_spec=keys, conform_of=conform_of)
            except Exception as e:  # integration is an add-on: never lose the single-source models
                wh.log_run(run_id, ds, "conform", "failed", st, {"error": repr(e)})
                steps.append({"step": "conform", "status": "failed", "error": repr(e)})
            if conformed:
                c = conformed["diagnostics"]
                for t in silver:
                    for typ in c["detected"].get(t, {}):
                        if typ in c["dims"]:
                            wh.lineage(ds, t, c["dims"][typ], "conform")
                    if t in c["facts"]:
                        wh.lineage(ds, t, c["facts"][t], "conform")
                for typ, dim in c["dims"].items():
                    for t, f in c["facts"].items():
                        if typ in c["detected"].get(t, {}):
                            wh.lineage(ds, dim, f, "fk")
                for f in c["facts"].values():
                    wh.lineage(ds, f, c["integrated"], "integrate")
                for tname in conformed["tables"]:
                    layer, name = tname.split(".", 1)
                    pq = wh.lake / layer / f"{name}.parquet"
                    pq.parent.mkdir(parents=True, exist_ok=True)
                    wh.con.execute(f"COPY {layer}.{ident(name)} TO '{pq.as_posix()}' (FORMAT parquet)")
                conformed["erd"] = erd(wh, conformed["tables"], strip=f"{ds}__")
                models["models"]["conformed"] = conformed
                (out / "models").mkdir(parents=True, exist_ok=True)
                (out / "models" / "conformed.sql").write_text(";\n\n".join(conformed["sql"]) + ";\n", encoding="utf-8")
                (out / "models" / "conformed.mmd").write_text(conformed["erd"], encoding="utf-8")
                wh.log_run(run_id, ds, "conform", "ok", st, {"shared_keys": c["shared_keys"], "integrated_rows": c["integrated_rows"]})
                steps.append({"step": "conform", "status": "ok", "shared_keys": c["shared_keys"]})
        timings["conform"] = round(time.time() - t0, 2)

        summary = {
            "dataset": ds, "run_id": run_id, "finished_at": now_iso(), "timings": timings, "steps": steps,
            "bronze": bronze, "silver": silver, "primary": main,
            "gold": sorted({t for m in models["models"].values() for t in m["tables"]}),
            "quality": {k: {"score_before": v["score_before"], "score_after": v["score_after"],
                            "rows": v["after"]["rows"], "issues": len(v["before"]["issues"])} for k, v in quality.items()},
            "models": {k: {"tables": m["tables"], "erd": m["erd"]} for k, m in models["models"].items()},
            "column_plan": models["plan"], "rationale": models["rationale"], "recommended": models["recommended"],
            "provenance": provenance,
            "conformed": conformed["diagnostics"] if conformed else None,
        }
        # written before serving so the deck/report built by the insight engine can show pipeline, model,
        # quality and provenance slides; rewritten below with serving timings + final lineage
        out.mkdir(parents=True, exist_ok=True)
        _dump(summary, out / "pipeline.json")
        _dump(quality, out / "quality.json")
        _dump(provenance, out / "provenance.json")
        if conformed:
            _dump(conformed["diagnostics"], out / "conformed.json")
        elif (out / "conformed.json").exists():
            (out / "conformed.json").unlink()

        # ---------------- Serving: insight engine on gold OBT
        served = None
        if serve:
            t0 = time.time()
            from ..pipeline import run as insight_run
            obt = wh.lake / "gold" / f"obt_{ds}.parquet"
            served = insight_run(obt, out_root=out.parent, name=ds, **(serve_kwargs or {}))
            wh.lineage(ds, f"gold.obt_{ds}", "serving:dashboard", "serve")
            wh.lineage(ds, f"gold.obt_{ds}", "serving:insights+deck", "serve")
            timings["serve"] = round(time.time() - t0, 2)
        wh.lineage(ds, f"gold.obt_{ds}", "serving:api+ai_analyst", "serve")

        graph = lineage_graph(wh, ds)
        summary["finished_at"] = now_iso()
        _dump(summary, out / "pipeline.json")
        _dump(quality, out / "quality.json")
        if conformed:
            graph["join_coverage"] = {"joins": conformed["diagnostics"]["joins"], "sources": conformed["diagnostics"]["sources"]}
        _dump(graph, out / "lineage.json")
        (out / "lineage.mmd").write_text(lineage_mermaid(graph), encoding="utf-8")
        _dump(provenance, out / "provenance.json")
        summary["served"] = bool(served)
        return summary
    finally:
        if own:
            wh.close()


def run_file(path: str | Path, dataset: str | None = None, **kw) -> dict:
    p = Path(path)
    return run_flow(dataset or p.stem, [Source(name=p.stem, kind="file", uri=str(p.resolve()))], **kw)
