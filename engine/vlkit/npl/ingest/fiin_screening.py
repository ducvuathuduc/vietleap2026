"""Land FiinQuant statement indicators, validate bank-quarters and reconcile the PDF audit sample."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path

import pandas as pd

from .extra_landing import read_silver, write_silver
from .fiin import Collector, quiet_sdk
from .files import now
from .notes_contract import GROUP_FIELDS, NPL_FIELDS, SILVER_COLUMNS, agreement
from .notes_gates import GATE_COLUMNS, groups_gate, npl_gate
from .runner import LAKE, ROOT

DOC = "https://docs.fiinquant.vn/fiinquant-en/function-and-formula/screening-function"
SCREEN = "fiin_screening.parquet"
QUARANTINE = "fiin_screening_quarantine.parquet"
GATES = "fiin_screening_gate.csv"
SOURCE = "fiinquant_screening"
BRONZE = "fiinscreen"
TICKER = "Mã CK"

INDICATORS = {
    "group_1_current": "4.1. Nợ đủ tiêu chuẩn",
    "group_2_watch": "4.2. Nợ cần chú ý",
    "group_3_substandard": "4.3. Nợ dưới tiêu chuẩn",
    "group_4_doubtful": "4.4. Nợ nghi ngờ",
    "group_5_loss": "4.5. Nợ xấu có khả năng mất vốn",
    "loans_customer": "6.1. Cho vay khách hàng",
    "provision_balance_sheet": "6.2. Dự phòng rủi ro cho vay khách hàng",
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
COMPOSED = {
    "provision_opening": ("provision_opening_general", "provision_opening_specific"),
    "provision_charge": ("provision_charge_general", "provision_charge_specific"),
    "provision_used_writeoff": ("provision_used_general", "provision_used_specific"),
}
FLOWS = {
    "provision_charge_general", "provision_used_general", "provision_charge_specific",
    "provision_used_specific", "provision_expense", "loans_change_period",
    "provision_used_for_losses", "provision_charge", "provision_used_writeoff",
}
UNSIGNED = {
    "provision_balance_sheet", "provision_total", "provision_closing",
    "provision_opening_general", "provision_opening_specific", "provision_opening",
    "provision_used_general", "provision_used_specific", "provision_used_writeoff",
}
QUARTERLY = [f"{year}Q{quarter}" for year in range(2021, 2027) for quarter in range(1, 5)
             if (year, quarter) <= (2026, 3)]


def interim(period):
    return ("Yearly", period[:4]) if period.endswith("FY") else ("Quarterly", f"Q{period[-1]}-{period[:4]}")


def values_of(frame, name):
    """Read a single indicator in VND and return values in billion VND."""
    if frame is None or frame.empty or TICKER not in frame:
        return {}
    columns = [column for column in frame if str(column).startswith(name.strip())]
    if len(columns) != 1:
        return {}
    values = pd.to_numeric(frame[columns[0]], errors="coerce")
    return {str(bank).strip().upper(): float(value) / 1e9
            for bank, value in zip(frame[TICKER], values) if pd.notna(bank) and pd.notna(value)}


def _rows(frame, field, period, digest, banks):
    return [{"bank": bank, "period": period, "field": field, "value_vnd_bn": value, "raw_sha256": digest}
            for bank, value in values_of(frame, INDICATORS[field]).items() if banks is None or bank in banks]


def collect(collector, fields, periods, banks=None):
    """Request one indicator at a time so missing fields do not filter other indicators."""
    with quiet_sdk():
        screening = collector.client.StockScreening()
    rows = []
    for field in fields:
        for period in periods:
            if period.endswith("FY") and field not in FLOWS:
                continue
            code, interim_id = interim(period)
            condition = {"indicatorName": INDICATORS[field], "interimCode": code, "indicatorInterimId": interim_id,
                         "conditionValues": [-1e18, 1e18]}
            params = {"field": field, "period": period, "filter": [condition]}

            def operation():
                reply = screening.get(filter=[{**condition, "conditionValues": condition["conditionValues"].copy()}])
                if reply is None:
                    raise ValueError(f"no FiinQuant response for {field} {period}")
                return json.loads(reply.to_json(orient="records", force_ascii=False, double_precision=15))

            frame = collector.call(BRONZE, params, operation, doc_url=DOC)
            rows.extend(_rows(frame, field, period, collector.calls[-1]["raw_sha256"], banks))
    return rows


def replay(lake, runs, fields, periods, banks):
    """Load specified Bronze runs in order. Later runs replace an earlier request."""
    calls = {}
    root = lake / "bronze" / BRONZE
    for run in runs:
        if Path(run).name != run or not (root / run).is_dir():
            raise ValueError(f"unknown Bronze run: {run}")
        for path in sorted((root / run).glob("*.json")):
            if path.name.endswith(".raw.json"):
                continue
            meta = json.loads(path.read_bytes())
            field, period = (meta["params"][key] for key in ("field", "period"))
            if field not in fields or period not in periods:
                continue
            content = path.with_suffix(".raw.json").read_bytes()
            if sha256(content).hexdigest() != meta["raw_sha256"]:
                raise ValueError(f"Bronze digest mismatch: {field} {period}")
            calls[field, period] = _rows(pd.DataFrame(json.loads(content)), field, period, meta["raw_sha256"], banks)
    missing = [(field, period) for field in fields for period in periods
               if (not period.endswith("FY") or field in FLOWS) and (field, period) not in calls]
    if missing:
        raise ValueError(f"missing Bronze requests: {missing[:8]} ({len(missing)} total)")
    return [row for batch in calls.values() for row in batch], len(calls)


def flow_basis(rows):
    """Distinguish a cumulative Q4 from four separate quarters using the yearly amount."""
    groups = defaultdict(dict)
    for row in rows:
        field, period = row["field"], row["period"]
        if field in FLOWS:
            value = row["value_vnd_bn"]
            groups[row["bank"], period[:4], field][period[4:]] = abs(value) if field in UNSIGNED else value

    assessed = {}
    by_bank = defaultdict(Counter)
    by_field = defaultdict(Counter)
    for (bank, year, field), values in groups.items():
        annual = values.get("FY")
        if annual is None or "Q4" not in values:
            continue
        ytd = agreement(values["Q4"], annual, rel=.005)
        quarters = [values.get(f"Q{q}") for q in range(1, 5)]
        complete = all(value is not None for value in quarters)
        single = complete and agreement(sum(quarters), annual, rel=.005)
        earlier_usage = field in UNSIGNED and any(value is not None and value > .001 for value in quarters[:3])
        if ytd and not single and (complete or earlier_usage):
            label = "ytd"
        elif single and not ytd:
            label = "quarter"
        else:
            label = "mismatch" if complete and not ytd else "unknown"
        assessed[bank, year, field] = label
        if label in {"quarter", "ytd"}:
            by_bank[bank, field][label] += 1
            by_field[field][label] += 1

    basis = assessed.copy()
    for bank, year, field in groups:
        key = (bank, year, field)
        if basis.get(key) == "mismatch":
            basis[key] = "unknown"
            continue
        if basis.get(key) in {"quarter", "ytd"}:
            continue
        votes = by_bank[bank, field]
        if len(votes) == 1:
            basis[key] = next(iter(votes))
        elif not votes and len(by_field[field]) == 1:
            basis[key] = next(iter(by_field[field]))
        else:
            basis[key] = "unknown"

    evidence = {field: {
        "compared": dict(Counter(label for key, label in assessed.items() if key[2] == field)),
        "classified": dict(Counter(label for key, label in basis.items() if key[2] == field)),
    } for field in sorted({key[2] for key in groups})}
    return basis, evidence


def compose(rows):
    """Sum compatible component values; the balance-sheet provision is the closing stock."""
    groups = defaultdict(dict)
    for row in rows:
        key = (row["bank"], row["period"], row.get("basis"))
        groups[key][row["field"]] = row
    out = list(rows)
    for fields in groups.values():
        for field, parts in COMPOSED.items():
            if all(part in fields for part in parts):
                first, second = (fields[part] for part in parts)
                out.append({**first, "field": field, "value_vnd_bn": first["value_vnd_bn"] + second["value_vnd_bn"],
                            "raw_sha256": "|".join((first["raw_sha256"], second["raw_sha256"]))})
        closing = fields.get("provision_balance_sheet") or fields.get("provision_total")
        if closing is not None:
            out.append({**closing, "field": "provision_closing", "value_vnd_bn": abs(closing["value_vnd_bn"])})
        if all(field in fields for field in NPL_FIELDS):
            parts = [fields[field] for field in NPL_FIELDS]
            out.append({**parts[0], "field": "groups_3_5", "value_vnd_bn": sum(part["value_vnd_bn"] for part in parts),
                        "raw_sha256": "|".join(part["raw_sha256"] for part in parts)})
    return out


def to_silver(rows, basis):
    """Derive single quarters within the same bank, field and year."""
    reported = {}
    for row in rows:
        bank, period, field = (row[key] for key in ("bank", "period", "field"))
        if period.endswith("FY"):
            continue
        value = row["value_vnd_bn"]
        if field in UNSIGNED:
            value = abs(value)
        key = (bank, period, field)
        label = basis if isinstance(basis, str) else basis.get((bank, period[:4], field), "unknown")
        clock = {"quarter": "quarterly", "ytd": "ytd"}.get(label, "unknown") if field in FLOWS else "point"
        reported[key] = {**row, "basis": clock, "value_vnd_bn": value}
    records = list(reported.values())
    for (bank, period, field), row in reported.items():
        if row["basis"] not in {"ytd", "unknown"}:
            continue
        quarter = int(period[-1])
        if quarter == 1:
            records.append({**row, "basis": "quarterly"})
        elif row["basis"] == "ytd":
            previous = reported.get((bank, period[:5] + str(quarter - 1), field))
            if previous is not None and previous["basis"] == "ytd":
                records.append({**row, "basis": "quarterly",
                                "value_vnd_bn": row["value_vnd_bn"] - previous["value_vnd_bn"],
                                "raw_sha256": "|".join((row["raw_sha256"], previous["raw_sha256"]))})
        elif field in UNSIGNED and row["value_vnd_bn"] == 0:
            prior = [reported.get((bank, f"{period[:5]}{q}", field)) for q in range(1, quarter)]
            if all(previous is not None and previous["value_vnd_bn"] == 0 for previous in prior):
                records.append({**row, "basis": "quarterly",
                                "raw_sha256": "|".join([*(previous["raw_sha256"] for previous in prior),
                                                        row["raw_sha256"]])})
    return pd.DataFrame([
        {**row, "page": None, "source_url": DOC, "statement_type": "consolidated", "unit": "bn",
         "reader": SOURCE, "grade": "single"}
        for row in compose(records)
    ], columns=SILVER_COLUMNS)


def _quality(silver, vendor_pct):
    rows, reasons, field_reasons = [], {}, {}
    for (bank, period), group in silver.groupby(["bank", "period"], sort=True):
        values = group.loc[group.basis.eq("point")].set_index("field")["value_vnd_bn"].to_dict()
        loans = values.get("loans_customer")
        parts = [values.get(field) for field in GROUP_FIELDS]
        total = sum(parts) if all(value is not None for value in parts) else None
        group_result = groups_gate(values)
        npl_result = npl_gate({**values, "loans_customer": total}, vendor_pct.get((bank, period)))
        bad_loans = loans is not None and not 1_000 <= loans <= 10_000_000
        negative_stock_or_usage = group.field.isin([*GROUP_FIELDS, *UNSIGNED, "npl_written_off_stock"])
        suspicious = ~group.value_vnd_bn.map(math.isfinite) | (negative_stock_or_usage & group.value_vnd_bn.lt(0))
        if loans is not None and not bad_loans:
            suspicious |= group.value_vnd_bn.abs().gt(loans) & ~group.field.eq("npl_written_off_stock")
        for field, parts in COMPOSED.items():
            bad_bases = group.loc[suspicious & group.field.isin(parts), "basis"]
            suspicious |= group.field.eq(field) & group.basis.isin(bad_bases)
        bad_fields = group.loc[suspicious, "field"]
        magnitude = ("fail" if not bad_fields.empty or bad_loans
                     else "skipped" if loans is None else "pass")
        magnitude_result = {
            "gate": "magnitude", "status": magnitude, "value": loans, "threshold": None,
            "detail": f"Gross loans {loans} bn VND (expected 1,000–10,000,000); out-of-range fields: "
                      f"{', '.join(sorted(bad_fields.unique())) or 'none'}",
        }
        checks = [group_result, npl_result, magnitude_result]
        rows.extend({"bank": bank, "period": period, **check} for check in checks)
        core_invalid = bad_loans or bad_fields.isin(GROUP_FIELDS).any() or loans is None
        required = checks if core_invalid else checks[:2]
        problems = [f"{check['gate']}: {check['detail']}" for check in required if check["status"] != "pass"]
        if problems:
            reasons[bank, period] = "; ".join(problems)
        field_reasons.update({index: f"magnitude: {magnitude_result['detail']}" for index in bad_fields.index})
    return pd.DataFrame(rows, columns=GATE_COLUMNS), reasons, field_reasons


def audit(screening, pdf, tolerance=.005):
    """Compare all overlapping like-for-like balances and flows before quarantine."""
    keys = ["bank", "period", "field", "basis"]
    columns = [*keys, "screening_vnd_bn", "pdf_vnd_bn", "pdf_grade", "pdf_scope", "comparable", "match"]
    overlap = pd.DataFrame(columns=columns)
    if pdf is not None and not pdf.empty and not screening.empty:
        sample = pdf.rename(columns={"grade": "pdf_grade", "statement_type": "pdf_scope",
                                     "value_vnd_bn": "pdf_vnd_bn"})
        sample = sample.reindex(columns=[*keys, "pdf_vnd_bn", "pdf_grade", "pdf_scope"])
        sample.loc[sample.field.eq("provision_opening"), "basis"] = "point"
        screen = screening
        if "flow_basis" in screening:
            # The silver basis column is the source label. flow_basis is point, quarterly or ytd.
            screen = screening.assign(basis=screening["flow_basis"])
        overlap = screen[[*keys, "value_vnd_bn"]].rename(columns={"value_vnd_bn": "screening_vnd_bn"}).merge(
            sample, on=keys)
        overlap["comparable"] = overlap.pdf_grade.isin(["single", "verified"]) & overlap.pdf_scope.eq("consolidated")
        scale = overlap[["screening_vnd_bn", "pdf_vnd_bn"]].abs().max(axis=1)
        overlap["match"] = (overlap.screening_vnd_bn - overlap.pdf_vnd_bn).abs().le((tolerance * scale).clip(lower=.001))
    vetted = overlap.loc[overlap.comparable.eq(True)]
    counts = vetted.groupby("field")["match"].agg(pairs="size", match="sum")
    by_field = {field: {"pairs": int(block.pairs), "match": int(block.match), "rate": block.match / block.pairs}
                for field, block in counts.iterrows()}
    matches = int(vetted["match"].sum()) if len(vetted) else 0
    all_rows_n = len(overlap)
    all_matched = int(overlap["match"].sum()) if all_rows_n else 0
    return {"overlaps": all_rows_n, "pairs": len(vetted), "match": matches,
            "rate": matches / len(vetted) if len(vetted) else None,
            "headline": {"matched": matches, "comparable": len(vetted),
                         "rate": matches / len(vetted) if len(vetted) else None},
            "all_rows": {"matched": all_matched, "rows": all_rows_n,
                         "rate": all_matched / all_rows_n if all_rows_n else None},
            "by_field": by_field}, overlap[columns]


def run_screening(lake=LAKE, credentials=None, today=None, fields=None, periods=None, collector=None, bronze_runs=None):
    """Land the complete batch, keeping quality failures and the PDF audit available for review."""
    lake = Path(lake)
    run_id = "fiinscreen-" + now().strftime("%Y%m%dT%H%M%S")
    periods, fields = list(periods or QUARTERLY), list(fields or INDICATORS)
    annual = sorted({period[:4] + "FY" for period in periods if period.endswith("Q4")})
    vendor = read_silver(lake, "bank_quarter.parquet")
    if vendor is None or vendor.empty:
        raise ValueError("bank_quarter.parquet is required for screening coverage and the NPL gate")
    if "basis" in vendor:
        vendor = vendor.loc[vendor.basis.eq("consolidated")]
    vendor = vendor.assign(ticker=vendor.ticker.str.strip().str.upper().replace({"BIDV": "BID"}))
    banks = set(vendor.ticker)
    if bronze_runs:
        rows, calls = replay(lake, bronze_runs, fields, periods + annual, banks)
    else:
        if collector is None:
            collector = Collector(credentials or ROOT / ".env.local", lake, run_id, today=today)
        if collector.client is None:
            collector.login()
        rows = collect(collector, fields, periods + annual, banks)
        calls = len(collector.calls)
    if not rows:
        raise ValueError("no screening observations for the bank panel")
    basis, evidence = flow_basis(rows)
    silver = to_silver(rows, basis)
    ratios = pd.to_numeric(vendor["npl"], errors="coerce") * 100
    vendor_pct = {(bank, period): value for bank, period, value in zip(vendor.ticker, vendor.period, ratios)
                  if pd.notna(value)}
    gates, reasons, field_reasons = _quality(silver, vendor_pct)
    reason = pd.Series([reasons.get((row.bank, row.period), field_reasons.get(row.Index))
                        for row in silver.itertuples()], index=silver.index, dtype="string")
    clean = silver.loc[reason.isna()]
    quarantine = silver.loc[reason.notna()].assign(reason=reason)
    audit_summary, audit_rows = audit(silver, read_silver(lake, "notes_bank_quarter.parquet"))
    coverage = silver.groupby(["field", "period"]).bank.nunique()
    coverage = coverage.reindex(pd.MultiIndex.from_product(
        [sorted(set(fields) | set(silver.field)), periods], names=["field", "period"]), fill_value=0)
    accepted = clean.groupby(["field", "period"]).bank.nunique()
    coverage_rows = coverage.rename("reported_banks").to_frame()
    coverage_rows["accepted_banks"] = accepted.reindex(coverage.index, fill_value=0)
    quarterly = clean.loc[clean.basis.eq("quarterly")].groupby(["field", "period"]).bank.nunique()
    coverage_rows["accepted_quarterly_banks"] = quarterly.reindex(coverage.index, fill_value=0)
    meta = {"run_id": run_id, "bronze_runs": list(bronze_runs or [run_id]), "flow_basis_evidence": evidence}
    for name, frame in ((SCREEN, clean), (QUARANTINE, quarantine)):
        write_silver(lake, name, frame.assign(flow_basis=frame.basis, basis=SOURCE), meta)
    write_silver(lake, GATES, gates, meta)
    write_silver(lake, "fiin_screening_audit.csv", audit_rows, meta)
    write_silver(lake, "fiin_screening_coverage.csv", coverage_rows.reset_index(), meta)
    status = gates.groupby("gate").status.value_counts().unstack(fill_value=0)
    counts = {field: {period: int(value) for period, value in block.droplevel("field").items()}
              for field, block in coverage.groupby(level="field")}
    return {"run_id": run_id, "basis_evidence": evidence, "banks": len(banks), "calls": calls, "rows": len(silver),
            "silver_rows": len(clean), "quarantine_rows": len(quarantine), "gates": status.to_dict(orient="index"),
            "audit": audit_summary, "coverage": counts}
