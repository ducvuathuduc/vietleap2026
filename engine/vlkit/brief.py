"""Problem-statement parser (T8): paste the hackathon brief (VI/EN) → brief.json analysis plan.

Rule-based and offline. It extracts the questions, the target metric (resolved to a real or engine-derived
column when the dataset's columns are given), unit of analysis, segments, time/geo scope, decision type,
deliverables and the best-matching scenario pack (scenarios/packs/*.yaml) with its recipe and decision template.

    python de.py brief scenarios/briefs/bds_gia_m2.md --data data/practice/synthetic_messy_bds.csv
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .vn import ascii_key, nfc

PACKS_DIR = Path(__file__).resolve().parents[2] / "scenarios" / "packs"
_VI_CHARS = re.compile(r"[ăâđêôơưàáạảãèéẹẻẽìíịỉĩòóọỏõùúụủũỳýỵỷỹ]", re.I)


@dataclass(frozen=True)
class Concept:
    """A metric the brief may ask about. `columns`: patterns that find a raw column (all '&' words must appear).
    `derived` + `requires`: an engine-derived metric (vlkit.domains) available when every required pattern resolves."""
    id: str
    label: str
    phrases: tuple[str, ...]
    domain: str
    columns: tuple[str, ...] = ()
    derived: str | None = None
    requires: tuple[tuple[str, ...], ...] = field(default_factory=tuple)


# Order matters only for ties: more specific concepts first.
CONCEPTS: tuple[Concept, ...] = (
    Concept("price_per_m2", "Giá/m²", ("gia m2", "gia tren m2", "gia moi m2", "gia 1 m2", "gia tren met vuong", "don gia",
            "price per m2", "price per square", "price per sqm", "price m2"), "property",
            derived="price_per_m2", requires=(("gia ban", "price", "gia"), ("dien tich", "area", "m2"))),
    Concept("rent", "Giá thuê", ("gia thue", "tien thue", "rent", "rental"), "property", columns=("gia thue", "rent")),
    Concept("house_price", "Giá bán", ("gia ban", "gia nha", "house price", "sale price", "home price"), "property",
            columns=("gia ban", "price")),
    Concept("household_income", "Thu nhập hộ", ("thu nhap ho", "household income"), "property",
            columns=("thu nhap ho", "household income", "income")),
    Concept("roe", "ROE", ("roe", "loi nhuan tren von chu", "return on equity", "ty suat loi nhuan tren von"), "firm",
            derived="roe_pct", requires=(("loi nhuan sau thue", "npat", "net income", "net profit"), ("von chu so huu", "equity"))),
    Concept("roa", "ROA", ("roa", "loi nhuan tren tai san", "return on assets"), "firm",
            derived="roa_pct", requires=(("loi nhuan sau thue", "npat", "net income"), ("tong cong tai san", "tong tai san", "total assets"))),
    Concept("net_margin", "Biên lợi nhuận ròng", ("bien loi nhuan rong", "bien lnst", "net margin", "profit margin"), "firm",
            derived="net_margin_pct", requires=(("loi nhuan sau thue", "npat", "net income"), ("doanh thu thuan", "doanh thu", "revenue"))),
    Concept("leverage", "Đòn bẩy nợ/vốn", ("don bay", "no tren von", "debt to equity", "leverage"), "firm",
            derived="debt_to_equity", requires=(("no phai tra", "liabilities"), ("von chu so huu", "equity"))),
    Concept("npat", "Lợi nhuận sau thuế", ("loi nhuan sau thue", "lnst", "net profit", "net income"), "firm",
            columns=("loi nhuan sau thue", "net profit", "net income", "npat")),
    Concept("firm_revenue", "Doanh thu", ("doanh thu thuan", "doanh thu", "net revenue", "sales"), "firm",
            columns=("doanh thu thuan", "doanh thu", "net revenue", "revenue", "sales")),
    Concept("tax_revenue", "Thu thuế (% GDP)", ("thu thue", "nguon thu thue", "tax revenue", "tax to gdp", "tax gdp"),
            "public_finance", columns=("tax revenue", "thu thue", "tax")),
    Concept("gov_revenue", "Thu ngân sách", ("thu ngan sach", "thu nsnn", "government revenue", "public revenue", "revenue gdp"),
            "public_finance", columns=("revenue pct", "thu ngan sach", "thu nsnn", "revenue")),
    Concept("gov_expense", "Chi ngân sách", ("chi ngan sach", "chi tieu cong", "chi nsnn", "government expenditure",
            "public spending", "expense"), "public_finance", columns=("expense", "chi ngan sach", "expenditure", "chi")),
    Concept("public_debt", "Nợ công / nợ chính phủ", ("no cong", "no chinh phu", "public debt", "government debt", "debt gdp"),
            "public_finance", columns=("debt", "no cong", "no chinh phu")),
    Concept("budget_execution", "Tỷ lệ thực hiện dự toán", ("thuc hien du toan", "giai ngan", "budget execution", "disbursement"),
            "public_finance", columns=("thuc hien", "giai ngan", "execution")),
    Concept("gdp_per_capita", "GDP/người", ("gdp binh quan", "gdp dau nguoi", "gdp per capita", "thu nhap binh quan"),
            "public_finance", columns=("gdp per capita", "gdp binh quan", "grdp binh quan")),
    Concept("gdp_growth", "Tăng trưởng GDP", ("tang truong gdp", "tang truong kinh te", "tang truong grdp", "gdp growth",
            "economic growth"), "public_finance", columns=("gdp growth", "tang truong")),
    Concept("inflation", "Lạm phát", ("lam phat", "cpi", "inflation"), "public_finance", columns=("inflation", "lam phat", "cpi")),
    Concept("fdi", "FDI", ("fdi", "von dau tu nuoc ngoai", "foreign direct investment"), "public_finance", columns=("fdi",)),
    Concept("education_spend", "Chi giáo dục", ("chi giao duc", "education spending", "education expenditure"), "generic",
            columns=("education", "giao duc")),
    Concept("traffic_count", "Lưu lượng phương tiện", ("luu luong", "dem xe", "so phuong tien", "traffic volume", "vehicle count"),
            "generic", columns=("count", "in", "luu luong")),
)

UNITS = {
    "province": ("tinh", "tinh thanh", "dia phuong", "province", "provincial"),
    "district": ("quan huyen", "cap huyen", "cap quan", "phuong xa", "district"),
    "region": ("vung", "region"),
    "year": ("nam", "hang nam", "year", "annual"),
    "quarter": ("quy", "quarter"),
    "month": ("thang", "month"),
    "firm": ("doanh nghiep", "cong ty", "ma ck", "firm", "company", "listed"),
    "sector": ("nganh", "sector", "industry"),
    "country": ("quoc gia", "country", "countries"),
    "household": ("ho gia dinh", "household"),
}

DECISIONS = {
    "budget_allocation": ("Phân bổ ngân sách / nguồn lực", ("phan bo", "ngan sach", "nguon luc", "allocate", "allocation", "budget")),
    "regional_priority": ("Ưu tiên khu vực / nhóm đối tượng", ("uu tien", "khu vuc", "vung", "prioriti", "target")),
    "pricing_policy": ("Chính sách giá / thuế / phí", ("chinh sach gia", "gia", "thue suat", "phi", "pricing", "tax rate", "tariff")),
    "investment": ("Quyết định đầu tư", ("dau tu", "danh muc", "invest", "portfolio")),
    "regulation": ("Quy định / giám sát", ("quy dinh", "giam sat", "quan ly", "regulat", "oversight", "monitor")),
    "forecast_planning": ("Dự báo & kế hoạch", ("du bao", "ke hoach", "forecast", "plan")),
}

DELIVERABLES = {
    "dashboard": ("dashboard", "bang dieu khien", "truc quan"),
    "data_pipeline": ("pipeline", "luong du lieu", "etl", "ingestion"),
    "recommendation": ("khuyen nghi", "de xuat", "recommend", "propose", "policy brief"),
    "presentation": ("thuyet trinh", "pitch", "slide", "trinh bay", "presentation"),
    "report": ("bao cao", "report"),
    "model": ("du bao", "mo hinh", "forecast", "predict", "model"),
}

SEGMENT_CUES = re.compile(r"(?=\b(?:theo|giua cac|giua|tung|moi|by|across|between|per|each)\s+((?:[a-z0-9]+\s?){1,3}))")
QUESTION_CUES = ("hay", "phan tich", "de xuat", "danh gia", "xac dinh", "so sanh", "du bao", "tim", "giai thich", "lam ro",
                 "analy", "propose", "recommend", "identify", "compare", "forecast", "assess", "evaluate", "explain", "which",
                 "what", "how", "why", "design", "build", "xay dung")
SOURCE_CUES = {"api": ("api",), "web_scraping": ("scrap", "thu thap tu web", "website"), "survey": ("khao sat", "survey"),
               "database": ("database", "co so du lieu", "sql"), "open_data": ("du lieu mo", "open data", "cong khai"),
               "social": ("mang xa hoi", "social", "rss", "bao chi", "news"), "video": ("video", "camera")}


def _has(text_key: str, phrase: str) -> int:
    return len(re.findall(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text_key))


def _find_col(columns: list[str], patterns: tuple[str, ...]) -> str | None:
    keys = [(c, ascii_key(c)) for c in columns]
    for p in patterns:
        words = [w.strip() for w in p.split("&")]
        for c, k in keys:
            if all(_has(k, w) for w in words):
                return c
    return None


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)              # markdown headings
    parts = re.split(r"(?<=[.?!;:])\s+|\n+\s*(?:[-*•]|\d+[.)])?\s*", text)
    return [p.strip(" -*•\t") for p in parts if p and len(p.strip()) > 3]


def detect_language(text: str) -> str:
    letters = sum(ch.isalpha() for ch in text) or 1
    return "vi" if len(_VI_CHARS.findall(text)) / letters > 0.02 else "en"


def load_packs(packs_dir: Path = PACKS_DIR) -> list[dict]:
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(packs_dir.glob("*.yaml"))]


def match_pack(text_key: str, packs: list[dict]) -> tuple[dict | None, dict[str, int]]:
    scores = {p["id"]: sum(_has(text_key, ascii_key(k)) for k in p.get("keywords", [])) for p in packs}
    best = max(scores, key=scores.get) if scores else None
    if not best or scores[best] == 0:
        return None, scores
    return next(p for p in packs if p["id"] == best), scores


def _score_concepts(text_key: str, question_keys: list[str]) -> list[tuple[Concept, float]]:
    """Mentions in question/task sentences weigh 2×, elsewhere 1×; an earlier first mention breaks ties."""
    scored = []
    for c in CONCEPTS:
        n_all = sum(_has(text_key, ascii_key(p)) for p in c.phrases)
        if not n_all:
            continue
        n_q = sum(_has(q, ascii_key(p)) for q in question_keys for p in c.phrases)
        first = min((m.start() for p in c.phrases for m in re.finditer(rf"(?<![a-z0-9]){re.escape(ascii_key(p))}(?![a-z0-9])", text_key)),
                    default=len(text_key))
        scored.append((c, n_all + n_q + 1.0 - first / max(len(text_key), 1)))
    return sorted(scored, key=lambda x: -x[1])


def resolve_concept(c: Concept, columns: list[str] | None) -> tuple[str | None, str]:
    """→ (column name usable as --target, how it was resolved)."""
    if columns is None:
        return (c.derived or None), "no dataset columns given"
    if c.derived:
        if c.derived in columns:
            return c.derived, "derived column present"
        if c.requires and all(_find_col(columns, req) for req in c.requires):
            return c.derived, f"engine derives '{c.derived}' from " + ", ".join(_find_col(columns, r) for r in c.requires)
    col = _find_col(columns, c.columns) if c.columns else None
    return (col, "matched column name") if col else (None, "no matching column in dataset")


def _direct_column_mentions(text_key: str, columns: list[str]) -> list[str]:
    hits = []
    for c in columns:
        k = ascii_key(c)
        if len(k) >= 3 and _has(text_key, k):
            hits.append(c)
    return hits


def parse_brief(text: str, columns: list[str] | None = None, packs: list[dict] | None = None) -> dict:
    text = re.sub(r"<!--.*?-->", " ", nfc(text or ""), flags=re.S).strip()   # drop markdown/HTML comments
    if not text:
        raise ValueError("brief text is empty")
    text_key = ascii_key(text)
    sents = split_sentences(text)
    questions = [s for s in sents if s.endswith("?") or any(ascii_key(s).startswith(q) or f" {q}" in f" {ascii_key(s)}"
                                                             for q in QUESTION_CUES)]
    q_keys = [ascii_key(q) for q in questions]

    ranked = _score_concepts(text_key, q_keys)
    target, alternatives, warnings = None, [], []
    for c, score in ranked:
        col, how = resolve_concept(c, columns)
        entry = {"concept": c.id, "label": c.label, "column": col, "resolved": how, "domain": c.domain, "score": round(score, 2)}
        if target is None and (col or columns is None):
            target = entry
        else:
            alternatives.append(entry)
    if columns and target is None:
        direct = _direct_column_mentions(text_key, columns)
        if direct:
            target = {"concept": "column", "label": direct[0], "column": direct[0], "resolved": "column named in brief",
                      "domain": None, "score": 1.0}
    if target is None:
        warnings.append("Không xác định được biến mục tiêu từ đề — chọn thủ công (--target) hoặc để engine tự chọn.")

    units = [u for u, kws in UNITS.items() if any(_has(text_key, k) for k in kws)]
    decisions = [{"id": d, "label": lbl, "hits": n} for d, (lbl, kws) in DECISIONS.items()
                 if (n := sum(_has(text_key, k) for k in kws))]
    decisions.sort(key=lambda d: -d["hits"])
    deliverables = [d for d, kws in DELIVERABLES.items() if any(_has(text_key, k) for k in kws)]
    sources = [s for s, kws in SOURCE_CUES.items() if any(k in text_key for k in kws)]
    years = sorted({int(y) for y in re.findall(r"\b(19[89]\d|20[0-4]\d)\b", text)})

    segments = []
    if columns:
        for m in SEGMENT_CUES.finditer(text_key):
            frag = m.group(1).strip()
            for c in columns:
                k = ascii_key(c)
                if c not in segments and (target is None or c != target.get("column")) and k and (k in frag or frag.startswith(k)):
                    segments.append(c)

    packs = load_packs() if packs is None else packs
    pack, pack_scores = match_pack(text_key, packs)
    domain = (target or {}).get("domain") or (pack or {}).get("domain") or "auto"

    run_config = {"target": (target or {}).get("column"), "domain": domain if domain != "generic" else "auto",
                  "segment_by": segments}
    plan = [
        f"Biến mục tiêu: {target['label']} → cột '{target['column']}'" if target and target.get("column")
        else "Biến mục tiêu: để engine tự chọn (chưa khớp cột)",
        f"Đơn vị phân tích: {', '.join(units) or 'chưa rõ'}; phân khúc: {', '.join(segments) or 'theo cột phân loại engine phát hiện'}",
        f"Loại quyết định: {decisions[0]['label'] if decisions else 'chưa rõ — hỏi BTC'}",
        *((pack or {}).get("recipe") or []),
    ]
    return {
        "language": detect_language(text),
        "title": sents[0][:160] if sents else "",
        "questions": questions[:12],
        "target": target,
        "alternatives": alternatives[:5],
        "units": units,
        "segments": segments,
        "time": {"years": years, "range": [years[0], years[-1]] if years else None},
        "decision_types": decisions,
        "deliverables": deliverables,
        "data_sources_mentioned": sources,
        "pack": {k: pack[k] for k in ("id", "title", "sponsor", "kpis", "recipe", "decision_template", "deck_storyline",
                                      "expected_columns")} if pack else None,
        "pack_scores": pack_scores,
        "run_config": run_config,
        "plan": plan,
        "warnings": warnings,
    }
