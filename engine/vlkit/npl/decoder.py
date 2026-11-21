"""Decode declines in reported NPL and estimate within-bank associations."""

import numpy as np
import pandas as pd

from .model import AMOUNTS, SILVER, derive_credit_quality
from .real_context import statement_amounts
from .real_models import _fit
from .regression import REGRESSORS
from .snapshot_metrics import json_safe


NOTES_BANKS = ("VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "STB")
KEYS = ["bank_code", "period"]
RATIOS = ["npl_ratio", "g2_ratio", "coverage", "writeoff_ratio", "npl_formation", "broad_problem_ratio", "loan_growth"]
VENDOR_LEVEL_FIELDS = ("npl_ratio", "coverage", "loan_growth", "nim", "lagged_coverage")
CHANGES = ["delta_npl_ratio", "delta_g2_ratio", "delta_coverage", "delta_writeoff_ratio"]
SEASON = ["expected_change_pp", "lo80_pp", "hi80_pp"]
COVERAGE_TOLERANCE = .0001  # One basis point of coverage, in fraction units.
SIGNALS = {
    "S1": ("Rủi ro có thể dồn sang nhóm 2", "Risk may be moving into group 2"),
    "S2": ("Tỷ lệ xóa nợ hoặc dự phòng sử dụng tăng", "Write-offs or provisions used rose relative to loans"),
    "S3": ("Đệm dự phòng và dự phòng trên dư nợ cùng mỏng đi", "Coverage and provisions relative to loans both fell"),
    "S4": ("Nhịp mùa vụ cuối năm", "Usual year-end movement"),
}
STATUS = {
    "clean": ("Cải thiện có cơ sở", "Improvement supported by the data"),
    "review": ("Cờ vàng cần xem xét", "Yellow flag to review"),
    "missing": ("Thiếu dữ liệu", "Missing data"),
    "not_applicable": ("Tỷ lệ nợ xấu không giảm", "NPL ratio did not fall"),
}


def _vendor_ratios(panel):
    data = panel.sort_values(KEYS).copy()
    consecutive = data.groupby("bank_code")["quarter_id"].diff().eq(1)
    data["npl_ratio"] = data["npl_pct"] / 100
    data["delta_npl_ratio"] = data["d_npl_pct"] / 100
    data["coverage"] = data["coverage_pct"] / 100
    data["delta_coverage"] = data["d_coverage_pct"] / 100
    data["lagged_coverage"] = data.groupby("bank_code")["coverage"].shift().where(consecutive)
    data["loan_growth"] = data["loan_growth_yoy_pct"] / 100
    data["nim"] = data["nim_pct"] / 100
    for field in ["g2_ratio", "writeoff_ratio", "npl_formation"]:
        if field not in data:
            data[field] = np.nan
    for field in ["g2_ratio", "writeoff_ratio"]:
        delta = f"delta_{field}"
        if delta not in data:
            data[delta] = data.groupby("bank_code")[field].diff().where(consecutive)
    data["broad_problem_ratio"] = data["npl_ratio"] + data["g2_ratio"]
    return data[[*KEYS, *RATIOS, *CHANGES, "lagged_coverage", "nim"]]


def _notes_ratios(notes, screening=None):
    amounts, _ = statement_amounts(notes, screening=screening)
    has_screening = screening is not None and not screening.empty
    if has_screening:
        observed = amounts.loc[amounts.source.eq("fiin_screening")].set_index(KEYS).drop(columns="source")
        pdf = amounts.loc[amounts.source.eq("notes_bank_quarter")].set_index(KEYS).drop(columns="source")
        amounts = observed.combine_first(pdf).reset_index()
    fields = {"customer_loans": "loans_vnd_bn", "group2_loans": "group2_vnd_bn", "groups345_loans": "npl_vnd_bn",
              "provision_balance": "provision_vnd_bn", "writeoffs": "writeoff_vnd_bn"}
    amounts = amounts[[*KEYS, *fields]].rename(columns=fields)
    # A statement with contradictory totals cannot support the component ratios.
    problem = amounts[["npl_vnd_bn", "group2_vnd_bn"]].fillna(0).sum(axis=1)
    invalid = problem.gt(amounts["loans_vnd_bn"]) & ~np.isclose(
        problem, amounts["loans_vnd_bn"], rtol=1e-12, atol=0)
    amounts.loc[invalid, ["npl_vnd_bn", "group2_vnd_bn"]] = np.nan
    amounts["basis"] = "consolidated"
    amounts["writeoff_basis"] = "quarter"
    credit = derive_credit_quality(amounts.reindex(columns=SILVER))
    if has_screening:
        reported = observed.index[observed.writeoffs.notna()]
        proxy = pd.Series(pd.MultiIndex.from_frame(credit[KEYS]).isin(reported), index=credit.index)
        comparable = proxy.eq(proxy.groupby(credit.bank_code).shift(fill_value=False))
        credit["delta_writeoff_ratio"] = credit["delta_writeoff_ratio"].where(comparable)
    return credit[[*KEYS, *AMOUNTS, *RATIOS, *CHANGES, "lagged_coverage"]]


def _assessment(row):
    decline = row.delta_npl_ratio
    missing = []
    accounting = []
    context = []
    if pd.notna(getattr(row, "loan_growth", np.nan)):
        context.append("loan_growth")
    if bool(getattr(row, "legal_regime", False)):
        context.append("legal_regime")
    if pd.isna(decline):
        missing.append("delta_npl_ratio")
        status = "missing"
    elif decline >= -1e-12:
        status = "not_applicable"
    else:
        provision_down = getattr(row, "delta_provisions_to_loans", np.nan)
        checks = [
            ("S1", "delta_g2_ratio", row.delta_g2_ratio, row.delta_g2_ratio > 1e-12),
            ("S2", "delta_writeoff_ratio", row.delta_writeoff_ratio,
             row.delta_writeoff_ratio > 1e-12 and bool(getattr(row, "writeoff_quarter_flow", False))),
            ("S3", "delta_coverage", row.delta_coverage,
             row.delta_coverage < -1e-12 and pd.notna(provision_down) and provision_down < -1e-12),
        ]
        for rule, field, value, fired in checks:
            if pd.isna(value):
                missing.append(field)
            elif fired:
                accounting.append(rule)
        if row.period.endswith("Q4"):
            if any(pd.isna(getattr(row, field)) for field in SEASON):
                missing.append("seasonal_band")
            else:
                surprise = 100 * decline - row.expected_change_pp
                if row.lo80_pp - 1e-10 <= surprise <= row.hi80_pp + 1e-10:
                    context.append("S4")
        if {"delta_g2_ratio", "delta_writeoff_ratio"}.intersection(missing):
            status = "missing"
        elif accounting:
            status = "review"
        else:
            status = "missing" if missing else "clean"
    if bool(getattr(row, "coverage_contested", False)):
        quality = "cách ly"
    elif missing:
        quality = "thiếu"
    else:
        quality = "đủ"
    shown = [*accounting, *(["S4"] if "S4" in context else [])]
    vi, en = STATUS[status]
    return {"status": status, "status_vi": vi, "status_en": en, "missing_inputs": missing,
            "layers": {"data_quality": quality, "accounting": accounting, "context": context},
            "signals": [{"id": rule, "text_vi": SIGNALS[rule][0], "text_en": SIGNALS[rule][1]} for rule in shown]}


SCREEN_FIELDS = ["g2_ratio", "delta_g2_ratio", "writeoff_ratio", "delta_writeoff_ratio"]
WITHOUT_WRITEOFF = ["delta_g2_ratio", "loan_growth", "lagged_coverage"]
REDUCED = ["loan_growth", "lagged_coverage"]


def _with_screening(vendor, screening):
    """Replace the empty note fields with FiinQuant group 2 and quarterly write-offs."""
    if screening is None or screening.empty:
        return vendor
    ratios = _notes_ratios(None, screening)
    if ratios.empty:
        return vendor
    extra = ratios[[*KEYS, *SCREEN_FIELDS]].drop_duplicates(KEYS)
    return vendor.drop(columns=SCREEN_FIELDS).merge(extra, on=KEYS, how="left")


def _sample_banks(data, terms):
    used = data.dropna(subset=["delta_npl_ratio", *terms])
    return sorted(used.bank_code.astype(str).unique())


def _sample_sentence(label_vi, label_en, fit, banks):
    if not fit or not fit.get("n"):
        return (f"{label_vi}: không có quan sát đủ trường.", f"{label_en}: no complete observations.")
    span = "–".join(fit["period"]) if fit.get("period") else ""
    names = ", ".join(banks)
    return (f"{label_vi}: n={fit['n']}, kỳ {span}, ngân hàng {names}.",
            f"{label_en}: n={fit['n']}, period {span}, banks {names}.")


def _decoder_fit(data, *, grid_n, vendor):
    outcome = "delta_npl_ratio"
    complete = _fit(data, outcome, REGRESSORS, bank=True, bootstrap=True)[0]
    absent = [field for field in REGRESSORS if not data[field].notna().any()]
    if vendor:
        without = _fit(data, outcome, WITHOUT_WRITEOFF, bank=True, bootstrap=True)[0]
        available = _fit(data, outcome, REDUCED, bank=True, bootstrap=True)[0]
        sample_banks = {
            "full": _sample_banks(data, REGRESSORS),
            "without_writeoff": _sample_banks(data, WITHOUT_WRITEOFF),
            "available": _sample_banks(data, REDUCED),
        }
        parts = [
            _sample_sentence("Mẫu (a), đủ biến kể cả tỷ lệ xóa nợ theo quý",
                             "(a) full sample, including the quarterly write-off ratio",
                             complete, sample_banks["full"]),
            _sample_sentence("Mẫu (b), không gồm xóa nợ", "(b) without write-off",
                             without, sample_banks["without_writeoff"]),
            _sample_sentence("Mẫu (c), tăng trưởng dư nợ và bao phủ trễ",
                             "(c) loan growth and lagged coverage",
                             available, sample_banks["available"]),
        ]
        reading_vi = " ".join(part[0] for part in parts)
        reading_en = " ".join(part[1] for part in parts)
        if not data["writeoff_ratio"].notna().any() and not data["delta_g2_ratio"].notna().any():
            reading_vi = "Mô hình rút gọn do thiếu dữ liệu nhóm 2 và xóa nợ. " + reading_vi
            reading_en = "Reduced model because Group 2 and write-off data are missing. " + reading_en
        reading_vi += " Tăng trưởng dư nợ là cùng kỳ năm trước."
        reading_en += " Loan growth is year over year."
    else:
        terms = [field for field in REGRESSORS if field not in absent]
        without = None
        available = (_fit(data, outcome, terms, bank=True, bootstrap=True)[0] if absent and terms else None)
        sample_banks = None
        reading_vi = "Mẫu ghi chú dùng tăng trưởng dư nợ theo quý; hệ số có thể gợi ý chiều liên hệ."
        reading_en = "The notes sample uses quarter-over-quarter loan growth; coefficients can suggest a direction."
    return {
        "n_panel": len(data), "grid_n": grid_n,
        "panel_period": [data.period.min(), data.period.max()] if len(data) else None,
        "full": complete, "without_writeoff": without, "available": available,
        "sample_banks": sample_banks, "unavailable_fields": absent,
        "n_by_field": {column: int(data[column].count()) for column in [outcome, *REGRESSORS]},
        "growth_measure": "year_over_year" if vendor else "quarter_over_quarter",
        "reading_vi": reading_vi,
        "reading_en": reading_en,
        "does_not_show_vi": ("Bao phủ quý trước và biến động NPL cùng dùng mức NPL quý trước, nên hệ số chỉ mô tả liên hệ."
                             if vendor else "Mẫu ghi chú nhỏ chỉ gợi ý chiều liên hệ; độ lớn của tác động còn bất định."),
        "does_not_show_en": ("Lagged coverage and the NPL change both use prior-quarter NPL, so the coefficient describes an association."
                             if vendor else "The small notes sample supports directional interpretation; the effect size remains uncertain."),
    }


def build_decoder(panel, seasonal, notes, screening=None, *, regimes=None):
    """Attach screening inputs first, using the audited PDFs for missing fields."""
    vendor = _vendor_ratios(panel)
    pdf = _notes_ratios(notes)
    statements = _notes_ratios(notes, screening) if screening is not None else pdf
    start, end = panel.period.min(), panel.period.max()
    periods = pd.period_range(end=end, periods=6, freq="Q").astype(str).tolist()
    banks = sorted(vendor.bank_code.unique())
    history = pd.period_range(start, end, freq="Q").astype(str).tolist()
    statements = statements.loc[statements.bank_code.isin(banks) & statements.period.le(end)]
    pdf = pdf.loc[pdf.bank_code.isin(banks) & pdf.period.le(end)]

    note_fields = ["g2_ratio", "delta_g2_ratio", "writeoff_ratio", "delta_writeoff_ratio",
                   "npl_formation", "broad_problem_ratio"]
    grid = pd.MultiIndex.from_product([banks, history], names=KEYS).to_frame(index=False)
    board = grid.merge(vendor.drop(columns=note_fields), on=KEYS, how="left", validate="one_to_one")
    board = board.merge(
        statements[[*KEYS, *AMOUNTS, *note_fields]],
        on=KEYS, how="left", validate="one_to_one",
    ).merge(
        pdf[[*KEYS, "coverage", "delta_coverage"]].rename(
            columns={"coverage": "notes_coverage", "delta_coverage": "notes_delta_coverage"}),
        on=KEYS, how="left", validate="one_to_one",
    ).merge(seasonal[[*KEYS, *SEASON]], on=KEYS, how="left", validate="one_to_one")

    both = board["coverage"].notna() & board["notes_coverage"].notna()
    agrees = np.isclose(board["coverage"], board["notes_coverage"], rtol=0, atol=COVERAGE_TOLERANCE + 1e-12)
    board["coverage_contested"] = both & ~agrees
    board["coverage_source"] = np.select(
        [agrees, board["coverage"].notna()], ["notes", "fiinquant"], default=None,
    )
    # Use one source for both endpoints to avoid flags caused by a source switch.
    previous_agrees = board["coverage_source"].eq("notes").groupby(board["bank_code"]).shift(fill_value=False)
    coverage_change = board["delta_coverage"].mask(agrees & previous_agrees, board.pop("notes_delta_coverage"))
    board["coverage"] = board["coverage"].mask(agrees, board.pop("notes_coverage"))
    previous_contested = board.groupby("bank_code")["coverage_contested"].shift(fill_value=False)
    board["delta_coverage"] = coverage_change.where(~board["coverage_contested"] & ~previous_contested)
    loans = board["loans_vnd_bn"].replace(0, np.nan) if "loans_vnd_bn" in board else np.nan
    board["provisions_to_loans"] = board["provision_vnd_bn"] / loans if "provision_vnd_bn" in board else np.nan
    consecutive = board.groupby("bank_code").period.transform(
        lambda series: pd.Series(pd.PeriodIndex(series.astype(str), freq="Q").asi8, index=series.index).diff().eq(1))
    board["delta_provisions_to_loans"] = board.groupby("bank_code").provisions_to_loans.diff().where(consecutive)
    # Amounts that reach this table are already quarter flows: screening keeps flow_basis quarterly,
    # and the notes path keeps verified quarterly or consolidated write-offs. A YTD flow never arrives.
    board["writeoff_quarter_flow"] = board["writeoff_vnd_bn"].notna() if "writeoff_vnd_bn" in board else False
    board["legal_regime"] = board.period.isin(set(regimes or ()))
    rows = [{**row._asdict(), **_assessment(row)} for row in board.itertuples(index=False)]
    focus_index = pd.MultiIndex.from_product([NOTES_BANKS, periods], names=KEYS)
    focus_board = board.set_index(KEYS).reindex(focus_index).reset_index()
    focus_board["coverage_contested"] = focus_board["coverage_contested"].eq(True)
    focus = [{**row._asdict(), **_assessment(row)} for row in focus_board.itertuples(index=False)]
    availability = {}
    for rule, field in [("S1", "delta_g2_ratio"), ("S2", "delta_writeoff_ratio"),
                        ("S3", "delta_coverage"), ("S4", "seasonal_band")]:
        eligible = [row for row in rows if pd.notna(row["delta_npl_ratio"])
                    and row["delta_npl_ratio"] < -1e-12 and (rule != "S4" or row["period"].endswith("Q4"))]
        available = sum(field not in row["missing_inputs"] for row in eligible)
        availability[rule] = {"eligible": available, "missing": [field] if not available else [],
                              "fired": sum(any(flag["id"] == rule for flag in row["signals"]) for row in eligible)}
    return json_safe({
        "title_vi": "Sau tỷ lệ nợ xấu: Chất lượng tín dụng của các ngân hàng Việt Nam có thực sự cải thiện?",
        "title_en": "Behind the NPL Ratio: Is Credit Quality in Vietnamese Banks Really Improving?",
        "periods": periods, "banks": list(NOTES_BANKS), "rows": rows, "focus": focus,
        "signal_availability": availability,
        "regression": {
            "outcome": "delta_npl_ratio", "regressors": REGRESSORS,
            "estimator": "bank fixed effects OLS; bank-clustered SE; restricted wild cluster bootstrap",
            "fiinquant": _decoder_fit(_with_screening(vendor, screening), grid_n=len(banks) * len(history), vendor=True),
            "notes": _decoder_fit(pdf, grid_n=None, vendor=False),
        },
        "reading_vi": ("Trạng thái cần xem xét chỉ bật khi có tín hiệu kế toán S1, S2 hoặc S3. "
                       "S4, tăng trưởng dư nợ và chế độ pháp lý là bối cảnh. S4 dùng dải mùa vụ M7."),
        "reading_en": ("The review status turns on only for accounting signals S1, S2 or S3. "
                       "S4, loan growth and the legal regime are context. S4 uses the M7 seasonal band."),
        "does_not_show_vi": "Cờ vàng đặt ưu tiên rà soát; bằng chứng cần thêm về chất lượng tín dụng và nguyên nhân.",
        "does_not_show_en": "Yellow flags prioritize review; determining credit quality and its causes requires more evidence.",
    })
