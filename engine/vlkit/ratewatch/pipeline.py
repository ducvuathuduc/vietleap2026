"""Run RateWatch ingestion, gold transformation or publication."""
import argparse
from datetime import datetime
import json
from pathlib import Path

import httpx

from .sources import ingest_sources
from .sources.fiin import fiin_provider
from .sources.http import PublicHttp, USER_AGENT
from .sources.macro import cpi_provider, daily_provider, monthly_provider, parse_fx, parse_interbank, parse_omo
from .warehouse import TZ, _bank_register, transform

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LAKE = ROOT / "data/lake/ratewatch"
DEFAULT_OUTPUT = ROOT / "out/ratewatch"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["all", "ingest", "transform", "publish"], default="all")
    parser.add_argument("--non-rate-only", action="store_true")
    parser.add_argument("--lake", type=Path, default=DEFAULT_LAKE)
    parser.add_argument("--rates-lake", type=Path, help="Read posted-rate silver from this existing lake")
    parser.add_argument("--banks", type=Path, default=ROOT / "scenarios/ratewatch/banks.yaml")
    parser.add_argument("--credentials", type=Path, default=ROOT / ".env.local")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--snapshot", type=Path, default=ROOT / "web/seed/ratewatch/snapshot.json")
    parser.add_argument("--geo", type=Path, help="Published province data from the geography pipeline")
    parser.add_argument("--fixture", type=Path, help="Fixture directory containing rates.csv and banks.yaml")
    parser.add_argument("--as-of", type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    now = args.as_of or datetime.now(TZ)
    if now.utcoffset() is None:
        parser.error("--as-of must include a timezone")
    now = now.astimezone(TZ)
    run_id = now.strftime("rw-%Y%m%dT%H%M")
    rates_lake = args.rates_lake or args.lake
    bank_path = args.fixture / "banks.yaml" if args.fixture else args.banks

    ingest_exit = 0
    if args.stage in {"all", "ingest"}:
        if args.fixture:
            parser.error("--fixture supports transform and publish")
        rate_failed = False
        if not args.non_rate_only:
            from .ingest.runner import run_ingest
            rates = run_ingest(run_id, out=args.lake, banks_path=bank_path)
            rate_failed = rates.silver.empty
        tickers = [bank["ticker"] for bank in _bank_register(bank_path) if bank["listed"]]
        cpi_silver = args.lake / "silver/nonrate/cpi.json"
        cpi_rows = json.loads(cpi_silver.read_text(encoding="utf-8")) if cpi_silver.exists() else []
        watermark = max((row["month"] for row in cpi_rows), default=None)
        with httpx.Client(timeout=12, headers={"User-Agent": USER_AGENT}) as session:
            fetch = PublicHttp(session)
            providers = [
                daily_provider(fetch, "interbank", "lãi-suất1", parse_interbank),
                daily_provider(fetch, "omo", "nghiệp-vụ-thị-trường-mở", parse_omo),
                daily_provider(fetch, "central_fx", "tỷ-giá", parse_fx),
                monthly_provider(fetch, "sbv_credit", now.date()),
                monthly_provider(fetch, "sbv_deposit", now.date()),
                cpi_provider(fetch, watermark),
                fiin_provider(args.credentials, tickers, now.date()),
            ]
            log = ingest_sources(args.lake, run_id, providers)
        print(json.dumps(log, ensure_ascii=False))
        if rate_failed:
            return 1
        if log["errors"]:
            ingest_exit = 2 if log["records"] or not args.non_rate_only else 1
        if args.stage == "ingest":
            return ingest_exit

    db = args.out / "ratewatch.duckdb"
    if args.stage in {"all", "transform"}:
        if args.fixture:
            rate_files = [args.fixture / "rates.csv"]
            sources = list((args.fixture / "nonrate").glob("*.json"))
        else:
            rate_files = sorted(
                parquet if (parquet := folder / "rates.parquet").is_file() else folder / "rates.csv"
                for folder in (rates_lake / "silver").glob("rw-*")
                if (folder / "rates.parquet").is_file() or (folder / "rates.csv").is_file()
            )
            sources = list((args.lake / "silver/nonrate").glob("*.json"))
        transform(db, rate_files, bank_path, sources)
    if args.stage in {"all", "publish"}:
        from .snapshot import publish
        logs = sorted((args.lake / "run_log").glob("*-nonrate.json"))
        latest_log = json.loads(logs[-1].read_text(encoding="utf-8")) if logs and not args.fixture else None
        geo = json.loads(args.geo.read_text(encoding="utf-8")) if args.geo else None
        publish(db, args.snapshot, args.out, now=now, source_log=latest_log, geo=geo)
    return ingest_exit


if __name__ == "__main__":
    raise SystemExit(main())
