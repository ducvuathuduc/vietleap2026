"""Vendor calls, retry/backoff policy and bronze landing for the NPL lake."""

from datetime import date
import hashlib
import json
import time
from pathlib import Path

import pandas as pd

from tools.fiinquant.fetch_fiinquant import AuthError, HttpPolicy, frame_of, quiet_sdk

from .files import atomic, now


class IngestError(RuntimeError):
    """A call failed after its retries; the message is safe for the run log."""


class Collector:
    """One authenticated session per run; every vendor call lands in bronze."""

    def __init__(self, credentials, lake, run_id, today=None, sleep=time.sleep, attempts=3):
        self.credentials = Path(credentials)
        self.lake = Path(lake)
        self.run_id = run_id
        self.today = today or date.today()
        self.sleep = sleep
        self.attempts = attempts
        self.policy = HttpPolicy()
        self.client = None
        self.calls = []

    def login(self):
        from dotenv import dotenv_values
        from FiinQuantX import FiinSession

        config = dotenv_values(self.credentials)
        username, password = config.get("FIINQUANT_USERNAME"), config.get("FIINQUANT_PASSWORD")
        if not username or not password:
            raise IngestError("missing FiinQuant credentials")
        with quiet_sdk(), self.policy.install():
            try:
                self.client = FiinSession(username=username, password=password).login()
            except NameError:
                raise AuthError("FiinQuant login rejected") from None
        return self

    def _convert(self, value):
        return value if isinstance(value, pd.DataFrame) else frame_of(value)

    def call(self, dataset, params, operation, doc_url="", want_raw=False):
        """Run one vendor call with retry/backoff, then land the raw frame in bronze."""
        started = time.monotonic()
        for attempt in range(self.attempts):
            try:
                with quiet_sdk(), self.policy.install():
                    raw = operation()
                break
            except AuthError:
                raise
            except Exception as exc:
                if attempt + 1 == self.attempts:
                    raise IngestError(f"{dataset}: {type(exc).__name__}") from None
                self.sleep(2 ** attempt)
        frame = self._convert(raw)
        seconds = round(time.monotonic() - started, 3)
        meta = self.land(dataset, frame, params, raw, doc_url, seconds)
        self.calls.append(meta)
        return (frame, raw) if want_raw else frame

    def land(self, dataset, frame, params, raw, doc_url, seconds):
        folder = self.lake / "bronze" / dataset / self.run_id
        stem = hashlib.sha256(json.dumps([dataset, params], sort_keys=True, default=str).encode()).hexdigest()[:16]
        parquet, sidecar = folder / f"{stem}.parquet", folder / f"{stem}.json"
        folder.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(parquet, index=False)
        raw_bytes = json.dumps(raw, ensure_ascii=False, default=str).encode("utf-8")
        meta = {
            "call": dataset, "vendor": "FiinQuantX", "doc_url": doc_url, "params": params,
            "fetched_at": now().isoformat(timespec="seconds"), "run_id": self.run_id,
            "rows": len(frame), "columns": list(frame.columns), "seconds": seconds,
            "sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(),
            "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(), "http_calls": self.policy.calls,
        }
        atomic(sidecar, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        atomic(folder / f"{stem}.raw.json", raw_bytes)
        return meta
