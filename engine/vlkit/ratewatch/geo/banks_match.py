"""Match an OSM amenity=bank element's tags to a bank code from scenarios/ratewatch/banks.yaml.

Two tiers, both on the normalised strings (deaccented, lowercase, generic words
"ngan hang / tmcp / bank / joint stock commercial" dropped):
1. exact: the whole normalised tag equals a normalised alias (name_vi spellings live here);
2. token subset: every alias token appears in the tag tokens (brand spellings like
   "Vietcombank" inside longer strings); a single-token alias must be >= 3 chars so
   tickers like "MB" only match exactly.
"""
from __future__ import annotations

import re
import unicodedata

GENERIC_WORDS = {"ngan", "hang", "tmcp", "bank", "joint", "stock", "commercial"}
_TAG_KEYS = ("brand", "operator", "name")

# OSM brand spellings that banks.yaml does not carry (its agg_names use the aggregator's
# spellings). Keys are bank codes, values extra alias strings; banks.yaml claims win.
OSM_ALIASES = {
    "VPB": ["VPBank"],
    "SSB": ["SeABank"],
    "HDB": ["HDBank"],
    "ABB": ["ABBank"],
    "LPB": ["LPBank"],
    "SGB": ["Saigonbank"],
    "ACB": ["ACBbank"],
    "PGB": ["PG Bank", "PGBank"],
    "GPB": ["GPBank", "GP Bank"],
    "OCEAN": ["Oceanbank"],
    "BAB": ["BacAbank"],
    "MSB": ["Maritime Bank"],
    "KLB": ["Kienlongbank"],
    "BVB": ["BaoVietBank"],
    "BVBANK": ["BVBank"],
    "CBB": ["CBBank"],
}


def normalise_name(text: str) -> str:
    text = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    tokens = [t for t in re.sub(r"[^a-z0-9]+", " ", text).split() if t not in GENERIC_WORDS]
    return " ".join(tokens)


def alias_map(banks: list[dict]) -> dict[str, str]:
    """normalised alias -> bank code; the first bank in file order keeps a contested alias."""
    aliases: dict[str, str] = {}
    for bank in banks:
        code = bank["code"]
        candidates = [bank.get("code"), bank.get("ticker"), bank.get("name_vi"), bank.get("name_en"),
                      *(bank.get("agg_names") or []), *OSM_ALIASES.get(code, [])]
        for candidate in candidates:
            if not candidate:
                continue
            key = normalise_name(str(candidate))
            if key:
                aliases.setdefault(key, code)
    return aliases


def match_bank(tags: dict | None, aliases: dict[str, str]) -> str | None:
    if not tags:
        return None
    candidates = [str(tags[k]) for k in _TAG_KEYS if tags.get(k)]
    normalised = [normalise_name(c) for c in candidates]
    for key in normalised:
        code = aliases.get(key)
        if code:
            return code
    for key in normalised:
        tokens = set(key.split())
        if not tokens:
            continue
        for alias, code in aliases.items():
            alias_tokens = set(alias.split())
            if len(alias_tokens) == 1 and len(alias) < 3:
                continue
            if alias_tokens <= tokens:
                return code
        # full-name shorthand: a >= 3-token tag fully inside a bank's longer name
        # ("dau tu va phat trien" -> BIDV); 2-token tags stay unmatched ("viet nam").
        if len(tokens) >= 3:
            for alias, code in aliases.items():
                if tokens <= set(alias.split()):
                    return code
    return None
