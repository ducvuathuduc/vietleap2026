"""Flatten vendor ratio payloads into snake_case columns plus a vendor field map."""

import re

import pandas as pd

ALIASES = {
    "ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans": "npl",
    "LoanLossReservesToNPLs": "coverage",
    "LDRPercentage": "ldr",
    "NIM": "nim",
    "ROA": "roa",
    "ROE": "roe",
    "AverageLoansGrowthPercentageYoY": "loan_growth",
    "AverageDepositGrowthPercentageYoY": "deposit_growth",
}
CORE = list(ALIASES.values())
KEY = ["ticker", "period", "year", "quarter"]


def snake(name):
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return re.sub(r"[^0-9a-z]+", "_", name.lower()).strip("_")


def _leaves(node, prefix=()):
    if isinstance(node, dict):
        for name, value in node.items():
            yield from _leaves(value, (*prefix, name))
    else:
        yield prefix, node


def _period(record):
    if record.get("quarter") is None:
        return str(record["year"])
    return f"{record['year']}Q{record['quarter']}"


def flatten_ratios(records):
    """Return one row per vendor record and the vendor-name -> column map."""
    rows, vendors = [], {}
    for record in records:
        if not isinstance(record, dict):
            continue
        row = {"ticker": record.get("ticker"), "period": _period(record),
               "year": record.get("year"), "quarter": record.get("quarter")}
        for name, value in record.items():
            if name in ("ticker", "year", "quarter"):
                continue
            for path, leaf in _leaves(value, (name,)):
                name_parts = path[1:] if path[0] == "ratios" else path
                column = snake("_".join(name_parts))
                vendors[".".join(path)] = column + (
                    "" if ALIASES.get(path[-1]) is None else f" -> {ALIASES[path[-1]]}")
                row[column] = leaf
                if alias := ALIASES.get(path[-1]):
                    row[alias] = leaf
        rows.append(row)
    frame = pd.DataFrame(rows, columns=KEY + CORE + [])
    extra = sorted({column for row in rows for column in row} - set(frame.columns))
    frame = pd.concat([frame, pd.DataFrame(rows, columns=extra)], axis=1) if extra else frame
    for alias in CORE:
        if alias not in frame:
            frame[alias] = pd.NA
    metrics = [column for column in frame.columns if column not in KEY]
    field_map = pd.DataFrame({
        "vendor_name": list(vendors),
        "column": [column.split(" -> ")[0] for column in vendors.values()],
        "alias": [column.split(" -> ")[1] if " -> " in column else None for column in vendors.values()],
    }).sort_values("vendor_name", ignore_index=True)
    return frame[KEY + metrics], field_map
