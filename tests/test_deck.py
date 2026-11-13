"""T10 deck: DE slides (pipeline, data model, quality before/after, provenance, policy recommendation, limitations)
built from real flow outputs, and the text-fit / overflow guard (no LibreOffice needed)."""
import pytest

from test_pipeline_smoke import _messy_property_csv


@pytest.fixture(scope="module")
def deck(tmp_path_factory):
    from pptx import Presentation

    from vlkit import pipeline, report
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    from vlkit.de.warehouse import Warehouse

    tmp = tmp_path_factory.mktemp("deck")
    csv = _messy_property_csv(tmp / "tiny_bds.csv")
    wh = Warehouse(tmp / "wh.duckdb", lake=tmp / "lake")
    try:
        run_flow("deck_ds", [Source("tiny_bds", "file", str(csv))], out_root=tmp / "out", wh=wh)  # writes pipeline/quality/provenance
        out = tmp / "out" / "deck_ds"
        res = pipeline.run(wh.lake / "gold" / "obt_deck_ds.parquet", out_root=tmp / "res", name="deck_ds", reports=False, domain="property")
    finally:
        wh.close()
    de = report.load_de(out)
    path = report.build_deck(res, tmp, {}, de)
    return Presentation(path), path, de


def _slide_texts(prs):
    return [" | ".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame) for s in prs.slides]


def test_de_slides_present(deck):
    prs, _, de = deck
    assert de and de["provenance"] and de["quality_full"]
    texts = _slide_texts(prs)
    for kicker in ("DATA PIPELINE", "DATA MODEL", "DATA QUALITY", "POLICY RECOMMENDATION", "LIMITATIONS & NEXT STEPS", "DATA PROVENANCE"):
        assert any(t.startswith(kicker) for t in texts), kicker
    model = next(t for t in texts if t.startswith("DATA MODEL"))
    for m in ("ONE BIG TABLE", "STAR SCHEMA", "SNOWFLAKE", "DATA VAULT"):
        assert m in model


def test_numbers_come_from_flow(deck):
    prs, _, de = deck
    q = de["quality_full"][de["primary"]]
    tables = [[c.text for c in r.cells] for s in prs.slides for sh in s.shapes if getattr(sh, "has_table", False) and sh.has_table for r in sh.table.rows]
    score = next(r for r in tables if r[0].startswith("Quality score"))
    assert score[1:] == [str(q["score_before"]), str(q["score_after"])]
    dups = next(r for r in tables if r[0] == "Duplicate rows")
    assert dups[1] == f"{q['before']['duplicate_rows']:,}"
    prov = next(r for r in tables if r[0] == "tiny_bds")
    assert prov[2] == "tiny_bds.csv"  # never a local absolute path on a slide


def test_no_overflow(deck):
    from vlkit import report
    _, path, _ = deck
    assert report.deck_overflow(path) == []


def test_overflow_guard_detects_and_fit_prevents(tmp_path):
    from pptx import Presentation
    from pptx.util import Inches, Pt

    from vlkit import report
    long = "Một câu rất dài về ngân sách tỉnh và chi tiêu công " * 12
    prs = Presentation()
    tb = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(0.6))
    tb.text_frame.word_wrap = True
    tb.text_frame.paragraphs[0].text = long
    tb.text_frame.paragraphs[0].font.size = Pt(18)
    p = tmp_path / "bad.pptx"
    prs.save(p)
    assert report.deck_overflow(p)
    lines, size = report.fit_text([long, "dòng 2"], 3, 0.6, 18)
    assert size >= report.MIN_PT and lines and lines[-1].endswith("…")
    assert report.text_height_pt(lines, 3, size) <= (0.6 - report.INSET_H) * 72
    assert report.fit_text(["ngắn"], 3, 0.6, 18) == (["ngắn"], 18)


def test_short_uri_hides_paths():
    from vlkit.report import _short_uri, _when
    assert _short_uri("/home/user/secret/data.csv") == "data.csv"
    assert _short_uri("postgresql://u:***@db:5432/vl?sslmode=require") == "postgresql://…/vl"
    assert _short_uri("https://api.worldbank.org/v2/x?format=json") == "https://api.worldbank.org/v2/x"
    assert _when("Fri 2026-11-13 4:37 PM (UTC+07:00)") == "2026-11-13 16:37"
    assert _when("2026-11-13T16:37:56+07:00") == "2026-11-13 16:37"


def test_pitch_md_marp_storyline(deck, tmp_path):
    from vlkit import report
    _, _, de = deck
    res = {"meta": {"target": "price_per_m2", "rows": 2500, "columns": 9, "source_file": "x.csv"}, "caveats": ["c1", "c2"],
           "insights": [{"type": "segment_gap", "title_vi": "T1", "sentence_vi": "Câu 1 (n=567)", "test": "KW", "p_value": 0.0001},
                        {"type": "what_if", "title_vi": "W", "sentence_vi": "Nếu tăng 10%", "test": "Ridge", "p_value": None}],
           "recommendations": [{"now_what_vi": "Làm A", "so_what_vi": "Vì B", "impact_vi": "≈ +35,9%"}]}
    md = report.pitch_md(res, de)
    assert md.startswith("---\nmarp: true")
    assert "Từ 2.500 bản ghi" in md and "Câu 1 (n=567)" in md and "Làm A" in md and "Nếu tăng 10%" in md
    for t in ("0:00–0:45", "0:45–2:00", "2:00–4:00", "4:00–5:00", "5:00–5:45", "5:45–6:15", "6:15–7:00"):
        assert t in md
    q = de["quality"][de["primary"]]
    assert f"{q['score_before']} → {q['score_after']}" in md
