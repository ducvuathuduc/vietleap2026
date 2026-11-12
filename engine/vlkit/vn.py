"""Vietnamese-aware text, number, date and province helpers.

Everything here is pure and unit-tested (tests/test_vn.py).
"""
from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from unidecode import unidecode

RESOURCES = Path(__file__).parent / "resources"

# ----------------------------------------------------------------------------- text

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def clean_text(s):
    """NFC-normalise, collapse whitespace, strip. Non-strings pass through."""
    if not isinstance(s, str):
        return s
    s = nfc(s).replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def ascii_key(s: str) -> str:
    """Diacritic-free, lower-case, alnum-only key used for fuzzy matching."""
    s = unidecode(nfc(str(s))).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def slug(s: str) -> str:
    return re.sub(r"\s+", "_", ascii_key(s)) or "col"


# ----------------------------------------------------------------------------- numbers

UNIT_MULT = [
    # order matters (longest first)
    (r"ty|ti", 1e9),
    (r"trieu|tr", 1e6),
    (r"nghin|ngan|k", 1e3),
]
NULL_WORDS = {"", "nan", "none", "null", "n/a", "na", "-", "--", "thoa thuan", "lien he", "khong ro",
              "chua co", "dang cap nhat", "x", "..", "...", "#n/a", "#value!", "#div/0!"}

_num_re = re.compile(r"\(?[-+]?\d[\d.,\s]*\)?")


def _to_float(tok: str, decimal: str) -> float | None:
    tok = tok.strip().replace(" ", "")
    neg = tok.startswith("(") and tok.endswith(")")
    tok = tok.strip("()")
    if not tok:
        return None
    sign = -1.0 if tok.startswith("-") else 1.0
    tok = tok.lstrip("+-")
    has_dot, has_comma = "." in tok, "," in tok
    if has_dot and has_comma:
        dec = "." if tok.rfind(".") > tok.rfind(",") else ","
    elif has_comma:
        parts = tok.split(",")
        if len(parts) > 2:
            dec = "."  # commas are thousands
        elif len(parts[1]) == 3 and decimal == ".":
            dec = "."  # 1,234 in an English-style column
        else:
            dec = "," if len(parts[1]) != 3 or decimal == "," else "."
    elif has_dot:
        parts = tok.split(".")
        if len(parts) > 2:
            dec = ","  # dots are thousands (VN style)
        elif len(parts[1]) == 3 and decimal == ",":
            dec = ","  # 1.234 in a VN-style column
        else:
            dec = "."
    else:
        dec = "."
    if dec == ",":
        tok = tok.replace(".", "").replace(",", ".")
    else:
        tok = tok.replace(",", "")
    try:
        v = float(tok)
    except ValueError:
        return None
    return -v if neg else sign * v


def detect_decimal(values) -> str:
    """Guess the decimal separator of a text column from unambiguous examples."""
    comma = dot = 0
    for v in values:
        if not isinstance(v, str):
            continue
        s = v.replace(" ", "")
        if re.search(r"\d,\d{1,2}(?!\d)", s) or re.search(r"\d\.\d{3}\.\d{3}", s) or re.search(r"\d\.\d{3},\d", s):
            comma += 1
        if re.search(r"\d\.\d{1,2}(?!\d)", s) or re.search(r"\d,\d{3},\d{3}", s) or re.search(r"\d,\d{3}\.\d", s):
            dot += 1
    return "," if comma > dot else "."


def parse_vn_number(raw, decimal: str = ","):
    """Parse a Vietnamese/English formatted quantity.

    Returns (value, info) where info is a dict with keys unit ('ty','trieu',...), per ('m2' if per-square-metre),
    pct (bool). Value is in base units (VND, m², count). None when unparseable.
    Examples: '2,5 tỷ' -> 2.5e9; '850 triệu' -> 8.5e8; '35 tr/m²' -> 3.5e7 per m2; '1.234,5' -> 1234.5;
    '2 tỷ 300 triệu' -> 2.3e9; '(1.200)' -> -1200; '12,5%' -> 12.5 pct.
    """
    info = {"unit": None, "per": None, "pct": False}
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None, info
    if isinstance(raw, (int, float, np.integer, np.floating)) and not isinstance(raw, bool):
        return float(raw), info
    s = str(raw)
    key = ascii_key(s)
    if key in NULL_WORDS:
        return None, info
    low = unidecode(nfc(s)).lower().strip()
    if re.fullmatch(r"[-+]?\d+(\.\d+)?e[-+]?\d+", low):
        return float(low), info
    if "%" in low:
        info["pct"] = True
    low = re.sub(r"(?<![/a-z])(m2|m\^2|m²|km2|km²)\b", " ", low).replace("m²", " ")
    if re.search(r"/\s*(m2|m\^2|m²|met vuong)", low) or "/m" in low.replace(" ", ""):
        info["per"] = "m2"
        low = re.split(r"/", low)[0]
    if re.search(r"/\s*(thang|month)", low):
        info["per"] = "month"
    # compound: "2 ty 300 trieu"
    total, matched = 0.0, False
    for m in re.finditer(r"(\(?[-+]?\d[\d.,]*\)?)\s*(ty|ti|trieu|tr|nghin|ngan|k|dong|d|vnd|usd|\$)?\b", low):
        num = _to_float(m.group(1), decimal)
        if num is None:
            continue
        unit = m.group(2)
        mult = 1.0
        if unit in ("ty", "ti"):
            mult, info["unit"] = 1e9, info["unit"] or "ty"
        elif unit in ("trieu", "tr"):
            mult, info["unit"] = 1e6, info["unit"] or "trieu"
        elif unit in ("nghin", "ngan", "k"):
            mult, info["unit"] = 1e3, info["unit"] or "nghin"
        total += num * mult
        matched = True
        if unit is None:
            break  # a plain number: stop (avoid summing e.g. '46 m2 4 tang')
    if not matched:
        return None, info
    # reject strings that are mostly text (e.g. addresses containing a house number)
    words = re.findall(r"[a-z]+", low)
    allowed = {"ty", "ti", "trieu", "tr", "nghin", "ngan", "dong", "d", "vnd", "usd", "m", "phong", "tang", "pn", "wc",
               "nam", "thang", "k", "met", "vuong", "can", "nguoi", "ha", "km", "khoang", "tren", "duoi", "hon", "approx",
               "about", "over", "under", "mil", "bn", "million", "billion", "e"}
    if any(w not in allowed for w in words):
        return None, info
    return total, info


def parse_numeric_series(s: pd.Series, min_ok: float = 0.7):
    """Try to turn an object Series into floats. Returns (series or None, report dict)."""
    vals = s.dropna()
    if vals.empty:
        return None, {}
    sample = vals.astype(str).head(3000)
    dec = detect_decimal(sample.tolist())
    units, pers, pct = {}, {}, 0
    counts = s.value_counts(dropna=True)
    lookup = {}
    for v, cnt in counts.items():  # parse each distinct value once
        x, info = parse_vn_number(v, dec)
        lookup[v] = np.nan if x is None else x
        if x is not None:
            if info["unit"]:
                units[info["unit"]] = units.get(info["unit"], 0) + int(cnt)
            if info["per"]:
                pers[info["per"]] = pers.get(info["per"], 0) + int(cnt)
            pct += int(cnt) * info["pct"]
    out = s.map(lookup).astype("float64")
    nonnull_in = s.notna() & ~s.astype(str).map(ascii_key).isin(NULL_WORDS)
    ok = out.notna().sum() / max(1, nonnull_in.sum())
    if ok < min_ok:
        return None, {"ok_ratio": ok}
    return out, {"ok_ratio": round(float(ok), 4), "decimal": dec, "units": units, "per": pers,
                 "pct": pct, "failed": int((nonnull_in & out.isna()).sum())}


# ----------------------------------------------------------------------------- dates

_quarter_re = re.compile(r"(?:q|quy)\s*([1-4])\D{0,3}(\d{4})|(\d{4})\D{0,3}(?:q|quy)\s*([1-4])", re.I)


def parse_dates(s: pd.Series, min_ok: float = 0.8):
    """Parse a text column to datetimes (day-first, VN style). Handles quarters ('Q1 2021', 'Quý 2/2023')."""
    vals = s.dropna().astype(str).head(2000)
    if vals.empty:
        return None
    keys = vals.map(lambda v: unidecode(v).lower())
    qm = keys.str.extract(_quarter_re)
    if qm.notna().any(axis=1).mean() >= min_ok:
        def q2d(v):
            m = _quarter_re.search(unidecode(str(v)).lower())
            if not m:
                return pd.NaT
            q = int(m.group(1) or m.group(4)); y = int(m.group(2) or m.group(3))
            return pd.Timestamp(year=y, month=3 * (q - 1) + 1, day=1)
        return s.map(q2d)
    if not vals.str.contains(r"\d{1,4}[-/.]\d{1,2}(?:[-/.]\d{1,4})?", regex=True).mean() >= min_ok:
        return None
    iso = vals.str.match(r"^\d{4}-\d{2}-\d{2}").mean() > 0.8
    out = pd.to_datetime(s, errors="coerce", dayfirst=not iso, format="mixed")
    if out.notna().sum() / max(1, s.notna().sum()) < min_ok:
        return None
    return out


# ----------------------------------------------------------------------------- provinces

PROVINCES_63 = [
    "An Giang", "Bà Rịa - Vũng Tàu", "Bạc Liêu", "Bắc Giang", "Bắc Kạn", "Bắc Ninh", "Bến Tre", "Bình Dương",
    "Bình Định", "Bình Phước", "Bình Thuận", "Cà Mau", "Cao Bằng", "Cần Thơ", "Đà Nẵng", "Đắk Lắk", "Đắk Nông",
    "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang", "Hà Nam", "Hà Nội", "Hà Tĩnh", "Hải Dương",
    "Hải Phòng", "Hậu Giang", "Hòa Bình", "Hồ Chí Minh", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum",
    "Lai Châu", "Lạng Sơn", "Lào Cai", "Lâm Đồng", "Long An", "Nam Định", "Nghệ An", "Ninh Bình", "Ninh Thuận",
    "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sóc Trăng",
    "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", "Trà Vinh",
    "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc", "Yên Bái",
]
ALIASES = {
    "hcm": "Hồ Chí Minh", "tphcm": "Hồ Chí Minh", "tp hcm": "Hồ Chí Minh", "hcmc": "Hồ Chí Minh",
    "sai gon": "Hồ Chí Minh", "saigon": "Hồ Chí Minh", "ho chi minh city": "Hồ Chí Minh", "sg": "Hồ Chí Minh",
    "hn": "Hà Nội", "ha noi": "Hà Nội", "hanoi": "Hà Nội", "ha noi capital": "Hà Nội",
    "brvt": "Bà Rịa - Vũng Tàu", "ba ria vung tau": "Bà Rịa - Vũng Tàu", "vung tau": "Bà Rịa - Vũng Tàu",
    "hue": "Thừa Thiên Huế", "thua thien hue": "Thừa Thiên Huế", "tt hue": "Thừa Thiên Huế",
    "dak lak": "Đắk Lắk", "daklak": "Đắk Lắk", "dac lac": "Đắk Lắk", "dak nong": "Đắk Nông", "daknong": "Đắk Nông",
    "da nang": "Đà Nẵng", "danang": "Đà Nẵng", "can tho": "Cần Thơ", "hai phong": "Hải Phòng", "haiphong": "Hải Phòng",
    "khanh hoa": "Khánh Hòa", "thanh hoa": "Thanh Hóa", "hoa binh": "Hòa Bình", "bac can": "Bắc Kạn",
}
PREFIX_RE = re.compile(r"^(tinh|thanh pho|tp|t p|city of|province of|thu do)\s+")
SUFFIX_RE = re.compile(r"\s+(province|city|capital)$")


@lru_cache(maxsize=1)
def _province_index():
    idx = {ascii_key(p): p for p in PROVINCES_63}
    idx.update({k: v for k, v in ALIASES.items()})
    return idx


@lru_cache(maxsize=1)
def _merge_map():
    m = {}
    with open(RESOURCES / "province_63_to_34.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m[r["old_province"]] = r["new_province"]
    return m


@lru_cache(maxsize=20000)
def normalize_province(name) -> str | None:
    """Map any spelling ('TP.HCM', 'Ha Noi', 'Tỉnh Bình Dương') to the canonical 63-province name, else None."""
    if not isinstance(name, str) or not name.strip():
        return None
    k = ascii_key(name)
    k = PREFIX_RE.sub("", k)
    k = SUFFIX_RE.sub("", k).strip()
    idx = _province_index()
    if k in idx:
        return idx[k]
    k2 = k.replace(" ", "")
    for kk, v in idx.items():
        if kk.replace(" ", "") == k2:
            return v
    # address strings: take the last comma-separated part
    if "," in name:
        return normalize_province(name.split(",")[-1])
    return None


def to_new_province(old: str | None) -> str | None:
    """Map a canonical old (63) province name to the post-1 Jul 2025 (34) unit (Resolution 202/2025/QH15)."""
    if old is None:
        return None
    return _merge_map().get(old, old if old in _merge_map().values() else None)
