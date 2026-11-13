"""Outputs: chart PNGs, PowerPoint deck, executive summary (MD/HTML/PDF), self-contained static HTML dashboard."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from . import fmt
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
    import re
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


def _thousands(x) -> str:
    try:
        return f"{int(x):,}"
    except (TypeError, ValueError):
        return "—"


# ----------------------------------------------------------------------------- deck

def build_deck(res: dict, out: Path, chart_pngs: dict, de: dict | None = None) -> str:
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

    def text(slide, x, y, w, h, s, size=18, bold=False, color=INK, align=None):
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        lines, size = fit_text([l for l in (s if isinstance(s, list) else [s])], w, h, size, bold)
        lines = lines or [""]
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.size, p.font.bold, p.font.color.rgb, p.font.name = Pt(size), bold, color, "Calibri"
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
        text(slide, 0.7, 7.0, 8, 0.3, "VietLeap 2026 · From Data to Decision", 10, False, MUTED)

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
    top3 = [i for i in ins if i.get("chart")][:3]
    n = 1
    # 1 title
    s = prs.slides.add_slide(blank)
    text(s, 0.9, 1.0, 11, 0.5, "VIETLEAP HACKATHON 2026 · FROM DATA TO DECISION", 14, True, ACCENT)
    text(s, 0.9, 1.8, 11.5, 2.2, f"What drives {tgt}? Evidence and decisions from {meta['rows']:,} records", 40, True)
    text(s, 0.9, 4.4, 11, 0.6, f"Domain: {meta['domain'].replace('_', ' ')} · Source: {meta['source_file']}", 18, False, MUTED)
    text(s, 0.9, 5.6, 11, 0.5, "Team ____ · UEH, 21/11/2026", 18, False, MUTED)
    # 2 problem
    n += 1; s = prs.slides.add_slide(blank); header(s, "Problem & question", "The decision we want to inform", n)
    by = meta.get("geo_col") or (meta["category_cols"][0] if meta["category_cols"] else "segment")
    text(s, 0.7, 2.1, 7.4, 4.5, [f"Question: How does {tgt} vary across {by}{' and over time' if meta.get('time_col') else ''}, and which levers are associated with it?",
                                 "Why it matters: decision makers allocate money and attention by location and segment; mis-reading the data is costly.",
                                 "Success = 3 robust, quantified insights → 3–5 actions with expected impact."], 20)
    card(s, 8.5, 2.1, 4.1, 4.2, "SCOPE", [f"{meta['rows']:,} rows · {meta['columns']} columns", f"Target: {tgt}", f"Time: {meta.get('time_col') or '—'}", f"Geography: {meta.get('geo_col') or '—'}"], 16)
    # 3 data & method
    n += 1; s = prs.slides.add_slide(blank); header(s, "Data & method", "Clean → profile → test → model → decide", n)
    key_log = [l for l in res["cleaning_log"] if any(w in l for w in ["→", "duplicate", "flagged", "derived", "transposed", "stacked", "normalised"])][:5]
    card(s, 0.7, 2.1, 6.0, 4.6, "DATA PREPARATION", [("• " + l)[:120] for l in key_log], 13)
    card(s, 6.9, 2.1, 5.7, 2.4, "METHODS", ["Kruskal–Wallis / Mann–Whitney + effect sizes", "Spearman with Bonferroni & partial correlation", "Ridge + gradient boosting, 5-fold CV, permutation importance", "k-means segmentation · ETS/linear forecast"], 13)
    card(s, 6.9, 4.7, 5.7, 2.0, "CAVEATS", ["• " + c[:110] for c in res["caveats"][:3]], 12)
    q_full = (de or {}).get("quality_full") or {}
    prim = (de or {}).get("primary")
    qp = q_full.get(prim) or (next(iter(q_full.values())) if q_full else None)
    if de:
        # Data pipeline — the 4 stages of the 16/11 workshop
        n += 1; s = prs.slides.add_slide(blank); header(s, "Data pipeline", "Ingestion → Storage → Transform → Serving", n)
        prov = de.get("provenance") or []
        kinds = sorted({p_.get("kind", "?") for p_ in prov})
        rows_in = sum(t.get("rows", 0) for p_ in prov for t in (p_.get("tables") or {}).values())
        tim = de.get("timings") or {}
        qs = de.get("quality") or {}
        q_line = [f"{k.split('.', 1)[-1].split('__')[-1][:20]}: {v['score_before']} → {v['score_after']}" for k, v in list(qs.items())[:2]]
        stages = [
            ("1 · INGESTION", [f"{len(prov)} source(s): {', '.join(kinds)}", f"{_thousands(rows_in)} rows read", "provenance per source (time, licence, fingerprint)", f"{tim.get('ingest', '—')} s"]),
            ("2 · STORAGE", ["DuckDB warehouse + Parquet lake", f"bronze {len(de.get('bronze') or [])} · silver {len(de.get('silver') or [])} · gold {len(de.get('gold') or [])} tables", "raw kept with _src, _ingested_at, _row_hash"]),
            ("3 · TRANSFORM", ["missing · duplicate · outlier (flagged)", "quality score before → after:"] + q_line + [f"{len(de.get('models') or {})} data models · {tim.get('clean', '—')} + {tim.get('model', '—')} s"]),
            ("4 · SERVING", [f"gold OBT → dashboard, SQL, AI analyst", f"recommended: {(de.get('recommended') or {}).get('serving', '—')} for serving, {(de.get('recommended') or {}).get('semantic', '—')} for the semantic layer", "insights + deck + summary from gold"]),
        ]
        for k, (t, body) in enumerate(stages):
            card(s, 0.7 + k * 3.03, 2.05, 2.85, 4.35, t, body, 13)
        text(s, 0.7, 6.5, 11.9, 0.4, "Every number in this deck traces back to a gold table + SQL (lineage: source → bronze → silver → gold → serving).", 12, False, MUTED)

        # Data model — OBT vs Star vs Snowflake vs Data Vault & why
        n += 1; s = prs.slides.add_slide(blank); header(s, "Data model", "OBT vs Star vs Snowflake vs Data Vault — and why", n)
        mods = de.get("models") or {}
        rec = de.get("recommended") or {}
        why = {
            "obt": ("One Big Table", "Fastest for dashboards & ML; easy for non-SQL teammates. Cost: duplicated values."),
            "star": ("Star schema", "Kimball fact + dimensions (time, geography, categories): the model we present to decision makers."),
            "snowflake": ("Snowflake", "Normalised hierarchies (province → 2025 province → region; day → month → year). Fewer duplicates, more joins."),
            "data_vault": ("Data Vault 2.0", "Hubs/links/satellites with hash keys, load_dts, record_source: audit trail across sources. Heavy for 28 h."),
        }
        for k, key in enumerate(["obt", "star", "snowflake", "data_vault"]):
            title, reason = why[key]
            tag = ["✓ Chosen for serving (dashboard, AI)"] if rec.get("serving") == key else (["✓ Chosen for presentation"] if rec.get("semantic") == key else [])
            ntab = len((mods.get(key) or {}).get("tables") or [])
            card(s, 0.7 + k * 3.03, 2.05, 2.85, 3.6, title.upper(), tag + [reason, f"{ntab} table(s) built" if ntab else "not built"], 13)
        text(s, 0.7, 5.8, 11.9, 1.1, [f"Choice: {rec.get('serving', 'obt')} serves the dashboard & AI analyst (no joins); {rec.get('semantic', 'star')} is how we explain the data.",
                                      "Snowflake & Data Vault are built to show hierarchy and auditability — not worth their join/ETL cost in 28 hours."], 13)

        # Data quality before / after
        if qp:
            n += 1; s = prs.slides.add_slide(blank); header(s, "Data quality", "Before → after cleaning (bronze → silver)", n)
            b, a = qp.get("before") or {}, qp.get("after") or {}
            rows = [["Metric", "Before", "After"],
                    ["Rows", _thousands(b.get("rows")), _thousands(a.get("rows"))],
                    ["Missing cells", _thousands(b.get("missing_cells")), _thousands(a.get("missing_cells"))],
                    ["Invalid / text-as-number cells", _thousands(b.get("invalid_cells")), _thousands(a.get("invalid_cells"))],
                    ["Duplicate rows", _thousands(b.get("duplicate_rows")), _thousands(a.get("duplicate_rows"))],
                    ["Quality score (0–100)", str(qp.get("score_before", "—")), str(qp.get("score_after", "—"))]]
            table(s, 0.7, 2.1, 5.6, rows, [3.0, 1.3, 1.3], 13)
            log = [("• " + str(l)) for l in (qp.get("cleaning_log") or [])][:7]
            card(s, 6.6, 2.05, 6.0, 4.6, "CLEANING LOG (EXCERPT)", log or ["(no cleaning steps needed)"], 12)
            text(s, 0.7, 4.5, 5.6, 2.1, ["Outliers are flagged (3×IQR), not deleted; robust statistics (medians, rank tests) are used downstream.",
                                         "Raw data stays in bronze, so every cleaning step can be audited and re-run."], 12, False, MUTED)
    # 4-6 insights
    for k, i in enumerate(top3):
        n += 1; s = prs.slides.add_slide(blank); header(s, f"Insight {k + 1}", i["title_en"], n)
        png = chart_pngs.get(i["id"])
        if png:
            s.shapes.add_picture(png, Inches(0.7), Inches(2.0), width=Inches(7.4))
        card(s, 8.4, 2.0, 4.2, 2.9, "WHAT WE FOUND", i["sentence_en"][:330], 13)
        ev = f"{i['test']} · {fmt.p(i['p_value'])}" if i["p_value"] is not None else i["test"]
        card(s, 8.4, 5.05, 4.2, 1.65, "EVIDENCE", [ev[:110], f"rank score {i['score']:.2f}"], 12)
    # 7 recommendations
    n += 1; s = prs.slides.add_slide(blank); header(s, "Recommendations", "So what → Now what", n)
    y = 2.0
    for k, rc in enumerate(res["recommendations"][:4]):
        text(s, 0.7, y, 0.6, 0.6, f"{k + 1}", 26, True, ACCENT)
        text(s, 1.3, y, 5.2, 1.1, rc["so_what_en"][:150], 14, True)
        text(s, 6.6, y, 6.0, 1.1, [rc["now_what_en"][:170], "Impact: " + rc["impact_en"][:120]], 12)
        y += 1.22
    # 8 what-if
    n += 1; s = prs.slides.add_slide(blank); header(s, "Impact", "What-if scenarios from the fitted model", n)
    wi = next((i for i in ins if i["type"] == "what_if"), None)
    if wi and chart_pngs.get(wi["id"]):
        s.shapes.add_picture(chart_pngs[wi["id"]], Inches(0.7), Inches(2.0), width=Inches(7.4))
        card(s, 8.4, 2.0, 4.2, 4.6, "SCENARIO", [wi["sentence_en"][:260], "", "Association from observational data — validate with a pilot before scaling."], 14)
    else:
        text(s, 0.7, 2.2, 11, 2, "No stable numeric lever was found; the decision layer relies on segment and trend evidence instead.", 20, False, MUTED)
    # Policy recommendation — one decision, owner, KPI, evidence
    recs_ = res["recommendations"]
    if recs_:
        n += 1; s = prs.slides.add_slide(blank); header(s, "Policy recommendation", "From data to decision", n)
        r0 = recs_[0]
        src_i = next((i for i in ins if i["id"] == r0.get("from_insight")), None)
        conf = {"high": "High", "medium": "Medium"}.get(r0.get("confidence"), str(r0.get("confidence") or "—"))
        text(s, 0.7, 2.05, 7.6, 1.5, r0["now_what_en"], 22, True)
        card(s, 0.7, 3.75, 3.7, 2.9, "WHY (SO WHAT)", r0["so_what_en"], 13)
        card(s, 4.6, 3.75, 3.7, 2.9, "EXPECTED IMPACT", [r0["impact_en"], f"Confidence: {conf}"], 13)
        ev = [f"{src_i['test']} · {fmt.p(src_i['p_value'])}" if src_i and src_i.get("p_value") is not None else (src_i or {}).get("test", "—")]
        if src_i and isinstance((src_i.get("evidence") or {}).get("n"), (int, float)):
            ev.append(f"n = {int(src_i['evidence']['n']):,}")
        card(s, 8.5, 2.05, 4.1, 2.3, "EVIDENCE", ev, 12)
        card(s, 8.5, 4.5, 4.1, 2.15, "OWNER · KPI · CHECK", [f"KPI: median {tgt} by segment", "Owner: the decision maker named in the brief",
                                                               "Pilot first, then re-run this pipeline to measure"], 12)
    # 9 limitations
    n += 1; s = prs.slides.add_slide(blank); header(s, "Limitations & next steps", "What this analysis cannot tell you", n)
    lim = ["• " + c for c in res["caveats"][:5]]
    if qp:
        a = qp.get("after") or {}
        if a.get("missing_cells"):
            lim.append(f"• {int(a['missing_cells']):,} cells still missing after cleaning (not imputed unless --impute)")
        if len(((de or {}).get("provenance") or [])) <= 1:
            lim.append("• Single source: no external data joined yet to explain the gaps")
    text(s, 0.7, 2.1, 6.2, 4.6, lim, 14)
    card(s, 7.3, 2.1, 5.3, 4.4, "NEXT STEPS", ["• Join external data (income, infrastructure, population) to explain gaps", "• Validate the top lever with a pilot or natural experiment", "• Re-run the pipeline monthly; monitor the KPI set", "• Re-aggregate to the 34-province map (post 1/7/2025)"], 14)
    # Provenance — source, time, licence, fingerprint (organisers asked for this in the entry test)
    if de and de.get("provenance"):
        n += 1; s = prs.slides.add_slide(blank); header(s, "Data provenance", "Where every number comes from", n)
        rows = [["Source", "Kind", "Location", "Fetched", "Rows × cols", "Fingerprint", "Licence"]]
        for p_ in de["provenance"][:8]:
            for tname, t in list((p_.get("tables") or {}).items())[:2]:
                rows.append([str(p_.get("source", tname))[:24], p_.get("kind", "—"), _short_uri(p_.get("uri", "")), _when(p_.get("fetched_at")),
                             f"{_thousands(t.get('rows'))} × {t.get('cols', '—')}", str(t.get("fingerprint", "—"))[:16], (p_.get("license_note") or "see source")[:30]])
        rows = rows[:10]
        table(s, 0.7, 2.05, 11.9, rows, [1.7, 0.8, 2.7, 2.0, 1.4, 1.6, 1.7], 11)
        text(s, 0.7, 6.3, 11.9, 0.5, "Full provenance (settings, read log, bytes) in provenance.json; lineage graph in lineage.json / the dashboard Pipeline page.", 12, False, MUTED)
    # 10 Q&A
    n += 1; s = prs.slides.add_slide(blank); header(s, "Team & Q&A", "Thank you — questions?", n)
    text(s, 0.7, 2.1, 6, 4, ["Team members: ____", "Roles: data · analysis · dashboard · story", "Dashboard: live web app + static HTML", "Code & method: reproducible pipeline (run.py)"], 18)
    card(s, 7.3, 2.1, 5.3, 4.4, "LIKELY JUDGE QUESTIONS", ["Is this causal? → No: associations; pilot proposed", "How did you treat outliers? → flagged, robust stats", "How representative is the data? → see caveats", "What would you do with 1 more week? → join external data"], 13)
    path = out / "deck.pptx"
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


PITCH_TIMING = [("Vấn đề", "0:00–0:45"), ("Dữ liệu & pipeline", "0:45–2:00"), ("3 insight", "2:00–4:00"), ("Quyết định đề xuất", "4:00–5:00"),
                ("Tác động", "5:00–5:45"), ("Hạn chế", "5:45–6:15"), ("Demo", "6:15–7:00")]


def pitch_md(res: dict, de: dict | None = None) -> str:
    """Marp deck for the 7-minute pitch, filled with this dataset's engine numbers (template: slides/pitch.md)."""
    m = res["meta"]
    tgt = m["target"]
    ins = res["insights"][:3]
    recs = res["recommendations"]
    wi = next((i for i in res["insights"] if i["type"] == "what_if"), None)
    q = None
    if de and de.get("quality"):
        q = de["quality"].get(de.get("primary")) or next(iter(de["quality"].values()))
    prov = (de or {}).get("provenance") or []
    out = ["---", "marp: true", "paginate: true", f"title: VietLeap 2026 — {tgt}", "---", "",
           "<!-- _class: lead -->", f"# Điều gì quyết định {tgt}?", f"### Từ {m['rows']:,} bản ghi đến một quyết định".replace(",", "."), "", "Đội ____ · VietLeap 2026 · From Data to Decision", "",
           f"<!-- {PITCH_TIMING[0][1]} · Vấn đề: ai đang phải quyết định điều gì, vì sao sai thì tốn kém. -->", "", "---", "",
           "## 1 · Dữ liệu & pipeline", ""]
    if prov:
        out.append(f"- **Ingestion:** {len(prov)} nguồn ({', '.join(sorted({p_.get('kind', '?') for p_ in prov}))}), có provenance")
        out.append(f"- **Storage:** DuckDB bronze/silver/gold · **Transform:** làm sạch + OBT/Star/Snowflake/Data Vault")
        if q:
            out.append(f"- **Chất lượng:** điểm {q['score_before']} → {q['score_after']} (missing, duplicate, outlier gắn cờ)")
        out.append(f"- **Serving:** dashboard + AI Analyst trên bảng gold ({(de.get('recommended') or {}).get('serving', 'obt')})")
    else:
        out.append(f"- {m['rows']:,} dòng".replace(",", ".") + f" × {m['columns']} cột · nguồn: {m['source_file']}")
    out += ["", f"<!-- {PITCH_TIMING[1][1]} · Nói đúng 4 giai đoạn workshop; vì sao OBT phục vụ dashboard, Star để trình bày. -->", "", "---", ""]
    for k, i in enumerate(ins, 1):
        out += [f"## 2.{k} · {i['title_vi']}", "", i["sentence_vi"], "", f"*Kiểm định: {i['test']} · {fmt.p(i['p_value'])}*", ""]
        if i.get("chart_png"):
            out += [f"![w:900]({i['chart_png']})", ""]
        out += [f"<!-- {PITCH_TIMING[2][1]} · Mỗi insight ~40 giây: con số → vì sao quan trọng → lưu ý. -->", "", "---", ""]
    if recs:
        r0 = recs[0]
        out += ["## 3 · Quyết định đề xuất", "", f"**{r0['now_what_vi']}**", "", f"- Vì sao: {r0['so_what_vi']}", f"- Tác động ước tính: {r0['impact_vi']}",
                f"- KPI theo dõi: trung vị {tgt} theo phân khúc · Ai thực hiện: ____", "", f"<!-- {PITCH_TIMING[3][1]} · Ai làm gì, ở đâu, đo bằng KPI nào. -->", "", "---", ""]
    out += ["## 4 · Tác động", ""]
    out += [wi["sentence_vi"] if wi else "Chưa có đòn bẩy số ổn định — tác động dựa trên khoảng cách giữa các phân khúc.", "",
            f"<!-- {PITCH_TIMING[4][1]} · Dùng trang Drivers & What-if để minh hoạ trực tiếp. -->", "", "---", "",
            "## 5 · Hạn chế", ""] + [f"- {c}" for c in res["caveats"][:4]] + ["", f"<!-- {PITCH_TIMING[5][1]} · Chủ động nói trước khi giám khảo hỏi. -->", "", "---", "",
            "<!-- _class: lead -->", "## Demo: Câu chuyện insight + Hỏi AI", "", "Dashboard → nút **Câu chuyện** → bấm **Hỏi AI** vào một biểu đồ", "",
            f"<!-- {PITCH_TIMING[6][1]} · Nếu mạng lỗi: chế độ offline vẫn chạy; có video dự phòng. -->", ""]
    return "\n".join(out)


def md_to_html(md: str, title: str) -> str:
    import re
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


def build_all(res: dict, df: pd.DataFrame, whatif: dict | None, out: Path) -> dict:
    files = {}
    pngs = {}
    todo = [(i, figure(i["chart"]), out / "charts" / f"{i['id']}_{i['type']}.png") for i in res["insights"] if i.get("chart")]
    try:  # one browser session for all charts (much faster than one per chart)
        pio.write_images([t[1] for t in todo], [str(t[2]) for t in todo], width=1000, height=560, scale=2)
        ok = True
    except Exception as e:
        print(f"[warn] PNG export failed ({type(e).__name__}: {str(e)[:200]}); set BROWSER_PATH or run tools/setup_env.sh")
        ok = False
    for i, _, p in todo:
        if ok and p.exists():
            pngs[i["id"]] = str(p)
            i["chart_png"] = os.path.relpath(p, out)
    files["charts"] = len(pngs)
    files["deck"] = os.path.relpath(build_deck(res, out, pngs, load_de(out)), out)
    md = summary_md(res)
    (out / "executive_summary.md").write_text(md, encoding="utf-8")
    hp = out / "executive_summary.html"
    hp.write_text(md_to_html(md, "Executive summary"), encoding="utf-8")
    files["summary_md"] = "executive_summary.md"
    (out / "pitch.md").write_text(pitch_md(res, load_de(out)), encoding="utf-8")
    files["pitch_md"] = "pitch.md"
    pdf = html_to_pdf(hp, out / "executive_summary.pdf")
    files["summary_pdf"] = "executive_summary.pdf" if pdf else None
    files["dashboard_html"] = os.path.relpath(static_dashboard(res, df, whatif, out), out)
    return files
