"""One run for the extra (non-FiinQuant) NPL sources.

Order: WDI benchmark, SBV system credit/deposits, the legal register, HOSE disclosure dates, the TCB case
study. Each source lands bronze + silver and reports its own errors, so one blocked host does not stop
the others; the run log and the watermarks follow the D1 lake rules.
"""

from datetime import date
import json
from pathlib import Path
import time

from . import extra_disclosure, extra_legal, extra_sbv, extra_tcb, extra_wdi
from .extra_landing import Fetcher, now
from .runner import BANKS, LAKE, banks_from_register
from .watermark import load, save
from .files import atomic

DATASETS = ("wdi", "sbv", "legal", "disclosure", "tcb")
SILVER = {"wdi": "wdi_bank.parquet", "sbv": "sbv_system.parquet", "legal": "legal_register.csv",
          "disclosure": "disclosure_dates.csv", "tcb": "case_tcb.csv"}
BACKSLASH = chr(92)


def tinyfetch_url(url):
    """Free TinyFetch fallback for hosts this machine cannot reach directly (api.worldbank.org blocks it)."""
    from ...de.tinyfish import fetch_text

    body = fetch_text([url]).get(url) or ""
    if not body:
        raise ValueError("TinyFetch returned nothing")
    fence = body.split("```")[1] if body.count("```") >= 2 else body
    head, _, rest = fence.partition("\n")
    if rest and head.strip().lower() in ("json", ""):
        fence = rest
    for char in "_*[]()#`+~>-":  # the markdown pass escapes these, which json.loads rejects
        fence = fence.replace(BACKSLASH + char, char)
    return fence


def run_extra(lake=LAKE, today=None, fetcher=None, run_id=None, datasets=DATASETS, banks=BANKS,
              tinyfetch=tinyfetch_url, sleep=None):
    started = time.monotonic()
    today = today or date.today()
    lake = Path(lake)
    run_id = run_id or "extra-" + now().strftime("%Y%m%dT%H%M%S")
    fetcher = fetcher or Fetcher(lake=lake, run_id=run_id, **({"sleep": sleep} if sleep else {}))
    tickers = banks_from_register(banks)
    log = {"run_id": run_id, "started_at": now().isoformat(timespec="seconds"),
           "datasets": {}, "errors": {}, "tickers": len(tickers)}
    steps = {"wdi": lambda: extra_wdi.run(lake, fetcher, run_id, tinyfetch=tinyfetch),
             "sbv": lambda: extra_sbv.run(lake, fetcher, run_id, today=today.isoformat()),
             "legal": lambda: extra_legal.run(lake, fetcher, run_id, now().isoformat(timespec="seconds")),
             "disclosure": lambda: extra_disclosure.run(lake, fetcher, run_id, tickers),
             "tcb": lambda: extra_tcb.run(lake, fetcher, run_id)}
    for name in datasets:
        try:
            frame, stats = steps[name]()
        except Exception as exc:  # a source failure is a logged outcome, never a crashed run
            log["errors"][name] = f"{type(exc).__name__}: {exc}"[:200]
            continue
        log["datasets"][name] = stats
        if stats.get("errors"):
            log["errors"][name] = stats["errors"]
    state = lake / "state/watermarks.json"
    marks = load(state)
    for name, table in SILVER.items():
        if (lake / "silver" / table).exists():
            marks[f"extra_{name}"] = now().isoformat(timespec="seconds")
    save(state, marks)
    log["watermarks"] = {key: value for key, value in marks.items() if key.startswith("extra_")}
    log["http_calls"] = len(fetcher.calls)
    log["elapsed_s"] = round(time.monotonic() - started, 3)
    atomic(lake / "run_log" / f"{run_id}.json",
           json.dumps(log, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    return log
