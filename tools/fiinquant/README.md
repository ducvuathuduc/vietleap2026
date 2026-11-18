# FiinQuant connector — VN market daily trading data → bronze lake

Fetches daily OHLCV (+ buy/sell, foreign flow) for **VNINDEX, VN30** and a small
watchlist (**HPG, VCB, VIC, FPT, MSN, VNM**) via FiinQuantX `Fetch_Trading_Data`
(`by='1d'`, `adjusted=True`) and lands it as bronze Parquet, following the repo's
connector conventions (retry, logging, raw kept, idempotent replace-mode runs).

## Account

- Username: `thanhhdse184021@fpt.edu.vn` (FiinQuant trial, Professional plan,
  verified active 18/11/2026; **trial expiry 30/11/2026 could NOT be verified in
  the portal UI** — re-check before the contest).
- Credentials come **only** from environment variables. Never hard-code them,
  never commit them (`.env` is git-ignored).

## Install

FiinQuantX is **not on PyPI** — it ships as a wheel from the FiinQuant portal
(and a pip index mirror). Any one of these works:

```bash
# A. from the portal wheel (offline copy kept next to this README)
pip install tools/fiinquant/fiinquantx-0.1.73-py3-none-any.whl

# B. from the FiinQuant pip index
pip install --extra-index-url https://fiinquant.github.io/fiinquantx/simple fiinquantx
```

Then verify the library imports:

```bash
python -c "import FiinQuantX"
```

If the import fails, resolve the missing dependency named in the error before
running a real fetch. Known: wheel 0.1.73 needs `matplotlib` at import time (not
declared as a wheel dependency) — run `pip install matplotlib` if the import fails
with `ModuleNotFoundError: No module named 'matplotlib'`. (Wheel 0.1.73, SHA256
`cc2c106251f601a86727b628756a3a816e12d07015cc7c808c9ab4fe2c5d6aff`.)

## The one fetch command

```bash
FIINQUANT_USERNAME='thanhhdse184021@fpt.edu.vn' FIINQUANT_PASSWORD='...' \
  python tools/fiinquant/fetch_fiinquant.py --from-date 2024-01-01
```

Output:

- `data/lake/bronze/fiinquant/fiinquant__trading_daily.parquet`
  (columns: `ticker, timestamp, open, high, low, close, volume, value, bu, sd,
  fb, fs, fn` + `_src, _ingested_at, _run_id, _mock, _row_hash`)
- `data/lake/bronze/fiinquant/fiinquant__trading_daily.run.json`
  (run metadata: run_id, fetched_at, tickers, rows, sha256)

Re-runs are idempotent (replace mode, de-duplicated on ticker+timestamp).

## Mock mode (no credentials, no wheel)

```bash
python tools/fiinquant/fetch_fiinquant.py --mock
```

Writes a deterministic seeded sample (same tickers, ~500 business days max) to
the same bronze path, with `_mock=true` in the metadata. Use it to test the
downstream pipeline without touching the trial quota.

## Options

```bash
python tools/fiinquant/fetch_fiinquant.py --help
# --from-date YYYY-MM-DD   earliest bar (default 2024-01-01)
# --tickers A B C          override the full ticker list
# --watchlist A B C        override the watchlist (default HPG VCB VIC FPT MSN VNM)
# --out DIR                bronze output dir
```

## Ingest into the warehouse (no code changes needed)

The bronze Parquet is directly consumable by the existing pipeline:

```bash
python de.py file data/lake/bronze/fiinquant/fiinquant__trading_daily.parquet --name fiinquant_trading
```

## Notes / unverified items

- Index tickers `VNINDEX` / `VN30` follow the docs' example style (`UPCOMINDEX`
  is used as a ticker in the official example). If the API rejects one, drop it
  or swap `VN30` for the futures ticker `VN30F1M` and re-run.
- Real fetch is **not yet tested end-to-end** (no credentials available in this
  environment). First real run should be watched once, then re-runs are safe.
- FiinQuantX 0.1.73 ships obfuscated code (upstream packaging choice) — do not
  vendor-edit the wheel; upgrade only from the portal / pip index above.
- Docs: https://docs.fiinquant.vn — login
  (`FiinSession(username, password).login()`), history data
  (`Fetch_Trading_Data`, section 2.2).
