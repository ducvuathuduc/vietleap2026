"""Optional TinyFish agent connector (``kind: tinyfish``) + the free TinyFetch helper.

TinyAgent drives a real browser (JS pages, anti-bot pages) and returns structured data:
  - Start a run:  POST https://agent.tinyfish.ai/v1/automation/run-async
      Headers: X-API-Key: <TINYFISH_API_KEY>
      Body:    {"url": "...", "goal": "...", "output_schema": {...}, "browser_profile": "lite|stealth",
                "proxy_config": {...}, "agent_config": {"max_duration_seconds": 180}}
      Returns: {"run_id": "..."}
  - Poll a run:   GET  https://agent.tinyfish.ai/v1/runs/{run_id}   (status PENDING/RUNNING/COMPLETED/FAILED/CANCELLED)
  - Cancel a run: POST https://agent.tinyfish.ai/v1/runs/{run_id}/cancel   (only for async/batch/sse runs)
TinyFetch (free, 1.000 URLs/day) turns a page into markdown:
  POST https://api.fetch.tinyfish.ai  {"urls": [...], "format": "markdown"} -> {"results": [{url, text, ...}], "errors": []}

Cost control (docs.tinyfish.ai/pricing: agent $0.016/step, docs note 2 concurrent runs on the default plan):
  * per-run cost = num_of_steps x rate (rate from the run payload if the API reports one, else ``usd_per_step``);
  * every paid run is appended to ``data/cache/tinyfish/_spend.jsonl``;
  * ``options.max_usd`` caps one source, ``TINYFISH_MAX_USD`` (default 10) caps the project;
  * a run whose URL + goal + schema were already paid for inside ``cache_ttl_h`` is served from
    ``data/cache/tinyfish/<sha1>.json`` and costs nothing.

API key handling: read ONLY from the environment variable ``TINYFISH_API_KEY``. When it is absent (and
``mock`` is false) the outcome is ``skipped`` with a clear message so offline runs and tests never fail and
never spend money. robots.txt / ToS of the target site still apply: TinyFish must not be used to bypass
logins, captchas or a site's terms.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import jsonschema

from ..vn import parse_vn_number

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Asia/Saigon")
TINYFISH_ENV_VAR = "TINYFISH_API_KEY"
MAX_USD_ENV_VAR = "TINYFISH_MAX_USD"
BASE_URL = "https://agent.tinyfish.ai/v1"
RUN_ASYNC_URL = f"{BASE_URL}/automation/run-async"
FETCH_URL = "https://api.fetch.tinyfish.ai"
DEFAULT_USD_PER_STEP = 0.016        # GET /v1/wallet rates.meters.Agent (19/11/2026)
DEFAULT_MAX_USD = 10.0              # project-wide cap (MASTER_PLAN §0)
DEFAULT_TIMEOUT = 60.0
CANCEL_GRACE_S = 3.0
MAX_SCHEMA_BYTES = 64 * 1024
MAX_SCHEMA_DEPTH = 10
MAX_FETCH_URLS = 10                 # TinyFetch limit per request
RETRY_ATTEMPTS = 4
RETRY_STATUS = {429, 500, 502, 503, 504}
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
SPEND_FILE = "_spend.jsonl"

KIT = Path(__file__).resolve().parents[3]
CACHE_DIR = KIT / "data" / "cache" / "tinyfish"
SLEEP = time.sleep


class TinyFishError(RuntimeError):
    """Non-retryable TinyFish HTTP/transport failure (400/401/402/403, retries exhausted, bad payload)."""


@dataclass
class TinyFishOutcome:
    status: str  # "ok" | "mock" | "skipped" | "invalid" | "cancelled"
    source: str
    run_id: str | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] | None = None
    output_json: str | None = None
    steps: int | None = None
    cost_usd: float = 0.0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------- options

def _depth(obj: Any, level: int = 1) -> int:
    if isinstance(obj, dict):
        return max([level] + [_depth(v, level + 1) for v in obj.values()])
    if isinstance(obj, (list, tuple)):
        return max([level] + [_depth(v, level + 1) for v in obj])
    return level


def validate_options(options: Mapping[str, Any] | None) -> None:
    """Reject tinyfish options that are unsupported, would spend money by accident or the API would 400 on."""
    o = dict(options or {})
    goal = o.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("tinyfish source: options.goal is required (a plain-language instruction for the agent)")
    if o.get("mode", "async") != "async":
        raise ValueError(f"tinyfish source: options.mode must be 'async', got {o.get('mode')!r}")
    schema = o.get("output_schema")
    if schema is not None:
        if not isinstance(schema, dict):
            raise ValueError("tinyfish source: options.output_schema must be a JSON-Schema object")
        size = len(json.dumps(schema, ensure_ascii=False).encode("utf-8"))
        if size > MAX_SCHEMA_BYTES:
            raise ValueError(f"tinyfish source: options.output_schema is {size} bytes, the API rejects > 64KB")
        depth = _depth(schema)
        if depth > MAX_SCHEMA_DEPTH:
            raise ValueError(f"tinyfish source: options.output_schema depth {depth} > {MAX_SCHEMA_DEPTH}")
    if o.get("browser_profile") not in (None, "lite", "stealth"):
        raise ValueError("tinyfish source: options.browser_profile must be 'lite' or 'stealth'")
    if o.get("proxy_country") is not None and not re.fullmatch(r"[A-Za-z]{2}", str(o["proxy_country"])):
        raise ValueError("tinyfish source: options.proxy_country must be an ISO-2 code such as 'VN'")
    for key in ("poll_s", "deadline_s", "cache_ttl_h", "max_usd", "usd_per_step"):
        if o.get(key) is None:
            continue
        try:
            value = float(o[key])
        except (TypeError, ValueError):
            raise ValueError(f"tinyfish source: options.{key} must be a number") from None
        if value < 0 or (value == 0 and key in ("poll_s", "deadline_s")):
            raise ValueError(f"tinyfish source: options.{key} must be positive, got {value:g}")
    for key in ("mock", "cache", "schema_strict", "evidence"):
        if o.get(key) is not None and not isinstance(o[key], bool):
            raise ValueError(f"tinyfish source: options.{key} must be true or false")


# --------------------------------------------------------------------- helpers

def _now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")[:40] or "page"


def mock_run_response(uri: str, goal: str) -> dict[str, Any]:
    """Deterministic run-shaped payload for an offline dry run (``options.mock: true``) — no API call, no spend."""
    return {
        "run_id": f"mock-tinyfish-{_slug(uri)}",
        "status": "COMPLETED",
        "goal": goal,
        "num_of_steps": 3,
        "result": {
            "title": f"Trang mẫu (TinyFish --mock): {uri}",
            "total_registered_fdi_usd_bn": 54.85,
            "source_url": uri,
            "note": "dữ liệu giả lập, không phải số thật",
        },
        "error": None,
    }


def records_from_result(result: Any) -> list[dict[str, Any]]:
    """Rows of a run result: the items of the array, or the object itself as one row."""
    if isinstance(result, list):
        return [item if isinstance(item, dict) else {"value": item} for item in result]
    if isinstance(result, dict) and result:
        return [result]
    return []


def validate_records(records: Sequence[Mapping[str, Any]], output_schema: Mapping[str, Any] | None,
                     strict: bool = True) -> tuple[bool, list[str]]:
    """jsonschema check of every row plus the business rule "a required field may not be null"."""
    if not output_schema or not records:
        return True, []
    schema = output_schema.get("items") if output_schema.get("type") == "array" else output_schema
    if not isinstance(schema, dict):
        return True, []
    errors: list[str] = []
    for index, record in enumerate(records):
        try:
            jsonschema.validate(dict(record), schema)
        except jsonschema.ValidationError as e:
            errors.append(f"row {index}: {e.message}")
        except jsonschema.SchemaError as e:      # the schema itself is wrong: do not trust the result
            return False, [f"invalid output_schema: {e.message}"]
        if strict:
            for key in schema.get("required") or []:
                if record.get(key) is None:
                    errors.append(f"row {index}: required field '{key}' is null or missing")
    return (not errors), errors[:10]


_NUMBERISH = re.compile(r"^[-+]?\d[\d.,]*\s*%?$")


def _as_number(raw: Any) -> float | None:
    """A value that is a plain number (float or "54,85" / "2.438,9%" text); dates and prose are not evidence."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not _NUMBERISH.match(text):
        return None
    return parse_vn_number(text, ",")[0]


def _text_numbers(text: str) -> set[float]:
    found: set[float] = set()
    for token in re.findall(r"\d[\d.,]*", text or ""):
        token = token.rstrip(".,")
        if not token:
            continue
        for decimal in (",", "."):              # "2.438,9" and "2,438.9" both resolve
            value = parse_vn_number(token, decimal)[0]
            if value is not None:
                found.add(round(value, 6))
    return found


def evidence_check(values: Mapping[str, Any] | Sequence[Any], text: str) -> dict[str, bool | None]:
    """Which extracted numbers literally appear in the page text (Vietnamese number formats normalised).

    Returns field -> True/False, or None for values that are not numbers (titles, dates, prose).
    """
    items = values.items() if isinstance(values, Mapping) else enumerate(values)
    numbers = _text_numbers(text)
    out: dict[str, bool | None] = {}
    for key, raw in items:
        number = _as_number(raw)
        out[str(key)] = None if number is None else round(number, 6) in numbers
    return out


def row_evidence(row: Mapping[str, Any], text: str | None) -> bool | None:
    """True when every number of the row appears in the page text, False when one does not, None without numbers."""
    if not text:
        return None
    checks = [found for found in evidence_check(row, text).values() if found is not None]
    return all(checks) if checks else None


# --------------------------------------------------------------------- spend / budget

def _spend_path(cache_dir: str | Path | None) -> Path:
    return Path(cache_dir or CACHE_DIR) / SPEND_FILE


def _read_spend(cache_dir: str | Path | None) -> list[dict[str, Any]]:
    path = _spend_path(cache_dir)
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def _sum_spend(records: Sequence[Mapping[str, Any]], source: str | None = None) -> float:
    total = 0.0
    for record in records:
        if source is not None and record.get("source") != source:
            continue
        try:
            total += float(record.get("cost_usd") or 0)
        except (TypeError, ValueError):
            continue
    return round(total, 4)


def spend_total(cache_dir: str | Path | None = None) -> float:
    """USD spent through this cache dir (all sources)."""
    return _sum_spend(_read_spend(cache_dir))


def spend_for(source: str, cache_dir: str | Path | None = None) -> float:
    """USD spent by one source name."""
    return _sum_spend(_read_spend(cache_dir), str(source))


def _record_spend(record: dict[str, Any], cache_dir: str | Path | None) -> None:
    path = _spend_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _budget_refusal(source: str, max_usd: float | None, cache_dir: str | Path | None) -> str | None:
    """Reason to refuse a run before it starts (None = allowed). A run's own cost is only known when it ends."""
    try:
        cap = float(os.environ.get(MAX_USD_ENV_VAR, "") or DEFAULT_MAX_USD)
    except ValueError:
        cap = DEFAULT_MAX_USD
    spent = spend_total(cache_dir)
    if spent >= cap:
        return (f"[tinyfish] refused: spent {spent:.4f} USD of the {MAX_USD_ENV_VAR}={cap:g} cap — "
                f"raise the cap or rely on cached pages")
    if max_usd is not None and spend_for(source, cache_dir) >= float(max_usd):
        return (f"[tinyfish] refused: source '{source}' already spent "
                f"{spend_for(source, cache_dir):.4f} USD of its max_usd={float(max_usd):g} budget")
    return None


# --------------------------------------------------------------------- cache

def _cache_key(uri: str, goal: str, output_schema: Mapping[str, Any] | None, browser_profile: str | None,
               proxy_country: str | None) -> str:
    blob = json.dumps([uri, goal, output_schema or {}, browser_profile or "", proxy_country or ""],
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _cache_read(cache_dir: str | Path | None, key: str, ttl_h: float) -> dict[str, Any] | None:
    path = Path(cache_dir or CACHE_DIR) / f"{key}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(str(data["fetched_at"]))
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None
    if datetime.now(TZ) - fetched_at > timedelta(hours=float(ttl_h)):
        return None
    return data


def _cache_write(cache_dir: str | Path | None, key: str, payload: dict[str, Any]) -> None:
    path = Path(cache_dir or CACHE_DIR) / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


# --------------------------------------------------------------------- HTTP

def _error_code(response: httpx.Response) -> str:
    try:
        body = response.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict) and err.get("code"):
            return f"{err['code']}: {err.get('message', '')}".strip(": ")
    except ValueError:
        pass
    return (response.text or "")[:200]


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("retry-after")
    if header:
        try:
            return max(0.0, min(60.0, float(header)))
        except ValueError:
            pass
    return min(30.0, float(2 ** attempt))


def _request(client: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:
    """Retry only 429/5xx/transport errors (honouring Retry-After); 400/401/402/403 fail at once."""
    for attempt in range(RETRY_ATTEMPTS):
        last = attempt == RETRY_ATTEMPTS - 1
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            if last:
                raise TinyFishError(f"TinyFish {method} {url} failed: {exc!r}") from exc
            SLEEP(min(30.0, float(2 ** attempt)))
            continue
        if response.status_code not in RETRY_STATUS:
            if response.status_code >= 400:
                raise TinyFishError(f"TinyFish {method} {url} -> HTTP {response.status_code} {_error_code(response)}")
            return response
        if last:
            raise TinyFishError(f"TinyFish {method} {url} -> HTTP {response.status_code} {_error_code(response)}")
        SLEEP(_retry_delay(response, attempt))
    raise TinyFishError(f"TinyFish {method} {url} failed")  # pragma: no cover - loop always returns or raises


def _poll(client: httpx.Client, headers: dict[str, str], run_id: str, poll_s: float,
          deadline_s: float) -> tuple[dict[str, Any], bool]:
    run: dict[str, Any] = {}
    deadline = time.monotonic() + float(deadline_s)
    while time.monotonic() < deadline:
        SLEEP(float(poll_s))
        run = _request(client, "GET", f"{BASE_URL}/runs/{run_id}", headers=headers).json()
        if run.get("status") in TERMINAL:
            return run, False
    _request(client, "POST", f"{BASE_URL}/runs/{run_id}/cancel", headers=headers)
    SLEEP(CANCEL_GRACE_S)
    final = _request(client, "GET", f"{BASE_URL}/runs/{run_id}", headers=headers).json()
    return (final or run), True


def _usd_per_step(run: Mapping[str, Any], default: float) -> float:
    """Price per step: from a run/wallet payload when it reports one (rates.meters[], unit_amount per step), else the option."""
    for key in ("usd_per_step", "cost_per_step"):
        value = run.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return float(value)
    rates = run.get("rates")
    meters = rates.get("meters") if isinstance(rates, dict) else None
    meters = [meters] if isinstance(meters, dict) else meters
    for meter in meters if isinstance(meters, list) else []:
        if not isinstance(meter, dict) or "agent" not in str(meter.get("label") or "").lower():
            continue
        if meter.get("per") not in (None, "step"):
            continue
        try:
            return float(meter["unit_amount"])
        except (KeyError, TypeError, ValueError):
            continue
    return float(default)


def run_goal(uri: str, goal: str, *, output_schema: Mapping[str, Any] | None = None, poll_s: float = 5.0,
             deadline_s: float = 180.0, browser_profile: str | None = None, proxy_country: str | None = None,
             cache: bool = True, cache_ttl_h: float = 24.0, max_usd: float | None = None,
             usd_per_step: float = DEFAULT_USD_PER_STEP, schema_strict: bool = True, mock: bool = False,
             out_json: str | Path | None = None, client: httpx.Client | None = None, net_guard: bool = False,
             source: str | None = None, cache_dir: str | Path | None = None) -> TinyFishOutcome:
    """Run one TinyAgent goal on ``uri`` and return the validated records (never raises on a missing key)."""
    uri, goal = str(uri).strip(), str(goal or "").strip()
    if not uri:
        raise ValueError("TinyFish uri must not be blank")
    if not goal:
        raise ValueError("TinyFish goal must not be blank")
    source_name = str(source or uri)
    cache_dir = Path(cache_dir or CACHE_DIR)
    body: dict[str, Any] = {"url": uri, "goal": goal, "agent_config": {"max_duration_seconds": max(1, int(deadline_s))}}
    if output_schema:
        body["output_schema"] = dict(output_schema)
    if browser_profile:
        body["browser_profile"] = browser_profile
    if proxy_country:
        body["proxy_config"] = {"enabled": True, "type": "tinyfish", "country_code": proxy_country}
    key = _cache_key(uri, goal, output_schema, browser_profile, proxy_country)

    if mock:
        run: dict[str, Any] = mock_run_response(uri, goal)
        cancelled = False
    else:
        if cache:
            hit = _cache_read(cache_dir, key, cache_ttl_h)
            if hit:
                return TinyFishOutcome(status="ok", source=uri, run_id=hit.get("run_id"),
                                       records=hit.get("records") or [], raw=hit.get("raw"),
                                       steps=hit.get("num_steps"), cost_usd=float(hit.get("cost_usd") or 0),
                                       message=f"[tinyfish] cache hit for {uri} (no run, no spend)")
        api_key = os.environ.get(TINYFISH_ENV_VAR, "").strip()
        if not api_key:
            message = (f"[tinyfish] skipped: {TINYFISH_ENV_VAR} is not set "
                       f"(set it in .env.local or use mock: true for a dry run)")
            logger.info(message)
            return TinyFishOutcome(status="skipped", source=uri, message=message)
        refusal = _budget_refusal(source_name, max_usd, cache_dir)
        if refusal:
            logger.warning(refusal)
            return TinyFishOutcome(status="skipped", source=uri, message=refusal)
        if net_guard:
            from .netguard import check_url

            check_url(uri)
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        own_client = client is None
        http = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
        try:
            started = _request(http, "POST", RUN_ASYNC_URL, headers=headers, json=body).json()
            run_id = str(started.get("run_id") or "")
            if not run_id:
                raise TinyFishError(f"TinyFish {RUN_ASYNC_URL} returned no run_id: {started!r}")
            run, cancelled = _poll(http, headers, run_id, poll_s, deadline_s)
        finally:
            if own_client:
                http.close()
        run.setdefault("run_id", run_id)

    steps = run.get("num_of_steps")
    steps = int(steps) if isinstance(steps, (int, float)) and not isinstance(steps, bool) else None
    cost = round(steps * _usd_per_step(run, usd_per_step), 4) if steps else 0.0
    run_status = str(run.get("status") or "")
    records: list[dict[str, Any]] = []
    if mock:
        status, message = "mock", f"[tinyfish] mock run for {uri} (no API call, no spend)"
        records = records_from_result(run.get("result"))     # mock data is not validated against a real schema
    elif cancelled or run_status == "CANCELLED":
        status, message = "cancelled", f"[tinyfish] cancelled {run.get('run_id')} at the {deadline_s:g}s deadline"
    elif run_status == "FAILED":
        status, message = "invalid", f"[tinyfish] run {run.get('run_id')} FAILED: {json.dumps(run.get('error'))[:300]}"
    else:
        records = records_from_result(run.get("result"))
        if not records:
            status, message = "invalid", f"[tinyfish] run {run.get('run_id')} COMPLETED with an empty result"
        else:
            valid, errors = validate_records(records, output_schema, strict=schema_strict)
            if valid:
                status = "ok"
                message = f"[tinyfish] {run.get('run_id')} {run_status}, {len(records)} rows, {steps or 0} steps"
            else:
                status, message = "invalid", (f"[tinyfish] run {run.get('run_id')} result does not match "
                                              f"output_schema: " + "; ".join(errors[:3]))
                records = []

    artifact = {
        "status": status,
        "uri": uri,
        "fetched_at": _now_iso(),
        "endpoint": RUN_ASYNC_URL,
        "request": {"body": body, "api_key": "***"},
        "run_id": run.get("run_id"),
        "num_steps": steps,
        "cost_usd": cost,
        "records": records,
        "raw": run,
        "message": message,
    }
    written: str | None = None
    if out_json is not None:
        target = Path(out_json)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(artifact, ensure_ascii=False, indent=1), encoding="utf-8")
        written = str(target)
    if status == "ok" and cache:
        _cache_write(cache_dir, key, artifact)
    if not mock and cost > 0:
        _record_spend({"ts": artifact["fetched_at"], "source": source_name, "run_id": run.get("run_id"),
                       "steps": steps, "cost_usd": cost}, cache_dir)
    if status == "ok":
        logger.info(message)
    else:
        logger.warning(message)
    return TinyFishOutcome(status=status, source=uri, run_id=run.get("run_id"), records=records, raw=run,
                           output_json=written, steps=steps, cost_usd=cost, message=message)


def fetch_text(urls: Sequence[str] | str, *, client: httpx.Client | None = None) -> dict[str, str]:
    """Free TinyFetch call: URL -> markdown text. Empty dict when the key is missing or the fetch fails."""
    items = [str(u).strip() for u in ([urls] if isinstance(urls, str) else list(urls or [])) if str(u).strip()]
    api_key = os.environ.get(TINYFISH_ENV_VAR, "").strip()
    if not api_key or not items:
        logger.info("[tinyfish] TinyFetch skipped: %s is not set or no URL given", TINYFISH_ENV_VAR)
        return {}
    own_client = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
    try:
        response = _request(http, "POST", FETCH_URL, headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                            json={"urls": items[:MAX_FETCH_URLS], "format": "markdown"})
        data = response.json()
    except (TinyFishError, httpx.HTTPError, ValueError) as exc:
        logger.warning("[tinyfish] TinyFetch failed: %s", exc)
        return {}
    finally:
        if own_client:
            http.close()
    return {str(result["url"]): str(result.get("text") or "")
            for result in data.get("results") or [] if isinstance(result, dict) and result.get("url")}
