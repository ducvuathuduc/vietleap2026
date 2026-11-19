import json
import re
from collections import Counter
from pathlib import Path

import pytest
from pptx import Presentation

from vlkit import fmt


FIXTURE = Path(__file__).parent / "fixtures" / "vn_monitor" / "deck_payload.json"
NUMBER = re.compile(r"(?<!\w)[−-]?\d+(?:[.,]\d+)*(?!\w)")
BANNED = re.compile(
    r"\b(?:toàn diện|đột phá|mạnh mẽ|vượt trội|tối ưu hoá|hệ sinh thái|nâng tầm|khai phá|đòn bẩy|"
    r"chuyển đổi số|kỷ nguyên|bức tranh toàn cảnh|điểm sáng|đáng chú ý|nhìn chung|về cơ bản|có thể nói rằng|"
    r"dữ liệu cho thấy|góc nhìn|câu chuyện|hành trình|sức mạnh|theo dõi sát sao|unlock|unleash|seamless|"
    r"powerful|effortless|supercharge|elevate|empower|revolutionize|cutting-edge|world-class|robust|"
    r"leverage|delve|underscore|showcase|intricate|tapestry|landscape|one-stop|end-to-end|insights-driven|"
    r"powered by ai|ai|engine|pipeline|beta|live|chính xác 100%|thời gian thực|đảm bảo|dự báo chắc chắn|"
    r"tối ưu nhất|dẫn đầu)\b|[!★\U0001F000-\U0001FAFF\u2600-\u27BF]|\b\d{4}-(?:Q[1-4]|\d{2}(?:-\d{2})?)\b",
    re.I,
)


def numeric_strings(payload):
    def walk(item):
        if isinstance(item, dict):
            for value in item.values():
                yield from walk(value)
        elif isinstance(item, list):
            for value in item:
                yield from walk(value)
        else:
            yield item

    facts = list(walk(payload))
    sources = payload["sources"]
    for method in {source["method"] for source in sources} | {"file"}:
        group = [s for s in sources if s["method"] == method or method == "file" and s["method"] == "pdf"]
        facts.extend([len(group), sum(s.get("rows", 0) for s in group)])
    facts.extend(Counter(r["verdict"] for r in payload["reconciliation"]).values())
    for layer in ("bronze", "silver", "gold"):
        facts.append(sum(t["rows"] for t in payload["model"]["tables"] if t["layer"] == layer))
    tokens = set()
    for fact in facts:
        if isinstance(fact, str):
            literal = NUMBER.findall(fact.replace("−", "-"))
            tokens.update(literal)
            tokens.update(token.translate(str.maketrans(",.", ".,")) for token in literal)
            tokens.update(re.findall(r"\d+", fact))
        elif type(fact) in (int, float):
            for lang in ("vi", "en"):
                for digits in range(4):
                    tokens.update(fmt.fixed(value, digits, lang) for value in (fact, abs(fact)))
                    for value in (fact, abs(fact)):
                        grouped = f"{value:,.{digits}f}"
                        tokens.add(grouped.translate(str.maketrans(",.", ".,")) if lang == "vi" else grouped)
    return tokens


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    from vlkit.monitor.deck import build_deliverables

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = tmp_path_factory.mktemp("monitor-deck")
    files = build_deliverables(payload, out, pdf=False)
    return payload, out, files


@pytest.mark.parametrize("lang", ["vi", "en"])
def test_deck_has_sourced_sector_charts_and_notes(package, lang):
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    payload, out, files = package
    deck = Presentation(out / files[f"deck_{lang}"])
    assert len(deck.slides) == 13
    titles = [slide.shapes[0].text for slide in deck.slides]
    assert len(set(titles)) == len(titles)
    assert (titles[0] == payload["meta"]["title_vi"]) is (lang == "vi")
    supported = numeric_strings(payload)
    for i, slide in enumerate(deck.slides):
        notes = slide.notes_slide.notes_text_frame.text
        assert len(notes.split()) >= 35
        visible = "\n".join(shape.text for shape in slide.shapes if shape.has_text_frame)
        assert not BANNED.search(visible + "\n" + notes)
        assert set(NUMBER.findall(visible.replace("−", "-"))) <= supported
        if 4 <= i <= 8:
            assert sum(shape.shape_type == MSO_SHAPE_TYPE.PICTURE for shape in slide.shapes) == 1
            assert ("Nguồn" if lang == "vi" else "Source") in visible
        if i == 10:
            links = [shape.click_action.target_slide.slide_id for shape in slide.shapes
                     if shape.click_action.target_slide is not None]
            assert links == [deck.slides[index].slide_id for index in (4, 5, 6)]


def test_executive_report_lists_figures_and_source_links(package):
    payload, out, files = package
    report = (out / files["report_vi"]).read_text(encoding="utf-8")
    sections = ["Có gì mới", "Cần theo dõi", "Các hình", "Khuyến nghị", "Nguồn"]
    offsets = [report.index(f"## {section}") for section in sections]
    assert offsets == sorted(offsets)
    assert "Hình 1" in report and payload["sources"][0]["url"] in report


@pytest.mark.parametrize("lang", ["vi", "en"])
def test_deck_text_fits_published_boxes(package, lang):
    from vlkit.report import deck_overflow

    _, out, files = package
    assert deck_overflow(out / files[f"deck_{lang}"]) == []


def test_disbursement_groups_use_latest_common_source_and_keep_ties_together():
    import pandas as pd
    from vlkit.monitor.rules import evaluate

    rows = [{"indicator_id": "dtc_province_disbursed", "period": "2026-10", "measure_type": "pct_plan",
             "source_id": "ministry", "geo_type": "province", "unit": "%", "geo": province, "value": value}
            for province, value in [("an_giang", 40), ("ha_noi", 80), ("bac_ninh", 80)]]
    rows.append({**rows[0], "geo": "quang_ninh", "source_id": "press", "value": 20})
    result = evaluate({"observations": pd.DataFrame(rows)}, [])
    table, = [t for t in result["tables"]["public_finance"] if t["id"] == "province_disbursement"]
    assert table["source_ids"] == ["ministry"]
    assert sum(r["count"] for r in table["rows"]) == 3
    assert max(r["count"] for r in table["rows"]) == 2
