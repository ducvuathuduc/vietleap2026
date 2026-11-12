#!/usr/bin/env python3
"""VietLeap Insight Kit — one command from raw file to profile, insights, decisions, dashboard and deck.

  python run.py data.csv [--target COL] [--time COL] [--geo COL] [--domain auto|property|public_finance|firm]
                         [--sheet NAME] [--transpose] [--name NAME] [--out out] [--no-reports]
Outputs go to out/<name>/ (results.json, clean.parquet, charts/, deck.pptx, dashboard.html, executive_summary.*).
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "engine"))

from vlkit import pipeline  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--target"); ap.add_argument("--time"); ap.add_argument("--geo")
    ap.add_argument("--domain", default="auto", choices=["auto", "property", "public_finance", "firm", "generic"])
    ap.add_argument("--sheet"); ap.add_argument("--transpose", action="store_true", default=None)
    ap.add_argument("--name"); ap.add_argument("--out", default=str(Path(__file__).parent / "out"))
    ap.add_argument("--no-reports", action="store_true")
    a = ap.parse_args(argv)
    t = time.time()
    res = pipeline.run(a.file, out_root=a.out, target=a.target, time_col=a.time, geo_col=a.geo, domain=a.domain,
                       sheet=a.sheet, transpose=a.transpose, name=a.name, reports=not a.no_reports)
    m = res["meta"]
    print(f"\n✓ {m['name']}: domain={m['domain']} target={m['target']} time={m['time_col']} geo={m['geo_col']} rows={m['rows']:,}")
    print("\nTop insights:")
    for i in res["insights"][:5]:
        print(f"  {i['rank']}. [{i['type']}, score {i['score']:.2f}] {i['sentence_en']}")
    print("\nRecommendations:")
    for r in res["recommendations"]:
        print(f"  • {r['so_what_en']} → {r['now_what_en']}")
    print(f"\nOutputs: {Path(a.out) / m['name']}  ({time.time() - t:.1f}s; {res['timings']})")


if __name__ == "__main__":
    main()
