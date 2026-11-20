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
    parser.add_argument("--out", type=Path, default=ROOT / "out/npl/eda")
    args = parser.parse_args(argv)
    if args.extra:
        extra = run_extra(lake=args.lake, today=args.as_of)
        print(json.dumps(extra, ensure_ascii=False, indent=2))
        return 1 if extra["errors"] else 0
    datasets = tuple(args.datasets) if args.datasets and not args.all else DATASETS
    log = run(lake=args.lake, credentials=args.credentials, banks=args.banks,
              today=args.as_of, datasets=datasets)
    print(json.dumps(log, ensure_ascii=False, indent=2))
    if args.eda:
        print(build(args.lake, args.out))
    return 1 if log["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
