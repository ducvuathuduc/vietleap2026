#!/usr/bin/env python3
"""VietLeap data pipeline CLI — Ingestion → Storage → Transform → Serving.

  python de.py file     <path> [--name DS] [--impute median|interpolate] [--serve] [--mode replace|append|incremental]  one file (csv/xlsx/json/parquet/zip)
  python de.py run      <sources.yaml> [--impute median|interpolate] [--serve]          many sources (file/api/sql/scrape/social/cv/reducto)
  python de.py reducto  <path_or_url> [--name DS] [--mock] [--bronze] [--out PATH]     optional Reducto PDF/scan parse -> JSON / Bronze
                        (file|run) --lang vi|en|both                        deck/pitch language(s) with --serve (default both)
  python de.py tables                                                    list warehouse tables
  python de.py sql      "SELECT ..."                                     read-only query on the warehouse
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "engine"))

from vlkit.i18n import DEFAULT_REPORT_LANG, REPORT_LANGS  # noqa: E402


def _print(s):
    print(f"\n✓ {s['dataset']}  run {s['run_id']}  {s['timings']}")
    ld = s.get("load") or {}
    if ld:
        print(f"  load {ld['mode']}: {ld['inserted']:,} rows inserted, {ld['skipped']:,} skipped (already loaded)"
              + "".join(f"\n    ↻ {t}: {v['reason']}" for t, v in ld["tables"].items() if v.get("rebuilt")))
    for k, q in s["quality"].items():
        print(f"  quality {k}: {q['score_before']} → {q['score_after']}  ({q['rows']:,} rows, {q['issues']} issues found)")
    for k, m in s["models"].items():
        print(f"  {k:<10} {', '.join(m['tables'])}")
    c = s.get("conformed")
    if c:
        print(f"  conformed  keys={','.join(c['shared_keys'])}  → {c['integrated']} ({c['integrated_rows']:,} rows)")
        for j in c["joins"]:
            print(f"    join {j['source']:<28} on {','.join(j['keys']) or '-':<12} {j['status']:<15} "
                  f"{j.get('matched_rows', 0):,} rows matched ({j.get('match_pct', 0)}%)")
    for f in s["steps"]:
        if f["status"] == "skipped":
            print(f"  ↷ {f['step']}: skipped")
        elif f["status"] != "ok":
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


def _reducto(a):
    try:
        from vlkit.de.reducto import parse_document
    except ModuleNotFoundError:
        import importlib.util

        mod_path = Path(__file__).parent / "engine" / "vlkit" / "de" / "reducto.py"
        spec = importlib.util.spec_from_file_location("vlkit_de_reducto", mod_path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        import sys as _sys
        _sys.modules["vlkit_de_reducto"] = mod
        spec.loader.exec_module(mod)
        parse_document = mod.parse_document

    outcome = parse_document(
        a.source,
        mock=a.mock,
        out_json=a.out,
        bronze=a.bronze,
        dataset=a.name,
        mode=a.mode,
    )
    print(outcome.message)
    if outcome.output_json:
        print(f"  json:   {outcome.output_json}")
    if outcome.bronze_table:
        print(f"  bronze: {outcome.bronze_table}")
    if outcome.records:
        print(f"  blocks: {len(outcome.records)}")


def main(argv=None):
    if (argv if argv is not None else sys.argv[1:])[:1] == ["monitor"]:
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("file"); f.add_argument("path"); f.add_argument("--name")
    r = sub.add_parser("run"); r.add_argument("yaml"); r.add_argument("--primary")
    r.add_argument("--offline", action="store_true", help="dùng tệp local hoặc snapshot đã chuẩn bị")
    for p in (f, r):
        p.add_argument("--impute", choices=["median", "interpolate"]); p.add_argument("--serve", action="store_true")
        p.add_argument("--target"); p.add_argument("--out")
        p.add_argument("--mode", choices=["replace", "append", "incremental"], default="replace",
                       help="bronze load: replace (default) | append | incremental (skip rows whose _row_hash exists)")
        p.add_argument("--lang", choices=REPORT_LANGS, default=DEFAULT_REPORT_LANG, help="deck/pitch language(s) with --serve")
    rd = sub.add_parser("reducto", help="optional PDF/scan parse via Reducto API -> JSON / Bronze")
    rd.add_argument("source", help="local document path or public http/https URL")
    rd.add_argument("--name", help="dataset name override")
    rd.add_argument("--mock", action="store_true", help="offline dry-run producing Reducto-shaped JSON without API key")
    rd.add_argument("--bronze", action="store_true", help="write parsed blocks into DuckDB bronze layer")
    rd.add_argument("--out", help="write structured Reducto JSON artifact to this path")
    rd.add_argument("--mode", choices=["replace", "append", "incremental"], default="replace")
    sub.add_parser("tables")
    q = sub.add_parser("sql"); q.add_argument("query"); q.add_argument("--limit", type=int, default=50)
    b = sub.add_parser("brief", help="đề bài (.md/.txt) → brief.json"); b.add_argument("path")
    b.add_argument("--data", help="dataset file to resolve the target column against"); b.add_argument("--out", help="write brief.json here")
    c = sub.add_parser("contest", help="chạy toàn bộ từ đề bài đến báo cáo song ngữ offline")
    c.add_argument("pack", help="tên pack hoặc đường dẫn sources.yaml")
    c.add_argument("brief", type=Path)
    c.add_argument("--out", type=Path)
    c.add_argument("--target")
    c.add_argument("--lang", choices=REPORT_LANGS, default=DEFAULT_REPORT_LANG)
    snapshot = sub.add_parser("snapshot", help="chuẩn bị nguồn của pack để chạy offline")
    snapshot.add_argument("pack", help="tên pack hoặc đường dẫn sources.yaml")
    sync = sub.add_parser("sync", help="đồng bộ bản sao Parquet gold")
    sync.add_argument("--to", choices=["s3"], required=True)
    monitor = sub.add_parser("monitor", help="dựng dữ liệu giám sát vĩ mô và tài chính Việt Nam")
    monitor.add_argument("--offline", action="store_true", help="chỉ đọc dữ liệu nguồn đã lưu")
    a = ap.parse_args(argv)
    if a.cmd == "monitor":
        from vlkit.fmt import count
        from vlkit.monitor.pipeline import run_monitor

        summary = run_monitor(offline=a.offline)
        rows = " · ".join(f"{layer} {count(n, lang='vi')}" for layer, n in summary["rows"].items())
        print(f"Hoàn tất vn_monitor trong {summary['duration_s']:.2f} giây. {rows} dòng.")
        print("Quy tắc kích hoạt " + (", ".join(summary["fired"]) or "chưa có"))
        print("Tệp " + ", ".join(summary["files"]))
        return
    if a.cmd == "reducto":
        _reducto(a)
        return
    from vlkit.de.flow import run_file, run_flow
    from vlkit.de.sources import load_recipe
    from vlkit.de.warehouse import Warehouse
    if a.cmd in ("file", "run"):
        sk = {"lang": a.lang, **({"target": a.target} if a.target else {})}
        if a.cmd == "file":
            s = run_file(a.path, dataset=a.name, impute=a.impute, serve=a.serve, serve_kwargs=sk, out_root=a.out,
                         mode=a.mode)
        else:
            recipe = load_recipe(a.yaml)
            s = run_flow(recipe.dataset, recipe.sources, impute=a.impute, serve=a.serve, primary=a.primary or recipe.primary,
                         serve_kwargs=sk, out_root=a.out, keys=recipe.keys, mode=a.mode, post_sql=recipe.post_sql,
                         analysis_table=recipe.analysis_table, offline=a.offline)
        _print(s)
    elif a.cmd == "brief":
        _brief(a)
    elif a.cmd in ("contest", "snapshot", "sync"):
        try:
            if a.cmd == "contest":
                from vlkit.de.contest import run_contest

                outputs = run_contest(a.pack, a.brief, out_root=a.out, lang=a.lang, target=a.target)
            elif a.cmd == "snapshot":
                from vlkit.de.contest import pack_recipe
                from vlkit.de.snapshots import prepare_snapshot

                outputs = prepare_snapshot(pack_recipe(a.pack))
            else:
                from vlkit.de.mirror import sync_gold

                outputs = sync_gold()
        except (ValueError, OSError, RuntimeError) as error:
            ap.exit(1, f"{error}\n")
        for output in outputs:
            print(output)
    elif a.cmd == "tables":
        wh = Warehouse()
        for t in wh.tables():
            print(f"{t['layer']:<7} {t['name']:<50} {t['rows']:>10,} rows {t['cols']:>4} cols")
    else:
        wh = Warehouse()
        print(wh.sql(a.query, limit=a.limit).to_string())


if __name__ == "__main__":
    main()
