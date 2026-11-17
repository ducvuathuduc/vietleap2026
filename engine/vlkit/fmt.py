"""Human formatting of numbers in English and Vietnamese (VND-aware)."""
from __future__ import annotations

import math


def _is_money(col: str | None) -> bool:
    if not col:
        return False
    k = col.lower()
    return any(w in k for w in ["price", "gia", "giá", "vnd", "revenue", "doanh thu", "lợi nhuận", "profit", "tài sản",
                                "assets", "equity", "vốn", "liabilit", "nợ", "income", "thu nhập", "cogs", "npat"]) and "pct" not in k and "%" not in k


def _vi_decimal(s: str) -> str:
    """'1,234.5' → '1.234,5' (Vietnamese thousands '.' and decimal ',')."""
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def num(v, col: str | None = None, lang: str = "en", digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    v = float(v)
    a = abs(v)
    if col and ("pct" in col.lower() or col.endswith("%")):
        return fixed(v, 1, lang) + "%"
    units_en = [(1e12, "tn"), (1e9, "bn"), (1e6, "m"), (1e3, "k")]
    units_vi = [(1e12, " nghìn tỷ"), (1e9, " tỷ"), (1e6, " triệu"), (1e3, " nghìn")]
    money = _is_money(col)
    if a >= 1e4:
        for base, u in (units_vi if lang == "vi" else units_en):
            if a >= base:
                s = f"{v / base:.{digits}g}"
                if lang == "vi":
                    return s.replace(".", ",") + u + (" đồng" if money and base < 1e9 else "")
                return ("VND " if money else "") + s + u
    if a >= 100:
        s = f"{v:,.0f}"
    elif a >= 1:
        s = f"{v:.{digits}g}"
    else:
        s = f"{v:.2g}"
    return _vi_decimal(s) if lang == "vi" else s


def fixed(v, digits: int, lang: str = "en") -> str:
    """Fixed-point number ('2.15' EN · '2,15' VI)."""
    s = f"{v:.{digits}f}"
    return _vi_decimal(s) if lang == "vi" else s


def pct(v, lang: str = "en") -> str:
    if v is None:
        return "n/a"
    s = f"{v:+.1f}%"
    return s.replace(".", ",") if lang == "vi" else s


def p(pv, lang: str = "en") -> str:
    if pv is None:
        return "p=—" if lang == "vi" else "p=n/a"
    s = "p<0.001" if pv < 0.001 else f"p={pv:.3f}"
    return _vi_decimal(s) if lang == "vi" else s


def count(x, lang: str = "en") -> str:
    """Integer with thousands separators ('1,234' EN · '1.234' VI); '—' when not a number."""
    try:
        s = f"{int(x):,}"
    except (TypeError, ValueError):
        return "—"
    return _vi_decimal(s) if lang == "vi" else s


def dec(v, lang: str = "en") -> str:
    """A number exactly as the engine stored it, with the decimal comma in Vietnamese; '—' when missing."""
    if v is None:
        return "—"
    s = str(v)
    return _vi_decimal(s) if lang == "vi" and isinstance(v, (int, float)) else s
