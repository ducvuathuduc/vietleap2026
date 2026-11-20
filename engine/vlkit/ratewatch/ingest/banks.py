"""The bank register (``scenarios/ratewatch/banks.yaml``) and the code/alias lookups readers need."""
from __future__ import annotations

from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parents[4]
DEFAULT_PATH = KIT / "scenarios" / "ratewatch" / "banks.yaml"
def load_banks(path: str | Path | None = None) -> list[dict]:
    """Every bank entry, in file order, with the optional keys materialised."""
    source = Path(path) if path else DEFAULT_PATH
    data = yaml.safe_load(source.read_text(encoding="utf-8-sig")) or []
    banks = []
    for entry in data.get("banks", data) if isinstance(data, dict) else data:
        bank = dict(entry)
        bank["code"] = str(bank["code"]).strip().upper()
        bank.setdefault("methods", [])
        bank.setdefault("agg_names", [])
        bank.setdefault("pdf_urls", [])
        bank.setdefault("ticker", "")
        bank.setdefault("reason", "")
        bank.setdefault("tinyfish", False)
        banks.append(bank)
    return banks


def bank_index(banks) -> dict[str, dict]:
    return {bank["code"]: bank for bank in banks}


def aggregator_index(banks) -> dict[str, str]:
    """Aggregator display name -> bank code (the comparison site does not use our codes)."""
    index = {}
    for bank in banks:
        for name in bank.get("agg_names") or []:
            index[name.strip().lower()] = bank["code"]
    return index


def code_for_aggregator_name(name: str, index: dict[str, str]) -> str | None:
    key = " ".join(str(name).split()).lower()
    if key in index:
        return index[key]
    compact = key.replace(" ", "")
    for alias, code in index.items():
        if alias.replace(" ", "") == compact:
            return code
    return None
