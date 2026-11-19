"""Map TinyFish/TinyFetch records to the W2-PRESS long contract (numbers, periods, evidence)."""
from __future__ import annotations

import csv
import re
from datetime import date

from unidecode import unidecode

from engine.vlkit.de.tinyfish import evidence_check
from engine.vlkit.vn import parse_vn_number

from .output import contract_row

_NUM = re.compile(r"[-+]?\d[\d.,]*")


def to_number(raw, decimal: str = ".") -> float | None:
    """Parse a number the way the source prints it (locale 'en'/'vn' or separator '.'/',')."""
    decimal = {"vn": ",", "en": "."}.get(decimal, decimal)
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None
    value, info = parse_vn_number(text, decimal)
    if value is None or info.get("unit") in ("ty", "trieu", "nghin"):
        # parse_vn_number multiplies units; a press value must stay in the printed scale
        match = _NUM.search(text)
        if match:
            value, _ = parse_vn_number(match.group(0), decimal)
    return value


def normalize_period(raw, default=None) -> str:
    text = str(raw or "").strip()
    if not text:
        return default or ""
    m = re.fullmatch(r"(\d{4})-Q([1-4])", text, re.I)
    if m:
        return f"{m.group(1)}-Q{m.group(2)}"
    if re.fullmatch(r"\d{4}-\d{2}", text) or re.fullmatch(r"\d{4}", text):
        return text
    m = re.search(r"Q([1-4])\s*[/\-]\s*(\d{4})", text, re.I)
    if m:
        return f"{m.group(2)}-Q{m.group(1)}"
    m = re.search(r"(?:tháng|thang)?\s*(\d{1,2})\s*(?:M|T|/)\s*[/\-]?\s*(\d{4})", text, re.I)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{4})", text)
    return m.group(1) if m else (default or "")


def normalize_date(raw) -> str:
    text = str(raw or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return text
    m = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", text)
    if m:
        day, month, year = (int(x) for x in m.groups())
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return ""
    return ""


def _line_at(text: str, pos: int, width: int = 400) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    end = len(text) if end < 0 else end
    if pos - start >= width:
        start = max(start, pos - width // 2)
    return text[start:min(end, start + width)].strip()


def find_snippet(text: str | None, value) -> str:
    """First source line that prints ``value`` (tries VN and EN separators)."""
    if not text or value is None or not evidence_check([abs(float(value))], text)["0"]:
        return ""
    target = float(value)
    for match in _NUM.finditer(text.replace("−", "-")):
        token = match.group().rstrip(".,")
        for decimal in (",", "."):
            parsed, _ = parse_vn_number(token, decimal)
            if parsed is None:
                continue
            prefix = text[max(0, match.start() - 80):match.start()]
            if parsed >= 0 and re.search(r"\b(?:giảm|down|fell|declined)\s+(?:\*\*)?$", prefix, re.I):
                parsed = -parsed
            if abs(parsed - target) <= max(0.0005, abs(target) * 1e-6):
                return _line_at(text, match.start())
    return ""


def _record_rows(record: dict, specs, target: dict, text: str, geo: str, url: str) -> list[dict]:
    rows = []
    for spec in specs or []:
        raw = record.get(spec["field"])
        if raw is None:
            continue
        value = to_number(raw, target.get("decimal", "."))
        if value is None:
            continue
        period = spec.get("period") or target.get("period")
        evidence = find_snippet(text, value)
        ok = bool(evidence)
        if not evidence and record.get("evidence"):
            evidence = str(record["evidence"])[:400]
        published = target.get("published_date", "")
        if target.get("published_date_field"):
            published = normalize_date(record.get(target["published_date_field"])) or published
        indicator_id = spec["indicator_id"]
        slug = record.get(spec.get("slug_field") or "")
        if slug:
            indicator_id += "_" + re.sub(r"[^a-z0-9]+", "_", unidecode(str(slug)).lower()).strip("_")
        rows.append(contract_row(
            indicator_id=indicator_id, period=normalize_period(period, target.get("period")),
            measure_type=spec.get("measure_type", "level"), value=value, unit=spec.get("unit", ""),
            geo=spec.get("geo") or geo, source_id=target["source_id"], source_url=url,
            published_date=published, evidence=evidence, evidence_ok=ok,
            method=target.get("method", "tinyfish"),
        ))
    return rows


def rows_from_mof_appendix(transcript: str, target: dict) -> list[dict]:
    """Read visually reviewed cells from Appendix Ia of the image-only MOF report."""
    rows = []
    for record in csv.DictReader(transcript.splitlines(), delimiter="\t"):
        for field, measure, unit in (("amount", "level", "triệu đồng"), ("pct_plan", "pct_plan", "%")):
            cell = record[field]
            value = to_number(cell, "vn")
            if value is None:
                continue
            rows.append(contract_row(
                indicator_id=f"dtc_{record['scope']}_disbursed", period=target["period"],
                measure_type=measure, value=value, unit=unit, geo=record["geo"],
                source_id=target["source_id"], source_url=f"{target['url']}#page={record['page']}",
                published_date=target["published_date"], evidence=cell,
                evidence_ok=evidence_check([value], cell)["0"], method="pdf",
            ))
    return rows


def rows_from_text(text: str, target: dict) -> list[dict]:
    """Extra rows taken from the saved page text with a regex recipe (``text_fields`` in targets.yaml)."""
    rows = []
    for spec in target.get("text_fields") or []:
        match = re.search(spec["pattern"], text or "", re.S)
        if not match:
            continue
        value = to_number(match.group(spec.get("group", 1)), target.get("decimal", "."))
        if value is None:
            continue
        evidence = _line_at(text, match.start(spec.get("group", 1)))
        rows.append(contract_row(
            indicator_id=spec["indicator_id"], period=normalize_period(spec.get("period") or target.get("period"),
                                                                      target.get("period")),
            measure_type=spec.get("measure_type", "level"), value=value, unit=spec.get("unit", ""),
            geo=spec.get("geo", target.get("geo", "VNM")), source_id=target["source_id"],
            source_url=target["url"], published_date=target.get("published_date", ""),
            evidence=evidence, evidence_ok=bool(evidence), method=target.get("method", "tinyfish"),
        ))
    if target.get("segment_table") == "cbre_realtique":
        rows += realtique_segment_rows(text, target)
    return rows


def realtique_segment_rows(text: str, target: dict) -> list[dict]:
    metrics = {
        "Nguồn cung mới": ("new_supply", "can"), "Số căn bán được": ("absorption", "can"),
        "Giá sơ cấp": ("primary_price", "tr_vnd_m2"),
        "Giá thứ cấp (giá chào)": ("secondary_price", "tr_vnd_m2"),
    }
    columns = []
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            columns = []
            continue
        label, *cells = (cell.strip() for cell in line.strip("|").split("|"))
        if label == "Quý 3/2026":
            columns = [re.fullmatch(r"(Căn hộ|Liền thổ) (Hà Nội|TP\.HCM)(?:\\\*)*", cell) for cell in cells]
            continue
        if label not in metrics:
            continue
        metric, unit = metrics[label]
        for column, cell in zip(columns, cells):
            if column is None:
                continue
            segment, city = column.groups()
            tokens = _NUM.findall(cell.replace("−", "-"))
            if len(tokens) < 2:
                continue
            prefix = "apartment" if segment == "Căn hộ" else "landed_home"
            for measure, token, row_unit in (("level", tokens[0], unit), ("yoy", tokens[-1], "%")):
                value = to_number(token, "vn")
                rows.append(contract_row(
                    indicator_id=f"{prefix}_{metric}", period=target["period"], measure_type=measure,
                    value=value, unit=row_unit, geo=city, source_id=target["source_id"],
                    source_url=target["url"], published_date=target.get("published_date", ""),
                    evidence=cell, evidence_ok=evidence_check([abs(value)], cell)["0"], method="tinyfetch",
                ))
    return rows


def rows_from_records(records, target: dict, text: str = "") -> list[dict]:
    """Contract rows from TinyFish records using the ``fields`` / ``lists`` recipe in targets.yaml."""
    rows: list[dict] = []
    records = records or []
    flat = records[0] if len(records) == 1 and isinstance(records[0], dict) else None
    base_records = records
    if flat is not None and target.get("record_list_field"):
        date_field = target.get("published_date_field")
        base_records = []
        for item in flat.get(target["record_list_field"]) or []:
            if isinstance(item, dict):
                item = dict(item)
                if date_field:
                    item.setdefault(date_field, flat.get(date_field))
                base_records.append(item)
    geo_default = target.get("geo", "VNM")
    page_url = ""
    if flat is not None:
        page_url = str(flat.get("source_page_url") or "")
    url = page_url or target["url"]
    for record in base_records:
        geo = record.get(target.get("geo_field") or "", geo_default) or geo_default
        rows += _record_rows(record, target.get("fields"), target, text, geo, url)
    if flat is not None:
        for block in target.get("lists") or []:
            geo_field = block.get("geo_field")
            for item in flat.get(block.get("list_field")) or []:
                if not isinstance(item, dict):
                    continue
                item = dict(item)
                date_field = target.get("published_date_field")
                if date_field and date_field not in item:
                    item[date_field] = flat.get(date_field)
                geo = item.get(geo_field or "", geo_default) or geo_default
                rows += _record_rows(item, block.get("fields"), target, text, geo, url)
    return rows
