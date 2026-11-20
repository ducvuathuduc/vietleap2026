"""Quality gates on the notes inputs: the three checks the brief asks for, with their tolerances.

1. groups 1-5 sum to total customer loans within 0.5%;
2. the provision roll-forward closes: opening + charge - used = closing within 1%;
3. our NPL ratio (groups 3-5 / loans) matches the vendor's NPL ratio within 10 bp.

A gate whose inputs are missing reports "skipped", never "pass": an unreadable statement is not a clean one.
"""

import pandas as pd

from .notes_contract import GROUP_FIELDS, NPL_FIELDS

GATE_COLUMNS = ["bank", "period", "gate", "status", "detail", "value", "threshold"]
GROUP_TOL = 0.005
ROLLFORWARD_TOL = 0.01
NPL_TOL_PP = 0.10          # 10 basis points, in percentage points


def values_of(rows):
    """field -> value for the printed basis of one bank-quarter."""
    out = {}
    for row in rows:
        if row.get("basis") in ("ytd", "point", None) and row.get("field") not in out:
            out[row["field"]] = float(row["value_vnd_bn"])
    return out


def groups_gate(values):
    total = values.get("loans_customer")
    parts = [values.get(field) for field in GROUP_FIELDS]
    if total in (None, 0) or any(part is None for part in parts):
        return {"gate": "groups_sum_to_loans", "status": "skipped",
                "detail": "loans or one of groups 1-5 missing", "value": None, "threshold": GROUP_TOL}
    gap = (sum(parts) - total) / total
    status = "pass" if abs(gap) <= GROUP_TOL else "fail"
    return {"gate": "groups_sum_to_loans", "status": status,
            "detail": f"sum(groups) {sum(parts):,.1f} vs loans {total:,.1f} (gap {gap:+.3%})",
            "value": round(gap, 6), "threshold": GROUP_TOL}


def rollforward_gate(values):
    opening = values.get("provision_opening")
    charge = values.get("provision_charge")
    used = values.get("provision_used_writeoff")
    closing = values.get("provision_closing")
    if any(part is None for part in (opening, charge, used, closing)) or not closing:
        return {"gate": "provision_rollforward", "status": "skipped",
                "detail": "opening, charge, used or closing missing", "value": None,
                "threshold": ROLLFORWARD_TOL}
    gap = (opening + charge - used - closing) / abs(closing)
    status = "pass" if abs(gap) <= ROLLFORWARD_TOL else "fail"
    return {"gate": "provision_rollforward", "status": status,
            "detail": f"{opening:,.1f} + {charge:,.1f} - {used:,.1f} = {opening + charge - used:,.1f} "
                      f"vs closing {closing:,.1f} (gap {gap:+.3%})",
            "value": round(gap, 6), "threshold": ROLLFORWARD_TOL}


def our_npl_ratio(values):
    total = values.get("loans_customer")
    parts = [values.get(field) for field in NPL_FIELDS]
    if total in (None, 0) or any(part is None for part in parts):
        return None
    return 100.0 * sum(parts) / total


def npl_gate(values, vendor_pct):
    """Our notes NPL ratio against the vendor's published ratio, both in percent."""
    ours = our_npl_ratio(values)
    if ours is None or vendor_pct is None:
        return {"gate": "npl_vs_vendor", "status": "skipped",
                "detail": f"our ratio {_pct(ours)} vs vendor {_pct(vendor_pct)}", "value": None,
                "threshold": NPL_TOL_PP}
    gap_pp = 100.0 * (ours - vendor_pct)
    status = "pass" if abs(gap_pp) <= NPL_TOL_PP else "fail"
    return {"gate": "npl_vs_vendor", "status": status,
            "detail": f"ours {ours:.2f}% vs vendor {vendor_pct:.2f}% (gap {gap_pp:+.1f} bp)",
            "value": round(gap_pp, 4), "threshold": NPL_TOL_PP}


def _pct(value):
    return "missing" if value is None else f"{value:.2f}%"


def run_gates(frame, vendor=None):
    """One row per bank-period-gate plus the share of gates that failed, for the run log and the report.

    `frame` is the long silver table; `vendor` maps (bank, period) -> vendor NPL percent, from bank_quarter.
    """
    if frame is None or frame.empty:
        return pd.DataFrame(columns=GATE_COLUMNS), {"gates": 0, "pass": 0, "fail": 0, "skipped": 0}
    rows = []
    for (bank, period), block in frame.groupby(["bank", "period"], sort=True):
        values = values_of(block.to_dict("records"))
        vendor_pct = (vendor or {}).get((bank, period))
        for gate in (groups_gate(values), rollforward_gate(values), npl_gate(values, vendor_pct)):
            rows.append({"bank": bank, "period": period, **gate})
    table = pd.DataFrame(rows, columns=GATE_COLUMNS)
    counts = table["status"].value_counts().to_dict() if len(table) else {}
    summary = {"gates": len(table), "pass": int(counts.get("pass", 0)), "fail": int(counts.get("fail", 0)),
               "skipped": int(counts.get("skipped", 0))}
    return table, summary
