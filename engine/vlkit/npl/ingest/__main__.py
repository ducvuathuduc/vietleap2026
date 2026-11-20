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
    parser.add_argument("--notes-discover", action="store_true", help="probe the Vietstock static PDF naming and save the links")
    parser.add_argument("--notes-separate", action="store_true", help="also probe the separate (cong ty me / rieng) statements")
    parser.add_argument("--notes-workers", type=int, default=1, help="bank-quarters read in parallel (default 1)")
    parser.add_argument("--notes-budget", type=float, default=40.0, help="OpenAI vision budget in USD for this run")
    parser.add_argument("--notes-fragment", type=Path, help="write harvested rows to this JSON instead of silver")
    parser.add_argument("--notes-merge", type=Path, help="merge every fragment JSON in this folder into silver")
    parser.add_argument("--notes-annual", help="comma-separated years to probe the audited annual (NAM) statements")
    parser.add_argument("--out", type=Path, default=ROOT / "out/npl/eda")
    args = parser.parse_args(argv)
    if args.notes and args.notes_merge:
        from .notes_runner import merge_fragment_dir
        from .files import now

        merge = merge_fragment_dir(args.lake, args.notes_merge, "notes-merge-" + now().strftime("%Y%m%dT%H%M%S"))
        print(json.dumps(merge, ensure_ascii=False, indent=2, default=str))
        return 0 if merge["datasets"]["notes_merge"]["fragments"] else 1
    if args.notes:
        from .notes_runner import LARGE, notes_periods, run_notes, tinyfish_agent

        banks = [code.strip().upper() for code in args.notes_banks.split(",")] if args.notes_banks \
            else list(LARGE)
        years = tuple(int(year) for year in args.notes_annual.split(",")) if args.notes_annual else ()
        notes = run_notes(lake=args.lake, banks=banks, periods=notes_periods(args.notes_periods, args.lake),
                          use_vision=not args.no_notes_vision, refresh=args.notes_refresh,
                          links_only=args.notes_links_only, today=args.as_of, discover_only=args.notes_discover,
                          separate=args.notes_separate, annual_years=years, workers=args.notes_workers,
                          budget_usd=args.notes_budget, fragment=args.notes_fragment,
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
