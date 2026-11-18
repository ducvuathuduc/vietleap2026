"""Dataset documentation built from warehouse metadata and the analysed profile."""
from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path

from .. import fmt
from ..vn import ascii_key
from .warehouse import Warehouse, ident

DICTIONARY_CSV = "data_dictionary.csv"
DICTIONARY_MD = "data_dictionary.md"
EDA_MD = "eda.md"
FIELDS = ("gold_table", "column", "type", "description", "unit", "source", "missing_pct", "sample")


def _usd(v: float) -> str:
    """4,716.66 → '4.716,66' (Vietnamese thousands '.' and decimal ',')."""
    return f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _cell(value: object) -> str:
    raw = "—" if value is None or value == "" else str(value)
    return html.escape(" ".join(raw.splitlines())).replace("\\", "\\\\").replace("|", r"\|").replace("[", r"\[")


def _csv_cell(value: object) -> object:
    if isinstance(value, str) and (value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@"))):
        return "'" + value
    return value


def _row(values) -> str:
    return "| " + " | ".join(_cell(value) for value in values) + " |"


def _origins(table: str, upstream: dict[str, set[str]]) -> set[str]:
    pending, seen = [table], set()
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node)
            pending.extend(upstream[node])
    return {node.removeprefix("source:") for node in seen if node.startswith("source:")}


def write_dictionary(wh: Warehouse, summary: dict, graph: dict, out: Path) -> None:
    upstream = defaultdict(set)
    source_columns = defaultdict(set)
    for edge in graph["edges"]:
        upstream[edge["to"]].add(edge["from"])
        if edge["to"] in summary["bronze"] and edge["from"].startswith("source:"):
            source = edge["from"].removeprefix("source:")
            source_columns[source].update(ascii_key(c["name"]) for c in wh.columns(edge["to"]))
    provenance = {source["source"]: source for source in summary["provenance"]}
    rows = []
    for table in [*summary["gold"], *summary.get("views", [])]:
        columns = wh.columns(table)
        layer, name = table.split(".", 1)
        aggregates = ["count(*)"]
        for column in columns:
            expr = ident(column["name"])
            aggregates += [f"count({expr})", f"min(substr(cast({expr} AS VARCHAR), 1, 160))"]
        total, *stats = wh.con.execute(f"SELECT {', '.join(aggregates)} FROM {layer}.{ident(name)}").fetchone()
        origins = _origins(table, upstream) or set(provenance)
        metadata, sources = {}, {}
        for origin in sorted(origins & provenance.keys()):
            record = provenance[origin]
            options = record.get("options", {})
            metadata.update(options.get("column_metadata", {}))
            urls = options.get("origins") or [options.get("origin") or record["uri"]]
            sources[origin] = urls
        for index, column in enumerate(columns):
            present, sample = stats[2 * index:2 * index + 2]
            field = column["name"]
            prefix, separator, suffix = field.partition("__")
            detail = metadata.get(field, metadata.get(suffix, {}) if separator else {})
            owners = [origin for origin in sources if ascii_key(field) in source_columns[origin]
                      or (separator and ascii_key(origin) == ascii_key(prefix) and ascii_key(suffix) in source_columns[origin])]
            urls = ", ".join(dict.fromkeys(url for origin in (owners or sources) for url in sources[origin]))
            provenance_text = urls if owners else f"Dẫn xuất từ {urls}" if urls else ""
            missing = round(100 * (total - present) / total, 4) if total else None
            rows.append((table, field, column["type"], detail.get("description"), detail.get("unit"), provenance_text, missing, sample))

    with (out / DICTIONARY_CSV).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        writer.writerows(tuple(map(_csv_cell, row)) for row in rows)
    labels = ("Bảng gold", "Cột", "Kiểu DuckDB", "Mô tả", "Đơn vị", "Nguồn", "% thiếu", "Giá trị mẫu")
    lines = [f"# Từ điển dữ liệu · {_cell(summary['dataset'])}", "", _row(labels), _row(["---"] * len(labels))]
    lines.extend(_row(row) for row in rows)
    (out / DICTIONARY_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_eda(results: dict, out: Path) -> str:
    profile = results["profile"]
    meta = results["meta"]
    lines = [f"# Phân tích khám phá · {_cell(meta['name'])}", "",
             f"Biến mục tiêu **{_cell(meta['target'])}** · {fmt.count(profile['rows'], 'vi')} dòng · "
             f"{fmt.count(profile['columns'], 'vi')} cột · {fmt.dec(profile['missing_overall_pct'], 'vi')}% ô thiếu · "
             f"{fmt.dec(profile['outlier_rows_pct'], 'vi')}% dòng gắn cờ ngoại lệ.", "",
             "## Hồ sơ cột", "", _row(("Cột", "Kiểu", "% thiếu", "Duy nhất", "Nhỏ nhất", "Trung vị", "Lớn nhất", "Ngoại lệ")),
             _row(["---"] * 8)]
    for column in profile["column_profiles"]:
        lines.append(_row((column.get(key) for key in ("name", "dtype", "missing_pct", "unique", "min", "median", "max", "outliers"))))
    points = (results.get("timeseries") or {}).get("points") or []
    if points:
        lines += ["", "## Phạm vi thời gian", "", f"{_cell(points[0]['period'])} → {_cell(points[-1]['period'])} · {len(points)} kỳ có quan sát."]
    lines += ["", "## Chất lượng", ""]
    lines.extend(f"- **{_cell(issue['column'])}** · {_cell(issue.get('issue_vi') or issue['issue'])}" for issue in profile["issues"])
    lines += ["", "## Bằng chứng", ""]
    for insight in results["insights"]:
        stats = f" · {fmt.p(insight['p_value'], 'vi')}" if insight["p_value"] is not None else ""
        lines.append(f"- {_cell(insight['sentence_vi'])} ({_cell(insight['test'])}{stats})")
    lines += ["", "## Hạn chế", "", *(f"- {_cell(text)}" for text in results["caveats_vi"])]
    qs = results.get("quality_summary") or {}
    if qs.get("bronze_rows") is not None and qs.get("silver_rows") is not None:
        dup = qs.get("duplicate_rows")
        dup_txt = (f" (loại {fmt.count(dup, 'vi')} dòng trùng hoàn toàn, giữ bản ghi mới nhất)"
                   if isinstance(dup, (int, float)) and dup else "")
        score_txt = ""
        if qs.get("score_before") is not None and qs.get("score_after") is not None:
            score_txt = f" · điểm chất lượng {fmt.dec(qs['score_before'], 'vi')} → {fmt.dec(qs['score_after'], 'vi')}"
        lines += ["", "## Dòng dữ liệu", "",
                  f"Bronze {fmt.count(qs['bronze_rows'], 'vi')} dòng → Silver {fmt.count(qs['silver_rows'], 'vi')} dòng"
                  f"{dup_txt}{score_txt}."]
    lines += ["", "## Ghi chú phương pháp (cho giám khảo)", "",
              "- **Làm sạch:** giá trị thiếu được giữ nguyên (NaN) trừ khi chạy với `--impute interpolate` — khi đó thiếu được nội suy tuyến tính theo thời gian trong từng ticker, kèm cột cờ `__imputed`. Khử trùng lặp giữ bản ghi mới nhất (`keep='last'`): khử dòng trùng hoàn toàn, rồi khử theo khóa suy đoán tối đa 2 cột (recipe có thể chỉ định khóa khác). Giá trị ngoại lệ chỉ gắn cờ, không xóa.",
              "- **Phục vụ (serving):** mỗi lần chạy xây cả OBT và star schema; dashboard đọc OBT (một bảng phẳng, nhanh) còn star schema là mô hình trình bày và phân tích."]
    v = results.get("validation") or {}
    if v.get("status"):
        lines += ["", "## Kiểm chứng độc lập", ""]
        if v["status"] == "match":
            lines.append(f"- GDP bình quân đầu người Việt Nam {v['year']}: kho {_usd(v['warehouse_value'])} USD so với API World Bank trực tiếp ({v['indicator']}) {_usd(v['live_value'])} USD — chênh {fmt.pct(v['diff_pct'], 'vi')} (kiểm chứng {v['checked_at']}, nguồn {v['source']}).")
        elif v["status"] == "mismatch":
            lines.append(f"- **LỆCH:** GDP bình quân đầu người Việt Nam {v['year']}: kho {_usd(v['warehouse_value'])} USD nhưng API World Bank trực tiếp ({v['indicator']}) trả {_usd(v['live_value'])} USD — chênh {fmt.pct(v['diff_pct'], 'vi')} (kiểm chứng {v['checked_at']}, nguồn {v['source']}). Cần kiểm tra lại trước khi dùng số này.")
        else:
            lines.append(f"- Chưa kiểm chứng được với API World Bank ({v['indicator']}): {v.get('reason', 'không rõ lý do')} — giá trị trong kho: {_usd(v['warehouse_value'])} USD (kiểm chứng {v['checked_at']}).")
    (out / EDA_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return EDA_MD
