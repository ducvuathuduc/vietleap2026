"""Bank-specific seasonal factors estimated from the information available at each quarter."""

import numpy as np
import pandas as pd


def _bank_vintages(bank, rows):
    periods = pd.PeriodIndex(rows.period, freq="Q")
    time = periods.asi8 - periods.asi8[0]
    quarters = periods.quarter.to_numpy() - 1
    npl = rows.npl_pct.to_numpy(dtype=float)
    known = np.isfinite(npl)
    design = np.column_stack((np.ones(len(rows)), time, np.eye(4)[quarters, 1:]))
    for index, period in enumerate(periods):
        value = float(npl[index]) if known[index] else None
        consecutive = index > 0 and time[index] - time[index - 1] == 1
        reported = value - float(npl[index - 1]) if value is not None and consecutive and known[index - 1] else None
        row = {
            "bank_code": bank, "period": str(period), "reported_npl_pct": value, "reported_change_pp": reported,
            "adjusted_npl_pct": None, "adjusted_change_pp": None, "seasonal_effect_pp": None,
            "trend_npl_pct": None, "trend_slope_pp_per_quarter": None, "fit_through": None, "train_n": 0,
        }
        history = np.flatnonzero(known[:index])
        if np.bincount(quarters[history], minlength=4).min() < 2:
            yield row
            continue
        x = design[history]
        beta, _, rank, _ = np.linalg.lstsq(x, npl[history], rcond=None)
        if rank < design.shape[1]:
            yield row
            continue
        uncentered = np.r_[0., beta[2:]]
        mean_effect = uncentered.mean()
        effects = uncentered - mean_effect
        current_effect = effects[quarters[index]]
        change = None if reported is None else float(reported - current_effect + effects[quarters[index - 1]])
        if change is not None and abs(change) < 1e-12:
            change = 0.
        yield {
            **row,
            "adjusted_npl_pct": None if value is None else float(value - current_effect),
            "adjusted_change_pp": change,
            "seasonal_effect_pp": float(current_effect),
            "trend_npl_pct": float(beta[0] + beta[1] * time[index] + mean_effect),
            "trend_slope_pp_per_quarter": float(beta[1]),
            "fit_through": str(periods[history[-1]]),
            "train_n": len(history),
        }


def seasonal_adjustment(panel):
    """Build an expanding-vintage adjustment and same-vintage comparisons of quarter changes."""
    series = []
    latest = []
    for bank, group in panel.sort_values(["bank_code", "period"]).groupby("bank_code", sort=False):
        bank_rows = list(_bank_vintages(bank, group))
        series.extend(bank_rows)
        latest.append(bank_rows[-1])
    declines = []
    for row in series:
        reported, adjusted = row["reported_change_pp"], row["adjusted_change_pp"]
        if row["period"].endswith("Q4") and reported is not None and reported < 0:
            declines.append({
                "bank_code": row["bank_code"], "period": row["period"],
                "reported_change_pp": reported, "adjusted_change_pp": adjusted,
                "seasonal_only": None if adjusted is None else adjusted >= 0,
            })
    adjustable = sum(row["adjusted_change_pp"] is not None for row in declines)
    count = sum(row["seasonal_only"] is True for row in declines)
    return {
        "series": series,
        "q4_declines": declines,
        "latest": latest,
        "counts": {"reported": len(declines), "adjustable": adjustable, "seasonal_only": count,
                   "seasonal_only_pct": 100 * count / adjustable if adjustable else None},
        "minimum_observations_per_quarter": 2,
        "reading_vi": (
            f"Trong {len(declines)} lần tỷ lệ nợ xấu giảm vào Quý 4, điều chỉnh được {adjustable} lần "
            f"và {count} lần không còn giảm sau điều chỉnh. Mỗi ngân hàng có xu hướng tuyến tính và hiệu ứng quý riêng, "
            "ước lượng từ các quý trước. Khi so mức thay đổi, dùng cùng một bộ hiệu ứng cho cả hai quý."
        ),
        "reading_en": (
            f"Of {len(declines)} reported Q4 declines, {adjustable} can be adjusted and {count} no longer fall after adjustment. "
            "Each bank has its own linear trend and quarter effects fitted on earlier quarters. "
            "Both endpoints of a change use the same vintage of effects."
        ),
        "what_this_does_not_show": {
            "vi": "Việc mức giảm biến mất sau điều chỉnh mô tả kết quả theo mô hình. Chất lượng khoản vay cần thêm bằng chứng.",
            "en": "A decline that disappears after adjustment is a model comparison. Credit quality still requires other evidence.",
        },
    }
