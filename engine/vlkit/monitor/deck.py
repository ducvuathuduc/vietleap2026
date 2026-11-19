"""Build locally reproducible presenter files from a monitor payload."""
from __future__ import annotations

import html
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import fill

from matplotlib import image as mpl_image, rc_context
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches, Pt

from .deck_copy import (SECTORS, SECTOR_NOTES, card_en, day, indicator_name, measure, number, period,
                        recommendation_parts, tidy)


W, H = 13.333, 7.5
INK, GREY, FAINT = "#20242b", "#515964", "#797f88"
FONT = "Arial"
METHODS = {
    "api": ("API", "API"), "file": ("Tệp và PDF", "Files and PDFs"),
    "scrape": ("Trang web tĩnh", "Static web pages"), "tinyfish": ("Trích xuất bằng TinyFish", "TinyFish extraction"),
    "social": ("Tin RSS", "RSS feeds"),
}
CHARTS = {
    "public_finance": ("nsnn_chi_pct_plan", "nsnn_thu_pct_plan", "budget_time_pace"),
    "fdi": ("fdi_thuc_hien_ytd", "fdi_dang_ky_ytd"), "banking": ("bank_npl",),
    "capital_market": ("market_liquidity_20d",), "real_estate": ("re_absorption",),
}
EXTRA_FACTS = {
    "public_finance": ("nsnn_thu_pct_plan",), "fdi": ("fdi_dang_ky_ytd",),
    "real_estate": ("re_new_supply", "mortgage_rate"),
}
LEGEND_VI = {
    "nsnn_chi_pct_plan": "Chi ngân sách", "nsnn_thu_pct_plan": "Thu ngân sách", "budget_time_pace": "Mốc theo thời gian",
    "fdi_thuc_hien_ytd": "Vốn thực hiện", "fdi_dang_ky_ytd": "Vốn đăng ký",
}


@dataclass
class Box:
    text: str
    x: float
    y: float
    w: float
    h: float
    size: float
    bold: bool = False
    color: str = INK
    link: int | None = None


@dataclass
class Chart:
    title: str
    source: str
    png: bytes


@dataclass
class Slide:
    title: str
    lang: str
    notes: str
    boxes: list[Box] = field(default_factory=list)
    chart: Chart | None = None

    def text(self, text, x, y, w, h, size, bold=False, color=INK, *, link=None):
        self.boxes.append(Box(text, x, y, w, h, size, bold, color, link))

    def all_boxes(self):
        cover = self.boxes and self.boxes[0].y >= 4
        title = Box(self.title, .72, 1.56 if cover else .63, 11.89, 2.39 if cover else 1.30,
                    43 if cover else 32, True)
        return [title, *self.boxes]


PLOT = (.68, 2.58, 7.08, 3.54)


def _chart_png(curves, labels, unit, lang, *, bars=False, share_track=False):
    with rc_context({"font.family": [FONT, "DejaVu Sans"], "font.size": 11, "text.color": INK,
                     "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY}):
        fig = Figure(figsize=(7.08, 3.54), dpi=165, facecolor="white")
        FigureCanvasAgg(fig)
        ax = fig.add_subplot()
        fig.subplots_adjust(left=.16 if bars else .13, right=.80 if bars else .82, top=.84, bottom=.19)
        ax.spines[:].set_visible(False)
        ax.tick_params(length=0, pad=8)
        if bars:
            values = curves[0]
            if share_track and 0 <= values[0] <= 100:
                ax.barh(labels, [100], color="#E5E7EB", height=.38)
                ax.set_xlim(0, 106)
            ax.barh(labels, values, color=[INK, *(["#BFC3C9"] * (len(values) - 1))], height=.38 if share_track else .56)
            for i, value in enumerate(values):
                ax.annotate(measure(value, unit, lang), (value, i), xytext=(6, 0), textcoords="offset points",
                            va="center", color=INK, weight="bold" if i == 0 else "normal", clip_on=False)
            ax.set_xticks([])
            ax.invert_yaxis()
        else:
            ax.grid(axis="y", color="#E5E7EB", linewidth=.7)
            all_values = [value for _, series in curves for value in series]
            bounds = sorted({min(all_values), max(all_values)})
            ax.set_yticks(bounds, [number(value, 1, lang) for value in bounds])
            x = range(len(labels))
            for i, (name, values) in enumerate(curves):
                color = (INK, "#707781", "#A9AFB7")[i]
                ax.plot(x, values, color=color, linewidth=2.8 if i == 0 else 1.8,
                        linestyle="--" if i == 2 else "-", label=name)
                ax.scatter([len(labels) - 1], [values[-1]], s=21, color=color, zorder=3)
                ax.annotate(measure(values[-1], unit, lang), (len(labels) - 1, values[-1]),
                            xytext=(6, 0), textcoords="offset points", va="center", color=color,
                            weight="bold" if i == 0 else "normal", clip_on=False)
            indexes = sorted({0, len(labels) // 2, len(labels) - 1})
            ax.set_xticks(indexes, [labels[i] for i in indexes])
            if len(curves) > 1:
                ax.legend(loc="lower left", bbox_to_anchor=(0, 1.03), ncols=len(curves), frameon=False,
                          fontsize=10, borderaxespad=0, handlelength=1.2, columnspacing=1.0)
        buffer = BytesIO()
        fig.savefig(buffer, format="png", facecolor="white")
        return buffer.getvalue()


def _series(payload, indicator, *, all_geos=False):
    points = payload["series"].get(indicator["id"]) or indicator.get("sparkline", [])
    usable = [p for p in points if isinstance(p["value"], (float, int)) and math.isfinite(p["value"])]
    if all_geos:
        return sorted(usable, key=lambda point: point["period"])
    for method in (lambda p: p.get("geo") in (None, "", "VNM"), lambda p: p.get("geo") == "TP.HCM"):
        if scoped := [p for p in usable if method(p)]:
            return sorted(scoped, key=lambda point: point["period"])
    return usable if len({p.get("geo") for p in usable}) == 1 else []


def _citation(sources, source_ids, observed, lang):
    publishers = list(dict.fromkeys(sources[key]["publisher"] for key in source_ids if key in sources))
    dates = [sources[key]["fetched_at"] for key in source_ids if key in sources]
    when = f" · {period(observed, lang)}" if observed else ""
    if dates:
        when += f" · {'truy xuất' if lang == 'vi' else 'retrieved'} {day(max(dates))}"
    return f"{'Nguồn' if lang == 'vi' else 'Source'}  {' / '.join(publishers)}{when}"


def _sector_chart(payload, sector_id, indicators, sources, lang):
    ids = CHARTS[sector_id]
    section = payload["sectors"].get(sector_id, {})
    ids = list(dict.fromkeys([*ids, *(i for chart in section.get("charts", []) for i in chart["indicator_ids"])]))
    series = [(indicators[key], _series(payload, indicators[key], all_geos=key == "bank_npl"))
              for key in ids if key in indicators]
    series = [(indicator, points) for indicator, points in series if points]
    if not series:
        return None
    lead, points = series[0]
    latest, unit = points[-1]["period"], lead["unit"]
    caption = indicator_name(lead, lang)
    source_ids = [lead["source_id"]]
    if lead["id"] == "bank_npl":
        selected = sorted((p for p in points if p["period"] == latest and p.get("geo")),
                          key=lambda p: (-p["value"], p["geo"]))[:5]
    else:
        selected = []
    if selected or len(points) == 1:
        bars = selected or [points[-1]]
        pic = _chart_png([[p["value"] for p in bars]], [p.get("geo") or period(latest, lang) for p in bars],
                         unit, lang, bars=True, share_track=lead["id"] == "re_absorption")
    else:
        points = points[-24:] if lead["frequency"] == "daily" else points[-8:]
        aligned = [p["period"] for p in points]
        labels = LEGEND_VI if lang == "vi" else {}
        curves = [(labels.get(lead["id"], caption), [p["value"] for p in points])]
        for indicator, peer in series[1:len(CHARTS[sector_id])]:
            values = {p["period"]: p["value"] for p in peer}
            if indicator["unit"] == unit and all(p in values for p in aligned):
                name = labels.get(indicator["id"]) or indicator_name(indicator, lang)
                curves.append((name, [values[p] for p in aligned]))
                source_ids.append(indicator["source_id"])
        pic = _chart_png(curves, [period(p, lang, short=True) for p in aligned], unit, lang)
        if len(curves) > 1:
            caption = ("Tiến độ thu và chi so với dự toán" if lang == "vi" else "Revenue and spending against plan") if (
                sector_id == "public_finance") else ("Vốn đăng ký và vốn thực hiện" if lang == "vi" else "Registered and realized FDI")
    return Chart(caption, _citation(sources, source_ids, latest, lang), pic)


def _sector_facts(payload, sector_id, indicators, lang):
    section = payload["sectors"].get(sector_id, {})
    cards = section.get("cards", [])[:3]
    lines = [tidy(c["sentence_vi"]) if lang == "vi" else card_en(c, indicators) for c in cards]
    extra = list(dict.fromkeys([*EXTRA_FACTS.get(sector_id, ()), *section.get("kpi_ids", [])]))
    used = {c.get("indicator_id") for c in cards}
    for key in extra:
        if len(lines) >= 3:
            break
        if key in used or key not in indicators:
            continue
        indicator = indicators[key]
        points = _series(payload, indicator)
        if points:
            last = points[-1]
            lines.append(f"{indicator_name(indicator, lang)} {'đạt' if lang == 'vi' else 'is'} "
                         f"{measure(last['value'], indicator['unit'], lang)} · {period(last['period'], lang)}.")
    return cards, lines


def _recommendations(payload):
    selected = []
    seen = set()
    for rec in payload["recommendations"]:
        sector = rec.get("sector", rec["id"])
        if sector not in seen:
            seen.add(sector)
            selected.append(rec)
    return selected[:3]


def _plain(title, notes, lang, lines):
    slide = Slide(title, lang, notes)
    for i, (label, body) in enumerate(lines):
        offset = 2.25 + i * 1.39
        slide.text(label, .74, offset, 3.05, .88, 21, True)
        slide.text(body, 3.91, offset, 8.48, 1.25, 21)
    return slide


def _collection(payload, lang):
    vi = lang == "vi"
    slide = Slide("Nguồn gốc dữ liệu được ghi theo cách thu thập" if vi else "Each source records how its data was collected", lang,
                  "Dòng số liệu được đếm tại nguồn, trước khi ghép theo kỳ và địa bàn. API cung cấp lịch sử theo chuỗi. Tệp và bản công bố lưu điều kiện sử dụng. "
                  "TinyFish hỗ trợ đọc báo cáo theo nguồn. Tin RSS bổ sung ngữ cảnh và được đếm riêng với quan sát tài chính." if vi else
                  "These counts describe source records before they are joined by period and geography. APIs provide historical series. Files preserve published tables and reuse terms. "
                  "TinyFish helps extract figures from reports. The RSS counts describe news enrichment and are separate from the financial observations.")
    columns = [(0.74, 4.35), (5.12, 1.55), (6.71, 2.71), (9.45, 3.0)]
    headers = ("Cách thu thập", "Nguồn", "Dòng", "Truy xuất gần nhất") if vi else ("Collection method", "Sources", "Rows", "Last retrieved")
    for label, (x, width) in zip(headers, columns, strict=True):
        slide.text(label, x, 2.05, width, .36, 14, True, GREY)
    for i, (method, name) in enumerate(METHODS.items()):
        group = [source for source in payload["sources"] if source["method"] == method or
                 (method == "file" and source["method"] == "pdf")]
        date = day(max(s["fetched_at"] for s in group)) if group else "–"
        values = (name[not vi], number(len(group), 0, lang), number(sum(s.get("rows", 0) for s in group), 0, lang), date)
        for value, (x, width) in zip(values, columns, strict=True):
            slide.text(value if group or x == .74 else "–", x, 2.62 + i * .63, width, .52, 20, x == .74)
    slide.text("Tin RSS bổ sung ngữ cảnh. Cơ sở dữ liệu phục vụ lưu trữ và tra cứu." if vi else
               "RSS supplies context. The database is used for storage and retrieval.", .74, 6.20, 11.6, .42, 15, color=GREY)
    return slide


def _workflow(payload, sources, lang):
    vi = lang == "vi"
    slide = Slide("Chỉ tiêu công bố truy về được nguồn" if vi else "Every published measure can be traced to its source", lang,
                  "Dữ liệu mới được ghi ở dạng gốc để kiểm tra lại. Sau đó, kiểu dữ liệu, kỳ, địa bàn và đơn vị được chuẩn hóa, còn ngoại lệ được đánh dấu. "
                  "Bảng số liệu trung tâm nối với các bảng tra cứu của mô hình sao. Đọc tỷ lệ chất lượng cùng phạm vi nguồn và kiểm tra số đo có nguồn độc lập trước khi đối chiếu." if vi else
                  "We keep the source records in their original form. Types, dates, geography and units are standardized, and unusual values are flagged. "
                  "The fact table joins to the dimensions of a star schema. Read quality scores within each source and compare sources only when they report the same measure and period.")
    steps = ("Thu thập", "Lưu trữ", "Chuẩn hóa", "Công bố") if vi else ("Ingestion", "Storage", "Transform", "Serving")
    for i, step in enumerate(steps):
        slide.text(step, .75 + i * 3.08, 2.07, 2.72, .52, 21, True)
        if i < len(steps) - 1:
            slide.text("→", 2.85 + i * 3.08, 2.07, .42, .52, 21, color=FAINT)
    layers = Counter()
    for table in payload.get("model", {}).get("tables", []):
        layers[table["layer"]] += table["rows"]
    slide.text("  ·  ".join(f"{layer.title()} {number(layers[layer], 0, lang)}" for layer in ("bronze", "silver", "gold") if layer in layers),
               .75, 2.78, 11.9, .46, 20)
    diagram = ("Kỳ  ·  Địa bàn  ·  Chỉ tiêu  ·  Nguồn   →   Bảng số liệu" if vi else
               "Period  ·  Geography  ·  Indicator  ·  Source   →   Fact table")
    slide.text(("Mô hình sao  " if vi else "Star schema  ") + diagram, .75, 3.49, 11.9, .52, 19, True)
    if payload["quality"]:
        quality = max(payload["quality"], key=lambda item: item["rows"])
        source = sources.get(quality["source_id"], {}).get("publisher", "")
        before, after = (number(quality[score], 2, lang) for score in ("score_before", "score_after"))
        slide.text(f"{'Điểm chất lượng trước và sau chuẩn hóa' if vi else 'Quality score before and after standardization'} · {source}  {before} → {after}",
                   .75, 4.45, 11.85, .52, 19)
        if 'outlier' in quality["flags"]:
            count = number(quality["flags"]["outlier"], 0, lang)
            slide.text(f"{count} {'dòng được gắn cờ ngoại lệ' if vi else 'rows flagged as outliers'}", .75, 5.10, 11.85, .47, 19)
    verdicts = Counter(r["verdict"] for r in payload["reconciliation"])
    labels = {"match": ("khớp", "match"), "mismatch": ("lệch", "differ"), "single_source": ("chỉ có một nguồn", "have one source")}
    if verdicts:
        line = "  ·  ".join(f"{number(value, 0, lang)} {labels[key][not vi]}" for key, value in sorted(verdicts.items()))
        slide.text(f"{'Đối chiếu theo cùng kỳ và đơn vị' if vi else 'Reconciliation by common period and unit'}  {line}",
                   .75, 5.75, 11.85, .52, 19)
    return slide


def _provinces(payload, sources, lang):
    vi = lang == "vi"
    table = next((table for table in payload["sectors"].get("public_finance", {}).get("tables", [])
                  if table["id"] == "province_disbursement"), None)
    if not table:
        return _plain("Chưa có tỷ lệ giải ngân để chia nhóm địa phương" if vi else "Provincial disbursement rates are unavailable",
                      "Phần này cần tỷ lệ giải ngân cùng kỳ từ một nguồn so sánh được. Khoản bổ sung có mục tiêu là một phép đo riêng. "
                      "Khi phụ lục mới được công bố, hãy kiểm tra số địa phương có tỷ lệ hợp lệ rồi mới phân nhóm." if vi else
                      "This comparison needs disbursement rates for a common period from one comparable source. Earmarked transfers are a separate measure. "
                      "When the next appendix is published, check which provinces have valid figures before making the comparison or calculating group boundaries.", lang,
                      [("Phạm vi" if vi else "Scope", "Thiếu bảng tỷ lệ giải ngân cùng kỳ." if vi else "No comparable disbursement table for this period.")])
    groups = table["rows"]
    observed = groups[0]["period"]
    count = number(sum(row["count"] for row in groups), 0, lang)
    title = (f"Có tỷ lệ giải ngân cho {count} tỉnh, thành phố" if vi else f"Disbursement rates cover {count} provinces and cities")
    slide = Slide(f"{title} · {period(observed, lang)}", lang,
                  "Các nhóm dùng cùng kỳ và một báo cáo để tỷ lệ có thể so sánh. Khoảng trên mỗi hàng là giá trị thấp nhất và cao nhất thực tế trong nhóm. "
                  "Các tỷ lệ bằng nhau ở cùng nhóm. Dùng số địa phương trong từng khoảng để chọn nhóm cần xem hồ sơ dự án." if vi else
                  "The groups come from a single release and period so the rates are comparable. Each range shows its lowest and highest recorded rates. "
                  "Equal values stay together at a boundary. Use the counts to select groups for a closer review of payment and project records.")
    slide.text("Khoảng tỷ lệ so với kế hoạch" if vi else "Range of rates against plan", .75, 2.14, 7.0, .45, 17, True, GREY)
    slide.text("Số tỉnh, thành phố" if vi else "Provinces and cities", 8.01, 2.14, 3.2, .45, 17, True, GREY)
    for i, row in enumerate(groups):
        interval = ' – '.join(measure(row[key], "%", lang) for key in ("min", "max"))
        slide.text(interval, .75, 2.71 + i * .55, 6.9, .51, 22, i == 0)
        slide.text(number(row["count"], 0, lang), 8.01, 2.71 + i * .55, 3.0, .51, 22, i == 0)
    slide.text(_citation(sources, table["source_ids"], observed, lang), .75, 6.11, 11.85, .58, 15, color=GREY)
    return slide


def _recommendation_slide(payload, cards, indicators, lang):
    vi = lang == "vi"
    recs = _recommendations(payload)
    title = "Chênh lệch hiện tại xác định hồ sơ cần rà soát" if vi else "The observed gaps identify which records to review"
    slide = Slide(title, lang,
                  "Đọc mỗi cột từ bằng chứng tới hàm ý, sau đó đến việc cần làm và cơ quan thực hiện. Mỗi việc có hạn và một đối tượng đo được. "
                  "Các hàm ý dựa trên số liệu của kỳ công bố. Khi nhận số liệu mới, hãy kiểm tra lại điều kiện trước khi giao việc." if vi else
                  "Read each column from the evidence to the implication, then to the proposed action and agency. Each action has a deadline and an object to measure. "
                  "The implications are conditional on the current release. Check the thresholds again when the next comparable observations arrive.")
    labels = ("Bằng chứng", "Hàm ý", "Hành động", "Cơ quan") if vi else ("Evidence", "Implication", "Action", "Agency")
    for i, rec in enumerate(recs):
        x = .74 + i * 4.05
        evidence, implication, action, agency = recommendation_parts(rec, lang, cards, indicators)
        if vi:
            evidence = tidy(rec["title_vi"])
        sector = rec.get("sector")
        target = 4 + list(SECTORS).index(sector) if sector in SECTORS else None
        for j, (label, value) in enumerate(zip(labels, (evidence, implication, action, agency), strict=True)):
            y = (1.93, 3.34, 4.71, 6.06)[j]
            slide.text(label, x, y, 3.78, .32, 13, True, GREY)
            slide.text(value, x, y + .33, 3.78, 1.04, 14, j == 3, link=target if j == 0 else None)
    if not recs:
        slide.text("Chưa có khuyến nghị đủ bằng chứng." if vi else "No recommendation has sufficient evidence.",
                   .74, 2.4, 11.0, .60, 22)
    return slide


def slides_for(payload, lang):
    vi = lang == "vi"
    meta = payload["meta"]
    indicators = {indicator["id"]: indicator for indicator in payload["indicators"]}
    sources = {source["id"]: source for source in payload["sources"]}
    cards = {c["rule_id"]: c for s in payload["sectors"].values() for c in s["cards"]}
    cover_en = "Tracking Vietnam’s public finances and markets"
    sector_slides = []
    for sector_id, name in SECTORS.items():
        facts, lines = _sector_facts(payload, sector_id, indicators, lang)
        heading = payload["sectors"].get(sector_id, {}).get("headline_vi", "Chưa có số liệu cho kỳ này") if vi else (
            card_en(facts[0], indicators) if facts else (lines[0].rstrip('.') if lines else "No observations for this period"))
        if payload["sectors"].get(sector_id, {}).get("headline_vi") == meta["title_vi"]:
            if not vi:
                cover_en = heading
            if sector_id == "public_finance" and (spending := indicators.get("nsnn_chi_pct_plan")):
                latest = spending["latest"]
                if latest["value"] is not None:
                    amount = measure(latest["value"], spending["unit"], lang)
                    when = period(latest["period"], lang)
                    heading = (f"Chi ngân sách đạt {amount} dự toán · {when}" if vi else
                               f"Budget spending reaches {amount} of plan · {when}")
        notes = " ".join([*lines[:1], SECTOR_NOTES[sector_id][not vi]])
        slide = Slide(tidy(heading), lang, notes, chart=_sector_chart(payload, sector_id, indicators, sources, lang))
        slide.text(name[not vi], .74, .25, 11.8, .34, 12, True, GREY)
        if slide.chart:
            slide.text(slide.chart.title, .74, 2.16, 6.96, .38, 16, True)
            slide.text(slide.chart.source, .74, 6.38, 7.02, .60, 13, color=GREY)
        else:
            slide.text("Chưa đủ số liệu để vẽ biểu đồ." if vi else "Not enough data for a chart.", .74, 2.75, 6.85, .8, 20)
        for i, line in enumerate(lines):
            if vi and i < len(facts):
                line = re.split(r", (?:khi|với|trong khi|tính trên|tính mức|thuộc nhóm) ", line, maxsplit=1)[0].rstrip(".") + "."
                if facts[i]["rule_id"] == "BR-CM1" and "thuộc nhóm" in lines[i]:
                    line = "Thanh khoản thuộc nhóm" + lines[i].split("thuộc nhóm", 1)[1]
            slide.text(line, 8.10, 2.30 + i * 1.38, 4.42, 1.32, 17, color=INK)
        sector_slides.append(slide)

    cover_title = meta["title_vi"] if vi else cover_en
    cover = Slide(tidy(cover_title), lang,
                  "Mở đầu bằng kết quả ngân sách ở kỳ mới nhất. Cùng một số liệu, người xem có thể xem nguồn, lần công bố và mức chênh so với mốc tiến độ. "
                  "Phần trình bày tiếp theo đi qua từng thị trường và kết thúc với những hồ sơ có thể giao cho cơ quan phụ trách." if vi else
                  "Open with the latest budget result. The audience can trace the number to its source, release and reference point. "
                  "Then follow how capital appears in investment, banks, traded markets and housing. Close by identifying records that specific agencies can review during the coming quarter.")
    cover.text(f"{'Bản công bố' if vi else 'Snapshot'} {day(meta['generated_at'])} · {'giờ Việt Nam' if vi else 'Vietnam time'}",
               .75, 4.23, 11.8, .65, 22, color=GREY)
    cover.text("VietLeap · Theo dõi tài chính Việt Nam" if vi else "VietLeap · Vietnam Financial Monitor", .75, 6.32, 11.8, .4, 17)

    question = _plain("Đo khoảng cách từ nguồn vốn đến thực hiện" if vi else "Where capital falls short of execution",
                      "Câu hỏi nối các dòng vốn với phần đã thực hiện. Chọn tài chính Việt Nam vì dữ liệu có cơ quan công bố và có kỳ quan sát rõ, "
                      "đồng thời phù hợp với nền tảng tài chính công của nhóm. Trang theo dõi cho phép đi từ cả nước xuống ngành và địa phương." if vi else
                      "The question connects funding with execution. We chose Vietnam's financial system because clear reporting periods and named publishers make the evidence traceable. "
                      "It also matches the team's public finance background. The published dashboard lets reviewers move from the national results to a sector or locality.", lang,
                      [("Câu hỏi" if vi else "Question", tidy(meta["question_vi"]) if vi else
                        "Where does capital stall between revenue, spending, investment and economic growth?"),
                       ("Cơ sở chọn lĩnh vực" if vi else "Why this domain", "Nguồn công bố chính thức và dữ liệu giao dịch cho phép so sánh theo kỳ. "
                        "Nhóm có nền tảng tài chính công." if vi else "Official releases and trading data let us compare across periods. The team brings a public finance background."),
                       ("Cách tra cứu" if vi else "How to explore", "Từ cả nước đến từng ngành và địa phương." if vi else "Move from national results to sectors and localities.")])
    limits = _plain("Phạm vi công bố quyết định phép so sánh" if vi else "Reporting coverage determines which comparisons hold",
                    "Mỗi nguồn có định nghĩa và kỳ riêng. Khi địa giới hoặc rổ dự án đổi, xem lại phạm vi trước khi nối chuỗi. "
                    "Tỷ trọng FDI dùng nhóm tỉnh có số liệu và chỉ tiêu thị trường dùng các phiên quan sát được. Dùng những mối liên hệ này để đặt câu hỏi kiểm tra tiếp." if vi else
                    "Each publisher uses its own coverage and reporting period. Check geography and the projects included before linking time series. "
                    "The FDI measure applies to observed provinces and market statistics to observed sessions. Treat the patterns as evidence for follow-up rather than causal estimates.", lang,
                    [("Định nghĩa" if vi else "Definitions", "So sánh cùng kỳ, đơn vị và cơ sở tính. Rổ dự án TP.HCM thay đổi theo kỳ công bố." if vi else
                      "Match period, units and denominator. The Ho Chi Minh City project basket changes across releases."),
                     ("Độ phủ" if vi else "Coverage", "Tỷ trọng FDI theo tỉnh chỉ tính trên nhóm có số liệu." if vi else
                      "Provincial FDI concentration covers the provinces with published figures."),
                     ("Diễn giải" if vi else "Interpretation", "Các phép so sánh mô tả số liệu quan sát được." if vi else
                      "These comparisons describe observed figures and establish no causal effect.")])
    tomorrow = _plain("Lần chạy lại cập nhật khi có nguồn mới" if vi else "A rerun incorporates new releases",
                      "GitHub Actions thu lại dữ liệu WDI mỗi sáng theo giờ Việt Nam. Khi có tệp nguồn mới, chạy lại quy trình giám sát để kiểm định và công bố. "
                      "Lần chạy sau kiểm tra mã băm của tệp. Bản ghi trùng khóa giữ bản công bố hợp lệ mới nhất, rồi tạo lại các tệp phục vụ thuyết trình." if vi else
                      "GitHub Actions retrieves WDI each morning, Vietnam time. After a new source file lands, rerun the monitor to validate and publish it. "
                      "File checksums identify unchanged inputs. For duplicate observation keys, keep the latest valid release, then regenerate the published files for the next meeting.", lang,
                      [("Lịch nguồn" if vi else "Source schedule", "GitHub Actions thu WDI mỗi sáng theo giờ Việt Nam. Các nguồn khác theo kỳ công bố." if vi else
                        "GitHub Actions collects WDI each morning, Vietnam time. Other sources follow their release calendars."),
                       ("Chạy lại" if vi else "Rerun", "Đối chiếu tệp mới bằng mã băm và giữ bản công bố hợp lệ theo khóa quan sát." if vi else
                        "Compare files by checksum and keep the latest valid release for each observation key."),
                       ("Công bố" if vi else "Publish", "Cập nhật trang theo dõi, tệp trình chiếu và bản tóm tắt từ cùng một bản dữ liệu." if vi else
                        "Refresh the dashboard, slides and brief from the same snapshot.")])
    return [cover, question, _collection(payload, lang), _workflow(payload, sources, lang), *sector_slides,
            _provinces(payload, sources, lang), _recommendation_slide(payload, cards, indicators, lang), limits, tomorrow]


def _pptx(slides, path):
    presentation = Presentation()
    presentation.slide_width, presentation.slide_height = Inches(W), Inches(H)
    links = []
    for spec in slides:
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor(255, 255, 255)
        for box in spec.all_boxes():
            shape = slide.shapes.add_textbox(*(Inches(v) for v in (box.x, box.y, box.w, box.h)))
            if box.link is not None:
                links.append((shape, box.link))
            frame = shape.text_frame
            frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
            frame.word_wrap = True
            frame.auto_size = MSO_AUTO_SIZE.NONE
            frame.text = box.text
            paragraph = frame.paragraphs[0]
            paragraph.font.name, paragraph.font.size, paragraph.font.bold = FONT, Pt(box.size), box.bold
            paragraph.font.color.rgb = RGBColor.from_string(box.color[1:])
        if spec.chart:
            slide.shapes.add_picture(BytesIO(spec.chart.png), *(Inches(v) for v in PLOT))
        slide.notes_slide.notes_text_frame.text = spec.notes
    for shape, target in links:
        shape.click_action.target_slide = presentation.slides[target]
    presentation.save(path)


def _report(payload, slides, out, pdf):
    from ..report import html_to_pdf, md_to_html

    meta = payload["meta"]
    indicators = {i["id"]: i for i in payload["indicators"]}
    cards = {c["rule_id"]: c for sector in payload["sectors"].values() for c in sector["cards"]}
    intro = [f"# {tidy(meta['title_vi'])}", f"Bản công bố {day(meta['generated_at'])} · giờ Việt Nam",
             "## Có gì mới", *[f"- {tidy(line)}" for line in meta["lead_vi"]], "## Cần theo dõi",
             *[f"- {tidy(line)}" for line in meta.get("watch_vi", [])[:3]], "## Các hình"]
    details = ["## Khuyến nghị"]
    for rec in _recommendations(payload):
        details.append(f"**{tidy(rec['title_vi'])}**")
        parts = recommendation_parts(rec, "vi", cards, indicators)
        details.extend(f"- **{label}** · {value}" for label, value in zip(("Bằng chứng", "Hàm ý", "Hành động", "Cơ quan"), parts, strict=True))
    details.append("## Nguồn")
    files = {"report_vi": "report.vi.md"}
    figures = []
    for i, slide in enumerate([s for s in (slides[4], slides[7], slides[8]) if s.chart], 1):
        chart = slide.chart
        filename = f"report.figure-{i}.png"
        (out / filename).write_bytes(chart.png)
        files[f"report_figure_{i}"] = filename
        figures.append((f"Hình {i} · {chart.title}", filename, chart.source))
    sources = [(s["publisher"], s["url"], day(s["fetched_at"])) for s in payload["sources"]]
    image_md = [f"**{title}**\n\n![{title}]({file})\n\n{citation}" for title, file, citation in figures]
    source_md = [f"- [{publisher}]({url}) · truy xuất {date}" for publisher, url, date in sources]
    (out / files["report_vi"]).write_text("\n\n".join([*intro, *image_md, *details, *source_md]) + "\n", encoding="utf-8")
    if pdf:
        def body(lines):
            return md_to_html("\n".join(lines), meta["title_vi"]).split("<body>", 1)[1].split("</body>", 1)[0]

        figure_html = "".join(f'<figure><b>{html.escape(title)}</b><img src="{file}" alt="{html.escape(title, quote=True)}">'
                              f'<figcaption>{html.escape(citation)}</figcaption></figure>'
                              for title, file, citation in figures)
        source_html = "".join(f'<li><a href="{html.escape(url, quote=True)}">{html.escape(publisher)}</a> · truy xuất {date}</li>'
                              for publisher, url, date in sources if url.startswith(("https://", "http://")))
        css = """body{font:10.5pt/1.35 Arial,sans-serif;color:#20242b;margin:0}
        h1{font-size:26pt;line-height:1.06;margin:0 0 10px}h2{font-size:14pt;border-bottom:1px solid #d4d4d4;margin:17px 0 7px}
        p{margin:4px 0}li{margin:0 0 4px 12px}.next{break-before:page}.figures{display:grid;grid-template-columns:1fr 1fr;gap:12px}
        figure{margin:0;padding-top:4px;min-width:0;break-inside:avoid}img{width:100%;display:block}figcaption{font-size:8pt;color:#515964}
        ul.sources{columns:2;padding:0;list-style:none;font-size:9pt}a{color:inherit}"""
        doc = (f'<!doctype html><html lang="vi"><meta charset="utf-8"><title>{html.escape(meta["title_vi"])}</title><style>{css}</style>'
               f'<body><section>{body(intro)}<div class="figures">{figure_html}</div></section>'
               f'<section class="next">{body(details)}<ul class="sources">{source_html}</ul></section></body></html>')
        with TemporaryDirectory(dir=out) as temporary:
            temp_html = Path(temporary) / "report.html"
            temp_html.write_text(doc.replace('src="report.', 'src="../report.'), encoding="utf-8")
            if html_to_pdf(temp_html, out / "report.vi.pdf"):
                files["report_pdf_vi"] = "report.vi.pdf"
    return files


def build_deliverables(payload, out, *, pdf=True):
    """Publish artifact paths relative to the monitor output directory."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    vi_slides = slides_for(payload, "vi")
    files = {"deck_vi": "deck.vi.pptx", "deck_en": "deck.en.pptx"}
    _pptx(vi_slides, out / files["deck_vi"])
    _pptx(slides_for(payload, "en"), out / files["deck_en"])
    return {**files, **_report(payload, vi_slides, out, pdf)}


def render_previews(payload, out, indexes=(4, 8, 11)):
    """Approximate slide typography with Matplotlib when an Office renderer is unavailable."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    slides = slides_for(payload, "vi")
    with rc_context({"font.family": [FONT, "DejaVu Sans"]}):
        for index in indexes:
            slide = slides[index - 1]
            fig = Figure(figsize=(W, H), dpi=120, facecolor="white")
            FigureCanvasAgg(fig)
            if slide.chart:
                x, y, w, h = PLOT
                ax = fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
                ax.imshow(mpl_image.imread(BytesIO(slide.chart.png)))
                ax.axis("off")
            for box in slide.all_boxes():
                width = max(8, int(box.w * 72 / (box.size * (.54 if box.bold else .49))))
                fig.text(box.x / W, 1 - box.y / H, fill(box.text, width), fontsize=box.size, color=box.color,
                         weight="bold" if box.bold else "normal", va="top", linespacing=1.1)
            fig.savefig(out / f"slide-{index:02}.png", facecolor="white")
