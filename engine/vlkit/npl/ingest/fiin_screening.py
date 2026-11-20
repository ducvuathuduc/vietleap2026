"""FiinQuant screening: the bank note fields for every ticker, one indicator per call.

`StockScreening` is an AND across its conditions, so a bank missing one field drops out of a multi-field request;
every call therefore asks for ONE indicator and the results are merged by ticker. Values come back in VND and are
converted to VND billion here. The note table FGFB_COFS_DR_NoteBank prints the provision movement cumulatively from
1 January, so the flow basis is measured against the Yearly interim before any quarter flow is derived.

What lands where: every call's raw frame and sidecar go to bronze/fiinscreen/<run_id> through the normal Collector;
the merged long table goes to silver/fiin_screening.parquet, the rows that fail a gate to
silver/fiin_screening_quarantine.parquet, and the gate rows to silver/fiin_screening_gate.csv.
"""

from pathlib import Path

import pandas as pd

from .extra_landing import read_silver, write_silver
from .fiin import Collector
from .files import now
from .notes_contract import SILVER_COLUMNS, to_quarterly
from .notes_gates import passes_silver, run_gates
from .runner import LAKE, ROOT

DOC = "https://docs.fiinquant.vn/fiinquant-en/function-and-formula/screening-function"
SCREEN = "fiin_screening.parquet"
QUARANTINE = "fiin_screening_quarantine.parquet"
GATES = "fiin_screening_gate.csv"
BRONZE = "fiinscreen"
TICKER = "Mã CK"
DIVISOR = 1e9                       # the screening values are VND

# field -> FiinQuant indicator name (FGFB_COFS_DR_NoteBank unless the table says otherwise)
INDICATORS = {
    "group_1_current": "4.1. Nợ đủ tiêu chuẩn",
    "group_2_watch": "4.2. Nợ cần chú ý",
    "group_3_substandard": "4.3. Nợ dưới tiêu chuẩn",
    "group_4_doubtful": "4.4. Nợ nghi ngờ",
    "group_5_loss": "4.5. Nợ xấu có khả năng mất vốn",
    "loans_customer": "6.1. Cho vay khách hàng",
    "provision_balance_sheet": "6.2. Dự phòng rủi ro cho vay khách hàng ",
    "provision_total": "9. Dự phòng cho vay khách hàng",
    "provision_opening_general": "9.1.1. Số đầu kỳ",
    "provision_charge_general": "9.1.2. Trích lập trong kỳ",
    "provision_used_general": "9.1.3. Sử dụng trong kỳ",
    "provision_opening_specific": "9.2.1. Số đầu kỳ",
    "provision_charge_specific": "9.2.2. Trích lập trong kỳ",
    "provision_used_specific": "9.2.3. Sử dụng trong kỳ",
    "provision_expense": "11. Chi phí dự phòng rủi ro tín dụng",
    "loans_change_period": "16. Tăng/Giảm các khoản cho vay khách hàng",
    "provision_used_for_losses": "18. Tăng/giảm nguồn dự phòng để bù đắp tổn thất các khoản",
    "npl_written_off_stock": "3. Nợ khó đòi đã xử lý",
}
# fields summed from their note components so the notes schema sees one movement table
COMPOSED = {"provision_opening": ("provision_opening_general", "provision_opening_specific"),
            "provision_charge": ("provision_charge_general", "provision_charge_specific"),
            "provision_used_writeoff": ("provision_used_general", "provision_used_specific")}
QUARTERLY = ["2021Q1", "2021Q2", "2021Q3", "2021Q4", "2022Q1", "2022Q2", "2022Q3", "2022Q4", "2023Q1", "2023Q2",
             "2023Q3", "2023Q4", "2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4",
             "2026Q1", "2026Q2", "2026Q3"]


def interim(period):
    """'2025Q2' -> ('Quarterly', 'Q2-2025'): FiinQuant's interim naming."""
    year, quarter = str(period)[:4], str(period)[5:]
    return "Quarterly", f"Q{quarter}-{year}"


def values_of(frame, name, ticker=TICKER):
    """ticker -> value in VND billion for one indicator reply (the column is the indicator name)."""
    if frame is None or not len(frame):
        return {}
    columns = [column for column in frame.columns if str(column).startswith(name)]
    if not columns or ticker not in frame:
        return {}
    series = pd.to_numeric(frame[columns[0]], errors="coerce")
    return {str(bank): float(value) / DIVISOR for bank, value in zip(frame[ticker], series)
            if pd.notna(value)}


def collect(collector, fields, periods, banks=None, sleep=None):
    """One call per (field, period): [(bank, period, field, value_vnd_bn, raw_sha256)] in VND billion."""
    screening = collector.client.StockScreening()
    rows = []
    for field in fields:
        name = INDICATORS[field]
        for period in periods:
            code, interim_id = interim(period)
            params = {"indicator": name, "interimCode": code, "indicatorInterimId": interim_id, "field": field}
            frame = collector.call(BRONZE, params, lambda name=name, code=code, interim_id=interim_id: screening.get(
                filter=[{"indicatorName": name, "interimCode": code, "indicatorInterimId": interim_id,
                         "conditionValues": [-1e15, 1e15]}]))
            sha = collector.calls[-1]["raw_sha256"] if collector.calls else ""
            for bank, value in values_of(frame, name).items():
                if banks is None or bank in banks:
                    rows.append({"bank": bank, "period": period, "field": field, "value_vnd_bn": value,
                                 "raw_sha256": sha})
            if sleep is not None:
                sleep()
    return rows


def compose(rows):
    """Add the summed movement fields (opening / charge / used) and provision_closing to the part rows."""
    by_key = {}
    for row in rows:
        by_key.setdefault((row["bank"], row["period"]), {})[row["field"]] = row
    out = list(rows)
    for (bank, period), fields in by_key.items():
        for field, parts in COMPOSED.items():
            found = [fields.get(part) for part in parts]
            if any(part is None for part in found):
                continue
            out.append({**found[0], "field": field, "value_vnd_bn": round(sum(part["value_vnd_bn"] for part in found), 6)})
        if "provision_total" in fields:
            out.append({**fields["provision_total"], "field": "provision_closing"})
    return out


def flow_basis(collector, field="provision_charge", year="2025", quarters=("2024Q4", "2025Q2")):
    """('quarter'|'ytd', evidence) from comparing a Q4 Quarterly reply with the same year's Yearly reply."""
    screening = collector.client.StockScreening()
    totals = {}
    for code, interim_id in (("Quarterly", f"Q4-{year}"), ("Yearly", year)):
        frame = collector.call(BRONZE, {"evidence": field, "interimCode": code, "interimInterimId": interim_id},
                               lambda code=code, interim_id=interim_id, name=INDICATORS[field]: screening.get(
                                   filter=[{"indicatorName": name, "interimCode": code,
                                            "indicatorInterimId": interim_id,
                                            "conditionValues": [-1e15, 1e15]}]))
        totals[code] = values_of(frame, INDICATORS[field])
    shared = sorted(set(totals["Quarterly"]) & set(totals["Yearly"]))
    if not shared:
        return "unknown", {"shared": 0}
    equal = sum(abs(totals["Quarterly"][bank] - totals["Yearly"][bank]) <= max(1.0, 0.01 * abs(totals["Yearly"][bank]))
                for bank in shared)
    basis = "ytd" if equal >= 0.8 * len(shared) else "quarter"
    return basis, {"shared": len(shared), "equal": equal, "year": year,
                   "example": {bank: {"quarterly": totals["Quarterly"][bank], "yearly": totals["Yearly"][bank]}
                               for bank in shared[:3]}}


def to_silver(rows, basis="ytd"):
    """The notes-schema long table: balances point, flows ytd plus the derived single quarters."""
    records = []
    for row in rows:
        field = row["field"]
        if field in ("provision_opening_general", "provision_charge_general", "provision_used_general",
                     "provision_opening_specific", "provision_charge_specific", "provision_used_specific",
                     "provision_total", "provision_balance_sheet", "provision_expense", "loans_change_period",
                     "provision_used_for_losses"):
            continue                    # parts and memo fields: kept in the bronze and the composition, not silver
        flow = field in ("provision_charge", "provision_used_writeoff", "provision_used_for_losses")
        records.append({"bank": row["bank"], "period": row["period"], "field": field,
                        "basis": "ytd" if flow and basis != "quarter" else "point",
                        "value_vnd_bn": round(float(row["value_vnd_bn"]), 6), "page": 1, "source_url": DOC,
                        "statement_type": "consolidated", "unit": "bn", "reader": "fiinquant_screening",
                        "grade": "single", "raw_sha256": row.get("raw_sha256") or ""})
    frame = pd.DataFrame(records, columns=SILVER_COLUMNS)
    if basis == "ytd":
        frame = pd.DataFrame(to_quarterly(frame.to_dict("records")), columns=SILVER_COLUMNS)
    return frame


def audit(screening, pdf, tolerance=0.005):
    """Match rate of the screening values against the PDF bank-quarters that overlap them."""
    if pdf is None or not len(pdf) or screening is None or not len(screening):
        return {"pairs": 0, "match": 0, "rate": None, "by_field": {}}
    left = screening[screening["basis"].isin(["point", "ytd"])].copy()
    right = pdf[pdf["basis"].isin(["point", "ytd"])].copy()
    left["key"] = left["bank"].astype(str) + "|" + left["period"].astype(str) + "|" + left["field"]
    right["key"] = right["bank"].astype(str) + "|" + right["period"].astype(str) + "|" + right["field"]
    left = left.groupby("key").first()
    right = right.groupby("key").first()
    shared = sorted(set(left.index) & set(right.index))
    by_field = {}
    for key in shared:
        ours, theirs = float(left.loc[key, "value_vnd_bn"]), float(right.loc[key, "value_vnd_bn"])
        ok = abs(ours - theirs) <= max(0.001, tolerance * max(abs(ours), abs(theirs)))
        field = key.rsplit("|", 1)[1]
        block = by_field.setdefault(field, {"pairs": 0, "match": 0})
        block["pairs"] += 1
        block["match"] += int(ok)
    matches = sum(block["match"] for block in by_field.values())
    return {"pairs": len(shared), "match": matches, "rate": round(matches / len(shared), 4) if shared else None,
            "by_field": {field: {**block, "rate": round(block["match"] / block["pairs"], 4)}
                         for field, block in by_field.items()}}


def run_screening(lake=LAKE, credentials=None, today=None, fields=None, periods=None, collector=None, sleep=None):
    """Pull the screening fields, gate them, write silver/quarantine/gates and return the run log."""
    lake = Path(lake)
    run_id = "fiinscreen-" + now().strftime("%Y%m%dT%H%M%S")
    periods = list(periods or QUARTERLY)
    fields = list(fields or INDICATORS)
    vendor = read_silver(lake, "bank_quarter.parquet")
    banks = sorted(vendor["ticker"].astype(str).unique()) if vendor is not None else []
    collector = collector or Collector(credentials or ROOT / ".env.local", lake, run_id, today=today, sleep=sleep)
    if collector.client is None:
        collector.login()
    basis, evidence = flow_basis(collector) if "provision_charge" in fields else ("quarter", {})
    rows = compose(collect(collector, fields, periods, banks=set(banks), sleep=sleep))
    silver = to_silver(rows, basis=basis)
    vendor_pct = {}
    if vendor is not None and "npl" in vendor:
        values = pd.to_numeric(vendor["npl"], errors="coerce")
        scale = 100.0 if values.dropna().le(1).all() else 1.0
        vendor_pct = {(str(row.ticker), str(row.period)): float(row.npl) * scale
                      for row in vendor.itertuples() if pd.notna(row.npl)}
    gates, summary = run_gates(silver, vendor=vendor_pct)
    status = {}
    for row in gates.to_dict("records"):
        status.setdefault((row["bank"], row["period"]), {})[row["gate"]] = row["status"]
    clean = silver[silver.apply(lambda row: passes_silver(status.get((str(row["bank"]), str(row["period"])), {})),
                                axis=1)] if len(silver) else silver
    quarantine = silver[~silver.index.isin(clean.index)] if len(silver) else silver
    write_silver(lake, SCREEN, clean, {"run_id": run_id, "basis_evidence": evidence, "flow_basis": basis})
    write_silver(lake, QUARANTINE, quarantine, {"run_id": run_id, "reason": "a protective gate did not pass"})
    if len(gates):
        write_silver(lake, GATES, gates, {"run_id": run_id})
    pdf = read_silver(lake, "notes_bank_quarter.parquet")
    match = audit(clean, pdf)
    log = {"run_id": run_id, "flow_basis": basis, "basis_evidence": evidence, "banks": len(banks),
           "periods": [periods[0], periods[-1]], "calls": len(collector.calls), "rows": len(silver),
           "silver_rows": int(len(clean)), "quarantine_rows": int(len(quarantine)),
           "gates": summary, "audit": match,
           "coverage": {field: int(clean[clean.field.eq(field)]["bank"].nunique()) if len(clean) else 0
                        for field in sorted(set(clean["field"]))} if len(clean) else {}}
    return log
