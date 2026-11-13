#!/usr/bin/env python3
"""VietLeap data pipeline CLI — Ingestion → Storage → Transform → Serving.

  python de.py file  <path> [--name DS] [--impute median] [--serve]     one file (csv/xlsx/json/parquet/zip)
  python de.py run   <sources.yaml> [--impute median] [--serve]          many sources (file/api/sql/scrape/social/cv)
  python de.py tables                                                    list warehouse tables
  python de.py sql   "SELECT ..."                                        read-only query on the warehouse
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "engine"))

from vlkit.de.flow import run_file, run_flow  # noqa: E402
from vlkit.de.sources import load_sources  # noqa: E402
from vlkit.de.warehouse import Warehouse  # noqa: E402


def _print(s):
    print(f"\n✓ {s['dataset']}  run {s['run_id']}  {s['timings']}")
    for k, q in s["quality"].items():
        print(f"  quality {k}: {q['score_before']} → {q['score_after']}  ({q['rows']:,} rows, {q['issues']} issues found)")
    for k, m in s["models"].items():
        print(f"  {k:<10} {', '.join(m['tables'])}")
    failed = [x for x in s["steps"] if x["status"] != "ok"]
    for f in failed:
        print(f"  ✗ {f['step']}: {f['error']}")


def _brief(a):
    import json

    from vlkit.brief import parse_brief
    from vlkit.de.connectors import ingest
    from vlkit.de.sources import Source
    cols = None
    if a.data:
        frames = ingest(Source("brief_data", "file", str(Path(a.data).resolve()))).frames
        cols = list(next(iter(frames.values())).columns)
    b = parse_brief(Path(a.path).read_text(encoding="utf-8"), columns=cols)
    out = json.dumps(b, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
    t = b["target"] or {}
    print(f"target: {t.get('label')} → {t.get('column')}  ({t.get('resolved')})")
    print(f"pack:   {(b['pack'] or {}).get('id')}   units: {', '.join(b['units'])}   segments: {', '.join(b['segments'])}")
    for line in b["plan"]:
        print(f"  • {line}")
    if not a.out:
        print(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("file"); f.add_argument("path"); f.add_argument("--name")
    r = sub.add_parser("run"); r.add_argument("yaml"); r.add_argument("--primary")
    for p in (f, r):
        p.add_argument("--impute", choices=["median"]); p.add_argument("--serve", action="store_true")
        p.add_argument("--target"); p.add_argument("--out")
    sub.add_parser("tables")
    q = sub.add_parser("sql"); q.add_argument("query"); q.add_argument("--limit", type=int, default=50)
    b = sub.add_parser("brief", help="đề bài (.md/.txt) → brief.json"); b.add_argument("path")
    b.add_argument("--data", help="dataset file to resolve the target column against"); b.add_argument("--out", help="write brief.json here")
    a = ap.parse_args(argv)
    if a.cmd in ("file", "run"):
        sk = {"target": a.target} if a.target else {}
        if a.cmd == "file":
            s = run_file(a.path, dataset=a.name, impute=a.impute, serve=a.serve, serve_kwargs=sk, out_root=a.out)
        else:
            ds, sources, _keys = load_sources(a.yaml)
            s = run_flow(ds, sources, impute=a.impute, serve=a.serve, primary=a.primary, serve_kwargs=sk, out_root=a.out)
        _print(s)
    elif a.cmd == "brief":
        _brief(a)
    elif a.cmd == "tables":
        wh = Warehouse()
        for t in wh.tables():
            print(f"{t['layer']:<7} {t['name']:<50} {t['rows']:>10,} rows {t['cols']:>4} cols")
    else:
        wh = Warehouse()
        print(wh.sql(a.query, limit=a.limit).to_string())


if __name__ == "__main__":
    main()
