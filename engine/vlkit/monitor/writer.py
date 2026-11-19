"""Build the versioned monitor payload and export its serving artifacts."""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from .. import fmt

_GRAIN = ["indicator_id", "period", "geo_type", "geo", "measure_type", "unit"]
_SCOPE = [column for column in _GRAIN if column != "period"]
_FACT_COLUMNS = [*_GRAIN, "value", "source_id"]
_QUESTIONS = {
    "public_finance": "Khâu nào đang chậm trong quá trình thu, chi và giải ngân?",
    "fdi": "Vốn đăng ký chuyển thành vốn thực hiện đến đâu và tập trung ở đâu?",
    "banking": "Tín dụng tăng nhanh hơn huy động đến đâu và ngân hàng nào có bộ đệm mỏng?",
    "capital_market": "Thanh khoản, khối ngoại, định giá và đòn bẩy đang thay đổi ra sao?",
    "real_estate": "Sức mua và nguồn cung thay đổi ra sao khi lãi suất biến động?",
}
_QUESTION = "Vốn của nền kinh tế đang kẹt ở đâu trên đường từ nguồn thu đến chi tiêu, đầu tư và tăng trưởng?"
_MISSING = "Chưa có đủ dữ liệu để đánh giá."


def _format_checker() -> FormatChecker:
    # Bare jsonschema installs omit the optional URI and date-time validators.
    checker = FormatChecker()
    if "uri" not in checker.checkers:
        @checker.checks("uri", raises=ValueError)
        def uri(value):
            if not isinstance(value, str):
                return True
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*", value):
                return False
            uri_parts = urlsplit(value)
            return not re.search(r"%(?![a-fA-F0-9]{2})", value) and (
                uri_parts.scheme not in {"http", "https"} or bool(uri_parts.hostname)
            )

    if "date-time" not in checker.checkers:
        @checker.checks("date-time", raises=ValueError)
        def date_time(value):
            if not isinstance(value, str):
                return True
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:[0-5]\d)", value.upper()):
                return False
            datetime.fromisoformat(value.upper())
            return True
    return checker


def _usable(observations: pd.DataFrame, *, include_imputed: bool) -> pd.DataFrame:
    facts = observations.reindex(columns=[*_FACT_COLUMNS, "published_date"]).copy()
    flags = ["is_invalid"] if include_imputed else ["is_invalid", "is_imputed"]
    rejected = observations.reindex(columns=flags).eq(True).any(axis=1)
    facts = facts.loc[~rejected].dropna(subset=["indicator_id", "period", "source_id"])
    facts["geo"] = facts["geo"].fillna("")
    facts["geo_type"] = facts["geo_type"].fillna("national")
    dates = pd.to_datetime(facts["published_date"], format="mixed", errors="coerce", utc=True)
    return facts.assign(published_date=dates).sort_values("published_date", kind="stable", na_position="first")


def reconcile(observations: pd.DataFrame, tolerances: dict[str, float] | None = None) -> list[dict]:
    """Compare readings at the same grain, keeping the latest single-source period per scope."""
    tolerances = tolerances or {}
    facts = _usable(observations, include_imputed=False).dropna(subset=["value"])
    facts = facts.loc[np.isfinite(facts["value"].astype(float))]
    facts = facts.drop_duplicates([*_GRAIN, "source_id"], keep="last")
    multi_source = facts.duplicated(_GRAIN, keep=False)
    single_source = facts.loc[~multi_source].sort_values("period", kind="stable")
    facts = pd.concat([facts.loc[multi_source], single_source.drop_duplicates(_SCOPE, keep="last")])
    rows = []
    for (indicator, period, geo_type, geo, measure, unit), group in facts.groupby(_GRAIN, sort=True):
        values = {source: float(value) for source, value in zip(group["source_id"], group["value"], strict=True)}
        largest = max(abs(value) for value in values.values())
        diff = (max(values.values()) - min(values.values())) / largest * 100 if largest else 0.0
        tolerance = tolerances.get(indicator, 1.0)
        verdict = "match" if diff <= tolerance else "mismatch"
        if len(values) == 1:
            verdict = "single_source"
        geography = geo or ("Toàn quốc" if geo_type == "national" else geo_type)
        rows.append({
            "indicator_id": indicator, "period": period, "values": values, "diff_pct": diff,
            "tolerance_pct": tolerance, "verdict": verdict, "note_vi": f"{geography} · {measure} · {unit}",
        })
    return rows


def _points(facts: pd.DataFrame) -> list[dict]:
    points = []
    for period, value, geo in facts[["period", "value", "geo"]].itertuples(index=False, name=None):
        point = {"period": period, "value": float(value) if pd.notna(value) else None}
        if geo:
            point["geo"] = geo
        points.append(point)
    return points


def _indicators(catalog, observations, sources, heatmap, indicator_fields):
    """Use a consistent source and measure within each served indicator."""
    grouped = dict(tuple(_usable(observations, include_imputed=True).groupby("indicator_id", sort=False)))
    sources_by_id = {source["id"]: source for source in sources}
    cells = {
        (row["indicator_id"], cell["period"]): cell["pctile"]
        for rows in heatmap.values() for row in rows for cell in row["cells"]
    }
    indicators, series = {}, {}
    for entry in catalog:
        indicator_id = entry["id"]
        facts = grouped.get(indicator_id, grouped.get(entry.get("base_id")))
        if facts is None:
            continue
        facts = facts.loc[facts["measure_type"].eq(entry["measure_type"]) & facts["unit"].eq(entry["unit"])]
        if facts.empty:
            continue
        source_id = entry["source_id"]
        if not facts["source_id"].eq(source_id).any():
            source_id = facts.sort_values("period", kind="stable")["source_id"].iloc[-1]
        source = sources_by_id[source_id]
        facts = facts.loc[facts["source_id"].eq(source_id)].drop_duplicates(_GRAIN, keep="last")
        facts = facts.sort_values(["period", "geo"], kind="stable")
        series[indicator_id] = _points(facts)
        summary = facts.loc[facts["geo_type"].eq("national")]
        if summary.empty:
            summary = facts.loc[facts["geo"].eq("VNM")]
        if summary.empty and facts["geo"].nunique() == 1:
            summary = facts
        sparkline = _points(summary.tail(24))
        latest = sparkline[-1] if sparkline else {"period": facts["period"].iloc[-1], "value": None}
        dates = facts.loc[facts["period"].eq(latest["period"]), "published_date"].dropna()
        last_updated = dates.max().date().isoformat() if not dates.empty else source["fetched_at"]
        indicators[indicator_id] = {
            **{key: value for key, value in entry.items() if key in indicator_fields},
            "source_id": source_id, "last_updated": last_updated,
            "next_release": entry.get("next_release", source.get("next_release")),
            "latest": latest, "sparkline": sparkline,
            "pctile_12m": cells.get((indicator_id, latest["period"])),
        }
    return indicators, series


def _number(value: float) -> str:
    """Preserve the observation's unit and format service prose in Vietnamese."""
    decimal = fmt.dec(abs(value), "vi")
    if "e" in decimal.lower():
        return fmt.dec(value, "vi")
    whole, _, fraction = decimal.partition(",")
    sign = "−" if value < 0 else ""
    fraction = fraction.rstrip("0")
    return sign + fmt.count(whole, "vi") + ("," + fraction if fraction else "")


def _headline(indicator) -> str:
    latest = indicator["latest"]
    unit = indicator["unit"]
    unit_suffix = unit if unit == "%" else f" {unit}" if unit else ""
    return f"{indicator['name_vi']} đạt {_number(latest['value'])}{unit_suffix} kỳ {latest['period']}."


def _charts(facts, tables, indicators, measured):
    table_by_id = {table["id"]: table for table in tables}
    results_by_chart = {}
    for result in facts:
        results_by_chart.setdefault(result["chart_id"], []).append(result)
    charts = {}
    for chart_id, results in results_by_chart.items():
        ids = dict.fromkeys(
            indicator for result in results
            for indicator in [*result.get("indicator_ids", []), result.get("indicator_id")]
            if indicator in indicators
        )
        table = table_by_id.get(chart_id)
        source_ids = [result["source_id"] for result in results]
        source_ids.extend(source_id for result in results for source_id in result.get("source_ids", []))
        if table:
            source_ids.extend(table["source_ids"])
        source_ids.extend(indicators[key]["source_id"] for key in ids)
        notes = dict.fromkeys(indicators[key]["note_vi"] for key in ids if indicators[key].get("note_vi"))
        charts[chart_id] = {
            "id": chart_id, "title_vi": results[0]["sentence_vi"],
            "kind": "table" if table else "heatmap" if chart_id == "monthly_heatmap" else "line",
            "indicator_ids": list(ids), "level": "overview", "source_ids": list(dict.fromkeys(source_ids)),
            "note_vi": " ".join(notes),
        }
    if not charts:
        for indicator in measured[:6]:
            key = indicator["id"]
            charts[key] = {
                "id": key, "kind": "line", "title_vi": _headline(indicator),
                "indicator_ids": [key], "source_ids": [indicator["source_id"]],
                "note_vi": indicator.get("note_vi", ""), "level": "overview",
            }
    return list(charts.values())


def _sections(evaluation, indicators, card_fields):
    results = evaluation["results"]
    sectors = {}
    for sector_id, question in _QUESTIONS.items():
        facts = [result for result in results if result["sector"] == sector_id and result["status"] != "not evaluated"]
        facts.sort(key=lambda result: result["status"] != "fired")
        missing = [
            result["sentence_vi"] for result in results
            if result["sector"] == sector_id and result["status"] == "not evaluated"
        ]
        measured = [
            indicator for indicator in indicators.values()
            if indicator["sector"] == sector_id and indicator["latest"]["value"] is not None
        ]
        tables = evaluation["tables"].get(sector_id, [])
        heatmap = evaluation["heatmap"].get(sector_id, [])
        cards = []
        for fact in facts[:3]:
            card = {key: value for key, value in fact.items() if key in card_fields}
            card["rule_id"] = fact["id"]
            if card.get("indicator_id") not in indicators:
                card.pop("indicator_id", None)
            cards.append(card)
        kpi_ids = dict.fromkeys([*(card.get("indicator_id") for card in cards), *(item["id"] for item in measured)])
        sectors[sector_id] = {
            "question_vi": question, "headline_vi": (
                cards[0]["sentence_vi"] if cards else _headline(measured[0]) if measured else _MISSING
            ),
            "cards": cards, "watch": missing[:4], "kpi_ids": [key for key in kpi_ids if key in indicators][:6],
            "charts": _charts(facts, tables, indicators, measured), "tables": tables, "heatmap": heatmap,
        }
    return sectors


def _recommendations(results):
    recommendations = {}
    for fact in results:
        if fact["status"] != "fired":
            continue
        key = fact["id"].lower().replace("-", "_")
        evidence = {"rule_id": fact["id"], "chart_id": fact["chart_id"], "fact_vi": fact["sentence_vi"]}
        if key in recommendations:
            recommendations[key]["evidence"].append(evidence)
            continue
        recommendations[key] = {
            "id": key, "title_vi": fact["sentence_vi"], "sector": fact["sector"],
            "evidence": [evidence], "so_what_vi": fact["so_what_vi"], "action_vi": fact["action_vi"],
            "agency_vi": fact["agency_vi"], "horizon_vi": fact.get("horizon_vi", "Quý tới"),
        }
    return list(recommendations.values())


def _md_table(headers, rows):
    def line(cells):
        fields = [str(cell).replace("|", r"\|").replace("\n", "<br>") if cell is not None else "—" for cell in cells]
        return "| " + " | ".join(fields) + " |"

    return "\n".join([line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)])


_DICTIONARY_LABELS = {
    "id": "Mã chỉ tiêu", "base_id": "Mã gốc", "name_vi": "Tên tiếng Việt", "name_en": "Tên tiếng Anh",
    "sector": "Lĩnh vực", "unit": "Đơn vị", "frequency": "Tần suất", "measure_type": "Loại phép đo",
    "definition_vi": "Định nghĩa", "note_vi": "Điều cần biết", "source_id": "Nguồn",
    "higher_is_better": "Giá trị cao hơn được ưu tiên", "tolerance_pct": "Dung sai đối chiếu (%)",
    "next_release": "Kỳ công bố kế tiếp",
}


def _dictionary(out, catalog):
    fields = list(dict.fromkeys(key for entry in catalog for key in entry))
    pd.DataFrame(catalog, columns=fields).to_csv(out / "data_dictionary.csv", index=False)
    table = _md_table(
        [_DICTIONARY_LABELS.get(key, key) for key in fields],
        ([entry.get(key) for key in fields] for entry in catalog),
    )
    (out / "data_dictionary.md").write_text(f"# Từ điển dữ liệu\n\n{table}\n", encoding="utf-8")


def _eda(profiles, reconciliation, results):
    parts = ["# Khám phá và đối chiếu dữ liệu"]
    for profile in profiles:
        counts = (
            ("Số dòng", profile["rows"]), ("Dòng trùng khóa theo thời gian", profile["duplicates"]),
            ("Kỳ thiếu trong chuỗi", profile["time_gap_count"]), ("Dòng ngoại lệ", profile["outliers"]),
        )
        parts += [
            f"## {profile['source_id']} · {profile['table']}",
            f"Khoảng quan sát từ {profile['date_from'] or '—'} đến {profile['date_to'] or '—'}.",
            _md_table(("Chỉ tiêu", "Số lượng"), ((key, fmt.count(value, "vi")) for key, value in counts)),
            _md_table(("Cột", "Kiểu dữ liệu", "Số giá trị thiếu"), (
                (column, dtype, fmt.count(profile["missing"].get(column), "vi"))
                for column, dtype in profile["columns"].items()
            )),
        ]
        if profile["correlations"]:
            parts.append(_md_table(("Cặp biến", "Tương quan"), (
                (key, fmt.fixed(value, 2, "vi") if value is not None else "—")
                for key, value in profile["correlations"].items()
            )))
    verdicts = {"match": "Khớp", "mismatch": "Lệch", "single_source": "Một nguồn"}
    parts += [
        "## Đối chiếu nguồn",
        "So sánh cùng chỉ tiêu, kỳ, địa bàn, kiểu đo và đơn vị, lấy bản công bố mới nhất của từng nguồn. "
        "Tỷ lệ chênh lệch bằng khoảng cách giữa giá trị lớn nhất và nhỏ nhất chia cho độ lớn tuyệt đối "
        "lớn nhất, nhân với 100. Hai giá trị bằng không có chênh lệch bằng không. "
        "Với các kỳ chỉ có một nguồn, bảng giữ kỳ gần nhất trong từng phạm vi đo.",
        _md_table(("Chỉ tiêu", "Kỳ", "Phạm vi đo", "Giá trị theo nguồn", "Lệch (%)", "Dung sai (%)", "Kết luận"), (
            (
                row["indicator_id"], row["period"], row["note_vi"],
                ", ".join(f"{source} = {_number(value)}" for source, value in row["values"].items()),
                fmt.fixed(row["diff_pct"], 2, "vi") if row["verdict"] != "single_source" else "—",
                fmt.fixed(row["tolerance_pct"], 2, "vi"), verdicts[row["verdict"]],
            )
            for row in reconciliation
        )),
    ]
    statuses = {"fired": "Kích hoạt", "evaluated": "Đã đánh giá", "not evaluated": "Chưa đánh giá"}
    parts += [
        "## Kết quả quy tắc",
        _md_table(("Quy tắc", "Trạng thái", "Kết quả"), (
            (result["id"], statuses[result["status"]], result["sentence_vi"]) for result in results
        )),
    ]
    return "\n\n".join(parts) + "\n"


def _json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Monitor payload contains {type(value).__name__}, which cannot be serialized to JSON")


def _validate_citations(payload, results):
    source_ids = {item["id"] for item in payload["sources"]}
    rule_ids = {item["id"] for item in payload["rules"]}
    for result in results:
        rule_id = result["id"]
        if rule_id not in rule_ids:
            raise ValidationError(f"Unknown rule in monitor results: {rule_id}")
        if result["status"] != "not evaluated":
            cited = {result["source_id"], *result.get("source_ids", [])}
            if unknown := cited - source_ids:
                raise ValidationError(f"Rule {rule_id} cites unregistered sources: {', '.join(sorted(unknown))}")


def write_monitor(
    out: Path,
    schema_path: Path,
    catalog: list[dict],
    sources: list[dict],
    observations: pd.DataFrame,
    evaluation: dict,
    model: dict,
    erd: str,
    views: dict[str, pd.DataFrame | Callable[[Path], None]],
) -> dict:
    """Validate before publishing any artifact. A view callback can export CSV with SQL COPY."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    all_observations = observations
    if evaluation["derived"]:
        all_observations = pd.concat([observations, pd.DataFrame(evaluation["derived"])], ignore_index=True)
    indicators, series = _indicators(
        catalog, all_observations, sources, evaluation["heatmap"],
        schema["properties"]["indicators"]["items"]["properties"],
    )
    sectors = _sections(evaluation, indicators, schema["$defs"]["card"]["properties"])
    recommendations = _recommendations(evaluation["results"])
    headlines = dict.fromkeys([
        *(item["title_vi"] for item in recommendations),
        *(sector["headline_vi"] for sector in sectors.values() if sector["headline_vi"] != _MISSING),
    ])
    tolerances = {entry["id"]: entry["tolerance_pct"] for entry in catalog if "tolerance_pct" in entry}
    reconciliation = reconcile(observations, tolerances)
    files = {
        "monitor": "monitor.json", "dictionary_csv": "data_dictionary.csv", "dictionary_md": "data_dictionary.md",
        "erd": "erd.mmd", "eda": "eda.md", **{name: f"csv/{name}.csv" for name in views},
    }
    payload = {
        "schema_version": 1,
        "meta": {
            "generated_at": datetime.now(ZoneInfo("Asia/Saigon")).isoformat(timespec="seconds"),
            "title_vi": "Theo dõi kinh tế vĩ mô và tài chính Việt Nam", "question_vi": _QUESTION,
            "lead_vi": list(headlines)[:3] or [_MISSING],
            "kpi_ids": list(dict.fromkeys(key for sector in sectors.values() for key in sector["kpi_ids"]))[:6],
            "watch_vi": [watch for sector in sectors.values() for watch in sector["watch"]][:4],
        },
        "sources": sources, "indicators": list(indicators.values()), "series": series,
        "sectors": sectors, "province": evaluation["province"], "asean": evaluation["asean"],
        "recommendations": recommendations, "rules": evaluation["rules"], "quality": model["quality"],
        "reconciliation": reconciliation, "model": {"erd_mermaid": erd, "tables": model["tables"]}, "files": files,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False, default=_json_scalar)
    payload = json.loads(encoded)
    validator = Draft202012Validator(schema, format_checker=_format_checker())
    validator.validate(payload)
    _validate_citations(payload, evaluation["results"])

    out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".monitor-", dir=out) as folder:
        stage = Path(folder)
        (stage / "csv").mkdir()
        for name, view in views.items():
            path = stage / files[name]
            if callable(view):
                view(path)
            else:
                view.to_csv(path, index=False)
            if not path.is_file():
                raise FileNotFoundError(f"Monitor view {name} did not produce its CSV")
        _dictionary(stage, catalog)
        (stage / files["erd"]).write_text(erd, encoding="utf-8")
        (stage / files["eda"]).write_text(_eda(model["profiles"], reconciliation, evaluation["results"]), encoding="utf-8")
        (stage / files["monitor"]).write_text(encoded + "\n", encoding="utf-8")
        for relative in [*(path for key, path in files.items() if key != "monitor"), files["monitor"]]:
            target = out / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            (stage / relative).replace(target)
    return payload
