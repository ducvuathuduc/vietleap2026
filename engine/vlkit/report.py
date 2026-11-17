"""Outputs: chart PNGs, PowerPoint deck, executive summary (MD/HTML/PDF), self-contained static HTML dashboard."""
from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from . import fmt
from .i18n import BRAND_KICKER, DEFAULT_REPORT_LANG, FOOTER, LANGS, caveats_for, langs_for, t, text_field
from .stats import r

PALETTE = ["#18181b", "#3b82f6", "#a1a1aa", "#d4d4d8", "#f97316"]
FONT = "Inter, Helvetica, Arial, sans-serif"


# ----------------------------------------------------------------------------- charts

def figure(spec: dict, title: str | None = None) -> go.Figure:
    kind = spec["kind"]
    fig = go.Figure()
    xs = spec["x"]
    for i, s in enumerate(spec["series"]):
        col = PALETTE[i % len(PALETTE)]
        if kind == "bar":
            fig.add_bar(x=[str(x) for x in xs], y=s["data"], name=s["name"], marker_color=PALETTE[1] if i == 0 else col)
        elif kind == "hbar":
            fig.add_bar(y=[str(x) for x in xs][::-1], x=s["data"][::-1], orientation="h", name=s["name"], marker_color=PALETTE[1])
        elif kind == "scatter":
            fig.add_scatter(x=xs, y=s["data"], mode="markers", name=s["name"], marker=dict(color=PALETTE[1], size=5, opacity=0.5))
        else:
            dash = "dot" if s["name"] in ("lower80", "upper80", "low 90%", "high 90%") else None
            fig.add_scatter(x=[str(x) for x in xs], y=s["data"], mode="lines+markers", name=s["name"],
                            line=dict(color=PALETTE[2] if dash else (PALETTE[1] if i == 1 else PALETTE[0]), width=2.5, dash=dash))
    fig.update_layout(template="simple_white", font=dict(family=FONT, size=14, color="#18181b"), margin=dict(l=60, r=20, t=50 if title else 20, b=60),
                      title=dict(text=title, font=dict(size=16)) if title else None, showlegend=len(spec["series"]) > 1,
                      legend=dict(orientation="h", y=1.08, x=0), xaxis_title=spec.get("x_label"), yaxis_title=spec.get("y_label"),
                      plot_bgcolor="white", paper_bgcolor="white")
    fig.update_yaxes(gridcolor="#f4f4f5", showgrid=True)
    if kind == "scatter":
        fig.update_xaxes(type="log" if min([v for v in xs if v is not None] or [0]) > 0 else "linear")
        if min([v for v in spec["series"][0]["data"] if v is not None] or [0]) > 0:
            fig.update_yaxes(type="log")
    return fig


def save_png(fig: go.Figure, path: Path, w=1000, h=560) -> str | None:
    try:
        fig.write_image(str(path), width=w, height=h, scale=2)
        return str(path)
    except Exception as e:  # kaleido needs a Chrome; keep going without PNGs
        print(f"[warn] PNG export failed ({type(e).__name__}: {e}); set BROWSER_PATH or run tools/setup_env.sh")
        return None



# ----------------------------------------------------------------------------- deck text fitting
# python-pptx never auto-shrinks text, so every text box is fitted here (font size down to MIN_PT, then
# truncation with "…") using a conservative Calibri width estimate. `deck_overflow()` re-checks a saved deck.

CHAR_W = 0.53     # average glyph width as a fraction of the font size (Calibri, mixed VI/EN text; slightly generous)
LINE_H = 1.2      # line height as a multiple of the font size
PARA_GAP = 8      # pt after each paragraph (matches text())
INSET_W, INSET_H = 0.2, 0.1  # inches lost to the default text-frame insets
MIN_PT = 10


def _lines_needed(line: str, width_in: float, size: float, bold: bool = False) -> int:
    import math
    cpl = max(1, int((width_in - INSET_W) * 72 / (size * CHAR_W * (1.06 if bold else 1.0))))
    # word wrap wastes part of each line: count words greedily
    n, cur = 1, 0
    for word in str(line).split(" "):
        wl = len(word)
        if wl > cpl:  # a very long token breaks across lines
            extra = cur + wl
            n += math.ceil(extra / cpl) - 1
            cur = extra % cpl
            continue
        if cur and cur + 1 + wl > cpl:
            n += 1
            cur = wl
        else:
            cur += (1 if cur else 0) + wl
    return n


def text_height_pt(lines: list[str], width_in: float, size: float, bold: bool = False) -> float:
    if not lines:
        return 0.0
    return sum(_lines_needed(l, width_in, size, bold) * size * LINE_H for l in lines) + PARA_GAP * (len(lines) - 1)


def fit_text(lines: list[str], width_in: float, height_in: float, size: float, bold: bool = False) -> tuple[list[str], float]:
    """Shrink the font (≥ MIN_PT, never below the requested size if smaller) and then truncate so the text fits the box."""
    avail = (height_in - INSET_H) * 72
    floor = min(size, MIN_PT)
    lines = [str(l) for l in lines]
    while size > floor and text_height_pt(lines, width_in, size, bold) > avail:
        size -= 1
    while lines and text_height_pt(lines, width_in, size, bold) > avail:
        head, last = lines[:-1], lines[-1]
        lo, hi = 0, len(last)  # longest prefix of the last paragraph that still fits (binary search)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if text_height_pt(head + [last[:mid].rstrip() + "…"], width_in, size, bold) <= avail:
                lo = mid
            else:
                hi = mid - 1
        if lo >= 8 or (not head and lo >= 1):
            lines = head + [last[:lo].rstrip() + "…"]
            break
        lines = head
    return lines, size


def deck_overflow(path: str | Path) -> list[str]:
    """Estimated overflow problems in a saved deck: text boxes whose text is taller than the box, tables taller than
    the space below them, and shapes outside the slide. Empty list = OK."""
    from pptx import Presentation
    from pptx.util import Emu
    prs = Presentation(str(path))
    W, H = prs.slide_width, prs.slide_height
    probs = []
    for n, slide in enumerate(prs.slides, 1):
        for sh in slide.shapes:
            if sh.left is not None and (sh.left < 0 or sh.top < 0 or sh.left + sh.width > W + Emu(9525) or sh.top + sh.height > H + Emu(9525)):
                probs.append(f"slide {n}: shape '{sh.name}' outside the slide")
            if sh.has_text_frame and sh.text_frame.text.strip():
                paras = sh.text_frame.paragraphs
                size = max((p.font.size.pt for p in paras if p.font.size), default=18)
                bold = any(p.font.bold for p in paras)
                need = text_height_pt([p.text for p in paras], sh.width / 914400, size, bold)
                if need > (sh.height / 914400 - INSET_H) * 72 + 1:
                    probs.append(f"slide {n}: text overflows '{sh.text_frame.text[:40]}…' ({need:.0f}pt > {(sh.height / 914400 - INSET_H) * 72:.0f}pt)")
            if getattr(sh, "has_table", False) and sh.has_table:
                tbl = sh.table
                total = 0.0
                for row in tbl.rows:
                    hmax = row.height / 12700
                    for ci, cell in enumerate(row.cells):
                        paras = cell.text_frame.paragraphs
                        size = max((r.font.size.pt for p in paras for r in p.runs if r.font.size), default=12)
                        need = text_height_pt([p.text for p in paras], tbl.columns[ci].width / 914400, size) + 0.1 * 72
                        hmax = max(hmax, need)
                    total += hmax
                if sh.top / 12700 + total > H / 12700 - 0.45 * 72:  # keep clear of the footer
                    probs.append(f"slide {n}: table '{sh.name}' too tall ({total:.0f}pt)")
    return probs


def load_de(out: Path) -> dict | None:
    """DE-layer outputs (pipeline.json + quality.json) written by vlkit.de.flow next to the insight results, if any."""
    try:
        pipe = json.loads((out / "pipeline.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        pipe["quality_full"] = json.loads((out / "quality.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pipe["quality_full"] = {}
    return pipe


def _short_uri(uri: str) -> str:
    """Never print local absolute paths on a slide: keep the file name; keep URLs without query strings."""
    u = str(uri or "")
    if u.startswith(("sqlite", "postgresql", "mysql", "mssql", "oracle", "duckdb")):
        return u.split("://", 1)[0] + "://…/" + u.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0][:40]
    if "://" in u and not u.startswith("file://"):
        return u.split("?", 1)[0][:70]
    return Path(u.replace("file://", "")).name[:60]


def _when(v) -> str:
    """ISO or 'Fri 2026-11-13 4:37 PM (UTC+07:00)' → '2026-11-13 16:37' (kept as given if unparseable)."""
    from datetime import datetime
    sv = str(v or "—")
    try:
        return datetime.fromisoformat(sv).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        m = re.search(r"(\d{4}-\d{2}-\d{2}) (\d{1,2}):(\d{2}) ?([AP]M)?", sv)
        if not m:
            return sv[:16]
        h = int(m.group(2)) % 12 + (12 if m.group(4) == "PM" else 0) if m.group(4) else int(m.group(2))
        return f"{m.group(1)} {h:02d}:{m.group(3)}"


# ----------------------------------------------------------------------------- story frame (feature 002) + language (003)
# Brief text is untrusted, user-supplied data: it is only quoted (prefixed "Brief:"/"Đề bài:"), capped, and never
# treated as a computed number or sent to an LLM as instructions. Every computed number still comes from results.json.
# Every fixed string comes from vlkit.i18n (EN/VI); engine text uses its `*_en` / `*_vi` fields.

BRIEF_FIELD_MAX = 2000
BLANK = "____"
DECISION_KEYS = ("who", "what", "where", "kpi", "caveat")
DECK_FILES = {"en": "deck.pptx", "vi": "deck.vi.pptx"}      # FR-303: names fixed per language
PITCH_FILES = {"vi": "pitch.md", "en": "pitch.en.md"}
DECK_KEYS = {"en": "deck", "vi": "deck_vi"}                 # keys in results.json.files = API export kinds
PITCH_KEYS = {"vi": "pitch_md", "en": "pitch_en"}


def _cap_strings(v):
    if isinstance(v, str):
        return v[:BRIEF_FIELD_MAX]
    if isinstance(v, list):
        return [_cap_strings(x) for x in v]
    if isinstance(v, dict):
        return {k: _cap_strings(x) for k, x in v.items()}
    return v


def _valid_brief(b) -> bool:
    """Required keys/types of specs/001-vietleap-insight-kit/contracts/brief.schema.json that the story relies on."""
    return (isinstance(b, dict) and isinstance(b.get("title"), str) and isinstance(b.get("questions"), list)
            and all(isinstance(q, str) for q in b["questions"])
            and isinstance(b.get("pack") or {}, dict) and isinstance((b.get("pack") or {}).get("decision_template") or {}, dict))


def load_brief(out: Path, target: str | None = None) -> dict | None:
    """out/<ds>/brief.json (written by POST /api/brief or `de.py brief --out`), capped; None when absent or invalid.
    `stale` is True when the brief resolved a different target column than the one analysed."""
    try:
        b = json.loads((Path(out) / "brief.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not _valid_brief(b):
        print(f"[warn] {Path(out) / 'brief.json'} ignored: not a brief.json document")
        return None
    b = _cap_strings(b)
    col = (b.get("target") or {}).get("column") if isinstance(b.get("target"), dict) else None
    b["stale"] = bool(target and col and col != target)
    return b


def _generic_question(meta: dict, lang: str) -> str:
    by = meta.get("geo_col") or (meta["category_cols"][0] if meta.get("category_cols") else t(lang, "generic_by"))
    over_time = t(lang, "generic_over_time") if meta.get("time_col") else ""
    return t(lang, "generic_question", target=meta["target"], by=by, over_time=over_time)


def _decision_frame(res: dict, brief: dict | None, lang: str = "en") -> dict:
    """Who decides what, where, measured by which KPI — from the brief; blanks stay '____' (never invented)."""
    meta = res["meta"]
    tpl = ((brief or {}).get("pack") or {}).get("decision_template") or {}
    explicit = next((q.strip() for q in (brief or {}).get("questions") or [] if q.strip()), "")
    pack_question = str(tpl.get("question") or "").strip() if not explicit else ""
    question = explicit or pack_question or ((brief or {}).get("title") or "").strip()
    frame = {k: (str(tpl.get(k) or "").strip() or BLANK) for k in DECISION_KEYS}
    if brief and question:
        return {**frame, "question": question, "source": "pack" if pack_question else "brief",
                "language": "vi" if pack_question else brief.get("language") or "vi",
                "stale": bool(brief.get("stale")), "target_column": ((brief.get("target") or {}).get("column"))}
    return {**frame, "kpi": t(lang, "generic_kpi", target=meta["target"]), "question": _generic_question(meta, lang),
            "source": "generic", "language": lang, "stale": False, "target_column": None}


def _brief_prefix(frame: dict, lang: str) -> str:
    """'Brief' / 'Đề bài', marked '(original language)' when the brief is in the other language (quoted unchanged)."""
    prefix = t(lang, "brief_prefix")
    return prefix if frame["language"] == lang else f"{prefix} ({t(lang, 'original_language')})"


def _quoted_question(frame: dict, lang: str) -> str:
    if frame["source"] != "brief":
        return frame["question"]
    return f"{_brief_prefix(frame, lang)}: “{frame['question']}”"


def _is_weak(ins: dict | None) -> bool:
    """FR-207: p ≥ 0.05 after the engine's correction, or flagged weak by the engine."""
    if not ins:
        return True
    p = ins.get("p_value")
    return bool(ins.get("weak")) or (p is not None and p >= 0.05)


def _headline_rec(res: dict) -> tuple[dict | None, dict | None]:
    """Recommendation #1 = the first one whose source insight is not weak; (None, None) when every one is weak."""
    by_id = {i.get("id"): i for i in res["insights"]}
    for rc in res["recommendations"]:
        src = by_id.get(rc.get("from_insight"))
        if not _is_weak(src):
            return rc, src
    return None, None


def _linked_first(insights: list[dict], recs: list[dict]) -> list[dict]:
    """Insights linked to a recommendation first, then engine rank (list order; sort is stable)."""
    linked = {rc.get("from_insight") for rc in recs}
    return sorted(insights, key=lambda i: i.get("id") not in linked)


def _story_insights(res: dict, k: int = 3) -> list[dict]:
    return _linked_first([i for i in res["insights"] if i.get("chart")], res["recommendations"])[:k]


def _evidence_line(ins: dict, lang: str = "en") -> str:
    parts = [ins["test"]]
    if ins.get("p_value") is not None:
        parts.append(fmt.p(ins["p_value"], lang))
    if ins.get("effect") is not None:
        parts.append(t(lang, "effect", value=fmt.dec(ins["effect"], lang)))
    n_obs = (ins.get("evidence") or {}).get("n")
    if isinstance(n_obs, (int, float)):
        parts.append(t(lang, "n_obs", n=fmt.count(n_obs, lang)))
    return " · ".join(parts)


def _causal_caveat(res: dict, lang: str = "en") -> str:
    """The engine's causal caveat in `lang` (caveats_vi is parallel to the English list)."""
    idx = next((k for k, c in enumerate(res["caveats"]) if "causal" in c.lower()), None)
    return caveats_for(res, lang)[idx] if idx is not None else t(lang, "cav_causal")


def _insight_caveat(ins: dict, res: dict, lang: str = "en") -> str:
    """The insight's own caveat (`caveat` EN / `caveat_vi`), else the engine's causal caveat."""
    if not ins.get("caveat"):
        return _causal_caveat(res, lang)
    return text_field({"caveat_en": ins["caveat"], "caveat_vi": ins.get("caveat_vi")}, "caveat", lang)


def _coverage_caveats(de: dict | None, qp: dict | None, lang: str = "en") -> list[str]:
    """Data-coverage limits with their real counts from the DE outputs (quality.json, pipeline.json conformed joins)."""
    out = []
    missing = ((qp or {}).get("after") or {}).get("missing_cells")
    if missing:
        out.append(t(lang, "cov_missing", n=fmt.count(missing, lang)))
    for j in (((de or {}).get("conformed") or {}).get("joins") or []):
        if j.get("unmatched_rows"):
            out.append(t(lang, "cov_unmatched", n=fmt.count(j["unmatched_rows"], lang), source=j.get("source", "?"),
                         keys=", ".join(j.get("keys") or j.get("join_on") or []), pct=fmt.dec(j.get("match_pct"), lang)))
    if de and len(de.get("provenance") or []) <= 1:
        out.append(t(lang, "cov_single"))
    return out


def _limitations(res: dict, de: dict | None, qp: dict | None, k: int = 6, lang: str = "en") -> list[str]:
    """US4: the causal-association caveat first, then coverage limits with real counts, then the other caveats."""
    causal = _causal_caveat(res, lang)
    rest = [c for c in caveats_for(res, lang) if c != causal]
    return ([causal] + _coverage_caveats(de, qp, lang) + rest)[:k]


def _clip(s: str, limit: int) -> str:
    """At most `limit` characters, cut at a word boundary and marked '…' (never in the middle of a number)."""
    if len(s) <= limit:
        return s
    return s[:limit].rsplit(" ", 1)[0].rstrip(" ,;:(") + "…"


def _notes(slide, lines: list[str]) -> None:
    slide.notes_slide.notes_text_frame.text = "\n".join(l for l in lines if l)


# ----------------------------------------------------------------------------- deck

def build_deck(res: dict, out: Path, chart_pngs: dict, de: dict | None = None, brief: dict | None = None,
               lang: str = "en") -> str:
    """The pitch deck in one language (`deck.pptx` EN, `deck.vi.pptx` VI): fixed text from vlkit.i18n, engine text from
    the `*_<lang>` fields, numbers formatted for the language by vlkit.fmt — the values themselves never change."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Emu, Inches, Pt

    INK, MUTED, ACCENT, LINE = RGBColor(0x18, 0x18, 0x1B), RGBColor(0x71, 0x71, 0x7A), RGBColor(0x3B, 0x82, 0xF6), RGBColor(0xE4, 0xE4, 0xE7)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    meta = res["meta"]
    tgt = meta["target"]

    def tr(key: str, **values) -> str:
        return t(lang, key, **values)

    def count(x) -> str:
        return fmt.count(x, lang)

    def dec(x) -> str:
        return fmt.dec(x, lang)

    def text(slide, x, y, w, h, s, size=18, bold=False, color=INK, align=None, italic=False):
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        lines, size = fit_text([l for l in (s if isinstance(s, list) else [s])], w, h, size, bold)
        lines = lines or [""]
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.size, p.font.bold, p.font.color.rgb, p.font.name = Pt(size), bold, color, "Calibri"
            p.font.italic = italic
            p.space_after = Pt(8)
            if align:
                p.alignment = align
        return tb

    def header(slide, kicker, title, n):
        text(slide, 0.7, 0.45, 10, 0.4, kicker.upper(), 12, True, ACCENT)
        text(slide, 0.7, 0.8, 12, 1.0, title, 30, True)
        ln = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.75), Inches(11.9), Emu(12000))
        ln.fill.solid(); ln.fill.fore_color.rgb = LINE; ln.line.fill.background()
        text(slide, 11.6, 7.0, 1.3, 0.3, f"{n}", 10, False, MUTED, PP_ALIGN.RIGHT)
        text(slide, 0.7, 7.0, 8, 0.3, FOOTER, 10, False, MUTED)

    def card(slide, x, y, w, h, title, body, size=15):
        sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.adjustments[0] = 0.06
        sh.fill.solid(); sh.fill.fore_color.rgb = RGBColor(0xFA, 0xFA, 0xFA); sh.line.color.rgb = LINE
        text(slide, x + 0.25, y + 0.15, w - 0.5, 0.5, title, 13, True, MUTED)
        text(slide, x + 0.25, y + 0.6, w - 0.5, h - 0.7, body, size)

    def table(slide, x, y, w, rows, col_w, size=12, header_fill=RGBColor(0xF4, 0xF4, 0xF5)):
        """Small table; cell text is fitted to its column (one line max for long values)."""
        shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(0.36 * len(rows)))
        tbl = shape.table
        for ci, cw in enumerate(col_w):
            tbl.columns[ci].width = Inches(cw)
        for ri, row in enumerate(rows):
            tbl.rows[ri].height = Inches(0.36)
            for ci, val in enumerate(row):
                cell = tbl.cell(ri, ci)
                cell.fill.solid(); cell.fill.fore_color.rgb = header_fill if ri == 0 else RGBColor(0xFF, 0xFF, 0xFF)
                cell.margin_top = cell.margin_bottom = Inches(0.03)
                lines, sz = fit_text([str(val)], col_w[ci], 0.36, size, ri == 0)
                cell.text = lines[0] if lines else ""
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        run.font.size, run.font.bold, run.font.color.rgb, run.font.name = Pt(sz), ri == 0, INK, "Calibri"
        return shape

    ins = res["insights"]
    caveats = caveats_for(res, lang)
    frame = _decision_frame(res, brief, lang)
    recs_by_insight = {rc.get("from_insight"): rc for rc in res["recommendations"]}
    n = 1
    # 1 title
    s = prs.slides.add_slide(blank)
    text(s, 0.9, 1.0, 11, 0.5, BRAND_KICKER, 14, True, ACCENT)
    text(s, 0.9, 1.8, 11.5, 2.2, tr("title_main", target=tgt, rows=count(meta["rows"])), 40, True)
    text(s, 0.9, 4.4, 11, 0.6, tr("title_domain", domain=meta["domain"].replace("_", " "), source=meta["source_file"]), 18, False, MUTED)
    text(s, 0.9, 5.6, 11, 0.5, tr("title_team"), 18, False, MUTED)
    # 2 decision question — who decides what, from the brief (FR-202); brief text is quoted, never computed
    n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_question"), tr("title_question"), n)
    text(s, 0.7, 2.1, 7.4, 2.7, _quoted_question(frame, lang), 22, False, INK, None, frame["source"] == "brief")
    text(s, 0.7, 4.95, 7.4, 1.35, [tr("line_decision", what=frame["what"]), tr("where", where=frame["where"])], 15)
    if frame["source"] == "generic":
        text(s, 0.7, 6.35, 7.4, 0.5, tr("generic_tag"), 12, False, MUTED)
    elif frame["stale"]:
        text(s, 0.7, 6.35, 7.4, 0.5, tr("stale_brief", brief_target=frame["target_column"], target=tgt), 11, False, MUTED)
    card(s, 8.5, 2.1, 4.1, 1.45, tr("card_who"), frame["who"], 14)
    card(s, 8.5, 3.7, 4.1, 1.45, tr("card_kpi"), frame["kpi"], 14)
    card(s, 8.5, 5.3, 4.1, 1.4, tr("card_scope"), [tr("scope_rows", rows=count(meta["rows"]), columns=meta["columns"]),
                                                    tr("target_line", target=tgt)], 12)
    _notes(s, [frame["question"], tr("qa_hint_question")])
    # 3 data & method
    n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_method"), tr("title_method"), n)
    key_log = [l for l in res["cleaning_log"] if any(w in l for w in ["→", "duplicate", "flagged", "derived", "transposed", "stacked", "normalised"])][:5]
    card(s, 0.7, 2.1, 6.0, 4.6, tr("card_prep"), [_clip("• " + l, 120) for l in key_log], 13)
    card(s, 6.9, 2.1, 5.7, 2.4, tr("card_methods"), [tr(k) for k in ("method_tests", "method_corr", "method_models", "method_segments")], 13)
    card(s, 6.9, 4.7, 5.7, 2.0, tr("card_caveats"), ["• " + _clip(c, 110) for c in caveats[:3]], 12)
    q_full = (de or {}).get("quality_full") or {}
    prim = (de or {}).get("primary")
    qp = q_full.get(prim) or (next(iter(q_full.values())) if q_full else None)
    if de:
        # Data pipeline — the 4 stages of the 16/11 workshop
        n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_pipeline"), tr("title_pipeline"), n)
        prov = de.get("provenance") or []
        kinds = sorted({p_.get("kind", "?") for p_ in prov})
        rows_in = sum(t_.get("rows", 0) for p_ in prov for t_ in (p_.get("tables") or {}).values())
        tim = de.get("timings") or {}
        qs = de.get("quality") or {}
        rec = de.get("recommended") or {}
        q_line = [f"{k.split('.', 1)[-1].split('__')[-1][:20]}: {dec(v['score_before'])} → {dec(v['score_after'])}" for k, v in list(qs.items())[:2]]
        stages = [
            (tr("stage_ingestion"), [tr("ing_sources", n=len(prov), kinds=", ".join(kinds)), tr("ing_rows", rows=count(rows_in)),
                                     tr("ing_provenance"), tr("seconds", s=dec(tim.get("ingest")))]),
            (tr("stage_storage"), [tr("sto_warehouse"), tr("sto_layers", bronze=len(de.get("bronze") or []), silver=len(de.get("silver") or []),
                                                          gold=len(de.get("gold") or [])), tr("sto_raw")]),
            (tr("stage_transform"), [tr("tr_checks"), tr("tr_score")] + q_line
             + [tr("tr_models", n=len(de.get("models") or {}), clean=dec(tim.get("clean")), model=dec(tim.get("model")))]),
            (tr("stage_serving"), [tr("srv_obt"), tr("srv_recommended", serving=rec.get("serving", "—"), semantic=rec.get("semantic", "—")),
                                   tr("srv_outputs")]),
        ]
        for k, (title, body) in enumerate(stages):
            card(s, 0.7 + k * 3.03, 2.05, 2.85, 4.35, title, body, 13)
        text(s, 0.7, 6.5, 11.9, 0.4, tr("pipeline_footnote"), 12, False, MUTED)

        # Data model — OBT vs Star vs Snowflake vs Data Vault & why
        n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_model"), tr("title_model"), n)
        mods = de.get("models") or {}
        for k, key in enumerate(["obt", "star", "snowflake", "data_vault"]):
            tag = [tr("tag_serving")] if rec.get("serving") == key else ([tr("tag_semantic")] if rec.get("semantic") == key else [])
            ntab = len((mods.get(key) or {}).get("tables") or [])
            card(s, 0.7 + k * 3.03, 2.05, 2.85, 3.6, tr(f"model_{key}").upper(),
                 tag + [tr(f"why_{key}"), tr("tables_built", n=ntab) if ntab else tr("not_built")], 13)
        text(s, 0.7, 5.8, 11.9, 1.1, [tr("model_choice", serving=rec.get("serving", "obt"), semantic=rec.get("semantic", "star")),
                                      tr("model_tradeoff")], 13)

        # Data quality before / after
        if qp:
            n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_quality"), tr("title_quality"), n)
            b, a = qp.get("before") or {}, qp.get("after") or {}
            rows = [[tr("q_metric"), tr("q_before"), tr("q_after")],
                    [tr("q_rows"), count(b.get("rows")), count(a.get("rows"))],
                    [tr("q_missing"), count(b.get("missing_cells")), count(a.get("missing_cells"))],
                    [tr("q_invalid"), count(b.get("invalid_cells")), count(a.get("invalid_cells"))],
                    [tr("q_duplicates"), count(b.get("duplicate_rows")), count(a.get("duplicate_rows"))],
                    [tr("q_score"), dec(qp.get("score_before")), dec(qp.get("score_after"))]]
            table(s, 0.7, 2.1, 5.6, rows, [3.0, 1.3, 1.3], 13)
            log = [("• " + str(l)) for l in (qp.get("cleaning_log") or [])][:7]
            card(s, 6.6, 2.05, 6.0, 4.6, tr("card_cleaning_log"), log or [tr("no_cleaning")], 12)
            text(s, 0.7, 4.5, 5.6, 2.1, [tr("outliers_note"), tr("raw_note")], 12, False, MUTED)
    # insights: EVIDENCE → FOR THE DECISION → LIMITATION (FR-203), linked insights first, weak ones labelled (FR-207)
    for k, i in enumerate(_story_insights(res)):
        kicker = tr("kicker_insight", k=k + 1) + (f" · {tr('weak_evidence')}" if _is_weak(i) else "")
        sentence = text_field(i, "sentence", lang)
        n += 1; s = prs.slides.add_slide(blank); header(s, kicker, text_field(i, "title", lang), n)
        png = chart_pngs.get(i["id"])
        if png:
            s.shapes.add_picture(png, Inches(0.7), Inches(2.0), width=Inches(5.6))
        rc = recs_by_insight.get(i["id"])
        card(s, 6.5, 2.0, 6.1, 3.1, tr("card_evidence"), [sentence, _evidence_line(i, lang)], 13)
        card(s, 0.7, 5.25, 5.85, 1.5, tr("card_for_decision"), text_field(rc, "so_what", lang) if rc else tr("no_decision_link"), 12)
        card(s, 6.75, 5.25, 5.85, 1.5, tr("card_limitation"), _insight_caveat(i, res, lang), 12)
        _notes(s, [sentence, _evidence_line(i, lang), tr("qa_hint_insight")])
    # recommendations
    n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_recs"), tr("title_recs"), n)
    y = 2.0
    for k, rc in enumerate(res["recommendations"][:4]):
        text(s, 0.7, y, 0.6, 0.6, f"{k + 1}", 26, True, ACCENT)
        text(s, 1.3, y, 5.2, 1.1, _clip(text_field(rc, "so_what", lang), 150), 14, True)
        text(s, 6.6, y, 6.0, 1.1, [_clip(text_field(rc, "now_what", lang), 170), tr("impact", text=_clip(text_field(rc, "impact", lang), 120))], 12)
        y += 1.22
    # what-if
    n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_impact"), tr("title_whatif"), n)
    wi = next((i for i in ins if i["type"] == "what_if"), None)
    if wi and chart_pngs.get(wi["id"]):
        s.shapes.add_picture(chart_pngs[wi["id"]], Inches(0.7), Inches(2.0), width=Inches(7.4))
        card(s, 8.4, 2.0, 4.2, 4.6, tr("card_scenario"), [_clip(text_field(wi, "sentence", lang), 260), "", tr("whatif_caveat")], 14)
    else:
        text(s, 0.7, 2.2, 11, 2, tr("no_lever"), 20, False, MUTED)
    # policy recommendation — one decision, owner, KPI, evidence
    recs_ = res["recommendations"]
    if recs_:
        n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_policy"), tr("title_policy"), n)
        r0, src_i = _headline_rec(res)
        r0 = r0 or recs_[0]
        level = r0.get("confidence")
        conf = tr(f"conf_{level}") if level in ("high", "medium") else str(level or "—")
        text(s, 0.7, 2.05, 7.6, 1.5, text_field(r0, "now_what", lang), 22, True)
        card(s, 0.7, 3.75, 3.7, 2.9, tr("card_why"), text_field(r0, "so_what", lang), 13)
        card(s, 4.6, 3.75, 3.7, 2.9, tr("card_expected"), [text_field(r0, "impact", lang), tr("confidence", level=conf)], 13)
        card(s, 8.5, 2.05, 4.1, 1.55, tr("card_evidence"), _evidence_line(src_i, lang) if src_i else tr("weak_only"), 12)
        card(s, 8.5, 3.75, 4.1, 2.9, tr("card_wwwk"), [tr("who", who=frame["who"]), tr("what", what=frame["what"]),
                                                       tr("where", where=frame["where"]), tr("kpi", kpi=frame["kpi"])], 12)
    # limitations
    n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_limits"), tr("title_limits"), n)
    lim = _limitations(res, de, qp, lang=lang)
    text(s, 0.7, 2.1, 6.2, 4.6, ["• " + c for c in lim], 14)
    _notes(s, lim + [tr("qa_hint_limits")])
    card(s, 7.3, 2.1, 5.3, 4.4, tr("card_next"), ["• " + tr(k) for k in ("next_join", "next_pilot", "next_rerun", "next_provinces")], 14)
    # provenance — source, time, licence, fingerprint (organisers asked for this in the entry test)
    if de and de.get("provenance"):
        n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_provenance"), tr("title_provenance"), n)
        rows = [[tr(k) for k in ("prov_source", "prov_kind", "prov_location", "prov_fetched", "prov_shape", "prov_fingerprint", "prov_licence")]]
        for p_ in de["provenance"][:8]:
            for tname, tb in list((p_.get("tables") or {}).items())[:2]:
                rows.append([str(p_.get("source", tname))[:24], p_.get("kind", "—"), _short_uri(p_.get("uri", "")), _when(p_.get("fetched_at")),
                             f"{count(tb.get('rows'))} × {tb.get('cols', '—')}", str(tb.get("fingerprint", "—"))[:16],
                             (p_.get("license_note") or tr("see_source"))[:30]])
        rows = rows[:10]
        table(s, 0.7, 2.05, 11.9, rows, [1.7, 0.8, 2.7, 2.0, 1.4, 1.6, 1.7], 11)
        text(s, 0.7, 6.3, 11.9, 0.5, tr("prov_footnote"), 12, False, MUTED)
    # team & Q&A
    n += 1; s = prs.slides.add_slide(blank); header(s, tr("kicker_qa"), tr("title_qa"), n)
    text(s, 0.7, 2.1, 6, 4, [tr(k) for k in ("qa_team", "qa_roles", "qa_dashboard", "qa_code")], 18)
    card(s, 7.3, 2.1, 5.3, 4.4, tr("card_judge"), [tr(k) for k in ("judge_causal", "judge_outliers", "judge_sample", "judge_week")], 13)
    path = out / DECK_FILES[lang]
    prs.save(path)
    return str(path)


# ----------------------------------------------------------------------------- summary

def summary_md(res: dict) -> str:
    m = res["meta"]
    lines = [f"# Executive summary — {m['target']} ({m['domain'].replace('_', ' ')})", "",
             f"*Source: {m['source_file']} · {m['rows']:,} records · generated {m['created']}*", "", "## Key insights"]
    for i in res["insights"][:3]:
        lines += [f"**{i['rank']}. {i['title_en']}** — {i['sentence_en']}", f"  *VI:* {i['sentence_vi']}", ""]
    lines += ["## Recommendations (So what → Now what)"]
    for k, rc in enumerate(res["recommendations"][:4], 1):
        lines += [f"{k}. **{rc['so_what_en']}** → {rc['now_what_en']} _Impact:_ {rc['impact_en']}"]
    lines += ["", "## Caveats"] + [f"- {c}" for c in res["caveats"][:5]]
    return "\n".join(lines)


PITCH_TIMING = {  # docs/CONTEST_ANALYSIS.md §4.6 — 7-minute default until the organisers publish the real length
    "hook": "0:00–0:40", "question": "0:40–1:20", "pipeline": "1:20–2:10", "insights": "2:10–4:10",
    "demo": "4:10–5:00", "decision": "5:00–6:10", "limits": "6:10–6:40", "close": "6:40–7:00",
}
_MD_SPECIAL = re.compile(r"([\\`*_\[\]#|])")


def _md_text(s: str) -> str:
    """Brief text into Marp markdown as inert text: no raw HTML/comments, no markdown formatting ('____' blanks kept)."""
    return s if s == BLANK else _MD_SPECIAL.sub(r"\\\1", html.escape(str(s), quote=False))


def _note(slot: str, text_: str) -> str:
    """Speaker note with its time slot (Marp renders HTML comments as presenter notes)."""
    return f"<!-- {PITCH_TIMING[slot]} · {text_} -->"


def _pitch_question(frame: dict, lang: str) -> list[str]:
    if frame["source"] == "brief":
        quote = f"> *{_brief_prefix(frame, lang)}:* “{_md_text(frame['question'])}”"
    elif frame["source"] == "pack":
        quote = f"> {_md_text(frame['question'])}"
    else:
        quote = f"> *{t(lang, 'generic_tag')}* {_md_text(frame['question'])}"
    return [f"## {t(lang, 'pitch_q_heading')}", "", quote, "",
            f"- **{t(lang, 'pitch_who')}:** {_md_text(frame['who'])}", f"- **{t(lang, 'pitch_what')}:** {_md_text(frame['what'])}",
            f"- **{t(lang, 'pitch_where')}:** {_md_text(frame['where'])}", f"- **{t(lang, 'pitch_kpi')}:** {_md_text(frame['kpi'])}", "",
            _note("question", t(lang, "pitch_note_question")), "", "---", ""]


def _pitch_pipeline(res: dict, de: dict | None, lang: str) -> list[str]:
    m = res["meta"]
    prov = (de or {}).get("provenance") or []
    out = [f"## {t(lang, 'pitch_data_heading')}", ""]
    if prov:
        q = None
        if de.get("quality"):
            q = de["quality"].get(de.get("primary")) or next(iter(de["quality"].values()))
        out.append("- " + t(lang, "pitch_ingestion", n=len(prov), kinds=", ".join(sorted({p_.get("kind", "?") for p_ in prov}))))
        out.append("- " + t(lang, "pitch_storage"))
        if q:
            out.append("- " + t(lang, "pitch_quality", before=fmt.dec(q["score_before"], lang), after=fmt.dec(q["score_after"], lang)))
        out.append("- " + t(lang, "pitch_serving", serving=(de.get("recommended") or {}).get("serving", "obt")))
    else:
        out.append("- " + t(lang, "pitch_rows", rows=fmt.count(m["rows"], lang), columns=m["columns"], source=m["source_file"]))
    return out + ["", _note("pipeline", t(lang, "pitch_note_pipeline")), "", "---", ""]


def pitch_md(res: dict, de: dict | None = None, brief: dict | None = None, lang: str = "vi") -> str:
    """Marp deck for the 7-minute pitch in one language (`pitch.md` VI, `pitch.en.md` EN), filled with this dataset's
    engine numbers (template: slides/pitch.md).
    Arc: decision question (brief) → pipeline → 3 insights → demo → decision → impact → limitations → close."""
    m = res["meta"]
    tgt = m["target"]
    frame = _decision_frame(res, brief, lang)
    recs = res["recommendations"]
    ins = _linked_first(res["insights"], recs)[:3]
    wi = next((i for i in res["insights"] if i["type"] == "what_if"), None)
    out = ["---", "marp: true", "paginate: true", f"title: VietLeap 2026 — {tgt}", "---", "",
           "<!-- _class: lead -->", f"# {t(lang, 'pitch_h1', target=tgt)}", f"### {t(lang, 'pitch_h3', rows=fmt.count(m['rows'], lang))}", "",
           t(lang, "pitch_team"), "", _note("hook", t(lang, "pitch_note_hook")), "", "---", ""]
    out += _pitch_question(frame, lang)
    out += _pitch_pipeline(res, de, lang)
    for k, i in enumerate(ins, 1):
        weak = t(lang, "pitch_weak") if _is_weak(i) else ""
        out += [f"## 2.{k} · {text_field(i, 'title', lang)}", "", text_field(i, "sentence", lang), "",
                t(lang, "pitch_test", test=i["test"], p=fmt.p(i["p_value"], lang)) + weak, ""]
        if i.get("chart_png"):
            out += [f"![w:900]({i['chart_png']})", ""]
        out += [_note("insights", t(lang, "pitch_note_insight")), "", "---", ""]
    out += ["<!-- _class: lead -->", f"## {t(lang, 'pitch_demo_heading')}", "", t(lang, "pitch_demo_line"), "",
            _note("demo", t(lang, "pitch_note_demo")), "", "---", ""]
    head, _ = _headline_rec(res)
    r0 = head or (recs[0] if recs else None)
    if r0:
        weak = "" if head else t(lang, "pitch_weak_rec")
        out += [f"## {t(lang, 'pitch_decision_heading')}", "", f"**{text_field(r0, 'now_what', lang)}**{weak}", "",
                "- " + t(lang, "pitch_why", text=text_field(r0, "so_what", lang)),
                "- " + t(lang, "pitch_impact", text=text_field(r0, "impact", lang)),
                "- " + t(lang, "pitch_owner", who=_md_text(frame["who"]), where=_md_text(frame["where"]), kpi=_md_text(frame["kpi"])), "",
                _note("decision", t(lang, "pitch_note_decision")), "", "---", ""]
    out += [f"## {t(lang, 'pitch_impact_heading')}", "",
            text_field(wi, "sentence", lang) if wi else t(lang, "pitch_no_lever"), "",
            _note("decision", t(lang, "pitch_note_whatif")), "", "---", "",
            f"## {t(lang, 'pitch_limits_heading')}", ""] + [f"- {c}" for c in _limitations(res, de, None, 4, lang)] + [
            "", _note("limits", t(lang, "pitch_note_limits")), "", "---", "",
            "<!-- _class: lead -->", f"## {t(lang, 'pitch_close_heading')}", "",
            f"**{text_field(r0, 'now_what', lang)}**" if r0 else t(lang, "pitch_thanks"), "",
            _note("close", t(lang, "pitch_note_close")), ""]
    return "\n".join(out)


def md_to_html(md: str, title: str) -> str:
    body = []
    for line in md.splitlines():
        esc = html.escape(line)
        esc = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc)
        esc = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<i>\1</i>", esc)
        esc = re.sub(r"_(Impact:)_", r"<i>\1</i>", esc)
        if line.startswith("# "):
            body.append(f"<h1>{esc[2:]}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{esc[3:]}</h2>")
        elif line.startswith("- "):
            body.append(f"<li>{esc[2:]}</li>")
        elif line.strip():
            body.append(f"<p>{esc}</p>")
    css = ("body{font-family:Inter,Helvetica,Arial,sans-serif;color:#18181b;max-width:820px;margin:28px auto;font-size:12.5px;line-height:1.45}"
           "h1{font-size:22px;margin:0 0 4px}h2{font-size:15px;margin:16px 0 6px;border-bottom:1px solid #e4e4e7;padding-bottom:4px}p{margin:4px 0}li{margin:2px 0 2px 16px}i{color:#52525b}")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{css}</style></head><body>{''.join(body)}</body></html>"


def html_to_pdf(html_path: Path, pdf_path: Path) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(html_path.resolve().as_uri())
            pg.pdf(path=str(pdf_path), format="A4", margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"})
            b.close()
        return str(pdf_path)
    except Exception as e:
        print(f"[warn] PDF export skipped: {type(e).__name__}: {str(e)[:200]}")
        return None


# ----------------------------------------------------------------------------- static dashboard

def static_dashboard(res: dict, df: pd.DataFrame, whatif: dict | None, out: Path) -> str:
    meta = res["meta"]
    tgt = meta["target"]
    figs = {}
    for i in res["insights"]:
        if i.get("chart"):
            figs[i["id"]] = json.loads(pio.to_json(figure(i["chart"])))
    seg_data = {}
    for c in meta["category_cols"][:8]:
        g = df.groupby(c)[tgt].agg(["median", "size"]).sort_values("median", ascending=False).head(25)
        seg_data[c] = {"x": [str(x) for x in g.index], "median": [r(v) for v in g["median"]], "n": [int(v) for v in g["size"]]}
    ts = res.get("timeseries") or {}
    wi = None
    if whatif:
        wi = {"target": whatif["target"], "log": whatif["log_target"], "base": whatif["target_mean"],
              "features": [{"name": f["name"], "mean": f["mean"], "sd": f["sd"], "beta": f["beta"], "boot": f["boot"][:200]} for f in whatif["features"] if f["numeric"]]}
    payload = {"meta": meta, "kpis": res["kpis"], "insights": [{k: i[k] for k in ("id", "rank", "title_en", "title_vi", "sentence_en", "sentence_vi", "test", "p_value", "score", "type")} for i in res["insights"]],
               "figs": figs, "seg": seg_data, "ts": ts.get("points") if ts else None, "whatif": wi, "recs": res["recommendations"], "caveats": res["caveats"]}
    plotly_js = Path(__import__("plotly").__file__).parent / "package_data" / "plotly.min.js"
    js_lib = plotly_js.read_text(encoding="utf-8") if plotly_js.exists() else ""
    tpl = (Path(__file__).parent / "resources" / "dashboard_template.html").read_text(encoding="utf-8")
    page = tpl.replace("/*PLOTLY*/", js_lib).replace("/*DATA*/", json.dumps(payload, ensure_ascii=False, default=str).replace("</", "<\\/"))
    path = out / "dashboard.html"
    path.write_text(page, encoding="utf-8")
    return str(path)


def _write_language_outputs(res: dict, out: Path, pngs: dict, de: dict | None, brief: dict | None, lang: str) -> dict:
    """FR-303 file matrix: one deck + one pitch per requested language; outputs of a language not requested this run
    are removed so results.json.files, the export endpoint and the web toggle never point at a stale file."""
    files = {}
    langs = langs_for(lang)
    for one in LANGS:
        deck, pitch = out / DECK_FILES[one], out / PITCH_FILES[one]
        if one not in langs:
            deck.unlink(missing_ok=True)
            pitch.unlink(missing_ok=True)
            continue
        files[DECK_KEYS[one]] = os.path.relpath(build_deck(res, out, pngs, de, brief, one), out)
        pitch.write_text(pitch_md(res, de, brief, one), encoding="utf-8")
        files[PITCH_KEYS[one]] = PITCH_FILES[one]
    return files


def build_all(res: dict, df: pd.DataFrame, whatif: dict | None, out: Path, lang: str = DEFAULT_REPORT_LANG,
              include_pdf: bool = True) -> dict:
    """Charts, deck(s), pitch(es), executive summary and static dashboard; `lang` = vi | en | both (decks/pitches)."""
    langs_for(lang)  # validate before any work
    files = {}
    pngs = {}
    todo = [(i, figure(i["chart"]), out / "charts" / f"{i['id']}_{i['type']}.png") for i in res["insights"] if i.get("chart")]
    try:  # one browser session for all charts (much faster than one per chart)
        pio.write_images([t_[1] for t_ in todo], [str(t_[2]) for t_ in todo], width=1000, height=560, scale=2)
        ok = True
    except Exception as e:
        print(f"[warn] PNG export failed ({type(e).__name__}: {str(e)[:200]}); set BROWSER_PATH or run tools/setup_env.sh")
        ok = False
    for i, _, p in todo:
        if ok and p.exists():
            pngs[i["id"]] = str(p)
            i["chart_png"] = os.path.relpath(p, out)
    files["charts"] = len(pngs)
    de, brief = load_de(out), load_brief(out, res["meta"]["target"])
    if brief and brief["stale"]:
        print(f"[warn] brief.json target differs from the analysed target '{res['meta']['target']}' — slide 2 carries a footnote")
    files.update(_write_language_outputs(res, out, pngs, de, brief, lang))
    md = summary_md(res)
    (out / "executive_summary.md").write_text(md, encoding="utf-8")
    hp = out / "executive_summary.html"
    hp.write_text(md_to_html(md, "Executive summary"), encoding="utf-8")
    files["summary_md"] = "executive_summary.md"
    pdf = html_to_pdf(hp, out / "executive_summary.pdf") if include_pdf else None
    files["summary_pdf"] = "executive_summary.pdf" if pdf else None
    files["dashboard_html"] = os.path.relpath(static_dashboard(res, df, whatif, out), out)
    return files


def rebuild_reports(out: Path, lang: str = DEFAULT_REPORT_LANG, include_pdf: bool = True,
                    *, destination: Path | None = None) -> dict:
    """Re-render stored results without rerunning analysis."""
    from shutil import copyfile

    out = Path(out)
    destination = destination or out
    (destination / "charts").mkdir(parents=True, exist_ok=True)
    if destination != out:
        for name in ("pipeline.json", "quality.json", "brief.json", "provenance.json", "scenarios.json"):
            path = out / name
            if path.is_file():
                copyfile(path, destination / name)
    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    clean = out / "clean.parquet"
    frame = pd.read_parquet(clean) if clean.is_file() else pd.read_csv(out / "clean_sample.csv")
    path = out / "whatif.json"
    whatif = json.loads(path.read_text(encoding="utf-8")) if results.get("drivers") and path.is_file() else None
    if whatif and whatif.get("target") != results["meta"]["target"]:
        whatif = None
    return build_all(results, frame, whatif, destination, lang=lang, include_pdf=include_pdf)
