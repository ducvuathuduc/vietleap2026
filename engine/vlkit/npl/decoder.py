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
    "S2": ("Giảm nhờ xóa nợ", "Fall driven by write-offs"),
    "S3": ("Đệm dự phòng mỏng đi", "Provision buffer thinner"),
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


def _notes_ratios(notes):
    amounts, _ = statement_amounts(notes)
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
    return credit[[*KEYS, *AMOUNTS, *RATIOS, *CHANGES, "lagged_coverage"]]


def _assessment(row):
    decline = row.delta_npl_ratio
    missing = []
    signals = []
    if pd.isna(decline):
        missing.append("delta_npl_ratio")
        status = "missing"
    elif decline >= -1e-12:
        status = "not_applicable"
    else:
        checks = [
            ("S1", "delta_g2_ratio", row.delta_g2_ratio, row.delta_g2_ratio > 1e-12),
            ("S2", "delta_writeoff_ratio", row.delta_writeoff_ratio, row.delta_writeoff_ratio > 1e-12),
            ("S3", "delta_coverage", row.delta_coverage, row.delta_coverage < -1e-12),
        ]
        for rule, field, value, fired in checks:
            if pd.isna(value):
                missing.append(field)
            elif fired:
                signals.append(rule)
        if row.period.endswith("Q4"):
            if any(pd.isna(getattr(row, field)) for field in SEASON):
                missing.append("seasonal_band")
            else:
                surprise = 100 * decline - row.expected_change_pp
                if row.lo80_pp - 1e-10 <= surprise <= row.hi80_pp + 1e-10:
                    signals.append("S4")
        if {"delta_g2_ratio", "delta_writeoff_ratio"}.intersection(missing):
            status = "missing"
        elif signals:
            status = "review"
        else:
            status = "missing" if missing else "clean"
    vi, en = STATUS[status]
    return {"status": status, "status_vi": vi, "status_en": en, "missing_inputs": missing,
            "signals": [{"id": rule, "text_vi": SIGNALS[rule][0], "text_en": SIGNALS[rule][1]} for rule in signals]}


def _decoder_fit(data, *, grid_n, vendor):
    outcome = "delta_npl_ratio"
    complete = _fit(data, outcome, REGRESSORS, bank=True, bootstrap=True)[0]
    absent = [field for field in REGRESSORS if not data[field].notna().any()]
    terms = [field for field in REGRESSORS if field not in absent]
    available = (_fit(data, outcome, terms, bank=True, bootstrap=True)[0]
                 if vendor and absent and terms else None)
    return {
        "n_panel": len(data), "grid_n": grid_n,
        "panel_period": [data.period.min(), data.period.max()] if len(data) else None,
        "full": complete, "available": available, "unavailable_fields": absent,
        "n_by_field": {column: int(data[column].count()) for column in [outcome, *REGRESSORS]},
        "growth_measure": "year_over_year" if vendor else "quarter_over_quarter",
        "reading_vi": ("Dữ liệu FiinQuant dùng tăng trưởng dư nợ cùng kỳ năm trước; khi thiếu cả trường, "
                       "mô hình rút gọn chỉ dùng các biến có dữ liệu." if vendor else
                       "Mẫu ghi chú dùng tăng trưởng dư nợ theo quý; hệ số có thể gợi ý chiều liên hệ."),
        "reading_en": ("FiinQuant uses year-over-year loan growth; the reduced model uses the regressors with data "
                       "when entire fields are absent." if vendor else
                       "The notes sample uses quarter-over-quarter loan growth; coefficients can suggest a direction."),
        "does_not_show_vi": ("Bao phủ quý trước và biến động NPL cùng dùng mức NPL quý trước, nên hệ số chỉ mô tả liên hệ."
                             if vendor else "Mẫu ghi chú nhỏ chỉ gợi ý chiều liên hệ; độ lớn của tác động còn bất định."),
        "does_not_show_en": ("Lagged coverage and the NPL change both use prior-quarter NPL, so the coefficient describes an association."
                             if vendor else "The small notes sample supports directional interpretation; the effect size remains uncertain."),
    }


def build_decoder(panel, seasonal, notes):
    """Build the vendor history and attach statement inputs by bank and quarter."""
    vendor = _vendor_ratios(panel)
    statements = _notes_ratios(notes)
    start, end = panel.period.min(), panel.period.max()
    periods = pd.period_range(end=end, periods=6, freq="Q").astype(str).tolist()
    banks = sorted(vendor.bank_code.unique())
    history = pd.period_range(start, end, freq="Q").astype(str).tolist()
    statements = statements.loc[statements.bank_code.isin(banks) & statements.period.le(end)]

    note_fields = ["g2_ratio", "delta_g2_ratio", "writeoff_ratio", "delta_writeoff_ratio",
                   "npl_formation", "broad_problem_ratio"]
    grid = pd.MultiIndex.from_product([banks, history], names=KEYS).to_frame(index=False)
    board = grid.merge(vendor.drop(columns=note_fields), on=KEYS, how="left", validate="one_to_one")
    board = board.merge(
        statements[[*KEYS, *AMOUNTS, *note_fields, "coverage", "delta_coverage"]]
        .rename(columns={"coverage": "notes_coverage", "delta_coverage": "notes_delta_coverage"}),
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
            "fiinquant": _decoder_fit(vendor, grid_n=len(banks) * len(history), vendor=True),
            "notes": _decoder_fit(statements, grid_n=None, vendor=False),
        },
        "reading_vi": ("Đọc cờ vàng khi tỷ lệ nợ xấu giảm và đọc trạng thái Thiếu dữ liệu cùng các cờ đã xác định. "
                       "S4 dùng dải mùa vụ M7 ước lượng từ dữ liệu FiinQuant."),
        "reading_en": ("Review yellow flags when the NPL ratio falls and read Missing data alongside any flags the data support. "
                       "S4 uses the M7 seasonal band estimated from FiinQuant."),
        "does_not_show_vi": "Cờ vàng đặt ưu tiên rà soát; bằng chứng cần thêm về chất lượng tín dụng và nguyên nhân.",
        "does_not_show_en": "Yellow flags prioritize review; determining credit quality and its causes requires more evidence.",
    })
