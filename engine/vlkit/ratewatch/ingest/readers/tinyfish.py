"""TinyFish agent reader: the only way to read a JS-rendered household rate page.

The goal and output schema are the ones that worked in the X-TF research run (24 banks, 319 rows): both
channels, individual customers only, every quote copied verbatim. A page can print several products at the same term/channel (BaoVietBank's standard board plus a "Gom lộc phát
tài" savings plan; HDBank's 12-month promo next to its plain board). They collapse to one silver row: the
standard term-deposit product first, then the plainest label, then the lower rate — a reader never picks the
most flattering number.
"""
from __future__ import annotations

import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from ..contract import normalise_row, parse_rate, parse_term, parse_vi_date
from ....vn import ascii_key

LICENCE = "TinyFish agent read of the bank's public page"
AGENT_DEADLINE_S = 360.0          # a hung run is cancelled after 6 minutes (X-TF: 1 in 3 runs hangs)
MAX_WORKERS = 2                   # the default TinyFish plan allows 2 concurrent runs
AGENT_GOAL = """On this page read the SAVINGS / TERM-DEPOSIT interest rate table (lai suat tiet kiem / lai suat huy dong)
that {bank} publishes for INDIVIDUAL customers (khach hang ca nhan), in VND, interest paid at maturity (cuoi ky),
terms 1 to 36 months. If the page has separate tables or tabs for "Tai quay" (at the counter) and
"Online / Truc tuyen / Internet Banking / App", read BOTH and emit rows for both channels.
One row per (channel, term_months) you can actually see. Do not read corporate (doanh nghiep) rates, do not read
demand/non-term rates (khong ky han), do not read other currencies, and do not follow links to other banks.
If the page links a PDF rate sheet (bieu lai suat), open that PDF and read it.
Fields: term_months = integer months (1,2,3,4,5,6,7,8,9,10,11,12,13,15,18,24,36 - only those the page lists);
channel = "counter" or "online"; rate_pct = annual percent per year exactly as printed (4,80 -> 4.8);
effective_date = the date printed on the table (ngay hieu luc / ap dung tu), format YYYY-MM-DD, empty if none;
product_name = the product/tier heading the row sits under, in Vietnamese, as printed;
quote = the exact cell text you read. Never invent, average or estimate a number: copy what is on the page.
If you can see no rate table at all, return rates: [] and say what you saw in note."""

ROW_SCHEMA = {
    "type": "object",
    "properties": {
        "channel": {"type": "string", "enum": ["counter", "online"]},
        "term_months": {"type": "integer"},
        "rate_pct": {"type": "number"},
        "effective_date": {"type": "string"},
        "product_name": {"type": "string"},
        "quote": {"type": "string"},
    },
    "required": ["channel", "term_months", "rate_pct"],
}
AGENT_SCHEMA = {
    "type": "object",
    "properties": {
        "bank": {"type": "string"},
        "rates": {"type": "array", "items": ROW_SCHEMA},
        "page_effective_date": {"type": "string"},
        "note": {"type": "string"},
    },
    "required": ["rates"],
}


def product_score(name: str) -> int:
    """How much a product label looks like the standard household term deposit (higher wins)."""
    key = ascii_key(name)
    score = 0
    if "tiet kiem" in key or "tien gui" in key:
        score += 2
    if "ky han" in key:
        score += 1
    if "thong thuong" in key:
        score += 1
    return score


def _result_of(payload: dict) -> dict:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    return result if isinstance(result, dict) else {}


def rows_from_payload(payload: dict, *, bank_code: str, source_url: str, run_id: str, observed_at: str,
                      raw_sha256: str) -> list[dict]:
    """Rows of one saved run payload (``result.rates`` of the agent, or the run record itself)."""
    status = str(payload.get("status") or "").upper()
    if status in ("FAILED", "CANCELLED", "INVALID", "SKIPPED"):
        return []
    result = _result_of(payload)
    page_date = parse_vi_date(result.get("page_effective_date") or "")
    best: dict[tuple[str, int], tuple[tuple[int, int, float], dict]] = {}
    for raw in result.get("rates") or []:
        if not isinstance(raw, dict):
            continue
        term = parse_term(raw.get("term_months"))
        rate = parse_rate(raw.get("rate_pct"))
        if term is None or rate is None:
            continue
        channel = str(raw.get("channel", "")).strip().lower()
        if channel not in ("online", "counter"):
            continue
        product = str(raw.get("product_name") or "")
        score = (-product_score(product), 1 if "(" in product else 0, rate)
        key = (channel, term)
        if key in best and best[key][0] <= score:
            continue
        row = normalise_row({
            "run_id": run_id, "bank_code": bank_code, "term_months": term, "channel": channel,
            "tier": "", "rate_pct": rate, "interest_basis": "at_maturity",
            "sheet_date": page_date or parse_vi_date(raw.get("effective_date") or ""),
            "observed_at": observed_at, "reader": "tinyfish", "source_url": source_url,
            "raw_sha256": raw_sha256,
        })
        best[key] = (score, row)
    return [row for _, row in best.values()]


def run_bank_agent(bank: dict, deadline_s: float = AGENT_DEADLINE_S) -> dict:
    """One paid agent run on the bank's rate page (``run_goal`` cancels the run at ``deadline_s``)."""
    from ....de.tinyfish import run_goal

    name = bank.get("name_vi") or bank["code"]
    started = time.monotonic()
    outcome = run_goal(bank["rate_page"], AGENT_GOAL.format(bank=name), output_schema=AGENT_SCHEMA,
                       deadline_s=deadline_s, poll_s=5.0, cache=True, cache_ttl_h=12.0,
                       source=f"ratewatch:{bank['code']}")
    cached = outcome.message.startswith("[tinyfish] cache hit")
    return {"status": outcome.status, "records": outcome.records,
            "cost_usd": 0.0 if cached else outcome.cost_usd,      # a cache hit is not money spent now
            "steps": outcome.steps, "run_id": outcome.run_id, "message": outcome.message, "cached": cached,
            "seconds": round(time.monotonic() - started, 1)}


def run_agent_queue(banks: list[dict], *, run_fn=None, max_usd: float = 5.0,
                    deadline_s: float = AGENT_DEADLINE_S, max_seconds: float = 2400.0,
                    max_workers: int = MAX_WORKERS, clock=time.monotonic) -> tuple[dict[str, dict], dict]:
    """Run the agent queue two at a time, stopping before the next launch once the budget/time is used up."""
    run_fn = run_fn or run_bank_agent
    started = clock()
    log: dict = {"usd": 0.0, "stopped": "done", "runs": [], "errors": []}
    outcomes: dict[str, dict] = {}

    def collect(bank: dict, outcome: dict) -> None:
        log["usd"] = round(log["usd"] + float(outcome.get("cost_usd") or 0.0), 4)
        log["runs"].append({"bank": bank["code"], "status": outcome.get("status"), "steps": outcome.get("steps"),
                            "usd": round(float(outcome.get("cost_usd") or 0.0), 4),
                            "seconds": outcome.get("seconds", 0.0),
                            "run_id": outcome.get("run_id"), "message": outcome.get("message", "")})
        outcomes[bank["code"]] = outcome

    def exhausted() -> str | None:
        if log["usd"] >= float(max_usd):
            return "budget"
        if clock() - started >= float(max_seconds):
            return "time"
        return None

    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as pool:
        pending: dict = {}
        for bank in banks:
            stop = exhausted()
            if stop:
                log["stopped"] = stop
                break
            pending[pool.submit(run_fn, bank, deadline_s)] = bank
            while len(pending) >= max(1, int(max_workers)):
                done, _ = wait(list(pending), return_when=FIRST_COMPLETED)
                for future in done:
                    collect(pending.pop(future), future.result())
        for future, bank in list(pending.items()):
            collect(bank, future.result())
    return outcomes, log
