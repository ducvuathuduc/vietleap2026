"""Ingest FiinQuant bank ratios and market series into data/lake/npl."""

from datetime import date, timedelta
import json
from pathlib import Path
import time

import pandas as pd
import yaml

from .calendar import report_calendar
from .files import atomic, now, write_parquet
from .fiin import Collector, IngestError
from .flatten import KEY, flatten_ratios
from .silver import KEYS, merge, normalise_foreign, normalise_prices, normalise_valuation
from .watermark import day_start, load, quarter_periods, save, year_periods

ROOT = Path(__file__).resolve().parents[4]
LAKE = ROOT / "data/lake/npl"
BANKS = ROOT / "scenarios/ratewatch/banks.yaml"
FIRST_QUARTER, FIRST_DAY, FIRST_YEAR = "2021Q1", "2011-01-01", 2021
PERMISSION_DAYS = 5475  # SDK: history is limited to 5475 days before today
PRICE_FIELDS = ["open", "high", "low", "close", "volume", "value", "bu", "sd", "fb", "fs", "fn"]
RATIO_DOC = "https://docs.fiinquant.vn/ham-va-cong-thuc/3.-phan-tich-co-ban-and-dinh-gia/3.2.-ham-chi-so-bao-cao-tai-chinh"
MARKET_DOC = "https://docs.fiinquant.vn/fiinquant-en/function-and-formula/historical-data-function"
DATASETS = ("bank_quarter", "bank_annual", "price_daily", "valuation_daily", "foreign_daily",
            "report_calendar")
SILVER = {name: f"silver/{name}.parquet" for name in KEYS}
ALIASES = {"BIDV": "BID"}


def banks_from_register(path):
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return sorted({ALIASES.get(bank["ticker"].upper(), bank["ticker"].upper())
                   for bank in document["banks"] if bank.get("ticker")})


def vendor_banks(ingest):
    from tools.fiinquant.fetch_fiinquant import quiet_sdk

    with quiet_sdk(), ingest.policy.install():
        values = list(ingest.client.TickerList(ticker="BANKS_L2"))
    return {ALIASES.get(str(value).upper(), str(value).upper()) for value in values}


def read_silver(lake, dataset):
    path = Path(lake) / SILVER[dataset]
    return pd.read_parquet(path) if path.exists() else None


def write_silver(lake, dataset, frame):
    write_parquet(Path(lake) / SILVER[dataset], frame)


def allowed_start(today):
    """The SDK refuses history older than 5475 days, so never request beyond it."""
    return (today - timedelta(days=PERMISSION_DAYS)).isoformat()


def chunks(values, size):
    return [values[offset:offset + size] for offset in range(0, len(values), size)]


def _stats(frame, new_rows, started, **extra):
    return {"records": len(frame), "new_records": new_rows,
            "seconds": round(time.monotonic() - started, 3), **extra}


def ingest_ratios(ingest, lake, dataset, tickers, today, marks):
    started = time.monotonic()
    records = []
    if dataset == "bank_quarter":
        latest = f"{today.year}Q{(today.month - 1) // 3 + 1}"
        periods = quarter_periods(FIRST_QUARTER, latest, marks.get(dataset))
        groups = {}
        for period in periods:
            groups.setdefault(int(period[:4]), []).append(int(period[-1]))
        for year, quarters in groups.items():
            params = {"tickers": tickers, "years": [year], "quarters": quarters, "type": "consolidated"}
            records.extend(ingest.call(
                dataset, params,
                lambda year=year, quarters=quarters: ingest.client.FundamentalAnalysis().get_ratios(
                    tickers=tickers, years=[year], quarters=quarters, type="consolidated"),
                RATIO_DOC, want_raw=True)[1])
    else:
        years = year_periods(FIRST_YEAR, today.year - 1, marks.get(dataset))
        for year in years:
            params = {"tickers": tickers, "years": [year], "type": "consolidated"}
            records.extend(ingest.call(
                dataset, params,
                lambda year=year: ingest.client.FundamentalAnalysis().get_ratios(
                    tickers=tickers, years=[year], type="consolidated"),
                RATIO_DOC, want_raw=True)[1])
    flat, field_map = flatten_ratios(records)
    merged = merge(read_silver(lake, dataset), flat, KEYS[dataset])
    write_silver(lake, dataset, merged)
    map_path = Path(lake) / "silver/field_map_ratios.csv"
    old_map = pd.read_csv(map_path) if map_path.exists() else pd.DataFrame(columns=field_map.columns)
    pd.concat([old_map, field_map], ignore_index=True).drop_duplicates("vendor_name", keep="last") \
        .sort_values("vendor_name").to_csv(map_path, index=False)
    marks[dataset] = str(max(merged["period"])) if not merged.empty else FIRST_QUARTER
    stats = _stats(merged, len(flat), started, fields=len(merged.columns) - len(KEY))
    if flat.empty:
        stats["warning"] = "empty vendor response"
    return merged, stats


def ingest_daily(ingest, lake, dataset, tickers, start, today, operation, normalise, marks):
    started, frames, size = time.monotonic(), [], 8 if dataset == "price_daily" else 10
    for chunk in chunks(tickers, size):
        params = {"tickers": chunk, "from_date": start, "to_date": today.isoformat()}
        frames.append(ingest.call(
            dataset, params,
            lambda chunk=chunk: operation(chunk, start, today.isoformat()), MARKET_DOC))
    frame = normalise(pd.concat(frames, ignore_index=True)) if frames else normalise(pd.DataFrame())
    merged = merge(read_silver(lake, dataset), frame, KEYS[dataset])
    write_silver(lake, dataset, merged)
    if not merged.empty:
        marks[dataset] = merged["date"].max()
    stats = _stats(merged, len(frame), started)
    if frame.empty:
        stats["warning"] = "empty vendor response"
    return merged, stats


def ingest_valuation(ingest, lake, tickers, today, marks):
    started, frames = time.monotonic(), []
    first_year = int(str(marks.get("valuation_daily") or FIRST_DAY)[:4])
    for year in year_periods(FIRST_YEAR, today.year, str(first_year)):
        from_date, to_date = f"{year}-01-01", min(f"{year}-12-31", today.isoformat())
        for chunk in chunks(tickers, 10):
            params = {"tickers": chunk, "from_date": from_date, "to_date": to_date, "scope": "stock"}
            frames.append(ingest.call(
                "valuation_daily", params,
                lambda chunk=chunk, from_date=from_date, to_date=to_date: ingest.client.MarketDepth()
                .get_stock_valuation(tickers=chunk, from_date=from_date, to_date=to_date), MARKET_DOC))
        params = {"tickers": ["VNINDEX"], "from_date": from_date, "to_date": to_date, "scope": "index"}
        frames.append(ingest.call(
            "valuation_daily", params,
            lambda from_date=from_date, to_date=to_date: ingest.client.MarketDepth()
            .get_index_valuation(tickers=["VNINDEX"], from_date=from_date, to_date=to_date), MARKET_DOC))
    frame = normalise_valuation(pd.concat(frames, ignore_index=True)) if frames else normalise_valuation(pd.DataFrame())
    merged = merge(read_silver(lake, "valuation_daily"), frame, KEYS["valuation_daily"])
    write_silver(lake, "valuation_daily", merged)
    if not merged.empty:
        marks["valuation_daily"] = merged["date"].max()
    stats = _stats(merged, len(frame), started)
    if frame.empty:
        stats["warning"] = "empty vendor response"
    return merged, stats


def ingest_calendar(lake, today, marks):
    started = time.monotonic()
    frame = report_calendar(today)
    path = Path(lake) / "silver/report_calendar.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    marks["report_calendar"] = frame["quarter"].max()
    return frame, _stats(frame, len(frame), started)


def run(lake=LAKE, credentials=None, banks=BANKS, today=None, datasets=DATASETS, ingest=None):
    started = time.monotonic()
    today = today or date.today()
    lake = Path(lake)
    run_id = "npl-" + now().strftime("%Y%m%dT%H%M%S")
    ingest = ingest or Collector(credentials or ROOT / ".env.local", lake, run_id, today=today)
    if ingest.client is None:
        ingest.login()
    state = lake / "state/watermarks.json"
    marks = load(state)
    tickers = sorted(set(banks_from_register(banks)) | vendor_banks(ingest))
    log = {"run_id": run_id, "started_at": now().isoformat(timespec="seconds"),
           "datasets": {}, "errors": {}, "banks": len(tickers), "tickers": tickers}

    for dataset in datasets:
        try:
            if dataset in ("bank_quarter", "bank_annual"):
                _, stats = ingest_ratios(ingest, lake, dataset, tickers, today, marks)
            elif dataset == "price_daily":
                _, stats = ingest_daily(
                    ingest, lake, dataset, [*tickers, "VNINDEX", "VN30"],
                    max(day_start(FIRST_DAY, marks.get(dataset)), allowed_start(today)), today,
                    lambda t, f, to: ingest.client.Fetch_Trading_Data(
                        tickers=t, from_date=f, to_date=to, realtime=False, adjusted=True, by="1d",
                        fields=PRICE_FIELDS), normalise_prices, marks)
            elif dataset == "valuation_daily":
                _, stats = ingest_valuation(ingest, lake, tickers, today, marks)
            elif dataset == "foreign_daily":
                _, stats = ingest_daily(
                    ingest, lake, dataset, tickers,
                    day_start(f"{FIRST_YEAR}-01-01", marks.get(dataset)), today,
                    lambda t, f, to: ingest.client.PriceStatistics().get_foreign(
                        tickers=t, time_filter="Daily", from_date=f, to_date=to),
                    normalise_foreign, marks)
            else:
                _, stats = ingest_calendar(lake, today, marks)
            log["datasets"][dataset] = stats
        except IngestError as exc:
            log["errors"][dataset] = str(exc)
    log["watermarks"] = marks
    log["http_calls"] = ingest.policy.calls
    log["elapsed_s"] = round(time.monotonic() - started, 3)
    save(state, marks)
    atomic(lake / "run_log" / f"{run_id}.json",
           json.dumps(log, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    return log
