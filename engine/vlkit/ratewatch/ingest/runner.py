"""RateWatch ingest: aggregator + bank pages + bank PDFs + TinyFish agents -> bronze, silver, run log.

One run is one ``run_id`` (``rw-YYYYMMDDTHHMM`` Asia/Saigon). Everything a reader returns is written to bronze
first (object + meta), then normalised to silver (CONTRACT A). A bank whose sheet is byte-identical to the
previous run is not parsed again: its silver rows are re-observed (new ``run_id``/``observed_at``) from the last
run, so ``observed_at`` still says when we looked. ``--offline`` replays a saved bronze tree instead of the
network: same code path, no requests, no spend.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from .banks import DEFAULT_PATH, bank_index, load_banks
from .bronze import BronzeObject, BronzeReplay, BronzeStore, now_iso
from .contract import TZ, dedupe_rows, rows_from_frame, silver_frame, write_silver
from .http import FetchError, HttpClient, robots_allowed
from .readers.aggregator import AGGREGATOR_URL, parse_aggregator_html
from .readers.bank_html import find_pdf_links, parse_bank_html
from .readers.bank_pdf import extract_pdf_text, parse_pdf_text
from .readers.tinyfish import AGENT_DEADLINE_S, rows_from_payload, run_agent_queue

KIT = Path(__file__).resolve().parents[4]
DEFAULT_OUT = KIT / "data" / "lake" / "ratewatch"
MAX_USD_ENV = "RATEWATCH_TINYFISH_MAX_USD"
MAX_SECONDS_ENV = "RATEWATCH_MAX_SECONDS"
DEFAULT_MAX_USD = 5.0
DEFAULT_MAX_SECONDS = 2700.0
LICENCE_AGGREGATOR = "public comparison table, reference use (robots.txt allows /)"
LICENCE_PAGE = "public bank page (robots.txt allows /)"
LICENCE_PDF = "public PDF rate sheet (robots.txt allows /)"
LICENCE_AGENT = "TinyFish agent read of the bank's public page"


class RobotsDenied(RuntimeError):
    """robots.txt of the host disallows the URL: the reader must not touch it."""


@dataclass
class RunResult:
    run_id: str
    silver: pd.DataFrame
    log: dict
    paths: dict


def make_run_id(moment: datetime | None = None) -> str:
    return "rw-" + (moment or datetime.now(TZ)).astimezone(TZ).strftime("%Y%m%dT%H%M")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


class _Sheets:
    """Obtain a sheet (live HTTP or offline replay) and land it in bronze."""

    def __init__(self, store: BronzeStore, replay: BronzeReplay | None, http: HttpClient):
        self.store = store
        self.http = http
        self.replay = replay
        self.replay_index: dict[tuple[str, str], BronzeObject] = {}
        if replay is not None:
            self.replay_index = {(obj.source, obj.name): obj for obj in replay.objects()}

    def obtain(self, source: str, name: str, url: str, licence: str) -> tuple[BronzeObject, dict] | None:
        if self.replay is not None:
            saved = self.replay_index.get((source, name))
            if saved is None:
                return None
            meta = self.store.save(source, name, saved.content, url=saved.meta.get("url", url),
                                   status=saved.meta.get("status", 200),
                                   robots_allowed=saved.meta.get("robots_allowed", True),
                                   licence=saved.meta.get("licence", licence), method=source,
                                   usd_cost=float(saved.meta.get("usd_cost") or 0.0))
            return self.store.load(source, name), meta
        if not robots_allowed(url):
            raise RobotsDenied(f"robots.txt disallows {url}")
        response = self.http.get(url)
        meta = self.store.save(source, name, response.content, url=response.url, status=response.status,
                               licence=licence, method=source)
        return self.store.load(source, name), meta


class _PreviousSilver:
    """Rows of the most recent earlier run, used for unchanged sheets."""

    def __init__(self, root: Path, run_id: str):
        self.frame: pd.DataFrame | None = None
        self.run: str | None = None
        if not root.is_dir():
            return
        folders = sorted((p.name for p in root.iterdir() if p.is_dir() and p.name != run_id))
        if not folders:
            return
        self.run = folders[-1]
        path = root / self.run / "rates.parquet"
        self.frame = pd.read_parquet(path) if path.is_file() else None

    def rows(self, bank_code: str, reader: str) -> list[dict] | None:
        if self.frame is None:
            return None
        subset = self.frame[(self.frame.bank_code == bank_code) & (self.frame.reader == reader)]
        return rows_from_frame(subset) if len(subset) else None

    def rows_of_reader(self, reader: str) -> list[dict] | None:
        if self.frame is None:
            return None
        subset = self.frame[self.frame.reader == reader]
        return rows_from_frame(subset) if len(subset) else None


def _reobserve(rows: list[dict], run_id: str, observed_at: str) -> list[dict]:
    return [{**row, "run_id": run_id, "observed_at": observed_at} for row in rows]


def run_ingest(run_id: str = "auto", *, out: str | Path | None = None, banks_path: str | Path | None = None,
               offline: str | Path | None = None, observed_at: str | None = None,
               http: HttpClient | None = None, allow_agents: bool = True, agent_fn=None) -> RunResult:
    started = time.monotonic()
    out = Path(out) if out else DEFAULT_OUT
    banks = load_banks(banks_path or DEFAULT_PATH)
    by_code = bank_index(banks)
    run_id = make_run_id() if str(run_id).lower() in ("", "auto") else str(run_id)
    observed_at = observed_at or now_iso()
    max_usd = _env_float(MAX_USD_ENV, DEFAULT_MAX_USD)
    max_seconds = _env_float(MAX_SECONDS_ENV, DEFAULT_MAX_SECONDS)
    store = BronzeStore(out / "bronze", run_id)
    replay = BronzeReplay(offline) if offline else None
    sheets = _Sheets(store, replay, http or HttpClient())
    previous = _PreviousSilver(out / "silver", run_id)
    rows: list[dict] = []
    log: dict = {"run_id": run_id, "started_at": observed_at, "finished_at": None, "seconds": 0.0,
                 "usd": 0.0, "records": 0, "offline": bool(offline), "max_usd": max_usd,
                 "max_seconds": max_seconds, "sources": {}, "banks": {}, "errors": [], "agent": {}}

    def elapsed() -> float:
        return time.monotonic() - started

    def keep(source: str, name: str, code: str, reader: str, obj: BronzeObject, meta: dict,
             parse) -> None:
        """Parse the sheet, or re-observe the previous rows when the sha256 has not changed."""
        record = log["banks"].setdefault(code, {"status": "ok", "rows": 0, "readers": [], "unchanged": False,
                                                "usd": 0.0})
        record.setdefault("sheets", {})[f"{source}/{name}"] = meta["sha256"]
        unchanged = store.previous_sha(source, name) == meta["sha256"]
        if unchanged:
            reused = previous.rows(code, reader)
            if reused:
                rows.extend(_reobserve(reused, run_id, observed_at))
                record["unchanged"] = True
                return
        rows.extend(parse(obj))

    # ---------------------------------------------------------------- aggregator (breadth)
    try:
        sheet = sheets.obtain("aggregator", "index.html", AGGREGATOR_URL, LICENCE_AGGREGATOR)
        if sheet is None:
            log["sources"]["aggregator"] = {"status": "absent"}
        else:
            obj, meta = sheet
            log["sources"]["aggregator"] = {"url": AGGREGATOR_URL, "sha256": meta["sha256"],
                                            "status": meta.get("status")}
            unchanged = store.previous_sha("aggregator", "index.html") == meta["sha256"]
            previous_rows = previous.rows_of_reader("aggregator")
            if unchanged and previous_rows:
                rows.extend(_reobserve(previous_rows, run_id, observed_at))
            else:
                rows.extend(parse_aggregator_html(obj.text, url=AGGREGATOR_URL, run_id=run_id,
                                                  observed_at=observed_at, raw_sha256=meta["sha256"],
                                                  banks=banks))
            log["sources"]["aggregator"]["unchanged"] = bool(unchanged and previous_rows)
    except RobotsDenied:
        log["sources"]["aggregator"] = {"status": "skipped_robots"}
        log["errors"].append(f"robots.txt disallows {AGGREGATOR_URL}")
    except FetchError as exc:
        log["sources"]["aggregator"] = {"status": "fetch_error", "detail": str(exc)}
        log["errors"].append(str(exc))

    # ---------------------------------------------------------------- per-bank sheets
    for bank in banks:
        code = bank["code"]
        record = log["banks"].setdefault(code, {"status": "ok", "rows": 0, "readers": [], "unchanged": False,
                                                "usd": 0.0})
        record["name_vi"] = bank["name_vi"]
        if elapsed() >= max_seconds:
            log["stopped"] = "time"
            break
        if bank["status"] == "unreadable":
            record["status"] = "unreadable"
            record["reason"] = bank.get("reason", "")
            continue
        bank_started = time.monotonic()
        try:
            page = sheets.obtain("bank_html", f"{code}.html", bank["rate_page"], LICENCE_PAGE)
        except RobotsDenied:
            record["status"] = "skipped_robots"
            log["errors"].append(f"robots.txt disallows {bank['rate_page']}")
            continue
        except FetchError as exc:
            record["status"] = "fetch_error"
            record["detail"] = str(exc)
            log["errors"].append(str(exc))
            continue
        if page is None:
            record["status"] = "absent_offline"
            continue
        obj, meta = page
        html_hint = bank.get("html")
        if html_hint:
            keep("bank_html", f"{code}.html", code, "bank_html", obj, meta,
                 lambda target, hint=html_hint, bank_code=code: parse_bank_html(
                     target.text, bank_code=bank_code, channel=hint["channel"], tier=hint.get("tier", ""),
                     rate_column=int(hint["rate_column"]), run_id=run_id, observed_at=observed_at,
                     source_url=bank["rate_page"], raw_sha256=meta["sha256"]))
        pdf_hint = bank.get("pdf")
        if pdf_hint:
            candidates = list(bank.get("pdf_urls") or []) + find_pdf_links(obj.text, bank["rate_page"])
            for position, url in enumerate(dict.fromkeys(candidates)):
                try:
                    pdf = sheets.obtain("bank_pdf", f"{code}_{position}.pdf", url, LICENCE_PDF)
                except (RobotsDenied, FetchError) as exc:
                    log["errors"].append(f"{code} pdf {url}: {exc}")
                    continue
                if pdf is None:
                    continue
                pdf_obj, pdf_meta = pdf
                keep("bank_pdf", f"{code}_{position}.pdf", code, "bank_pdf", pdf_obj, pdf_meta,
                     lambda target, hint=pdf_hint, bank_code=code, url=url: parse_pdf_text(
                         extract_pdf_text(target.content), bank_code=bank_code, channel=hint["channel"],
                         tier=hint.get("tier", ""), rate_column=int(hint["rate_column"]), run_id=run_id,
                         observed_at=observed_at, source_url=url, raw_sha256=pdf_meta["sha256"],
                         interest_basis=hint.get("interest_basis", "at_maturity")))
        record["seconds"] = round(time.monotonic() - bank_started, 1)

    # ---------------------------------------------------------------- TinyFish (JS-rendered sheets)
    agent_banks = [bank for bank in banks if bank.get("tinyfish")]
    if offline:
        for bank in agent_banks:
            try:
                saved = sheets.obtain("tinyfish", f"{bank['code']}.json", bank["rate_page"], LICENCE_AGENT)
            except (RobotsDenied, FetchError) as exc:
                log["errors"].append(f"{bank['code']} tinyfish: {exc}")
                continue
            if saved is None:
                continue
            obj, meta = saved
            keep("tinyfish", f"{bank['code']}.json", bank["code"], "tinyfish", obj, meta,
                 lambda target, bank=bank, sha=meta["sha256"]: rows_from_payload(
                     json.loads(target.text), bank_code=bank["code"], source_url=bank["rate_page"],
                     run_id=run_id, observed_at=observed_at, raw_sha256=sha))
    elif allow_agents and agent_banks:
        queued = []
        for bank in agent_banks:
            if not robots_allowed(bank["rate_page"]):
                record = log["banks"].setdefault(bank["code"], {"status": "ok", "rows": 0, "readers": [],
                                                                "unchanged": False, "usd": 0.0})
                record["status"] = "skipped_robots"
                log["errors"].append(f"robots.txt disallows {bank['rate_page']}")
                continue
            queued.append(bank)
        outstanding = max(0.0, max_seconds - elapsed())
        outcomes, agent_log = run_agent_queue(queued, run_fn=agent_fn, max_usd=max_usd,
                                              deadline_s=AGENT_DEADLINE_S, max_seconds=outstanding)
        log["agent"] = agent_log
        log["usd"] = agent_log["usd"]
        for code, outcome in outcomes.items():
            bank = by_code[code]
            records = outcome.get("records") or []
            payload = {"status": outcome.get("status"), "result": records[0] if records else {}}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            meta = store.save("tinyfish", f"{code}.json", data, url=bank["rate_page"],
                              status=200 if outcome.get("status") == "ok" else 0,
                              licence=LICENCE_AGENT, method="tinyfish",
                              usd_cost=float(outcome.get("cost_usd") or 0.0))
            if outcome.get("status") != "ok":
                log["errors"].append(f"{code} tinyfish: {outcome.get('message', '')}")
                record = log["banks"].setdefault(code, {"status": "ok", "rows": 0, "readers": [],
                                                        "unchanged": False, "usd": 0.0})
                record["tinyfish"] = outcome.get("status")
                continue
            rows.extend(rows_from_payload(payload, bank_code=code, source_url=bank["rate_page"],
                                          run_id=run_id, observed_at=observed_at, raw_sha256=meta["sha256"]))
        for run in agent_log.get("runs") or []:
            record = log["banks"].setdefault(run["bank"], {"status": "ok", "rows": 0, "readers": [],
                                                           "unchanged": False, "usd": 0.0})
            record["usd"] = run.get("usd", 0.0)
            record["seconds"] = round(record.get("seconds", 0.0) + run.get("seconds", 0.0), 1)
            record["tinyfish"] = run.get("status")

    # ---------------------------------------------------------------- silver
    deduped = dedupe_rows([row for row in rows if row["bank_code"] in by_code])
    frame = silver_frame(deduped)
    paths = write_silver(frame, out, run_id)
    for code, record in log["banks"].items():
        bank_rows = frame[frame.bank_code == code]
        record["rows"] = int(len(bank_rows))
        record["readers"] = sorted(set(bank_rows.reader)) if len(bank_rows) else []
        if record["rows"] and record["status"] in ("absent_offline", "unreadable"):
            record["status"] = "ok"
    log["sources"].setdefault("aggregator", {})["rows"] = int(len(frame[frame.reader == "aggregator"]))
    log["records"] = int(len(frame))
    log["banks_read"] = int(frame.bank_code.nunique())
    log["finished_at"] = now_iso()
    log["seconds"] = round(elapsed(), 1)
    log_dir = out / "run_log"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_id}.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    return RunResult(run_id=run_id, silver=frame, log=log, paths={**paths, "run_log": log_path})
