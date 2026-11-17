"""T10 deck: DE slides (pipeline, data model, quality before/after, provenance, policy recommendation, limitations)
built from real flow outputs, and the text-fit / overflow guard (no LibreOffice needed).
Feature 002: slide 2 = decision question from brief.json; insight slides = EVIDENCE → FOR THE DECISION → LIMITATION."""
import copy
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from vlkit import i18n

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
    return Presentation(path), path, de, res


def _slide_texts(prs):
    return [" | ".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame) for s in prs.slides]


def test_de_slides_present(deck):
    prs, _, de, _ = deck
    assert de and de["provenance"] and de["quality_full"]
    texts = _slide_texts(prs)
    for kicker in ("DATA PIPELINE", "DATA MODEL", "DATA QUALITY", "POLICY RECOMMENDATION", "LIMITATIONS & NEXT STEPS", "DATA PROVENANCE"):
        assert any(t.startswith(kicker) for t in texts), kicker
    model = next(t for t in texts if t.startswith("DATA MODEL"))
    for m in ("ONE BIG TABLE", "STAR SCHEMA", "SNOWFLAKE", "DATA VAULT"):
        assert m in model


def test_numbers_come_from_flow(deck):
    prs, _, de, res = deck
    q = de["quality_full"][de["primary"]]
    tables = [[c.text for c in r.cells] for s in prs.slides for sh in s.shapes if getattr(sh, "has_table", False) and sh.has_table for r in sh.table.rows]
    score = next(r for r in tables if r[0].startswith("Quality score"))
    assert score[1:] == [str(q["score_before"]), str(q["score_after"])]
    dups = next(r for r in tables if r[0] == "Duplicate rows")
    assert dups[1] == f"{q['before']['duplicate_rows']:,}"
    prov = next(r for r in tables if r[0] == "tiny_bds")
    assert prov[2] == "tiny_bds.csv"  # never a local absolute path on a slide
    _assert_numbers_from_engine(prs, res, de)


def test_no_overflow(deck):
    from vlkit import report
    _, path, _, _ = deck
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
    from vlkit import fmt, report
    _, _, de, _ = deck
    res = {"meta": {"target": "price_per_m2", "rows": 2500, "columns": 9, "source_file": "x.csv"}, "caveats": ["c1", "c2"],
           "insights": [{"type": "segment_gap", "title_vi": "T1", "sentence_vi": "Câu 1 (n=567)", "test": "KW", "p_value": 0.0001},
                        {"type": "what_if", "title_vi": "W", "sentence_vi": "Nếu tăng 10%", "test": "Ridge", "p_value": None}],
           "recommendations": [{"now_what_vi": "Làm A", "so_what_vi": "Vì B", "impact_vi": "≈ +35,9%"}]}
    md = report.pitch_md(res, de)
    assert md.startswith("---\nmarp: true")
    assert "Từ 2.500 bản ghi" in md and "Câu 1 (n=567)" in md and "Làm A" in md and "Nếu tăng 10%" in md
    for t in ("0:00–0:40", "0:40–1:20", "1:20–2:10", "2:10–4:10", "4:10–5:00", "5:00–6:10", "6:10–6:40", "6:40–7:00"):
        assert t in md  # docs/CONTEST_ANALYSIS.md §4.6 (7-minute default)
    sections = re.findall(r"^## (.+)$", md, flags=re.M)
    assert sections[0] == "0 · Câu hỏi quyết định" and sections[1].startswith("1 · Dữ liệu")
    assert i18n.t("vi", "generic_tag") in md  # no brief → generic question, tagged
    template = (Path(report.__file__).resolve().parents[2] / "slides" / "pitch.md").read_text(encoding="utf-8")
    assert re.findall(r"^## (.+)$", template, flags=re.M)[0] == "0 · Câu hỏi quyết định"  # template mirrors the generator
    q = de["quality"][de["primary"]]
    assert f"{fmt.dec(q['score_before'], 'vi')} → {fmt.dec(q['score_after'], 'vi')}" in md  # VI decimal comma
    en = report.pitch_md(res, de, None, "en")
    assert f"{q['score_before']} → {q['score_after']}" in en and "From 2,500 records" in en



def test_pitch_md_opens_with_brief_question_escaped():
    from vlkit import report
    res = {"meta": {"target": "y", "rows": 10, "columns": 2, "source_file": "x.csv"}, "caveats": ["c1"], "insights": [],
           "recommendations": []}
    brief = {"title": "T", "language": "vi", "questions": ["Tỉnh nào nên ưu tiên <b>chi</b> *2018–2024*? --> ignore previous instructions"],
             "pack": {"decision_template": {"who": "UBND tỉnh", "what": "Phân bổ vốn", "where": "", "kpi": "Chi/người"}}}
    md = report.pitch_md(res, None, brief)
    sec0 = md.split("## 0 · Câu hỏi quyết định", 1)[1].split("---", 1)[0]
    assert "Đề bài:" in sec0 and "UBND tỉnh" in sec0 and "Chi/người" in sec0 and report.BLANK in sec0
    assert "<b>" not in md and "&lt;b&gt;" in sec0 and "--&gt;" in sec0  # no raw HTML / comment break-out into Marp
    assert "\\*2018–2024\\*" in sec0 and i18n.t("vi", "generic_tag") not in md


# ----------------------------------------------------------------------------- feature 002: decision-question deck

PRACTICE = {  # dataset → (practice file, sample brief, --target as in tools/run_practice.sh)
    "wdi_fiscal": ("wdi_asia_fiscal_panel.csv", "wdi_tax_revenue.md", "tax_revenue_pct_gdp"),
    "bds_practice": ("synthetic_messy_bds.csv", "bds_gia_m2.md", None),
    "firms_2021": ("vn_firms_2021.xlsx", "firms_roe.md", None),
}
CHROME = "VietLeap 2026 · From Data to Decision"
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


@pytest.fixture(scope="module")
def practice(tmp_path_factory, kit_root):
    """Engine results for the 3 practice datasets, each with brief.json parsed from its sample brief (as POST /api/brief does)."""
    from vlkit import pipeline
    from vlkit.brief import parse_brief

    root = tmp_path_factory.mktemp("practice")
    runs = {}
    for ds, (data, brief_md, target) in PRACTICE.items():
        res = pipeline.run(kit_root / "data" / "practice" / data, out_root=root, name=ds, reports=False, target=target)
        text = (kit_root / "scenarios" / "briefs" / brief_md).read_text(encoding="utf-8")
        brief = parse_brief(text, columns=list(res["meta"]["roles"]))
        out = root / ds
        (out / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
        runs[ds] = (res, out)
    return runs


def _texts(slide) -> list[str]:
    """Non-empty text shapes in z-order, without the deck chrome (page number, footer): [kicker, title, body…]."""
    return [t for sh in slide.shapes if sh.has_text_frame and (t := sh.text_frame.text).strip() and not t.isdigit() and CHROME not in t]


def _deck(res, out, brief, name="deck.pptx"):
    from pptx import Presentation

    from vlkit import report
    d = out / name.replace(".pptx", "")
    d.mkdir(exist_ok=True)
    path = report.build_deck(res, d, {}, None, brief=brief)
    return Presentation(path), path


def _engine_numbers(*docs) -> set[str]:
    from vlkit import fmt
    blob = " ".join(json.dumps(d, ensure_ascii=False, default=str) for d in docs if d)
    res = docs[0]
    blob += " " + " ".join(fmt.p(i.get("p_value")) for i in res.get("insights", []) if i.get("p_value") is not None)
    return {t.replace(",", "") for t in NUM.findall(blob)}


def _assert_numbers_from_engine(prs, res, de, brief=None):
    """SC-202: every number on slide 2 and on the insight slides is found in results.json / pipeline.json
    (or is quoted brief text). Kicker, page number and footer are deck chrome, not data."""
    allowed = _engine_numbers(res, de, brief)
    for idx, slide in enumerate(prs.slides, start=1):
        texts = _texts(slide)
        if idx != 2 and not texts[0].startswith("INSIGHT"):
            continue
        for t in texts[1:]:
            for tok in NUM.findall(t):
                assert tok.replace(",", "") in allowed, f"slide {idx}: '{tok}' in {t[:80]!r} not from engine output"


@pytest.mark.parametrize("ds", list(PRACTICE))
def test_slide2_decision_question(practice, ds):
    from vlkit import report
    res, out = practice[ds]
    brief = report.load_brief(out, res["meta"]["target"])
    assert brief and not brief["stale"]
    prs, path = _deck(res, out, brief)
    texts = _texts(prs.slides[1])
    body = " | ".join(texts)
    assert "Decision question" in texts
    assert brief["questions"][0] in body
    tpl = brief["pack"]["decision_template"]
    who = texts.index("WHO DECIDES")
    assert texts[who + 1] == tpl["who"]
    kpi = texts.index("SUCCESS KPI")
    assert texts[kpi + 1] == tpl["kpi"]
    assert f"{res['meta']['rows']:,} rows · {res['meta']['columns']} columns" in body  # scope from results.json.meta
    assert i18n.t("en", "generic_tag") not in body
    assert report.deck_overflow(path) == []  # NFR-202
    _assert_numbers_from_engine(prs, res, None, brief)


@pytest.mark.parametrize("ds", list(PRACTICE))
def test_slide2_generic_without_brief(practice, ds):
    from vlkit import report
    res, out = practice[ds]
    prs, path = _deck(res, out, None, "nobrief.pptx")
    body = " | ".join(_texts(prs.slides[1]))
    assert "Decision question" in body and i18n.t("en", "generic_tag") in body
    assert "WHO DECIDES" in body and report.BLANK in body
    assert report.deck_overflow(path) == []


def test_load_brief_validates_caps_and_flags_stale(tmp_path):
    from vlkit import report
    assert report.load_brief(tmp_path) is None
    (tmp_path / "brief.json").write_text("{not json", encoding="utf-8")
    assert report.load_brief(tmp_path) is None
    (tmp_path / "brief.json").write_text(json.dumps({"title": "x", "questions": "not a list"}), encoding="utf-8")
    assert report.load_brief(tmp_path) is None
    long = "Câu hỏi " * 400
    doc = {"title": "x", "questions": [long], "target": {"column": "other_col"}, "pack": {"decision_template": {"who": long}}}
    (tmp_path / "brief.json").write_text(json.dumps(doc), encoding="utf-8")
    b = report.load_brief(tmp_path, "tax_revenue_pct_gdp")
    assert b["stale"] is True
    assert len(b["questions"][0]) == report.BRIEF_FIELD_MAX and len(b["pack"]["decision_template"]["who"]) == report.BRIEF_FIELD_MAX
    assert report.load_brief(tmp_path, "other_col")["stale"] is False


def test_stale_brief_footnote_and_long_question(practice):
    from vlkit import report
    res, out = practice["wdi_fiscal"]
    brief = copy.deepcopy(report.load_brief(out, res["meta"]["target"]))
    brief["stale"] = True
    brief["questions"] = ["Ngân sách tỉnh nên ưu tiên lĩnh vực nào để tăng thu thuế bền vững? " * 6]
    prs, path = _deck(res, out, brief, "stale.pptx")
    body = " | ".join(_texts(prs.slides[1]))
    assert "does not match" in body
    assert brief["questions"][0].strip() in prs.slides[1].notes_slide.notes_text_frame.text  # full text kept in notes
    assert report.deck_overflow(path) == []


def _insight_slides(prs):
    return [(_texts(s), s) for s in prs.slides if _texts(s)[0].startswith("INSIGHT")]


def test_insight_slide_evidence_decision_limitation(practice):
    from vlkit import report
    res, out = practice["wdi_fiscal"]
    prs, _ = _deck(res, out, report.load_brief(out, res["meta"]["target"]))
    slides = _insight_slides(prs)
    assert len(slides) == 3
    linked = {r["from_insight"]: r for r in res["recommendations"]}
    by_title = {i["title_en"]: i for i in res["insights"]}
    seen_unlinked = False
    for texts, slide in slides:
        ins = by_title[texts[1]]
        pos = [texts.index(c) for c in ("EVIDENCE", "FOR THE DECISION", "LIMITATION")]
        assert pos == sorted(pos)
        evidence, decision, limitation = (texts[p + 1] for p in pos)
        assert ins["test"] in evidence and f"n = {ins['evidence']['n']:,}" in evidence if ins["evidence"].get("n") else ins["test"] in evidence
        if ins["id"] in linked:
            assert not seen_unlinked, "insights linked to a recommendation come first"
            assert decision == linked[ins["id"]]["so_what_en"]
        else:
            seen_unlinked = True
            assert decision == i18n.t("en", "no_decision_link")
        assert limitation == (ins.get("caveat") or res["caveats"][0])
        notes = slide.notes_slide.notes_text_frame.text
        assert ins["sentence_en"] in notes and "causal" in notes.lower()  # FR-208 Q&A hint
    _assert_numbers_from_engine(prs, res, None)


def test_weak_insight_labelled_and_never_headline_evidence(practice):
    from vlkit import report
    res, out = practice["wdi_fiscal"]
    res = copy.deepcopy(res)
    first = res["recommendations"][0]
    weak = next(i for i in res["insights"] if i["id"] == first["from_insight"])
    weak["p_value"] = 0.2
    rec, src = report._headline_rec(res)
    assert rec is not first and src["id"] != weak["id"] and not report._is_weak(src)
    prs, path = _deck(res, out, None, "weak.pptx")
    kickers = {t[1]: t[0] for t, _ in _insight_slides(prs)}
    if weak["title_en"] in kickers:
        assert "WEAK EVIDENCE" in kickers[weak["title_en"]]
    policy = next(_texts(s) for s in prs.slides if _texts(s)[0] == "POLICY RECOMMENDATION")
    assert policy[2] == rec["now_what_en"]
    assert report.deck_overflow(path) == []


def test_policy_slide_names_who_what_where_kpi(practice):
    from vlkit import report
    res, out = practice["bds_practice"]
    brief = report.load_brief(out, res["meta"]["target"])
    brief["pack"]["decision_template"]["where"] = ""
    prs, _ = _deck(res, out, brief, "policy.pptx")
    policy = " | ".join(next(_texts(s) for s in prs.slides if _texts(s)[0] == "POLICY RECOMMENDATION"))
    tpl = brief["pack"]["decision_template"]
    assert f"Who: {tpl['who']}" in policy and f"KPI: {tpl['kpi']}" in policy and f"Where: {report.BLANK}" in policy


def test_limitations_causal_first_then_real_coverage_counts(deck):
    prs, _, de, res = deck
    lim = next(s for s in prs.slides if _texts(s)[0].startswith("LIMITATIONS"))
    bullets = _texts(lim)[2].split("\n")
    assert "causal" in bullets[0].lower()
    q = de["quality_full"][de["primary"]]["after"]
    if q.get("missing_cells"):
        assert bullets[1] == f"• {int(q['missing_cells']):,} cells still missing after cleaning (not imputed unless --impute)"
    notes = lim.notes_slide.notes_text_frame.text
    assert "63" in notes and "34" in notes  # FR-208: the 63→34 question is pre-empted


# ----------------------------------------------------------------------------- feature 003: --lang vi|en|both

def _all_text(prs) -> list[str]:
    """Per slide: every text frame and table cell, without the shared deck chrome."""
    out = []
    for slide in prs.slides:
        parts = list(_texts(slide))
        parts += [c.text for sh in slide.shapes if getattr(sh, "has_table", False) and sh.has_table for r in sh.table.rows for c in r.cells]
        out.append(" | ".join(parts))
    return out


def _static_chunks(lang: str) -> set[str]:
    """Fixed-text fragments (split at placeholders) of the string table that read as prose (≥ 3 words)."""
    from vlkit.i18n import STRINGS, TECHNICAL
    chunks = set()
    for key, value in STRINGS[lang].items():
        if key in TECHNICAL:
            continue
        for part in re.split(r"\{[^}]*\}", value):
            part = part.strip(" ·:—()'")
            if len(re.findall(r"[^\W\d_]{2,}", part)) >= 3:
                chunks.add(part)
    return chunks


def test_deck_lang_matrix(practice):
    """US1/FR-303: --lang both writes deck.pptx (EN) + deck.vi.pptx and pitch.md (VI) + pitch.en.md; a later --lang vi
    run removes the English outputs so files and disk agree."""
    from vlkit import report
    res, out = practice["bds_practice"]
    df = pd.read_parquet(out / "clean.parquet")
    files = report.build_all(copy.deepcopy(res), df, None, out, lang="both")
    assert {files["deck"], files["deck_vi"], files["pitch_md"], files["pitch_en"]} == {"deck.pptx", "deck.vi.pptx", "pitch.md", "pitch.en.md"}
    for name in ("deck.pptx", "deck.vi.pptx"):
        assert report.deck_overflow(out / name) == []
    assert "## 0 · Câu hỏi quyết định" in (out / "pitch.md").read_text(encoding="utf-8")
    assert "## 0 · Decision question" in (out / "pitch.en.md").read_text(encoding="utf-8")
    files = report.build_all(copy.deepcopy(res), df, None, out, lang="vi")
    assert "deck" not in files and "pitch_en" not in files and files["deck_vi"] == "deck.vi.pptx"
    assert not (out / "deck.pptx").exists() and not (out / "pitch.en.md").exists()
    with pytest.raises(ValueError):
        report.build_all(res, df, None, out, lang="fr")


@pytest.mark.parametrize("ds", list(PRACTICE))
def test_lang_decks_use_only_their_table(practice, ds):
    """SC-301: no slide kicker/title of one language's table appears in the other deck; no EN prose in the VI deck."""
    from vlkit import report
    from vlkit.i18n import STRINGS
    res, out = practice[ds]
    brief = report.load_brief(out, res["meta"]["target"])
    decks = {lang: _deck_lang(res, out, brief, lang) for lang in ("en", "vi")}
    for lang, other in (("en", "vi"), ("vi", "en")):
        prs, path = decks[lang]
        assert report.deck_overflow(path) == []
        foreign = {v.upper() for v in STRINGS[other].values()} | set(STRINGS[other].values())
        foreign -= set(STRINGS[lang].values()) | {v.upper() for v in STRINGS[lang].values()}
        for slide in prs.slides:
            for tx in _texts(slide)[:2]:
                assert tx not in foreign, f"{lang} deck shows {other} heading {tx!r}"
    vi_text = " ".join(_all_text(decks["vi"][0]))
    leaked = [c for c in _static_chunks("en") if c in vi_text]
    assert not leaked, f"English fixed text in the VI deck: {leaked[:3]}"
    assert "\ufffd" not in vi_text and "?" * 3 not in vi_text  # diacritics survive in the pptx XML


def _deck_lang(res, out, brief, lang):
    from pptx import Presentation

    from vlkit import report
    d = out / f"lang_{lang}"
    d.mkdir(exist_ok=True)
    path = report.build_deck(res, d, {}, None, brief, lang)
    return Presentation(path), path


@pytest.mark.parametrize("ds", list(PRACTICE))
def test_numbers_identical_across_languages(practice, ds):
    """SC-302: slide by slide, the numbers in deck.pptx and deck.vi.pptx parse to the same values."""
    from test_i18n import numbers

    from vlkit import report
    res, out = practice[ds]
    brief = report.load_brief(out, res["meta"]["target"])
    en, _ = _deck_lang(res, out, brief, "en")
    vi, _ = _deck_lang(res, out, brief, "vi")
    assert len(en.slides) == len(vi.slides)
    for k, (a, b) in enumerate(zip(_frames(en), _frames(vi)), start=1):
        assert len(a) == len(b), f"{ds} slide {k}: different layout"
        for x, y in zip(a, b):
            if "…" in x or "…" in y:  # clipped to fit the box; the full text is in results.json and the speaker notes
                continue
            assert numbers(x, "en") == numbers(y, "vi"), f"{ds} slide {k}: {x[:60]!r} vs {y[:60]!r}"


def _frames(prs) -> list[list[str]]:
    """Per slide: each text frame and table cell, in shape order."""
    return [[sh.text_frame.text for sh in s.shapes if sh.has_text_frame]
            + [c.text for sh in s.shapes if getattr(sh, "has_table", False) and sh.has_table for r in sh.table.rows for c in r.cells]
            for s in prs.slides]


@pytest.mark.parametrize("ds", ["wdi_fiscal", "bds_practice"])  # EN brief, VI brief
def test_pitch_languages_carry_same_numbers(practice, ds):
    from test_i18n import numbers

    from vlkit import report
    res, out = practice[ds]
    brief = report.load_brief(out, res["meta"]["target"])
    vi, en = report.pitch_md(res, None, brief, "vi"), report.pitch_md(res, None, brief, "en")
    strip = re.compile(r"<!--.*?-->|^title: .*$", re.S | re.M)  # timing notes / Marp title are language-neutral metadata
    assert numbers(strip.sub("", en), "en") == numbers(strip.sub("", vi), "vi")
    assert "Câu hỏi quyết định" not in en and "Decision question" not in vi
    marked = {"en": "(original language)" in en, "vi": "(nguyên văn)" in vi}  # brief quoted unchanged, marked when foreign
    assert marked == {"en": brief["language"] != "en", "vi": brief["language"] != "vi"}


FUNCTIONS_WITHOUT_LITERAL_TEXT = ("build_deck", "pitch_md", "_pitch_question", "_pitch_pipeline", "_decision_frame",
                                  "_generic_question", "_quoted_question", "_brief_prefix", "_evidence_line",
                                  "_causal_caveat", "_insight_caveat", "_coverage_caveats", "_limitations")


def test_report_has_no_inline_prose():
    """FR-301 lint: deck/pitch functions take every fixed sentence from vlkit.i18n (docstrings excluded)."""
    import ast

    from vlkit import report
    tree = ast.parse(Path(report.__file__).read_text(encoding="utf-8"))
    prose = re.compile(r"[^\W\d_]{3,} [^\W\d_]{3,}")
    found = []
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS_WITHOUT_LITERAL_TEXT):
        docs = {id(f.body[0].value) for f in ast.walk(fn) if isinstance(f, ast.FunctionDef)
                and isinstance(f.body[0], ast.Expr) and isinstance(f.body[0].value, ast.Constant)}
        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs and prose.search(node.value):
                found.append(f"{fn.name}: {node.value[:50]!r}")
    assert not found, found
