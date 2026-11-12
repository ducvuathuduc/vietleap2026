"""Number verification: every number the agent writes must be traceable to a tool output.

We collect all numeric values from tool results, expand them into the forms they are commonly written in
(×100 for shares, ÷1e3/1e6/1e9 for VND units, absolute values) and accept a written number when it matches a
known value within rounding tolerance. Years, small integers used for counting/ranking, and numbers that appear in
the user's own question are exempt."""
from __future__ import annotations

import math
import re
from typing import Any, Iterable

NUM_RE = re.compile(r"(?<![\w.])[-+−]?\d{1,3}(?:[,.]\d{3})+(?:[.,]\d+)?(?![\d])|(?<![\w.])[-+−]?\d+(?:[.,]\d+)?(?![\d])")
SCALE_WORDS = {"k": 1e3, "nghìn": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "triệu": 1e6, "tr": 1e6,
               "bn": 1e9, "billion": 1e9, "tỷ": 1e9, "tỉ": 1e9, "tn": 1e12, "trillion": 1e12}


def _walk(x: Any) -> Iterable[float]:
    if isinstance(x, bool) or x is None:
        return
    if isinstance(x, (int, float)):
        if not (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            yield float(x)
    elif isinstance(x, dict):
        for k, v in x.items():
            if k in ("boot",):
                continue
            yield from _walk(v)
    elif isinstance(x, (list, tuple)):
        for v in x[:2000]:
            yield from _walk(v)
    elif isinstance(x, str):
        for m in NUM_RE.finditer(x):
            v = parse_written(m.group(0))
            if v is not None:
                yield v


def known_values(tool_outputs: list[Any]) -> list[float]:
    vals = set()
    for out in tool_outputs:
        for v in _walk(out):
            for f in (1, 100, 0.01, 1e-3, 1e-6, 1e-9, 1e-12):
                vals.add(v * f)
                vals.add(abs(v * f))
    return sorted(vals)


def parse_written(tok: str) -> float | None:
    t = tok.replace("−", "-").replace("+", "")
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):
        t = t.replace(",", "")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", t):
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d+,\d+", t):
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _decimals(tok: str) -> int:
    m = re.search(r"[.,](\d+)$", tok)
    if m and not re.fullmatch(r"-?\d{1,3}([.,]\d{3})+", tok):
        return len(m.group(1))
    return 0


def check(text: str, tool_outputs: list[Any], question: str = "") -> dict:
    known = known_values(tool_outputs)
    asked = {parse_written(m.group(0)) for m in NUM_RE.finditer(question or "")}
    verified, unverified = [], []
    for m in NUM_RE.finditer(text):
        tok = m.group(0)
        v = parse_written(tok)
        if v is None:
            continue
        a = abs(v)
        after = text[m.end(): m.end() + 12].lower()
        before = text[max(0, m.start() - 6): m.start()]
        # exemptions: years, small counting integers, ranks/ids like I3 or #2, numbers the user typed, percentile labels
        if (float(a).is_integer() and (a <= 10 or 1900 <= a <= 2100)) or v in asked or re.search(r"[#IQCq]$", before) or after.startswith(("-fold", " fold", "th ", "%-trim")):
            continue
        tol = 0.5 * 10 ** (-_decimals(tok))
        candidates = [v, a]
        sw = re.match(r"\s?(k|mn|m|bn|tn|million|billion|trillion|nghìn|triệu|tr|tỷ|tỉ)\b", after)
        if sw:
            candidates += [c * SCALE_WORDS[sw.group(1)] for c in (v, a)]
        ok = False
        for c in candidates:
            scale = SCALE_WORDS[sw.group(1)] if sw and c >= 1e3 and c != v and c != a else 1
            t = max(tol * scale, abs(c) * 0.006)
            # binary search for nearest known value
            lo, hi = 0, len(known)
            while lo < hi:
                mid = (lo + hi) // 2
                if known[mid] < c:
                    lo = mid + 1
                else:
                    hi = mid
            for j in (lo - 1, lo):
                if 0 <= j < len(known) and abs(known[j] - c) <= t:
                    ok = True
                    break
            if ok:
                break
        (verified if ok else unverified).append(tok)
    return {"verified": verified, "unverified": unverified, "ok": not unverified}
