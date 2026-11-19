"""Extract FiinQuant market data to the raw landing area."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from collections import defaultdict, deque
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from importlib.metadata import version
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd

if __package__:
    from .landing import KEYS, date_range, land, landing_lock, prior_frame, starts_by_ticker
else:
    from landing import KEYS, date_range, land, landing_lock, prior_frame, starts_by_ticker

ROOT = Path(__file__).absolute().parents[2]
DEFAULT_OUT = ROOT / "data" / "lake" / "bronze" / "fiinquant"
DATASET = "fiinquant"
TABLE = "fiinquant__trading_daily"

LANDING = ROOT / "data" / "raw" / "fiinquant"
INDEXES = ["VNINDEX", "VN30", "HNXIndex", "UpcomIndex"]
INDEX_TICKERS = INDEXES[:2]
WATCHLIST = ["HPG", "VCB", "VIC", "FPT", "MSN", "VNM"]  # steel, bank, real estate, tech, consumer, staples
FIELDS = ["open", "high", "low", "close", "volume", "value", "bu", "sd", "fb", "fs", "fn"]
DEFAULT_FROM_DATE = "2024-01-01"
MOCK_SEED = 42
MOCK_MAX_DAYS = 500
MOCK_DATE = "2026-11-19"

log = logging.getLogger("fetch_fiinquant")


def now_iso() -> str:
    """Current time in Asia/Saigon (falls back to fixed UTC+7)."""
    try:
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat()
    except ZoneInfoNotFoundError:
        return datetime.now(timezone(timedelta(hours=7))).isoformat()


def _row_hash(ticker: str, ts: str, close) -> str:
    return hashlib.sha1(f"{ticker}|{ts}|{close}".encode()).hexdigest()[:16]


def normalize_frame(df: pd.DataFrame, run_id: str, fetched_at: str, mock: bool) -> pd.DataFrame:
    """Standardise a raw Fetch_Trading_Data frame: parse timestamps, sort, de-dupe, add metadata."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["ticker", "timestamp"]).drop_duplicates(subset=["ticker", "timestamp"], keep="last")
    df["_src"] = DATASET
    df["_ingested_at"] = fetched_at
    df["_run_id"] = run_id
    df["_mock"] = bool(mock)
    df["_row_hash"] = [_row_hash(str(t), str(ts), c) for t, ts, c in
                       zip(df["ticker"], df["timestamp"], df["close"])]
    cols = ["ticker", "timestamp", "open", "high", "low", "close", "volume", "value",
            "bu", "sd", "fb", "fs", "fn", "_src", "_ingested_at", "_run_id", "_mock", "_row_hash"]
    return df[[c for c in cols if c in df.columns]]


def build_mock_frame(tickers: list[str], from_date: str) -> pd.DataFrame:
    """Deterministic realistic daily OHLCV sample (seeded RNG) — no credentials, no wheel."""
    import numpy as np

    rng = np.random.default_rng(MOCK_SEED)
    # index points vs stock prices (VND)
    base = {"VNINDEX": 1300.0, "VN30": 1400.0, "HPG": 26_000.0, "VCB": 90_000.0,
            "VIC": 45_000.0, "FPT": 130_000.0, "MSN": 75_000.0, "VNM": 65_000.0}
    days = pd.bdate_range(start=from_date, end=MOCK_DATE)[-MOCK_MAX_DAYS:]
    rows: list[dict] = []
    for tk in tickers:
        price = base.get(tk, 50_000.0)
        rets = rng.normal(0.0005, 0.015, size=len(days))
        closes = price * np.exp(np.cumsum(rets))
        for d, close in zip(days, closes):
            o = close * (1 + rng.normal(0, 0.004))
            h = max(o, close) * (1 + abs(rng.normal(0, 0.003)))
            low = min(o, close) * (1 - abs(rng.normal(0, 0.003)))
            vol = int(rng.lognormal(15.0 if tk in ("VNINDEX", "VN30") else 13.5, 0.6))
            val = int(close * vol)
            bu = int(vol * rng.uniform(0.35, 0.6))
            sd = vol - bu
            fb = int(val * rng.uniform(0.05, 0.25))
            fs = int(val * rng.uniform(0.05, 0.25))
            rows.append({"ticker": tk, "timestamp": d.strftime("%Y-%m-%d"),
                         "open": round(float(o), 2), "high": round(float(h), 2),
                         "low": round(float(low), 2), "close": round(float(close), 2),
                         "volume": vol, "value": val, "bu": bu, "sd": sd,
                         "fb": fb, "fs": fs, "fn": fb - fs})
    return pd.DataFrame(rows, columns=["ticker", "timestamp", *FIELDS])


def _require_credentials() -> tuple[str, str]:
    user = os.environ.get("FIINQUANT_USERNAME", "").strip()
    pw = os.environ.get("FIINQUANT_PASSWORD", "")
    if not user or not pw:
        raise RuntimeError(
            "real mode needs FIINQUANT_USERNAME and FIINQUANT_PASSWORD in the environment "
            "(see tools/fiinquant/README.md). Use --mock for a credential-free sample run.")
    return user, pw


def write_bronze(df: pd.DataFrame, out_dir: Path, run_id: str, fetched_at: str,
                 mock: bool, tickers: list[str], from_date: str) -> tuple[Path, Path]:
    """Write bronze parquet + run-metadata sidecar (replace mode = idempotent re-runs)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pq = out_dir / f"{TABLE}.parquet"
    df.to_parquet(pq, index=False, compression="snappy")
    meta = {"dataset": DATASET, "table": TABLE, "run_id": run_id, "fetched_at": fetched_at,
            "mode": "mock" if mock else "real", "source": "FiinQuantX Fetch_Trading_Data (by=1d, adjusted=True)",
            "tickers": tickers, "from_date": from_date, "rows": int(len(df)),
            "sha256": hashlib.sha256(pq.read_bytes()).hexdigest(),
            "columns": list(df.columns)}
    sidecar = out_dir / f"{TABLE}.run.json"
    sidecar.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return pq, sidecar


EXCHANGES = dict(zip(["HOSE", "HNX", "UPCOM"], ["VNINDEX", "HNXIndex", "UpcomIndex"]))
HISTORY_START = "2021-11-19"
INDEX_START = "2016-11-19"
RATIOS_START = "2015-01-01"
ROSTER_FIELDS = (
    "taxCode organizationName organizationShortName exchangeCode sector "
    "icbNameL5 icbNameL4 icbNameL3 icbNameL2 icbNameL1"
).split()
FOREIGN_FIELDS = (
    "foreignBuyVolumeTotal foreignSellVolumeTotal foreignBuyValueTotal foreignSellValueTotal "
    "foreignNetVolumeTotal foreignNetValueTotal foreignBuyVolumeMatched foreignSellVolumeMatched "
    "foreignBuyValueMatched foreignSellValueMatched foreignBuyVolumeDeal foreignSellVolumeDeal "
    "foreignBuyValueDeal foreignSellValueDeal foreignCurrentRoom foreignTotalRoom "
    "percentForeignTotalRoom foreignOwned percentForeignOwned"
).split()
INVESTOR_FIELDS = [
    f"{group}NetMatch{measure}"
    for measure in ("Volume", "Value")
    for group in ("localIndividual", "foreignIndividual", "localInstitutional", "foreignInstitutional")
] + ["proprietaryNetTotalMatchVolume", "proprietaryNetTotalMatchValue"]
RATIO_FIELDS = [
    "ratios.AssetQualityComponent.ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans",
    "ratios.AssetQualityComponent.LoanLossReservesToNPLs",
    "ratios.LiquidityAndAssetsComponent.LDRPercentage",
    "ratios.ProfitabilityComponent.NIM",
    "ratios.GrowthComponent.AverageLoansGrowthPercentageYoY",
    "ratios.GrowthComponent.AverageDepositGrowthPercentageYoY",
    "ratios.GrowthComponent.InterestincomeGrowthPercentageYoY",
    "ratios.ValuationRatios.BookValuePerShare",
    "ratios.ValuationRatios.BasicEPS",
    "ratios.ValuationRatios.PriceToBook",
    "ratios.ValuationRatios.PriceToEarning",
    "ratios.NetInterestIncome",
    "ratios.AttributeToParentCompany",
]
BREADTH_FIELDS = (
    "totalStockUpPrice totalStockDownPrice totalStockNoChangePrice "
    "totalStockUnderFloor totalStockOverCeiling"
).split()
WEIGHT_FIELDS = [
    "close", "FreeFloat", "OutstandingShare", "FreeFloatRate", "MarketCapFLimit",
    "TotalCapitalization", "Stock Ratio", "Shares to Buy", "Stock Value to Buy",
]
# MarketDepth 0.1.73 takes these ICB names with underscores and adds the level suffix.
ICB_L2 = (
    "OIL_AND_GAS CHEMICALS BASIC_RESOURCES CONSTRUCTION_AND_MATERIALS "
    "INDUSTRIAL_GOODS_AND_SERVICES AUTOMOBILES_AND_PARTS FOOD_AND_BEVERAGE "
    "PERSONAL_AND_HOUSEHOLD_GOODS HEALTH_CARE RETAIL MEDIA TRAVEL_AND_LEISURE "
    "TELECOMMUNICATIONS UTILITIES BANKS INSURANCE REAL_ESTATE FINANCIAL_SERVICES TECHNOLOGY"
).split()
CONTRIBUTION_TYPES = ("topGainers", "topLosers")


class ExtractionError(RuntimeError):
    """A sanitized message suitable for the run log."""


class AuthError(BaseException):
    """Stop SDK retry loops that catch ordinary Exceptions."""


class HttpPolicy:
    def __init__(self, clock=time.monotonic, sleep=time.sleep, async_sleep=asyncio.sleep):
        self.clock = clock
        self.sleep = sleep
        self.async_sleep = async_sleep
        self.lock = Lock()
        self.recent = deque()
        self.calls = 0
        self.pause_until = 0.0
        self.auth_status = None

    def claim(self):
        with self.lock:
            if self.auth_status:
                raise AuthError(f"HTTP {self.auth_status}")
            now = self.clock()
            while self.recent and now >= self.recent[0] + 1:
                self.recent.popleft()
            next_slot = self.recent[0] + 1 if len(self.recent) == 10 else now
            wait = max(next_slot, self.pause_until) - now
            if wait <= 0:
                self.recent.append(now)
                self.calls += 1
            return wait

    def retry(self, status, headers, attempt):
        if status in (401, 403):
            with self.lock:
                self.auth_status = status
            raise AuthError(f"HTTP {status}")
        if status != 429 and not 500 <= status < 600 and status != 0:
            return False
        wait = float(2 ** attempt)
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                seconds = float(retry_after)
            except ValueError:
                try:
                    seconds = parsedate_to_datetime(retry_after).timestamp() - time.time()
                except (ValueError, TypeError, OverflowError):
                    seconds = 0
            wait = max(wait, seconds)
        with self.lock:
            self.pause_until = max(self.pause_until, self.clock() + wait)
        if attempt == 2:
            raise ExtractionError(f"HTTP {status}" if status else "HTTP connection failed")
        return True

    def send(self, operation, network_errors=()):
        for attempt in range(3):
            while (wait := self.claim()) > 0:
                self.sleep(wait)
            try:
                response = operation()
            except network_errors:
                self.retry(0, {}, attempt)
                continue
            status = getattr(response, "status_code", getattr(response, "status", 0))
            if not self.retry(status, response.headers, attempt):
                return response
            if hasattr(response, "close"):
                response.close()

    async def request(self, operation, network_errors=(), response_error=()):
        for attempt in range(3):
            while (wait := self.claim()) > 0:
                await self.async_sleep(wait)
            try:
                response = await operation()
            except response_error as exc:
                if not self.retry(exc.status, exc.headers or {}, attempt):
                    raise
                continue
            except network_errors:
                self.retry(0, {}, attempt)
                continue
            if not self.retry(response.status, response.headers, attempt):
                return response
            if hasattr(response, "release"):
                response.release()

    @contextmanager
    def install(self):
        """Wrap the REST transports used by the pinned SDK for this CLI invocation."""
        import aiohttp
        import requests

        send = requests.Session.send
        request = aiohttp.ClientSession._request

        def send_limited(session, prepared, **kwargs):
            if kwargs.get("timeout") is None:
                kwargs["timeout"] = (8, 30)
            return self.send(lambda: send(session, prepared, **kwargs),
                             (requests.ConnectionError, requests.Timeout))

        async def request_limited(session, method, url, **kwargs):
            kwargs.setdefault("timeout", aiohttp.ClientTimeout(total=40))
            kwargs["allow_redirects"] = False
            session._retry_connection = False
            return await self.request(
                lambda: request(session, method, url, **kwargs),
                (aiohttp.ClientConnectionError, asyncio.TimeoutError), aiohttp.ClientResponseError,
            )

        requests.Session.send = send_limited
        aiohttp.ClientSession._request = request_limited
        try:
            yield
        finally:
            requests.Session.send = send
            aiohttp.ClientSession._request = request


@contextmanager
def quiet_sdk():
    """SDK diagnostics can include request data, so only emit our own messages."""
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with redirect_stdout(sink), redirect_stderr(sink):
                yield
    finally:
        logging.disable(previous)


def frame_of(value):
    if hasattr(value, "get_data"):
        value = value.get_data()
    if isinstance(value, pd.DataFrame):
        frame = value
    elif isinstance(value, dict):
        frame = pd.json_normalize(value)
    else:
        frame = pd.json_normalize(list(value)) if value is not None else pd.DataFrame()
    if not isinstance(frame.index, pd.RangeIndex) and any(frame.index.names):
        frame = frame.reset_index()
    # The probe flattens nested mappings for inspection. Keep every leaf value.
    nested = [column for column in frame if frame[column].map(lambda item: isinstance(item, dict)).any()]
    for column in nested:
        values = [item if isinstance(item, dict) else {} for item in frame[column]]
        expanded = pd.json_normalize(values).add_prefix(f"{column}.")
        expanded.index = frame.index
        frame = pd.concat([frame.drop(columns=column), expanded], axis=1)
    return frame


def filter_roster(frame, expected, report):
    venue_keys = list(zip(frame["ticker"], frame["exchangeCode"].str.upper()))
    report["dropped_tickers"] = sorted({ticker for ticker, venue in venue_keys if (ticker, venue) not in expected})
    report["missing_tickers"] = sorted({ticker for ticker, _ in expected.difference(venue_keys)})
    return frame.loc[[key in expected for key in venue_keys]]


def breadth_frame(breadth, contribution):
    daily = breadth.assign(ticker=breadth["comGroupCode"], index_code=breadth["comGroupCode"], kind="breadth")
    vnindex_days = breadth.loc[breadth["comGroupCode"] == "VNINDEX", "tradingDate"].dropna()
    if vnindex_days.empty:
        raise ExtractionError("VNINDEX breadth trading date missing")
    trading_day = vnindex_days.max()
    return pd.concat([daily, *(frame.assign(tradingDate=trading_day, index_code="VNINDEX", kind=kind)
                              for kind, frame in contribution.items())], ignore_index=True)


def batches(tickers, size):
    for offset in range(0, len(tickers), size):
        yield tickers[offset:offset + size]


class Extractor:
    def __init__(self, client, today, since, universe):
        self.client = client
        self.today = today
        self.since = since
        self.universe = universe
        self.group_members = {}

    def members(self, group):
        if group not in self.group_members:
            with quiet_sdk():
                values = list(self.client.TickerList(ticker=group))
            if not values:
                raise ExtractionError(f"empty ticker list for {group}")
            self.group_members[group] = sorted(set(values))
        return self.group_members[group]

    def stocks(self, default):
        group = self.universe or default
        if group == "all":
            return sorted({ticker for index in EXCHANGES.values() for ticker in self.members(index)})
        if group == "banks":
            return self.members("BANKS_L2")
        if group == "vn30":
            return self.members("VN30")
        if group == "banks+vn30":
            return sorted(set(self.members("BANKS_L2")) | set(self.members("VN30")))
        return sorted(set(group.upper().replace(",", " ").split()))

    def get(self, call):
        with quiet_sdk():
            return frame_of(call())

    def daily(self, function, tickers, previous, since, size, gaps, label, aliases=None):
        # Vendor sector input names differ from the codes returned in ticker.
        aliases = aliases or {}
        keys = {ticker: aliases.get(ticker, ticker) for ticker in tickers}
        starts = starts_by_ticker(previous, keys.values(), since)
        groups = defaultdict(list)
        for ticker, key in keys.items():
            groups[starts[key]].append(ticker)
        frames = []
        processed = 0
        for start, group in sorted(groups.items()):
            for batch in batches(group, size):
                data = self.get(lambda: function(tickers=batch, from_date=start, to_date=self.today))
                if not data.empty:
                    frames.append(data)
                processed += len(batch)
                if len(tickers) > size:
                    print(f"{label}: {processed}/{len(tickers)} requested", flush=True)
        frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        observed = {value.upper() for value in frame["ticker"]} if not frame.empty else set()
        gaps[f"{label}_missing"] = sorted(ticker for ticker, key in keys.items()
                                           if key.upper() not in observed)
        return frame

    def extract(self, dataset, previous, report):
        client = self.client
        stock_since = self.since or HISTORY_START
        if dataset == "roster":
            pairs = {(ticker, venue) for venue, index in EXCHANGES.items() for ticker in self.members(index)}
            stocks = sorted({ticker for ticker, _ in pairs})
            if self.universe:
                stocks = sorted(set(stocks) & set(self.stocks("all")))
                pairs = {pair for pair in pairs if pair[0] in stocks}
            frames = [self.get(lambda: client.BasicInfor(tickers=batch).get()) for batch in batches(stocks, 100)]
            raw = filter_roster(pd.concat(frames, ignore_index=True), pairs, report)
            return raw.assign(snapshot_date=self.today)

        if dataset == "bars":
            def fetch(**kwargs):
                return client.Fetch_Trading_Data(realtime=False, fields=FIELDS, adjusted=True, by="1d", **kwargs)

            default = self.stocks("all")
            requested_indexes = [ticker for ticker in INDEXES if self.universe in (None, "all")
                                 or ticker.upper() in default]
            stocks = [ticker for ticker in default if ticker not in {index.upper() for index in INDEXES}]
            stock_bars = self.daily(fetch, stocks, previous, stock_since, 40, report, "bars_stock")
            index_bars = self.daily(fetch, requested_indexes, previous, self.since or INDEX_START,
                                    4, report, "bars_index")
            return pd.concat([stock_bars, index_bars], ignore_index=True)

        if dataset == "foreign":
            return self.daily(lambda **kw: client.PriceStatistics().get_foreign(time_filter="Daily", **kw),
                              self.stocks("banks+vn30"), previous, stock_since, 20, report, "foreign")

        if dataset == "valuation":
            aliases = {name: f"{name}_L2" for name in ICB_L2}
            frames = []
            for scope, tickers, options in (
                ("stock", self.stocks("banks+vn30"), {}),
                ("sector", ICB_L2, {"level": 2}),
                ("index", INDEXES, {}),
            ):
                subset = previous.loc[previous["scope"] == scope] if not previous.empty else previous
                method = f"get_{scope}_valuation"

                def fetch(**kwargs):
                    return getattr(client.MarketDepth(), method)(**kwargs, **options)

                label = f"valuation_{scope}"
                raw = self.daily(fetch, tickers, subset, stock_since, 20, report, label,
                                 aliases if scope == "sector" else None)
                if not raw.empty:
                    frames.append(raw.assign(scope=scope))
            return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

        if dataset == "bank_ratios":
            stocks = sorted(set(self.members("BANKS_L2")) & set(self.stocks("banks")))
            since = date.fromisoformat(self.since or RATIOS_START)
            today = date.fromisoformat(self.today)
            latest = today.year * 4 + (today.month - 1) // 3
            first = since.year * 4 + (since.month - 1) // 3
            starts = dict.fromkeys(stocks, first)
            if not previous.empty:
                for ticker, past in previous.groupby("ticker"):
                    quarters = sorted(set(past["year"] * 4 + past["quarter"] - 1))
                    if ticker in starts and len(quarters) >= 5:
                        starts[ticker] = max(first, quarters[-5])
            frames = []
            empty_years = []
            for year in range(since.year, today.year + 1):
                groups = defaultdict(list)
                for ticker, start in starts.items():
                    quarters = tuple(q for q in range(1, 5) if start <= year * 4 + q - 1 < latest)
                    if quarters:
                        groups[quarters].append(ticker)
                year_frames = []
                for quarters, tickers in groups.items():
                    raw = self.get(lambda: client.FundamentalAnalysis().get_ratios(
                        tickers=tickers, years=[year], quarters=list(quarters), type="consolidated"))
                    if not raw.empty:
                        year_frames.append(raw)
                if groups and not year_frames:
                    empty_years.append(year)
                frames.extend(year_frames)
                if groups:
                    print(f"bank_ratios: {year} queried", flush=True)
            frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            report["empty_years"] = empty_years
            report["missing_tickers"] = sorted(set(stocks) - set(frame.get("ticker", [])))
            return frame

        if dataset == "breadth":
            breadth = self.get(lambda: client.MarketBreadth().get(tickers=INDEXES))
            if breadth.empty:
                raise ExtractionError("no breadth snapshots returned")
            contributions = {kind: self.get(lambda: client.MoneyFlow().get_contribution(
                ticker="VNINDEX", contribution_day="1Day", type=kind, top=10)) for kind in CONTRIBUTION_TYPES}
            report["empty_contribution"] = [kind for kind, frame in contributions.items() if frame.empty]
            return breadth_frame(breadth, contributions)

        if dataset == "vn30_weights":
            raw = self.get(lambda: client.Rebalance().get(Budget=100000000, Ticker="VN30"))
            if self.universe and not raw.empty:
                raw = raw.loc[raw["ticker"].isin(self.stocks("vn30"))]
            return raw.assign(snapshot_date=self.today)

        recent = (date.fromisoformat(self.today) - timedelta(days=28)).isoformat()
        return self.daily(lambda **kw: client.PriceStatistics().get_value_by_investor(**kw),
                          self.stocks("banks+vn30"), previous, max(recent, self.since or recent),
                          20, report, "investor_flow")


def mock_frame(dataset, universe, since):
    custom = universe and universe not in {"all", "banks", "vn30"}
    banks, vn30 = ["ACB", "VCB"], ["ACB", "HPG"]
    stocks = sorted(set(banks + vn30))
    tickers = sorted(set(universe.upper().replace(",", " ").split())) if custom else {
        "banks": banks, "vn30": vn30,
    }.get(universe, stocks)
    base = {"ticker": tickers, "timestamp": MOCK_DATE}

    def numeric(fields):
        return {field: i + 1 for i, field in enumerate(fields)}

    if dataset == "roster":
        return pd.DataFrame({"ticker": tickers, **dict.fromkeys(ROSTER_FIELDS, "MOCK"),
                             "exchangeCode": "HOSE", "icbNameL2": "BANKS_L2", "snapshot_date": MOCK_DATE})
    if dataset == "bars":
        return build_mock_frame([*tickers, *(INDEXES if universe in (None, "all") else [])],
                                since or HISTORY_START)
    if dataset == "foreign":
        return pd.DataFrame({**base, **numeric(FOREIGN_FIELDS)})
    if dataset == "valuation":
        return pd.concat([
            pd.DataFrame({"ticker": names, "timestamp": MOCK_DATE, "pe": 15.0, "pb": 1.5, "scope": scope})
            for scope, names in (("stock", tickers), ("sector", ["BANKS_L2", "INSURANCE_L2"]), ("index", INDEXES))
        ], ignore_index=True)
    if dataset == "bank_ratios":
        return pd.DataFrame({"ticker": sorted(set(tickers) & set(banks)), "year": 2026, "quarter": 3,
                             **numeric(RATIO_FIELDS)})
    if dataset == "breadth":
        breadth = pd.DataFrame({"comGroupCode": INDEXES, "tradingDate": MOCK_DATE, **numeric(BREADTH_FIELDS)})
        return breadth_frame(breadth, {
            kind: pd.DataFrame({"ticker": ["HPG"], "rank": 1, "contribution": value,
                                "contributionPercent": value / 100})
            for kind, value in zip(CONTRIBUTION_TYPES, (1.5, -1.5))
        })
    if dataset == "vn30_weights":
        return pd.DataFrame({**base, "ticker": sorted(set(tickers) & set(vn30)), "snapshot_date": MOCK_DATE,
                             **numeric(WEIGHT_FIELDS)})
    return pd.DataFrame({**base, **numeric(INVESTOR_FIELDS)})


def login():
    user, password = _require_credentials()
    with quiet_sdk():
        from FiinQuantX import FiinSession

        return FiinSession(username=user, password=password).login()


def legacy_main(args):
    """Retain the original flag-only bronze interface for existing callers."""
    tickers = args.tickers or INDEX_TICKERS + args.watchlist
    since = args.from_date or DEFAULT_FROM_DATE
    try:
        if args.mock:
            raw = build_mock_frame(tickers, since)
        else:
            http = HttpPolicy()
            with http.install():
                client = login()
                raw = Extractor(client, now_iso()[:10], since, None).get(
                    lambda: client.Fetch_Trading_Data(
                        realtime=False, tickers=tickers, fields=FIELDS, adjusted=True, by="1d", from_date=since))
        if raw.empty:
            raise ExtractionError("no bars returned")
        run_id, fetched_at = uuid.uuid4().hex[:8], now_iso()
        frame = normalize_frame(raw, run_id, fetched_at, args.mock)
        write_bronze(frame, Path(args.out or DEFAULT_OUT), run_id, fetched_at, args.mock, tickers, since)
    except (Exception, AuthError) as exc:
        log.error("Legacy bars failed (%s)", type(exc).__name__)
        return 1
    return 0


def collect(args, root, http, record):
    start_calls = http.calls
    sdk_version = "mock" if args.mock else version("fiinquantx")
    extractor = None if args.mock else Extractor(login(), record["started_at"][:10], args.since, args.universe)
    record["login_http_calls"] = http.calls - start_calls
    datasets = [*KEYS] if args.all else [args.dataset]
    if args.all:
        # Land the smaller datasets before the market-wide history.
        datasets.remove("bars")
        datasets.append("bars")
    for dataset in datasets:
        started, start_calls = time.monotonic(), http.calls
        gaps = {}
        params = {"since": args.since, "universe": args.universe, "mock": args.mock}
        print(f"Starting {dataset}", flush=True)
        try:
            previous = prior_frame(root, dataset)
            raw = (mock_frame(dataset, args.universe, args.since) if args.mock
                   else extractor.extract(dataset, previous, gaps))
            if http.auth_status:
                raise AuthError(f"HTTP {http.auth_status}")
            if raw.empty:
                raise ExtractionError("no rows returned")
            if not set(KEYS[dataset]).issubset(raw.columns) or raw[KEYS[dataset]].isna().any().any():
                raise ExtractionError("missing or null business key")
            gaps["duplicates_in_response"] = int(raw.duplicated(KEYS[dataset]).sum())
            params["coverage_gaps"] = gaps
            fetched_at = now_iso()
            coverage = date_range(dataset, raw)
            meta = land(root, dataset, raw, params, record["run_id"], fetched_at, sdk_version,
                        http.calls - start_calls, time.monotonic() - started)
            stats = dict(rows=meta["rows"], fetched_rows=len(raw), tickers=int(raw["ticker"].nunique()),
                         date_range=coverage, http_calls=meta["http_calls"],
                         duration_s=round(time.monotonic() - started, 3), gaps=gaps)
            record["datasets"][dataset] = stats
            record["rows"] += meta["rows"]
            print(f"{dataset}: {stats['rows']:,} rows, {stats['tickers']} tickers, "
                  f"{coverage[0]} to {coverage[1]}, {stats['http_calls']} HTTP, {stats['duration_s']} s", flush=True)
        except (Exception, AuthError) as exc:
            message = str(exc) if isinstance(exc, (ExtractionError, AuthError)) else type(exc).__name__
            record["errors"].append({"dataset": dataset, "error": message, "gaps": gaps,
                                     "http_calls": http.calls - start_calls,
                                     "duration_s": round(time.monotonic() - started, 3)})
            print(f"{dataset}: {message}", file=sys.stderr, flush=True)
            if isinstance(exc, AuthError):
                break


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", nargs="?", choices=KEYS)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--since", type=lambda value: date.fromisoformat(value).isoformat())
    parser.add_argument("--universe", help="all, banks, vn30, or a comma-separated ticker list")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--from-date")
    parser.add_argument("--tickers", nargs="+")
    parser.add_argument("--watchlist", nargs="+", default=WATCHLIST)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    if args.all and args.dataset:
        parser.error("choose a dataset or --all")
    if not args.all and not args.dataset and not args.since and not args.universe:
        return legacy_main(args)
    args.dataset = args.dataset or (None if args.all else "bars")
    if args.universe and not args.universe.strip():
        parser.error("--universe needs a group or ticker list")
    if args.universe and args.universe.lower() in {"all", "banks", "vn30"}:
        args.universe = args.universe.lower()

    root = args.out or (LANDING / "_mock" if args.mock else LANDING)
    record = dict(run_id=uuid.uuid4().hex[:12], started_at=now_iso(), rows=0, errors=[], datasets={})
    started = time.monotonic()
    http = HttpPolicy()
    try:
        with landing_lock(root):
            try:
                if args.mock:
                    collect(args, root, http, record)
                else:
                    with http.install():
                        collect(args, root, http, record)
            except (Exception, AuthError) as exc:
                message = str(exc) if isinstance(exc, (ExtractionError, AuthError)) else type(exc).__name__
                record["errors"].append({"error": message})
                print(f"Run failed: {message}", file=sys.stderr, flush=True)
            finally:
                record.update(duration_s=round(time.monotonic() - started, 3), http_calls=http.calls)
                with (root / "_runs.jsonl").open("a", encoding="utf-8") as runs:
                    runs.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"Landing unavailable: {type(exc).__name__} ({exc.errno})", file=sys.stderr)
        return 1
    return int(bool(record["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
