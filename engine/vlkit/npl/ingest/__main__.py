"""Download the NPL dataset from FiinQuant into data/lake/npl."""

import argparse
from datetime import date
import json
from pathlib import Path

from .eda import build
from .extra_runner import run_extra
from .runner import BANKS, DATASETS, LAKE, ROOT, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="run every dataset (default)")
    parser.add_argument("--datasets", nargs="+", choices=DATASETS)
    parser.add_argument("--lake", type=Path, default=LAKE)
    parser.add_argument("--credentials", type=Path, default=ROOT / ".env.local")
    parser.add_argument("--banks", type=Path, default=BANKS)
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--eda", action="store_true", help="profile silver/bank_quarter after ingest")
    parser.add_argument("--extra", action="store_true", help="run the extra public sources (WDI, SBV, legal, disclosure, TCB)")
    parser.add_argument("--notes", action="store_true", help="read the five notes inputs from the banks' statement PDFs")
    parser.add_argument("--notes-banks", help="comma-separated tickers (default: the 8 large banks)")
    parser.add_argument("--notes-periods", help="YYYYQn:YYYYQn, default 2021Q1 to the latest vendor quarter")
    parser.add_argument("--notes-refresh", action="store_true", help="re-read bank-quarters already in silver")
    parser.add_argument("--no-notes-vision", action="store_true", help="text layer only: never call the vision reader")
    parser.add_argument("--notes-links-only", action="store_true", help="discover and save the statement PDF links only")
    parser.add_argument("--notes-agent", action="store_true", help="use the TinyFish agent on JS-only investor pages")
    parser.add_argument("--out", type=Path, default=ROOT / "out/npl/eda")
    args = parser.parse_args(argv)
    if args.notes:
        from .notes_runner import LARGE, notes_periods, run_notes, tinyfish_agent

        banks = [code.strip().upper() for code in args.notes_banks.split(",")] if args.notes_banks \
            else list(LARGE)
        notes = run_notes(lake=args.lake, banks=banks, periods=notes_periods(args.notes_periods, args.lake),
                          use_vision=not args.no_notes_vision, refresh=args.notes_refresh,
                          links_only=args.notes_links_only, today=args.as_of,
                          agent=tinyfish_agent if args.notes_agent else None)
        print(json.dumps(notes, ensure_ascii=False, indent=2))
        return 0 if notes["datasets"] or notes.get("links", {}).get("rows") else 1
    if args.extra:
        extra = run_extra(lake=args.lake, today=args.as_of)
        print(json.dumps(extra, ensure_ascii=False, indent=2))
        return 0 if extra["datasets"] else 1
    datasets = tuple(args.datasets) if args.datasets and not args.all else DATASETS
    log = run(lake=args.lake, credentials=args.credentials, banks=args.banks,
              today=args.as_of, datasets=datasets)
    print(json.dumps(log, ensure_ascii=False, indent=2))
    if args.eda:
        print(build(args.lake, args.out))
    return 1 if log["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
