"""CLI: ``python -m vlkit.ratewatch.ingest --run-id auto --out data/lake/ratewatch``.

Writes ``bronze/`` (one object + meta per response), ``silver/<run_id>/rates.parquet|.csv`` and
``run_log/<run_id>.json``, then prints the per-bank coverage table. ``--offline DIR`` replays a saved bronze
tree (tests and reruns without network or spend).
"""
from __future__ import annotations

import argparse
import sys

from .banks import DEFAULT_PATH
from .runner import DEFAULT_OUT, run_ingest


def _print_summary(result) -> None:
    log = result.log
    print(f"run {result.run_id}: {log['records']} rows, {log.get('banks_read', 0)} banks, "
          f"{log['seconds']} s, USD {log['usd']:.4f}"
          + ("  [offline replay]" if log.get("offline") else ""))
    print(f"{'bank':8s} {'rows':>4s} {'readers':22s} {'status':16s} {'s':>6s} {'usd':>6s}")
    for code, record in log["banks"].items():
        readers = ",".join(record.get("readers") or []) or "-"
        status = record.get("status") or "-"
        if record.get("unchanged"):
            status += " (unchanged)"
        print(f"{code:8s} {record.get('rows', 0):4d} {readers:22s} {status:16s} "
              f"{record.get('seconds', 0):6.1f} {record.get('usd', 0):6.3f}")
    sources = ", ".join(f"{name}={value.get('status', 'ok')}" for name, value in log["sources"].items())
    print(f"sources: {sources}")
    agent = log.get("agent") or {}
    if agent:
        print(f"tinyfish: {len(agent.get('runs') or [])} runs, USD {agent.get('usd', 0):.4f}, "
              f"stopped={agent.get('stopped')}")
    if log["errors"]:
        print(f"errors ({len(log['errors'])}), first 3:")
        for line in log["errors"][:3]:
            print(f"  - {line}")
    print(f"silver: {result.paths['parquet']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m vlkit.ratewatch.ingest",
                                     description="Read Vietnamese posted deposit rates into bronze + silver.")
    parser.add_argument("--run-id", default="auto", help="rw-YYYYMMDDTHHMM (Asia/Saigon) or 'auto'")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="lake root (bronze/, silver/, run_log/)")
    parser.add_argument("--banks", default=str(DEFAULT_PATH), help="bank register YAML")
    parser.add_argument("--offline", default=None, help="replay this bronze tree instead of the network")
    args = parser.parse_args(argv)
    result = run_ingest(args.run_id, out=args.out, banks_path=args.banks, offline=args.offline)
    _print_summary(result)
    return 0 if result.log["records"] else 2


if __name__ == "__main__":
    sys.exit(main())
