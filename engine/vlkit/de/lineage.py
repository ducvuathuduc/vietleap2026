"""Lineage graph (source → bronze → silver → gold → serving) as JSON for the dashboard and Mermaid for slides."""
from __future__ import annotations

from .warehouse import Warehouse

STAGE = {"source": "Ingestion", "bronze": "Storage", "silver": "Transform", "gold": "Transform", "serving": "Serving"}


def lineage_graph(wh: Warehouse, ds: str) -> dict:
    rows = wh.con.execute("SELECT DISTINCT from_node, to_node, step FROM meta.lineage WHERE dataset=? ORDER BY 1, 2",
                          [ds]).fetchall()
    nodes, edges = {}, []
    for a, b, step in rows:
        for n in (a, b):
            layer = n.split(":", 1)[0] if n.startswith(("source:", "serving:")) else n.split(".", 1)[0]
            nodes[n] = {"id": n, "label": n.split(":", 1)[-1].split(".", 1)[-1], "layer": layer, "stage": STAGE.get(layer, layer)}
        edges.append({"from": a, "to": b, "step": step})
    return {"dataset": ds, "nodes": list(nodes.values()), "edges": edges}


def lineage_mermaid(graph: dict) -> str:
    out = ["flowchart LR"]
    ids = {n["id"]: f"n{i}" for i, n in enumerate(graph["nodes"])}
    for stage in ("Ingestion", "Storage", "Transform", "Serving"):
        members = [n for n in graph["nodes"] if n["stage"] == stage]
        if members:
            out.append(f"  subgraph {stage}")
            out += [f'    {ids[n["id"]]}["{n["label"]}"]' for n in members]
            out.append("  end")
    out += [f'  {ids[e["from"]]} -->|{e["step"]}| {ids[e["to"]]}' for e in graph["edges"]]
    return "\n".join(out)
