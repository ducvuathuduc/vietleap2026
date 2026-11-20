"""Derived metrics shared by the analytical run and the dashboard snapshot."""

import math

import numpy as np
import pandas as pd

from .model import build_signals


OPTIONAL_SIGNAL_DELTAS = ("delta_g2_ratio", "delta_writeoff_ratio", "delta_npl_formation")
SIGNAL_INPUTS = {
    "S1": ("delta_g2_ratio",),
    "S2": ("delta_writeoff_ratio",),
    "S3": ("delta_coverage",),
    "S4": ("delta_npl_formation",),
    "S5": ("delta_g2_ratio", "delta_writeoff_ratio", "delta_coverage"),
}
SIGNAL_LABELS = {
    "delta_g2_ratio": "tỷ lệ nợ nhóm 2 / group 2 loan ratio",
    "delta_writeoff_ratio": "tỷ lệ xóa nợ / write-off ratio",
    "delta_coverage": "tỷ lệ bao phủ / coverage ratio",
    "delta_npl_formation": "tỷ lệ phát sinh nợ xấu / NPL formation rate",
}


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _signals(panel):
    data = panel[["bank_code", "period", "basis"]].copy()
    data["delta_npl_ratio"] = panel["d_npl_pct"] / 100
    data["delta_coverage"] = panel["d_coverage_pct"] / 100
    for field in OPTIONAL_SIGNAL_DELTAS:
        data[field] = panel[field] if field in panel else float("nan")
    fired = build_signals(data).rename(columns={"signal": "id", "sentence_vi": "text_vi", "sentence_en": "text_en"})
    fired = fired[["bank_code", "id", "period", "text_vi", "text_en"]]
    availability = {}
    for rule, inputs in SIGNAL_INPUTS.items():
        eligible = int(data[["delta_npl_ratio", *inputs]].notna().all(axis=1).sum())
        absent = [SIGNAL_LABELS[field] for field in inputs if data[field].notna().sum() == 0]
        availability[rule] = {"eligible": eligible, "missing": absent, "fired": int(fired["id"].eq(rule).sum())}
    return fired, availability


def dashboard_metrics(panel):
    """Summarize consolidated observations without exporting bank-level source series."""
    panel = panel.sort_values(["bank_code", "period"]).copy()
    ordinal = panel.period.str[:4].astype(int) * 4 + panel.period.str[-1].astype(int)
    panel["ordinal"] = ordinal
    panel["quarter"] = panel.period.str[-1].astype(int)
    groups = panel.groupby("bank_code", sort=False)
    consecutive = (ordinal - groups["ordinal"].shift(3)).eq(3)
    average_4q = groups["npl_pct"].transform(lambda values: values.rolling(4, min_periods=4).mean())
    latest_period = panel["period"].max()

    by_period = panel.groupby("period").agg(
        npl_median_pct=("npl_pct", "median"),
        npl_p25_pct=("npl_pct", lambda values: values.quantile(.25)),
        npl_p75_pct=("npl_pct", lambda values: values.quantile(.75)),
        coverage_median_pct=("coverage_pct", "median"),
        n_banks=("npl_pct", "count"),
    )
    signal_rows, availability = _signals(panel)
    banks = {}
    for bank, rows in groups:
        delta = rows["d_npl_pct"]
        q4 = rows["quarter"].eq(4)
        next_delta = delta.shift(-1)
        pairs = q4 & rows["ordinal"].shift(-1).sub(rows["ordinal"]).eq(1) & delta.notna() & next_delta.notna()
        reversible = pairs & delta.lt(0) & next_delta.gt(0)
        available = rows.loc[rows["npl_pct"].notna()]
        latest = (available if not available.empty else rows).iloc[-1]
        signals = signal_rows.loc[signal_rows["bank_code"].eq(bank)].drop(columns="bank_code")
        banks[bank] = {
            "q4_change_median_pp": delta.loc[q4].dropna().median(),
            "q1_rebound_median_pp": delta.loc[rows["quarter"].eq(1)].dropna().median(),
            "down_then_up_years": int(reversible.sum()),
            "years": int(pairs.sum()),
            "latest": {"period": latest["period"], "adjusted_change_pp": latest["adjusted_d_npl_pct"]},
            "signals": signals.to_dict("records"),
        }
    return {
        "median_by_period": by_period.reset_index().to_dict("records"),
        "npl_4q_avg_median_pct": average_4q.loc[consecutive & panel.period.eq(latest_period)].dropna().median(),
        "banks": banks,
        "signal_availability": availability,
    }
