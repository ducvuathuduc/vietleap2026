"""Vision reader for scanned statement pages: render a page to PNG, ask a model for strict JSON.

Two independent prompts and two models read the same page image (`gpt-6-luna` with a table prompt,
`gpt-6-sol` with a copy-the-lines prompt), so a number that matters is never a single model's opinion.
Responses are cached by (image, prompt, model) and every paid call appends its token usage to
data/cache/notes_vision/_spend.jsonl; the API key is read from OPENAI_API_KEY and never written anywhere.

The model answers in VND billion, converted by the page's own "Đơn vị tính" line, and states the unit and the
page it read. A reply that is not valid JSON against the schema is a refusal, not a datum.
"""

from hashlib import sha1
import json
import os
from pathlib import Path

import httpx
import jsonschema

from .notes_contract import FIELDS

BASE_URL = "https://api.openai.com/v1"
MODEL_A = os.getenv("NOTES_VISION_MODEL_A", "gpt-6-luna")
MODEL_B = os.getenv("NOTES_VISION_MODEL_B", "gpt-6-sol")
CACHE = Path(__file__).resolve().parents[4] / "data" / "cache" / "notes_vision"
PRICE_IN_USD_PER_MTOK = float(os.getenv("NOTES_VISION_PRICE_IN", "1.25"))
PRICE_OUT_USD_PER_MTOK = float(os.getenv("NOTES_VISION_PRICE_OUT", "10.0"))

FIELDS_HINT = """loans_customer (total customer loans, "Cho vay khach hang"/"Du no cho vay khach hang"),
group_1_current ("No du tieu chuan"), group_2_watch ("No can chu y"), group_3_substandard
("No duoi tieu chuan"), group_4_doubtful ("No nghi ngo"), group_5_loss ("No co kha nang mat von"),
provision_opening ("So du dau ky"), provision_charge ("So trich lap trong ky"), provision_used_writeoff
("So su dung trong ky" / "Da su dung de xu ly rui ro"), provision_closing ("So du cuoi ky" or the balance
sheet line "Du phong rui ro cho vay khach hang"), writeoff_period ("No xau da xu ly", "Gia tri no da xu ly
rui ro")."""
SCHEMA = {
    "type": "object",
    "properties": {
        "page_label": {"type": "string"},
        "unit_printed": {"type": "string"},
        "period_label": {"type": "string"},
        "values": {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
        "lines": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        "note": {"type": "string"},
    },
    "required": ["values"],
}
PROMPT_A = f"""You are reading ONE page image of a Vietnamese bank's financial statement (bao cao tai chinh).
Read the table on the page and return STRICT JSON, nothing else:
{{"page_label": "...", "unit_printed": "the unit line as printed (Don vi tinh: ...)", "period_label": "the period the column belongs to",
  "values": {{"<field>": <number in VND BILLION or null>}}, "note": "anything that makes a value uncertain"}}
Fields to look for: {FIELDS_HINT}
Rules: take the CURRENT period column (the first amount column), not the prior-period column. Convert the printed
unit to VND billion (1 ty dong = 1 bn; 1 trieu dong = 0.001 bn; 1 dong = 1e-9 bn) and say which unit you saw.
Use null for a field the page does not show. Never estimate, never split a number across lines, never invent a
row. A balance printed in parentheses (a provision shown as a negative asset) is reported as a positive magnitude.
"""
PROMPT_B = f"""Transcribe, then report. On this page image of a Vietnamese bank financial statement, copy every
note line whose label matches one of these ideas: {FIELDS_HINT}
Return STRICT JSON only:
{{"page_label": "...", "unit_printed": "...", "period_label": "...",
  "lines": [{{"label": "the printed label", "numbers": ["the amounts exactly as printed, current column first"]}}],
  "values": {{"<field>": <number in VND BILLION or null>}}, "note": "..."}}
In "lines" copy the label and the numbers character by character, keeping Vietnamese diacritics and the printed
thousand separators. In "values" convert the CURRENT period amount of each matched line to VND billion. If a line
appears twice (notes and balance sheet), keep both in "lines" and put the notes figure in "values", saying so in
note. Never estimate or interpolate.
"""


class VisionError(RuntimeError):
    """The endpoint refused, or answered with something that is not the requested JSON."""


def api_key():
    return os.getenv("OPENAI_API_KEY", "").strip()


def digest(*parts):
    return sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def data_uri(png):
    import base64

    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def parse_json(text):
    """The JSON object in a model reply (a ```json fence or bare text), or None when it is not JSON."""
    body = (text or "").strip()
    if body.startswith("```"):
        body = body.split("```")[1]
        body = body.split("\n", 1)[1] if "\n" in body else body
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(body[start:end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def payload_values(payload):
    """field -> float for the fields the model returned as numbers."""
    from .notes_contract import FIELDS

    values = (payload or {}).get("values") or {}
    out = {}
    for field, value in values.items():
        if field not in FIELDS or value is None or isinstance(value, bool):
            continue
        try:
            out[field] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def read_line_numbers(payload):
    """The current-column amount of every transcribed line, keyed by the field its label matches.

    The transcribed numbers are printed units (triệu đồng on most Vietnamese statements), so they are scaled to
    VND billion with the unit line the model copied; a reply without a readable unit is not scaled silently.
    """
    from .notes_text import key_of, matches
    from .notes_contract import parse_number, unit_scale

    scale = unit_scale((payload or {}).get("unit_printed") or "")
    found = {}
    for line in (payload or {}).get("lines") or []:
        if not isinstance(line, dict):
            continue
        key = key_of(str(line.get("label") or ""))
        numbers = [parse_number(str(item)) for item in (line.get("numbers") or [])]
        numbers = [number * scale for number in numbers if number is not None]
        if not numbers:
            continue
        for field in FIELDS:
            if field in found or not matches(key, field):
                continue
            found[field] = numbers[0]
    return found


class VisionReader:
    """One OpenAI-compatible vision endpoint, with a response cache and a spend log."""

    def __init__(self, api_key=None, base_url=BASE_URL, cache=CACHE, client=None, timeout=120.0,
                 price_in=PRICE_IN_USD_PER_MTOK, price_out=PRICE_OUT_USD_PER_MTOK):
        self.key = api_key if api_key is not None else globals()["api_key"]()
        self.base_url = str(base_url).rstrip("/")
        self.cache = Path(cache)
        self.http = client or httpx.Client(timeout=timeout)
        self.price_in = float(price_in)
        self.price_out = float(price_out)
        self.calls = []
        self.cost_usd = 0.0

    def available(self):
        return bool(self.key)

    def read(self, png, prompt, model):
        """Parsed JSON payload for one page image, or raise VisionError (never silently return numbers)."""
        key = digest(png, prompt, model)
        path = self.cache / f"{key}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))["payload"]
            except (OSError, json.JSONDecodeError, KeyError):
                pass
        if not self.available():
            raise VisionError("OPENAI_API_KEY is not set")
        body = {"model": model, "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_uri(png)}}]}]}
        try:
            response = self.http.post(self.base_url + "/chat/completions",
                                      headers={"Authorization": f"Bearer {self.key}"}, json=body)
        except httpx.HTTPError as exc:
            raise VisionError(f"transport error: {type(exc).__name__}") from None
        if response.status_code >= 400:
            raise VisionError(f"HTTP {response.status_code}: {response.text[:200]}")
        payload = response.json()
        message = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = parse_json(message if isinstance(message, str) else json.dumps(message))
        if parsed is None:
            raise VisionError("reply is not JSON")
        try:
            jsonschema.validate(parsed, SCHEMA)
        except jsonschema.ValidationError as exc:
            raise VisionError(f"reply does not match the schema: {exc.message}") from None
        usage = payload.get("usage") or {}
        self._log(key, model, usage, parsed)
        return parsed

    def _log(self, key, model, usage, parsed):
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        cost = prompt_tokens / 1e6 * self.price_in + completion_tokens / 1e6 * self.price_out
        self.calls.append({"model": model, "prompt_tokens": prompt_tokens,
                           "completion_tokens": completion_tokens, "cost_usd": round(cost, 6)})
        self.cost_usd = round(self.cost_usd + cost, 6)
        self.cache.mkdir(parents=True, exist_ok=True)
        (self.cache / f"{key}.json").write_text(json.dumps(
            {"payload": parsed, "model": model, "usage": usage, "cost_usd": round(cost, 6)},
            ensure_ascii=False, indent=1), encoding="utf-8")
        with (self.cache / "_spend.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"model": model, "prompt_tokens": prompt_tokens,
                                     "completion_tokens": completion_tokens, "cost_usd": round(cost, 6)}) + "\n")


def read_page(reader, png, page):
    """Two independent vision reads of one page: (readings, errors) with reader names vision_a / vision_b."""
    readings, errors = [], {}
    for name, prompt, model in (("vision_a", PROMPT_A, MODEL_A), ("vision_b", PROMPT_B, MODEL_B)):
        try:
            payload = reader.read(png, prompt, model)
        except VisionError as exc:
            errors[name] = str(exc)[:160]
            continue
        values = payload_values(payload)
        if name == "vision_b":
            values = {**read_line_numbers(payload), **values}
        for field, value in values.items():
            readings.append({"field": field, "value_vnd_bn": value, "page": page, "reader": name})
    return readings, errors