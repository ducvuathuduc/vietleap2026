"""Contract for the notes-based NPL inputs: field names, units, YTD conversion, grading.

One value is one row (bank, period, field, value_vnd_bn, basis, page, source_url, reader, grade,
raw_sha256). `field` names follow the DECODER five inputs: customer loans L, group-2 loans G2, the NPL
groups 3-5 N, the loan-loss provision balance P and the write-offs of the period W, plus their movement
components so a provision roll-forward can be checked. Amounts are always VND billion, whatever unit the
statement prints; converted with the multiplier read from the statement's own "Đơn vị tính" line.

A quarterly Vietnamese statement prints balance-sheet items as of the quarter end (basis "point") and
income-statement / movement items cumulatively from 1 January (basis "ytd"). `to_quarterly` turns the YTD
flows into single-quarter values so the five inputs share one period definition.
"""

import re

KEY = ["bank", "period", "field", "basis"]
SILVER_COLUMNS = KEY + ["value_vnd_bn", "page", "source_url", "reader", "grade", "raw_sha256"]
READERS = ("text", "table", "vision_a", "vision_b")
GRADES = ("verified", "single", "contested")
STATEMENT_TYPES = ("consolidated", "separate", "unknown")
REL_TOL = 1e-6
ABS_TOL_BN = 0.001
PERIOD = re.compile(r"^([1-9][0-9]{3})(?:Q([1-4])|FY)$")

# field -> (kind, section) ; kind "balance" is point-in-time, "flow" is YTD for a quarterly statement
FIELDS = {
    "loans_customer": ("balance", "loans"),
    "group_1_current": ("balance", "groups"),
    "group_2_watch": ("balance", "groups"),
    "group_3_substandard": ("balance", "groups"),
    "group_4_doubtful": ("balance", "groups"),
    "group_5_loss": ("balance", "groups"),
    "provision_opening": ("point", "provision_movement"),
    "provision_charge": ("flow", "provision_movement"),
    "provision_used_writeoff": ("flow", "provision_movement"),
    "provision_closing": ("balance", "provision_balance"),
    "writeoff_period": ("flow", "writeoff"),
}
GROUP_FIELDS = ["group_1_current", "group_2_watch", "group_3_substandard", "group_4_doubtful", "group_5_loss"]
NPL_FIELDS = GROUP_FIELDS[2:]
PROVISION_MOVEMENT = ["provision_opening", "provision_charge", "provision_used_writeoff", "provision_closing"]

UNIT_SCALE = [
    (r"nghin", 1e-6),
    (r"trieu", 1e-3),
    (r"ty|ti", 1.0),
]
UNIT_LINE = re.compile(r"(?:don vi(?: tinh)?|unit)\s*[:\-]?\s*(.{0,32})")
NUMBER = re.compile(r"\(?-?\d[\d.,]*\)?")


def kind_of(field):
    return FIELDS[field][0]


def unit_scale(text):
    """Multiplier from the statement's printed unit to VND billion; 1.0 (tỷ đồng) when the line is absent.

    Vietnamese statements print 'Đơn vị tính: Triệu VND' / 'tỷ đồng' / 'VND' at the top of every page, so the line is
    matched diacritic-free and the multiplier comes from the word after the colon.
    """
    from ...vn import ascii_key

    match = UNIT_LINE.search(ascii_key(text or ""))
    if match is None:
        return 1.0
    tail = match.group(1)
    for pattern, scale in UNIT_SCALE:
        if re.search(pattern, tail):
            return scale
    return 1e-9 if "dong" in tail or "vnd" in tail else 1.0


def parse_number(text):
    """A Vietnamese formatted number: '1.234.567' -> 1234567, '1.234,5' -> 1234.5, '(1.234)' -> -1234."""
    token = (text or "").strip()
    negative = token.startswith("(") and token.endswith(")")
    token = token.strip("()").replace(" ", "")
    if not re.fullmatch(r"-?\d[\d.,]*", token):
        return None
    if "," in token:
        token = token.replace(".", "").replace(",", ".")
    elif token.count(".") > 1 or re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", token):
        token = token.replace(".", "")
    try:
        value = float(token)
    except ValueError:
        return None
    return -value if negative else value


def numbers_in(line):
    """All numbers of a line, in order (dash and parenthesis negatives included)."""
    found = []
    for match in NUMBER.finditer(line or ""):
        value = parse_number(match.group())
        if value is not None:
            found.append(value)
    return found


def period_parts(period):
    match = PERIOD.match(str(period))
    if match is None:
        return None, None
    return int(match.group(1)), int(match.group(2)) if match.group(2) else None


def is_quarter(period):
    return PERIOD.match(str(period)) is not None and PERIOD.match(str(period)).group(2) is not None


def agreement(left, right, rel=REL_TOL, floor=ABS_TOL_BN):
    """Two reads of the same number agree when they differ by at most `rel` relatively (with a tiny floor)."""
    if left is None or right is None:
        return False
    return abs(left - right) <= max(floor, rel * max(abs(left), abs(right)))


def grade(readings, rel=REL_TOL, floor=ABS_TOL_BN):
    """(grade, value) for one field and period: two agreeing readers = verified, one reader = single."""
    values = [(reader, float(value)) for reader, value in readings if value is not None]
    if not values:
        return None, None
    best = values[0][1]
    agreeing = [value for _, value in values if agreement(best, value, rel, floor)]
    if len(values) == 1:
        return "single", best
    if len(agreeing) > 1:
        return "verified", best
    return "contested", best


def to_quarterly(rows):
    """Append a single-quarter row for every YTD flow: Q1 stays as printed, Q2 = YTD Q2 - YTD Q1, FY stays as printed.

    `rows` is a list of dicts (period, field, basis, value_vnd_bn, ...). The printed row is kept unchanged (so the
    provision roll-forward can be checked exactly as the statement prints it); the derived row carries
    basis "quarterly" and the page it was derived from. A quarter whose previous quarter is missing gets no
    derived row: the difference would be a nine-month number wearing a one-quarter label.
    """
    raw = {(row["period"], row["field"]): row for row in rows}
    out = list(rows)
    for row in rows:
        field, period = row["field"], row["period"]
        if kind_of(field) != "flow" or row.get("basis") not in ("ytd", None) or not is_quarter(period):
            continue
        year, quarter = period_parts(period)
        if quarter == 1:
            out.append({**row, "basis": "quarterly"})
            continue
        previous = raw.get((f"{year}Q{quarter - 1}", field))
        if previous is None or previous.get("basis") not in ("ytd", None):
            continue
        out.append({**row, "value_vnd_bn": round(row["value_vnd_bn"] - previous["value_vnd_bn"], 6),
                    "basis": "quarterly", "derived_from": previous.get("period")})
    return out
