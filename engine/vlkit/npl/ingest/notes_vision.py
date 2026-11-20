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
import re

import httpx
import jsonschema

from .notes_contract import FIELDS, unit_of

BASE_URL = "https://api.openai.com/v1"
MODEL_A = os.getenv("NOTES_VISION_MODEL_A", "gpt-6-luna")
MODEL_B = os.getenv("NOTES_VISION_MODEL_B", "gpt-6-sol")
MODEL_LOCATE = os.getenv("NOTES_VISION_MODEL_LOCATE", "gpt-5-mini")   # cheap page finder, not a reader
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
        "page_label": {"type": ["string", "null"]},
        "unit_printed": {"type": ["string", "null"]},
        "period_label": {"type": ["string", "null"]},
        "values": {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
        "values_printed": {"type": "object", "additionalProperties": {"type": ["number", "string", "null"]}},
        "lines": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        "note": {"type": ["string", "null"]},
    },
    "required": ["values"],
}
PROMPT_A = f"""You are reading ONE page image of a Vietnamese bank's financial statement (bao cao tai chinh).
Read the table on the page and return STRICT JSON, nothing else:
{{"page_label": "...", "unit_printed": "the unit line as printed (Don vi tinh: ...)", "period_label": "the period the column belongs to",
  "values": {{"<field>": <number in VND BILLION or null>}},
  "values_printed": {{"<field>": <the same amount EXACTLY as printed on the page, in the page's own unit>}},
  "note": "anything that makes a value uncertain"}}
Fields to look for: {FIELDS_HINT}
Rules: take the CURRENT period column (the first amount column), not the prior-period column. Convert the printed
unit to VND billion and say which unit you saw. The arithmetic, exactly: "Don vi tinh: ty dong" -> the printed
number is already VND billion; "Don vi tinh: trieu dong" -> divide the printed number by 1,000 (31,168,107 trieu
dong = 31,168.1 bn); "Don vi tinh: dong/VND" -> divide by 1,000,000,000. A provision balance is 10x to 20x the
NPL it covers, so if your converted closing provision is smaller than the NPL total on the page you have the unit
wrong: recheck the unit line before answering.
Use null for a field the page does not show. Never estimate, never split a number across lines, never invent a
row. A balance printed in parentheses (a provision shown as a negative asset) is reported as a positive magnitude.
"""
PROMPT_B = f"""Transcribe, then report. On this page image of a Vietnamese bank financial statement, copy every
note line whose label matches one of these ideas: {FIELDS_HINT}
Return STRICT JSON only:
{{"page_label": "...", "unit_printed": "...", "period_label": "...",
  "lines": [{{"label": "the printed label", "numbers": ["the amounts exactly as printed, current column first"]}}],
  "values": {{"<field>": <number in VND BILLION or null>}},
  "values_printed": {{"<field>": <the same amount EXACTLY as printed, page unit>}}, "note": "..."}}
In "lines" copy the label and the numbers character by character, keeping Vietnamese diacritics and the printed
thousand separators. In "values" convert the CURRENT period amount of each matched line to VND billion: "ty dong" -> as printed,
"trieu dong" -> divide by 1,000 (31,168,107 -> 31,168.1), "dong/VND" -> divide by 1,000,000,000. Then check
yourself: opening + charge - used must equal closing; a provision balance is 10x to 20x the NPL it covers. If
either check fails, say so in note instead of hiding it. If a line appears twice (notes and balance sheet), keep
both in "lines" and put the notes figure in "values", saying so in note. Never estimate or interpolate.
"""


LOCATE_SCHEMA = {
    "type": "object",
    "properties": {
        "classification_pages": {"type": "array", "items": {"type": ["integer", "string"]}},
        "provision_pages": {"type": "array", "items": {"type": ["integer", "string"]}},
        "balance_sheet_pages": {"type": "array", "items": {"type": ["integer", "string"]}},
        "note": {"type": "string"},
    },
    "required": ["classification_pages", "provision_pages"],
}
LOCATE_PROMPT = """This image is a grid of pages from a Vietnamese bank financial statement, each page stamped
with its page number (p12, p13, ...) in red at the top-left corner. Reading order is left to right, top to bottom.
Answer with STRICT JSON only:
{"classification_pages": [<page numbers>], "provision_pages": [<page numbers>], "balance_sheet_pages": [<page numbers>], "note": "..."}
classification_pages = every page that shows the loan classification by credit quality group, i.e. a table with rows
"No du tieu chuan" (or "Nợ đủ tiêu chuẩn"), "No can chu y", "No duoi tieu chuan", "No nghi ngo", "No co kha nang mat von"
(possibly titled "Phan loai du no theo nhom" / "Phan tich chat luong no vay").
provision_pages = every page that shows the loan-loss provision movement, i.e. rows "So du dau ky", "So trich lap trong
ky" (or "Trich lap du phong"), "So su dung trong ky" / "Da su dung de xu ly rui ro", "So du cuoi ky" for
"Du phong rui ro cho vay khach hang".
balance_sheet_pages = the page of the balance sheet (Bang can doi ke toan) that carries the asset line
"Cho vay khach hang" with its amount, and, when visible on the same page, "Du phong rui ro cho vay khach hang".
Use the stamped page numbers, never positions in the grid. Empty arrays when a table is not in this grid. Do not guess.
"""


def pages_from_locate(payload, allowed=None):
    """(classification, provision, balance-sheet) page sets, filtered to pages that exist in the document."""
    ok = set(allowed) if allowed is not None else None

    def clean(key):
        found = set()
        for value in (payload or {}).get(key) or []:
            digits = re.search(r"\d+", str(value))       # "p40", "page 40" and 40 all mean page 40
            if digits is None:
                continue
            page = int(digits.group())
            if page > 0 and (ok is None or page in ok):
                found.add(page)
        return found
    return clean("classification_pages"), clean("provision_pages"), clean("balance_sheet_pages")


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
    """field -> VND billion, scaled HERE from the numbers the model transcribed and the unit line it read.

    A vision model asked to divide by a thousand sometimes divides by a million (TCB 2025Q3: 766.7 instead of
    766,700 bn), and a uniform slip is invisible to ratios and to the sum gate. So the prompt asks for the printed
    numbers, and this module applies `unit_of` — the same rule the text reader uses — instead of trusting arithmetic.
    `values` (already converted by the model) is only the fallback when it transcribed no printed amount at all.
    """
    from .notes_contract import FIELDS, unit_of

    scale, label = unit_of((payload or {}).get("unit_printed") or "")
    printed = (payload or {}).get("values_printed") or {}
    values = (payload or {}).get("values") or {}
    out = {}
    # without a readable unit line the printed numbers cannot be scaled, so the model's own conversion is kept and
    # the row is labelled unit="unknown", which the unit gate turns into a quarantine instead of a silent rescale
    order = ((values, 1.0), (printed, scale)) if label == "unknown" else ((printed, scale), (values, 1.0))
    for source, factor in order:
        for field, value in (source or {}).items():
            if field in out or field not in FIELDS or value is None or isinstance(value, bool):
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            out[field] = number * factor if factor != 1.0 else number
    return out


def payload_unit(payload):
    """The unit label the model copied ("ty", "trieu", "nghin", "dong", "unknown")."""
    from .notes_contract import unit_of

    return unit_of((payload or {}).get("unit_printed") or "")[1]


def read_line_numbers(payload):
    """The current-column amount of every transcribed line, keyed by the field its label matches.

    The transcribed numbers are printed units (triệu đồng on most Vietnamese statements), so they are scaled to
    VND billion with the unit line the model copied; a reply without a readable unit is not scaled silently.
    """
    from .notes_text import key_of, matches
    from .notes_contract import parse_number

    scale, _ = unit_of((payload or {}).get("unit_printed") or "")
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

    def read(self, png, prompt, model, schema=None):
        """Parsed JSON payload for one page image, or raise VisionError (never silently return numbers).

        `schema` is the shape this prompt must answer with: the extraction schema by default, the locator schema
        for the page finder. A reply that does not match it is a refusal, and nothing is cached or spent on it.
        """
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
            jsonschema.validate(parsed, schema or SCHEMA)
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
        unit = payload_unit(payload)
        if name == "vision_b":
            values = {**read_line_numbers(payload), **values}
        for field, value in values.items():
            readings.append({"field": field, "value_vnd_bn": value, "page": page, "reader": name, "unit": unit})
    return readings, errors