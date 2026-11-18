"""Fetch VN market daily trading data via FiinQuantX into the bronze lake.

Real mode (needs the FiinQuantX wheel + a FiinQuant account):
    python tools/fiinquant/fetch_fiinquant.py
    FIINQUANT_USERNAME=... FIINQUANT_PASSWORD=... python tools/fiinquant/fetch_fiinquant.py --from-date 2024-01-01

Mock mode (no credentials, no wheel — writes a realistic deterministic sample):
    python tools/fiinquant/fetch_fiinquant.py --mock

Output (repo-relative, mirrors the bronze naming in data/lake/bronze/):
    data/lake/bronze/fiinquant/fiinquant__trading_daily.parquet
    data/lake/bronze/fiinquant/fiinquant__trading_daily.run.json   (run metadata sidecar)

Conventions followed (see engine/vlkit/de/connectors.py + flow.py):
- credentials ONLY from environment variables (FIINQUANT_USERNAME, FIINQUANT_PASSWORD);
  never hard-coded, never written to files, logs, or the sidecar.
- raw response kept as-is in bronze (only timestamp parsing + metadata columns added);
  re-runs are idempotent (replace mode, de-duplicated on ticker+timestamp).
- retry with backoff on transient failures; fail fast on auth errors.
- Asia/Saigon timestamps throughout.

Docs: https://docs.fiinquant.vn (login: FiinSession; history: Fetch_Trading_Data).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "data" / "lake" / "bronze" / "fiinquant"
DATASET = "fiinquant"
TABLE = "fiinquant__trading_daily"

INDEX_TICKERS = ["VNINDEX", "VN30"]
WATCHLIST = ["HPG", "VCB", "VIC", "FPT", "MSN", "VNM"]  # steel, bank, real estate, tech, consumer, staples
FIELDS = ["open", "high", "low", "close", "volume", "value", "bu", "sd", "fb", "fs", "fn"]
DEFAULT_FROM_DATE = "2024-01-01"
MOCK_SEED = 42
MOCK_MAX_DAYS = 500

log = logging.getLogger("fetch_fiinquant")


def now_iso() -> str:
    """Current time in Asia/Saigon (falls back to fixed UTC+7)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(timespec="seconds")
    except Exception:
        from datetime import timezone, timedelta
        return datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")


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
    days = pd.bdate_range(start=from_date, end=pd.Timestamp.now().normalize())[-MOCK_MAX_DAYS:]
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
    return pd.DataFrame(rows)


def _require_credentials() -> tuple[str, str]:
    user = os.environ.get("FIINQUANT_USERNAME", "").strip()
    pw = os.environ.get("FIINQUANT_PASSWORD", "")
    if not user or not pw:
        raise RuntimeError(
            "real mode needs FIINQUANT_USERNAME and FIINQUANT_PASSWORD in the environment "
            "(see tools/fiinquant/README.md). Use --mock for a credential-free sample run.")
    return user, pw


def fetch_real(username: str, password: str, tickers: list[str], from_date: str) -> pd.DataFrame:
    """Log in and pull daily bars via Fetch_Trading_Data. Retries transient failures (3x, backoff);
    fails fast on auth errors. The password is never logged."""
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            try:
                from FiinQuantX import FiinSession  # lazy: mock mode must work without the wheel
            except ImportError as e:
                raise RuntimeError(
                    "FiinQuantX is not importable in this environment — "
                    "install the wheel first (see tools/fiinquant/README.md).") from e
            log.info("FiinSession login as %s (attempt %d/3)", username, attempt)
            client = FiinSession(username=username, password=password).login()
            log.info("login ok, fetching %d tickers from %s", len(tickers), from_date)
            data = client.Fetch_Trading_Data(
                realtime=False, tickers=tickers, fields=FIELDS,
                adjusted=True, by="1d", from_date=from_date,
            ).get_data()
            return data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        except Exception as e:  # noqa: BLE001 — classify below, never log the password
            msg = str(e)
            if "Incorrect password" in msg or "does not exist" in msg:
                raise RuntimeError("FiinQuant login rejected (bad username/password) — not retrying.") from e
            last_exc = e
            log.warning("fetch attempt %d failed: %s", attempt, msg[:300])
            time.sleep(2 ** attempt)
    raise RuntimeError(f"FiinQuant fetch failed after 3 attempts: {last_exc}") from last_exc


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="write a deterministic sample; no credentials, no wheel")
    ap.add_argument("--from-date", default=DEFAULT_FROM_DATE, help="earliest bar date (default %(default)s)")
    ap.add_argument("--tickers", nargs="+", default=None, help="override ticker list (default: VNINDEX VN30 + watchlist)")
    ap.add_argument("--watchlist", nargs="+", default=WATCHLIST, help="watchlist tickers (default: %(default)s)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="bronze output dir (default: %(default)s)")
    ap.add_argument("--log-level", default="INFO")
    a = ap.parse_args(argv)
    logging.basicConfig(level=getattr(logging, a.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    tickers = a.tickers or (INDEX_TICKERS + a.watchlist)
    run_id, fetched_at = uuid.uuid4().hex[:8], now_iso()
    try:
        if a.mock:
            log.info("mock mode: %d tickers from %s", len(tickers), a.from_date)
            raw = build_mock_frame(tickers, a.from_date)
            mock = True
        else:
            user, pw = _require_credentials()
            raw = fetch_real(user, pw, tickers, a.from_date)
            mock = False
    except Exception as e:  # noqa: BLE001
        log.error("%s", e)
        return 1
    if raw.empty:
        log.error("no rows returned")
        return 1
    df = normalize_frame(raw, run_id, fetched_at, mock)
    pq, sidecar = write_bronze(df, Path(a.out), run_id, fetched_at, mock, tickers, a.from_date)
    log.info("wrote %s (%d rows, %d tickers, run %s)", pq, len(df), df["ticker"].nunique(), run_id)
    log.info("sidecar %s", sidecar)
    print(f"✓ {TABLE}: {len(df):,} rows, {df['ticker'].nunique()} tickers, "
          f"{df['timestamp'].min().date()} → {df['timestamp'].max().date()}  [{pq}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
