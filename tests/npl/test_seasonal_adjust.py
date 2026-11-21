"""Vintage-specific seasonal factors and contiguous changes."""

import numpy as np
import pandas as pd
import pytest

from vlkit.npl.seasonal_adjust import seasonal_adjustment


def _history():
    periods = pd.period_range("2020Q1", "2026Q3", freq="Q")
    rows = []
    for bank, amp in [("A", .4), ("B", .2)]:
        seasonal = {1: amp, 2: 0., 3: 0., 4: -amp}
        for index, period in enumerate(periods):
            rows.append({"bank_code": bank, "period": str(period),
                         "npl_pct": 2. + index * .02 + seasonal[period.quarter]})
    return pd.DataFrame(rows)


def test_each_vintage_uses_only_prior_periods_and_its_own_bank():
    panel = _history()
    first = seasonal_adjustment(panel)
    changed = panel.loc[panel.period.le("2025Q4")].copy()
    changed.loc[changed.period.ge("2025Q4") & changed.bank_code.eq("A"), "npl_pct"] += 10
    later_panel = seasonal_adjustment(changed)
    left = pd.DataFrame(first["series"]).set_index(["bank_code", "period"])
    right = pd.DataFrame(later_panel["series"]).set_index(["bank_code", "period"])
    pd.testing.assert_frame_equal(left.loc[right.index].loc[lambda x: x.index.get_level_values("period") < "2025Q4"],
                                  right.loc[lambda x: x.index.get_level_values("period") < "2025Q4"])
    assert left.loc[("A", "2025Q4"), "seasonal_effect_pp"] == right.loc[("A", "2025Q4"), "seasonal_effect_pp"]
    assert left.loc[("A", "2025Q4"), "adjusted_change_pp"] == pytest.approx(.02)
    assert left.loc[("A", "2025Q4"), "trend_slope_pp_per_quarter"] == pytest.approx(.02)
    assert not np.isclose(left.loc[("A", "2025Q4"), "seasonal_effect_pp"],
                          left.loc[("B", "2025Q4"), "seasonal_effect_pp"])


def test_q4_counts_keep_unadjustable_falls_and_omit_changes_across_gaps():
    panel = _history()
    panel = panel.loc[~(panel.bank_code.eq("A") & panel.period.eq("2025Q3"))]
    result = seasonal_adjustment(panel)
    declines = {(row["bank_code"], row["period"]): row for row in result["q4_declines"]}
    assert declines["A", "2020Q4"]["seasonal_only"] is None
    assert ("A", "2025Q4") not in declines
    assert declines["B", "2025Q4"]["seasonal_only"] is True
    assert result["counts"]["seasonal_only"] == result["counts"]["adjustable"]
    assert len(result["latest"]) == 2
