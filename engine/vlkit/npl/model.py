"""Silver contract, credit-quality calculations and quarter-on-quarter signals."""

import math

import numpy as np
import pandas as pd

KEY = ["bank_code", "period", "basis"]
BASES = ("consolidated", "separate")
AMOUNTS = ["loans_vnd_bn", "group2_vnd_bn", "npl_vnd_bn", "provision_vnd_bn", "writeoff_vnd_bn"]
SOURCE = ["source_url", "page", "extracted_by", "extracted_at", "raw_sha256"]
SILVER = KEY + AMOUNTS + ["writeoff_basis"] + SOURCE
SIGNAL_COLUMNS = KEY + ["signal", "sentence_vi", "sentence_en"]
THRESHOLDS = ("npl", "g2", "writeoff", "coverage", "formation")
SENTENCES = {
    "S1": ("Tỷ lệ nợ xấu giảm trong khi tỷ lệ nợ nhóm 2 tăng.",
           "The NPL ratio fell while the group 2 loan ratio rose."),
    "S2": ("Tỷ lệ nợ xấu giảm trong khi tỷ lệ xóa nợ tăng.",
           "The NPL ratio fell while the write-off ratio rose."),
    "S3": ("Tỷ lệ nợ xấu giảm trong khi mức bao phủ nợ xấu giảm.",
           "The NPL ratio fell while NPL coverage declined."),
    "S4": ("Tỷ lệ nợ xấu giảm trong khi tỷ lệ phát sinh nợ xấu trước xóa nợ tăng.",
           "The NPL ratio fell while the NPL formation rate before write-offs rose."),
    "S5": ("Tỷ lệ nợ xấu và tỷ lệ nợ nhóm 2 cùng giảm, với tỷ lệ xóa nợ không tăng "
           "và mức bao phủ không giảm đáng kể theo các ngưỡng đã chọn.",
           "The NPL and group 2 ratios fell, with no material rise in the write-off "
           "ratio or decline in coverage under the selected thresholds."),
}


def _validate_silver(silver):
    if missing := set(SILVER) - set(silver):
        raise ValueError(f"missing Silver columns: {', '.join(sorted(missing))}")
    df = silver[SILVER].copy().reset_index(drop=True)
    for field in KEY + ["writeoff_basis"] + SOURCE:
        df[field] = df[field].astype("string").str.strip().replace("", pd.NA)
    if df["bank_code"].isna().any():
        raise ValueError("missing bank_code")
    if not df["period"].str.fullmatch(r"[1-9][0-9]{3}Q[1-4]", na=False).all():
        raise ValueError("invalid or missing period, expected YYYYQn")
    if not df["basis"].isin(BASES).all():
        raise ValueError("invalid or missing reporting basis")
    if df.duplicated(KEY).any():
        raise ValueError("duplicate bank_code, period, basis")
    if (df["writeoff_basis"].notna() & ~df["writeoff_basis"].isin(["quarter", "ytd"])).any():
        raise ValueError("invalid writeoff_basis")
    for field in AMOUNTS:
        raw = df[field].replace(r"^\s*$", np.nan, regex=True)
        values = pd.to_numeric(raw, errors="coerce").astype(float)
        if (raw.notna() & (~np.isfinite(values) | (values < 0))).any():
            raise ValueError(f"invalid non-negative amount in {field}")
        df[field] = values
    # Non-negative amounts make a known component a lower bound when its peer is missing.
    problem = df["npl_vnd_bn"].fillna(0) + df["group2_vnd_bn"].fillna(0)
    too_large = (problem > df["loans_vnd_bn"]) & ~np.isclose(
        problem, df["loans_vnd_bn"], atol=0, rtol=1e-12,
    )
    if too_large.any():
        raise ValueError("loan balance must cover known NPL and group 2 balances")
    return df


def _quarter_writeoffs(series):
    """Convert one sorted bank/basis series. A reported YTD amount re-anchors the total."""
    cumulative = np.nan
    previous = None
    for row in series.itertuples():
        quarter = int(row.period[-1])
        if quarter == 1:
            cumulative = 0.0
        elif previous != row.period[:4] + "Q" + str(quarter - 1):
            cumulative = np.nan
        amount = row.writeoff_vnd_bn
        if pd.isna(row.writeoff_basis):
            yield np.nan
            cumulative = np.nan
        elif row.writeoff_basis == "ytd":
            change = amount - cumulative
            if change < 0 and not math.isclose(amount, cumulative, rel_tol=1e-12):
                raise ValueError(f"falling YTD write-off for {row.bank_code} {row.period} {row.basis}")
            yield max(change, 0.0)
            cumulative = amount
        else:
            yield amount
            cumulative += amount
        previous = row.period


def derive_credit_quality(silver):
    """Return validated observations and derived fractions, preserving missing input cells."""
    df = _validate_silver(silver).sort_values(KEY).reset_index(drop=True)
    missing = df.isna().to_numpy()
    df["missing_fields"] = [[name for name, absent in zip(SILVER, row) if absent] for row in missing]
    series = df.groupby(["bank_code", "basis"], sort=False)
    for _, group in series:
        df.loc[group.index, "writeoff_q_vnd_bn"] = list(_quarter_writeoffs(group))
    if df.empty:
        df["writeoff_q_vnd_bn"] = pd.Series(dtype=float)
    ordinal = df["period"].str[:4].astype(int) * 4 + df["period"].str[-1].astype(int)
    within_quarter = ordinal.groupby([df["bank_code"], df["basis"]]).diff().eq(1)

    def lag(field):
        return series[field].shift().where(within_quarter)

    loans = df["loans_vnd_bn"].replace(0, np.nan)
    npl = df["npl_vnd_bn"]
    group2 = df["group2_vnd_bn"]
    previous_loans = lag("loans_vnd_bn").replace(0, np.nan)
    previous_npl = lag("npl_vnd_bn")
    df["npl_ratio"] = (npl / loans).clip(upper=1)
    df["g2_ratio"] = (group2 / loans).clip(upper=1)
    df["coverage"] = df["provision_vnd_bn"] / npl.replace(0, np.nan)
    df["broad_problem_ratio"] = ((npl + group2) / loans).clip(upper=1)
    df["writeoff_ratio"] = df["writeoff_q_vnd_bn"] / previous_loans
    df["writeoff_ratio_annualised"] = 4 * df["writeoff_ratio"]
    df["npl_formation"] = (npl - previous_npl + df["writeoff_q_vnd_bn"]) / previous_loans
    df["npl_numerator_effect"] = (npl - previous_npl) / previous_loans
    df["npl_loan_growth_effect"] = npl / loans - npl / previous_loans
    df["loan_growth"] = df["loans_vnd_bn"] / previous_loans - 1
    df["lagged_coverage"] = lag("coverage")
    for field in ("npl_ratio", "g2_ratio", "coverage", "writeoff_ratio", "npl_formation"):
        df[f"delta_{field}"] = df[field] - lag(field)
    return df


def calibrate_npl(credit, reference, *, tolerance):
    """Gate supplied FiinQuant fractions keyed by (bank_code, period, basis)."""
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("FiinQuant tolerance must be finite and non-negative")
    actual = credit.set_index(KEY)["npl_ratio"]
    checks = []
    for key, expected in reference.items():
        if not math.isfinite(expected) or not 0 <= expected <= 1:
            raise ValueError(f"FiinQuant reference outside [0, 1] for {key}")
        observed = actual.get(key, np.nan)
        difference = abs(observed - expected)
        if not math.isfinite(difference) or (
            difference > tolerance and not math.isclose(difference, tolerance, rel_tol=1e-12)
        ):
            raise ValueError(f"FiinQuant calibration failed for {key}: observed {observed}, expected {expected}")
        checks.append((*key, observed, expected, difference))
    return pd.DataFrame(checks, columns=KEY + ["npl_ratio", "fiin_npl_ratio", "difference"])


def select_basis(credit, basis):
    if basis not in BASES:
        raise ValueError(f"invalid reporting basis: {basis}")
    return credit.loc[credit["basis"].eq(basis)]


def build_signals(credit, *, basis="consolidated", thresholds=None):
    """Return fired rules for one reporting basis, with metric-specific tolerances."""
    thresholds = {**dict.fromkeys(THRESHOLDS, 0.0), **(thresholds or {})}
    if set(thresholds) != set(THRESHOLDS) or any(
        not math.isfinite(value) or value < 0 for value in thresholds.values()
    ):
        raise ValueError("signal thresholds must be known, finite and non-negative")
    credit = select_basis(credit, basis)
    records = []
    for row in credit.itertuples():
        npl, g2, writeoff, coverage, formation = (
            float(value) if pd.notna(value) else np.nan
            for value in (row.delta_npl_ratio, row.delta_g2_ratio, row.delta_writeoff_ratio,
                          row.delta_coverage, row.delta_npl_formation)
        )
        if not npl < -thresholds["npl"]:
            continue
        rules = {
            "S1": g2 > thresholds["g2"],
            "S2": writeoff > thresholds["writeoff"],
            "S3": coverage < -thresholds["coverage"],
            "S4": formation > thresholds["formation"],
            "S5": (g2 < -thresholds["g2"] and writeoff <= thresholds["writeoff"]
                   and coverage >= -thresholds["coverage"]),
        }
        records.extend((row.bank_code, row.period, basis, rule, *SENTENCES[rule])
                       for rule, fired in rules.items() if fired)
    return pd.DataFrame(records, columns=SIGNAL_COLUMNS)
