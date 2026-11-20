"""Split a quarterly NPL-ratio change into a loan-growth part and a bad-debt stock part.

denominator + numerator = change. A bank-quarter whose five loan groups repeat an earlier
quarter, or whose groups do not add up to customer loans, is left out of the rows.
"""
import numpy as np
import pandas as pd

GROUPS = ["group_1_current", "group_2_watch", "group_3_substandard", "group_4_doubtful", "group_5_loss"]
FOCUS = ("TCB", "CTG", "VBB")
REPEAT_ATOL = 0.05


def _ordinal(period):
    text = str(period)
    if len(text) == 6 and text[4] == "Q" and text[:4].isdigit() and text[5] in "1234":
        return int(text[:4]) * 4 + int(text[5])
    return None


def _number(value):
    if value is None or not np.isfinite(value):
        return None
    return float(value)


def _panel(screening):
    stocks = screening.loc[screening["flow_basis"].eq("point") & screening["field"].isin([*GROUPS, "loans_customer"])]
    wide = stocks.pivot_table(index=["bank", "period"], columns="field", values="value_vnd_bn", aggfunc="first")
    wide = wide.dropna(subset=GROUPS).reset_index()
    wide["total"] = wide[GROUPS].sum(axis=1)
    wide["bad"] = wide[GROUPS[2:]].sum(axis=1)
    wide["npl_pct"] = wide["bad"] / wide["total"] * 100
    wide["g2_pct"] = wide["group_2_watch"] / wide["total"] * 100
    wide["ordinal"] = wide["period"].map(_ordinal)
    wide = wide.dropna(subset=["ordinal"]).sort_values(["bank", "ordinal"])
    writeoff = screening.loc[
        screening["field"].eq("provision_used_writeoff") & screening["flow_basis"].eq("quarterly"),
        ["bank", "period", "value_vnd_bn"],
    ].drop_duplicates(["bank", "period"])
    wide = wide.merge(writeoff.rename(columns={"value_vnd_bn": "writeoff"}), on=["bank", "period"], how="left")
    if "loans_customer" not in wide:
        wide["loans_customer"] = np.nan
    return wide


def _repeats(wide):
    """Bank-periods whose group stocks match an earlier quarter of the same bank."""
    flagged = []
    detail = []
    for bank, block in wide.groupby("bank", sort=False):
        rows = block.reset_index(drop=True)
        vectors = rows[GROUPS].to_numpy(dtype=float)
        for index in range(1, len(rows)):
            current = vectors[index]
            earlier = vectors[:index]
            match = np.isclose(earlier, current, rtol=0, atol=REPEAT_ATOL).all(axis=1)
            loans = rows.at[index, "loans_customer"]
            total = rows.at[index, "total"]
            gap = None if not np.isfinite(loans) else float(total - loans)
            basis_break = gap is not None and abs(gap) > max(1.0, 0.01 * abs(total))
            if match.any() or basis_break:
                flagged.append((bank, rows.at[index, "period"]))
            if str(rows.at[index, "period"]) == "2025Q4" or bank in FOCUS:
                previous = rows.iloc[index - 1]
                growth = None
                if rows.at[index, "ordinal"] - previous["ordinal"] == 1 and previous["total"]:
                    growth = float(rows.at[index, "total"] / previous["total"] - 1) * 100
                repeated = None if not match.any() else str(rows.at[int(np.flatnonzero(match)[-1]), "period"])
                detail.append({
                    "bank_code": bank,
                    "period": str(rows.at[index, "period"]),
                    "qoq_loan_growth_pct": growth,
                    "repeats_period": repeated,
                    "loans_gap_bn": gap,
                    "groups_total_bn": _number(total),
                    "loans_customer_bn": _number(loans),
                    "basis_break": bool(basis_break),
                })
    return flagged, detail


def _notes_note(notes):
    if notes is None or notes.empty:
        return None
    sample = notes.loc[notes["bank"].eq("CTG") & notes["period"].eq("2025Q4") & notes["field"].isin(GROUPS)]
    if sample.empty or "value_vnd_bn" not in sample:
        return None
    pdf = sample.groupby("field")["value_vnd_bn"].first()
    doubtful = pdf.get("group_4_doubtful")
    if doubtful is None or not np.isfinite(doubtful):
        return None
    return {
        "bank_code": "CTG",
        "period": "2025Q4",
        "pdf_group_4_bn": float(doubtful),
        "reading_vi": (
            f"Bản PDF hợp nhất của CTG quý 4/2025 ghi nợ nhóm 4 là {doubtful:.4f} tỷ đồng, "
            "trong khi các nhóm khác khớp FiinQuant. Con số PDF nhỏ hơn đúng 1.000 lần so với mức làm "
            "tổng năm nhóm bằng dư nợ khách hàng, nên đây là lệch đơn vị khi đọc PDF, không phải bảng FiinQuant lặp quý."
        ),
        "reading_en": (
            f"CTG's consolidated Q4 2025 PDF reads group-4 loans as {doubtful:.4f} billion VND, "
            "while the other groups match FiinQuant. The PDF figure is 1,000 times smaller than the amount "
            "that makes the five groups add up to customer loans, so it is a unit error in the PDF read, not a repeated FiinQuant quarter."
        ),
    }


def decompose_screening(screening, notes=None):
    if screening is None or len(screening) == 0:
        return {
            "rows": [], "by_quarter": [], "quarantine": [],
            "unavailable_reason": "no_screening_table",
            "reading_vi": "Chưa có bảng nhóm nợ FiinQuant, nên chưa tách được phần mẫu số và phần tử số.",
            "reading_en": "The FiinQuant loan-group table is absent, so the denominator and numerator split is unavailable.",
            "q4_2025_check": {"artefact": False, "quarantine": [], "banks": [],
                              "reading_vi": "Không có bảng nhóm nợ để kiểm tra quý 4/2025.",
                              "reading_en": "No loan-group table was available to check 2025Q4."},
        }
    wide = _panel(screening)
    flagged, detail = _repeats(wide)
    quarantine = sorted({bank for bank, period in flagged if str(period) == "2025Q4"})
    drop = {(bank, period) for bank, period in flagged}
    previous = wide.groupby("bank", sort=False).shift(1)
    consecutive = wide["ordinal"] - previous["ordinal"] == 1
    usable = wide.loc[consecutive].copy()
    prior = previous.loc[consecutive]
    keep = [pair not in drop for pair in zip(usable["bank"], usable["period"])]
    usable, prior = usable.loc[keep].copy(), prior.loc[keep].copy()
    growth = usable["total"].to_numpy(dtype=float) / prior["total"].to_numpy(dtype=float) - 1
    previous_npl = prior["npl_pct"].to_numpy(dtype=float)
    usable["d_npl_pp"] = usable["npl_pct"].to_numpy(dtype=float) - previous_npl
    usable["denominator_pp"] = -previous_npl * growth / (1 + growth)
    usable["numerator_pp"] = (usable["bad"].to_numpy(dtype=float) - prior["bad"].to_numpy(dtype=float)) / usable["total"].to_numpy(dtype=float) * 100
    usable["loan_growth_qoq_pct"] = growth * 100
    usable["d_g2_pp"] = usable["g2_pct"].to_numpy(dtype=float) - prior["g2_pct"].to_numpy(dtype=float)
    usable["writeoff_pct_loans"] = usable["writeoff"].abs() / usable["total"] * 100
    rows = []
    for record in usable.itertuples(index=False):
        rows.append({
            "bank_code": record.bank,
            "period": str(record.period),
            "npl_pct": _number(record.npl_pct),
            "d_npl_pp": _number(record.d_npl_pp),
            "denominator_pp": _number(record.denominator_pp),
            "numerator_pp": _number(record.numerator_pp),
            "loan_growth_qoq_pct": _number(record.loan_growth_qoq_pct),
            "g2_pct": _number(record.g2_pct),
            "d_g2_pp": _number(record.d_g2_pp),
            "writeoff_pct_loans": _number(record.writeoff_pct_loans),
        })
    frame = pd.DataFrame(rows)
    by_quarter = []
    if len(frame):
        frame["quarter"] = frame["period"].str[-1].astype(int)
        for quarter in (1, 2, 3, 4):
            part = frame.loc[frame["quarter"].eq(quarter)]
            if part.empty:
                continue
            writeoffs = part["writeoff_pct_loans"].dropna()
            summary = {
                "quarter": f"Q{quarter}",
                "n": int(len(part)),
                "mean_d_npl_pp": _number(part["d_npl_pp"].mean()),
                "median_d_npl_pp": _number(part["d_npl_pp"].median()),
                "mean_denominator_pp": _number(part["denominator_pp"].mean()),
                "median_denominator_pp": _number(part["denominator_pp"].median()),
                "mean_numerator_pp": _number(part["numerator_pp"].mean()),
                "median_numerator_pp": _number(part["numerator_pp"].median()),
                "mean_loan_growth_qoq_pct": _number(part["loan_growth_qoq_pct"].mean()),
                "median_loan_growth_qoq_pct": _number(part["loan_growth_qoq_pct"].median()),
                "mean_d_g2_pp": _number(part["d_g2_pp"].mean()),
                "median_d_g2_pp": _number(part["d_g2_pp"].median()),
                "mean_g2_pct": _number(part["g2_pct"].mean()),
                "share_falling_pct": _number((part["d_npl_pp"] < 0).mean() * 100),
                "mean_writeoff_pct_loans": _number(writeoffs.mean()) if len(writeoffs) else None,
                "writeoff_n": int(len(writeoffs)),
            }
            summary["reading_vi"] = (
                f"Quý {quarter}: n={summary['n']}, thay đổi NPL trung bình {summary['mean_d_npl_pp']:.4f} điểm, "
                f"trung vị {summary['median_d_npl_pp']:.4f}; phần mẫu số trung bình {summary['mean_denominator_pp']:.4f}, "
                f"phần tử số trung bình {summary['mean_numerator_pp']:.4f}; "
                f"{summary['share_falling_pct']:.1f}% quan sát có NPL giảm."
            )
            summary["reading_en"] = (
                f"Q{quarter}: n={summary['n']}, mean NPL change {summary['mean_d_npl_pp']:.4f} pp, "
                f"median {summary['median_d_npl_pp']:.4f}; mean denominator part {summary['mean_denominator_pp']:.4f}, "
                f"mean numerator part {summary['mean_numerator_pp']:.4f}; "
                f"NPL fell in {summary['share_falling_pct']:.1f}% of observations."
            )
            by_quarter.append(summary)
    focus = [item for item in detail if item["period"] == "2025Q4" and item["bank_code"] in FOCUS]
    focus_bits = ", ".join(
        f"{item['bank_code']} {item['qoq_loan_growth_pct']:.2f}%"
        for item in focus if item["qoq_loan_growth_pct"] is not None
    )
    yoy_bits = []
    for bank in FOCUS:
        end = wide.loc[wide["bank"].eq(bank) & wide["period"].eq("2025Q4"), "total"]
        start = wide.loc[wide["bank"].eq(bank) & wide["period"].eq("2024Q4"), "total"]
        if len(end) and len(start) and start.iloc[0]:
            yoy_bits.append(f"{bank} {(end.iloc[0] / start.iloc[0] - 1) * 100:.1f}%")
    yoy_text = ", ".join(yoy_bits)
    notes_note = _notes_note(notes)
    if quarantine:
        reason_vi = (
            "Các bảng nhóm nợ quý 4/2025 sau lặp một quý trước đó hoặc không cộng về dư nợ khách hàng, nên bị loại: "
            + ", ".join(quarantine) + "."
        )
        reason_en = (
            "These 2025Q4 loan-group tables repeat an earlier quarter or do not add up to customer loans, so they are left out: "
            + ", ".join(quarantine) + "."
        )
    else:
        reason_vi = (
            "TCB, CTG và VBB có dư nợ nhóm nợ quý 4/2025 tăng rất ít"
            + (f" ({focus_bits})" if focus_bits else "")
            + ". Bảng không trùng quý nào trước đó, và tổng năm nhóm khớp dư nợ khách hàng cùng kỳ. "
            + (f"Dư nợ cuối 2025 so với cuối 2024: {yoy_text}. " if yoy_text else "")
            + "Đây không phải bảng lặp hay lệch phạm vi."
        )
        reason_en = (
            "TCB, CTG and VBB show very small 2025Q4 loan-stock growth"
            + (f" ({focus_bits})" if focus_bits else "")
            + ". The group table does not repeat an earlier quarter, and the five groups add up to customer loans. "
            + (f"Loan stock from 2024Q4 to 2025Q4: {yoy_text}. " if yoy_text else "")
            + "This is not a repeated table or a basis mismatch."
        )
    if notes_note:
        reason_vi += " " + notes_note["reading_vi"]
        reason_en += " " + notes_note["reading_en"]
    check = {
        "period": "2025Q4",
        "artefact": bool(quarantine),
        "quarantine": quarantine,
        "banks": focus or [item for item in detail if item["period"] == "2025Q4"],
        "pdf_ctg": notes_note,
        "reading_vi": reason_vi,
        "reading_en": reason_en,
    }
    return {
        "n_pairs": len(rows),
        "banks": int(frame["bank_code"].nunique()) if len(frame) else 0,
        "period": [frame["period"].min(), frame["period"].max()] if len(frame) else None,
        "identity": "denominator_pp + numerator_pp = d_npl_pp",
        "rows": rows,
        "by_quarter": by_quarter,
        "quarantine": [{"bank_code": bank, "period": period} for bank, period in sorted(drop)],
        "q4_2025_check": check,
        "reading_vi": (
            "Thay đổi tỷ lệ nợ xấu được tách thành phần mẫu số, bằng trừ tỷ lệ kỳ trước nhân tăng trưởng dư nợ chia cho một cộng tăng trưởng, "
            "và phần tử số, bằng thay đổi số dư nhóm 3–5 chia dư nợ hiện tại. Hai phần cộng lại đúng bằng thay đổi tỷ lệ. "
            "Mỗi dòng ngân hàng-quý dùng cho biểu đồ nhiệt và thác nước."
        ),
        "reading_en": (
            "The NPL-ratio change splits into a denominator part, minus the previous ratio times loan growth over one plus growth, "
            "and a numerator part, the change in group 3–5 stock divided by current loans. The two parts add up to the change. "
            "Each bank-quarter row feeds the heatmap and the waterfall."
        ),
    }
