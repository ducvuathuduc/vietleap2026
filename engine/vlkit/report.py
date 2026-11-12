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


# ----------------------------------------------------------------------------- deck

def build_deck(res: dict, out: Path, chart_pngs: dict) -> str:
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
        lines = s if isinstance(s, list) else [s]
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
    # 9 limitations
    n += 1; s = prs.slides.add_slide(blank); header(s, "Limitations & next steps", "What this analysis cannot tell you", n)
    text(s, 0.7, 2.1, 6.2, 4.6, ["• " + c[:140] for c in res["caveats"][:6]], 14)
    card(s, 7.3, 2.1, 5.3, 4.4, "NEXT STEPS", ["• Join external data (income, infrastructure, population) to explain gaps", "• Validate the top lever with a pilot or natural experiment", "• Re-run the pipeline monthly; monitor the KPI set", "• Re-aggregate to the 34-province map (post 1/7/2025)"], 14)
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
    files["deck"] = os.path.relpath(build_deck(res, out, pngs), out)
    md = summary_md(res)
    (out / "executive_summary.md").write_text(md, encoding="utf-8")
    hp = out / "executive_summary.html"
    hp.write_text(md_to_html(md, "Executive summary"), encoding="utf-8")
    files["summary_md"] = "executive_summary.md"
    pdf = html_to_pdf(hp, out / "executive_summary.pdf")
    files["summary_pdf"] = "executive_summary.pdf" if pdf else None
    files["dashboard_html"] = os.path.relpath(static_dashboard(res, df, whatif, out), out)
    return files
