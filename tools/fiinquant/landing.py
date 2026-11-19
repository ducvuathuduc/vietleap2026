"""Publish and read deduplicated FiinQuant landing snapshots."""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager

import pandas as pd


DAILY_KEY = ["ticker", "timestamp"]
KEYS = {
    "roster": ["ticker", "exchangeCode", "snapshot_date"],
    "bars": DAILY_KEY,
    "foreign": DAILY_KEY,
    "valuation": ["scope", *DAILY_KEY],
    "bank_ratios": ["ticker", "year", "quarter"],
    "breadth": ["index_code", "kind", "ticker", "tradingDate"],
    "vn30_weights": ["ticker", "snapshot_date"],
    "investor_flow": DAILY_KEY,
}


@contextmanager
def landing_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / "_write.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def dataset_files(root, dataset):
    # The JSON sidecar is the write marker. Ignore interrupted, unpaired files.
    paths = (path for path in (root / dataset).glob("*.parquet") if path.with_suffix(".json").is_file())
    return sorted(paths, key=lambda path: json.loads(path.with_suffix(".json").read_text(
        encoding="utf-8"))["fetched_at"])


def prior_frame(root, dataset):
    files = dataset_files(root, dataset)
    return pd.read_parquet(files[-1]) if files else pd.DataFrame()


def land(root, dataset, frame, params, run_id, fetched_at, sdk_version, http_calls, duration_s):
    folder = root / dataset
    folder.mkdir(parents=True, exist_ok=True)
    prior = dataset_files(root, dataset)
    if prior:
        previous = pd.read_parquet(prior[-1])
        if dataset == "breadth":
            previous = previous.loc[~previous["tradingDate"].isin(frame["tradingDate"])]
        if dataset in {"roster", "vn30_weights"} and params.get("universe") in (None, "all"):
            previous = previous.loc[~previous["snapshot_date"].isin(frame["snapshot_date"])]
        frame = pd.concat([previous, frame], ignore_index=True)
    frame = frame.drop_duplicates(KEYS[dataset], keep="last")
    stem = folder / f"{fetched_at[:10]}_{run_id}"
    parquet, sidecar = stem.with_suffix(".parquet"), stem.with_suffix(".json")
    tmp_parquet, tmp_json = stem.with_suffix(".parquet.tmp"), stem.with_suffix(".json.tmp")
    meta = dict(run_id=run_id, dataset=dataset, params=params, rows=len(frame),
                columns=list(frame), fetched_at=fetched_at, sdk_version=sdk_version,
                http_calls=http_calls, duration_s=round(duration_s, 3))
    try:
        frame.to_parquet(tmp_parquet, index=False)
        with tmp_parquet.open("rb") as binary:
            meta["sha256"] = hashlib.file_digest(binary, "sha256").hexdigest()
        tmp_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_parquet.replace(parquet)
        tmp_json.replace(sidecar)
    finally:
        tmp_parquet.unlink(missing_ok=True)
        tmp_json.unlink(missing_ok=True)
    if prior:
        archive = folder / "_history"
        archive.mkdir(exist_ok=True)
        for old in prior:
            old.replace(archive / old.name)
            old.with_suffix(".json").replace(archive / old.with_suffix(".json").name)
    return meta


def starts_by_ticker(previous, tickers, since):
    starts = dict.fromkeys(tickers, since)
    if not previous.empty:
        sessions = previous.loc[previous["ticker"].isin(tickers), DAILY_KEY].copy()
        sessions["timestamp"] = pd.to_datetime(sessions["timestamp"], format="mixed").dt.date
        for ticker, group in sessions.groupby("ticker", sort=False):
            days = sorted(group["timestamp"].dropna().unique())
            if len(days) >= 5:
                starts[ticker] = max(since, days[-5].isoformat())
    return starts


def date_range(dataset, frame):
    if dataset == "bank_ratios":
        periods = frame["year"].astype("str") + "Q" + frame["quarter"].astype("str")
    else:
        column = next(name for name in ("tradingDate", "timestamp", "snapshot_date") if name in frame)
        periods = frame[column].astype("str").str.slice(0, 10)
    return [periods.min(), periods.max()]
