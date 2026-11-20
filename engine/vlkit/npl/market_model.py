"""NPL bands, a valuation kink, and a walk-forward price comparison.

Association only. A quarter's ratios are usable from the first trading session
strictly after the filing deadline in report_calendar.csv (the disclosure_deadline
column, not the quarter-end-plus-30-day anchor used elsewhere).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .real_data import clean_quarters
from .real_models import BOOTSTRAP_SEED, _wild_pvalues

TRAIN_START = "2021-02"
TEST_START = "2025-01"
KINK_GRID = np.round(np.linspace(1.0, 3.5, 26), 1)
KINK_REPS = 499
PB_WINDOW = 20
MIN_PB_DAYS = 10
FOOTER = "Nguồn: FiinQuant (FiinGroup); tính toán của nhóm"
BAND_TERMS = ("b1_2", "b2_3", "ge3")
BAND_LABELS = {
    "lt1": ("Dưới 1%", "Under 1%"),
    "b1_2": ("1–2%", "1–2%"),
    "b2_3": ("2–3%", "2–3%"),
    "ge3": ("Từ 3% trở lên", "3% and above"),
}
CAVEAT = {
    "vi": "Đây là liên hệ thống kê trong mẫu đã quan sát. Hệ số không chứng minh nợ xấu làm giá thay đổi, và không tách con số nợ xấu khỏi những thông tin khác trong cùng kỳ báo cáo.",
    "en": "This is a statistical association in the observed sample. The coefficients do not establish that NPL moves prices, and they do not separate the NPL figure from the other information in the same report.",
}


def npl_band(npl_pct):
    """Map an NPL percent to a band. 2.0 belongs to 2–3; 3.0 belongs to >=3."""
    if npl_pct is None or not np.isfinite(npl_pct):
        return None
    if npl_pct < 1.0:
        return "lt1"
    if npl_pct < 2.0:
        return "b1_2"
    if npl_pct < 3.0:
        return "b2_3"
    return "ge3"


def publication_dates(calendar, sessions):
    """First trading session strictly after each filing deadline."""
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).normalize().unique().sort_values()
    deadlines = pd.to_datetime(calendar["deadline"]).dt.normalize().to_numpy(dtype="datetime64[ns]")
    positions = sessions.searchsorted(deadlines, side="right")
    first = np.full(len(deadlines), np.datetime64("NaT"), dtype="datetime64[ns]")
    valid = positions < len(sessions)
    first[valid] = sessions.to_numpy(dtype="datetime64[ns]")[positions[valid]]
    return pd.DataFrame({
        "period": calendar["period"].astype(str).str.strip().str.upper().to_numpy(),
        "deadline": deadlines,
        "first_public_date": first,
    })


def asof_rows(panel, public, asof):
    """Latest published quarter for each bank. Quarters public later than asof are excluded."""
    asof = pd.Timestamp(asof).normalize()
    live = public.loc[
        public["first_public_date"].notna() & public["first_public_date"].le(asof),
        ["period", "first_public_date"],
    ]
    merged = panel.merge(live, on="period", how="inner")
    if merged.empty:
        return merged
    return merged.sort_values(["bank_code", "period"]).groupby("bank_code", as_index=False).tail(1)


def monthly_asof_features(panel, public, asof_dates):
    """Cross-bank NPL features using only quarters already public on each date."""
    rows = []
    for asof in asof_dates:
        current = asof_rows(panel, public, asof)
        npl = current["npl_pct"].dropna() if "npl_pct" in current.columns else pd.Series(dtype=float)
        record = {
            "asof": pd.Timestamp(asof).normalize(),
            "median_npl": float(npl.median()) if len(npl) else np.nan,
            "share_ge3": float(npl.ge(3).mean()) if len(npl) else np.nan,
            "max_period": None if current.empty else str(current["period"].max()),
            "n_banks": int(len(npl)),
        }
        if "npl_lag" in current.columns:
            change = (current["npl_pct"] - current["npl_lag"]).dropna()
            record["median_npl_change"] = float(change.median()) if len(change) else np.nan
        if "coverage_lag" in current.columns:
            coverage = current["coverage_lag"].dropna()
            record["median_coverage_lag"] = float(coverage.median()) if len(coverage) else np.nan
        if "loan_growth" in current.columns:
            growth = current["loan_growth"].dropna()
            record["median_loan_growth"] = float(growth.median()) if len(growth) else np.nan
        rows.append(record)
    return pd.DataFrame(rows)


def walk_forward_splits(months, *, train_start=TRAIN_START, test_start=TEST_START):
    """Expanding window. Training months are strictly earlier than the scored month."""
    ordered = sorted({str(month) for month in months})
    for month in ordered:
        if month < test_start:
            continue
        train = [item for item in ordered if train_start <= item < month]
        yield month, train


def walk_forward_predictions(frame, feature_columns, *, train_start=TRAIN_START, test_start=TEST_START):
    """OLS forecast of ret. Each fit uses only rows whose month is before the scored month."""
    work = frame.copy()
    work["month"] = work["month"].astype(str)
    rows = []
    for month, train_months in walk_forward_splits(work["month"], train_start=train_start, test_start=test_start):
        columns = ["month", "ret", *feature_columns]
        train = work.loc[work["month"].isin(train_months), columns].dropna()
        test = work.loc[work["month"].eq(month), columns].dropna()
        predicted = np.nan
        if len(train) > len(feature_columns) + 1 and len(test) == 1:
            train_x = np.column_stack([np.ones(len(train)), train[list(feature_columns)].to_numpy(dtype=float)])
            test_x = np.column_stack([np.ones(1), test[list(feature_columns)].to_numpy(dtype=float)])
            beta, *_ = np.linalg.lstsq(train_x, train["ret"].to_numpy(dtype=float), rcond=None)
            predicted = float((test_x @ beta)[0])
        rows.append({
            "month": month,
            "train_max": None if train.empty else str(train["month"].max()),
            "train_n": int(len(train)),
            "predicted": predicted,
        })
    return pd.DataFrame(rows)


def _band_dummies(npl_pct):
    band = npl_pct.map(npl_band)
    frame = pd.DataFrame({term: band.eq(term).astype(float) for term in BAND_TERMS}, index=npl_pct.index)
    frame.loc[band.isna(), :] = np.nan
    return frame


def _previous_period(period):
    year, quarter = int(period[:4]), int(period[-1])
    return f"{year - 1}Q4" if quarter == 1 else f"{year}Q{quarter - 1}"


def _next_period(period):
    year, quarter = int(period[:4]), int(period[-1])
    return f"{year + 1}Q1" if quarter == 4 else f"{year}Q{quarter + 1}"


def _filing_calendar(raw):
    period_column = "period" if "period" in raw.columns else "quarter"
    deadline_column = "disclosure_deadline" if "disclosure_deadline" in raw.columns else "deadline"
    calendar = pd.DataFrame({
        "period": raw[period_column].astype(str).str.strip().str.upper(),
        "deadline": pd.to_datetime(raw[deadline_column]),
    })
    return calendar.dropna().drop_duplicates("period")


def _prepare_market(prices, valuation):
    prices = prices.copy()
    prices["bank_code"] = prices["ticker"].astype(str).str.strip().str.upper().replace({"BIDV": "BID"})
    prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices = prices.loc[prices["close"].gt(0), ["bank_code", "date", "close"]]
    prices = prices.drop_duplicates(["bank_code", "date"], keep="last")
    valuation = valuation.copy()
    valuation["bank_code"] = valuation["ticker"].astype(str).str.strip().str.upper().replace({"BIDV": "BID"})
    valuation["date"] = pd.to_datetime(valuation["date"]).dt.normalize()
    valuation["pb"] = pd.to_numeric(valuation["pb"], errors="coerce")
    valuation = valuation.loc[:, ["bank_code", "date", "pb"]].drop_duplicates(["bank_code", "date"], keep="last")
    sessions = pd.DatetimeIndex(
        prices.loc[prices["bank_code"].eq("VNINDEX"), "date"].drop_duplicates().sort_values()
    )
    if sessions.empty:
        raise ValueError("Không có phiên VNINDEX với giá đóng cửa dương")
    return prices, valuation, sessions


def _valuation_outcome(panel, public, prices, valuation, sessions):
    session_values = pd.DatetimeIndex(sessions)
    indexed = public.dropna(subset=["first_public_date"]).copy()
    start = session_values.searchsorted(pd.DatetimeIndex(indexed["first_public_date"]), side="left")
    window_rows = []
    for period, position in zip(indexed["period"], start):
        days = session_values[position:position + PB_WINDOW]
        for day in days:
            window_rows.append((period, pd.Timestamp(day)))
    window = pd.DataFrame(window_rows, columns=["period", "date"])
    book = panel[["bank_code", "period", "bvps"]].drop_duplicates(["bank_code", "period"])
    long = book.merge(window, on="period", how="inner")
    long = long.merge(valuation, on=["bank_code", "date"], how="left")
    long = long.merge(prices, on=["bank_code", "date"], how="left")
    long["ratio"] = long["pb"].where(long["pb"].gt(0))
    fallback = long["ratio"].isna() & long["close"].gt(0) & long["bvps"].gt(0)
    long.loc[fallback, "ratio"] = long.loc[fallback, "close"] / long.loc[fallback, "bvps"]
    long["source"] = np.where(long["pb"].gt(0), "valuation_daily", np.where(fallback, "bvps", None))
    long = long.loc[long["ratio"].gt(0)].copy()
    long["log_ratio"] = np.log(long["ratio"].to_numpy(dtype=float))
    grouped = long.groupby(["bank_code", "period"], sort=False)
    summary = grouped.agg(
        mean_pb=("ratio", "mean"),
        mean_log_pb=("log_ratio", "mean"),
        n_days=("ratio", "size"),
        n_valuation=("source", lambda values: int((values == "valuation_daily").sum())),
        n_fallback=("source", lambda values: int((values == "bvps").sum())),
    ).reset_index()
    summary = summary.loc[summary["n_days"].ge(MIN_PB_DAYS)].copy()
    return summary


def _base_matrix(controls, periods):
    levels, inverse = np.unique(periods, return_inverse=True)
    fe_count = max(len(levels) - 1, 0)
    fe = np.zeros((len(periods), fe_count))
    for column, level in enumerate(range(1, len(levels))):
        fe[:, column] = inverse == level
    constant = np.ones((len(periods), 1))
    if controls.size == 0:
        return np.hstack([constant, fe]) if fe_count else constant
    return np.hstack([constant, controls, fe])


def _ssr_grid(y, controls, npl, periods, grid):
    base = _base_matrix(controls, periods)
    npl_column = npl.reshape(-1, 1)
    values = np.empty(len(grid))
    for index, kink_point in enumerate(grid):
        kink = np.maximum(npl - kink_point, 0.0).reshape(-1, 1)
        design = np.hstack([base, npl_column, kink])
        beta, residual, rank, _ = np.linalg.lstsq(design, y, rcond=None)
        if residual.size == 1 and rank == design.shape[1]:
            values[index] = residual[0]
        else:
            error = y - design @ beta
            values[index] = float(error @ error)
    return values


def _fit_terms(data, outcome, terms, *, quarter=True, bank=False, bootstrap=True):
    sample = data.dropna(subset=[outcome, *terms, "bank_code"]).copy()
    if quarter:
        sample = sample.dropna(subset=["period"])
    sample = sample.reset_index(drop=True)
    used, omitted = [], []
    for term in terms:
        if sample[term].nunique(dropna=True) >= 2:
            used.append(term)
        else:
            omitted.append(term)
    result = {
        "n": int(len(sample)),
        "clusters": int(sample["bank_code"].nunique()) if len(sample) else 0,
        "period": [str(sample["period"].min()), str(sample["period"].max())] if len(sample) and "period" in sample else None,
        "terms": {},
        "omitted_terms": omitted,
        "inference": "bank-clustered SE, t intervals; wild cluster bootstrap-t p uses Rademacher weights",
        "bootstrap_reps": 999 if bootstrap else 0,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    if result["clusters"] < 2 or not used:
        result["unavailable_reason"] = "insufficient_sample"
        return result, None, sample
    pieces = [pd.Series(1.0, index=sample.index, name="constant"), sample[used].astype(float)]
    if quarter:
        pieces.append(pd.get_dummies(sample["period"], prefix="period", drop_first=True, dtype=float))
    if bank:
        pieces.append(pd.get_dummies(sample["bank_code"], prefix="bank", drop_first=True, dtype=float))
    design = pd.concat(pieces, axis=1)
    y = sample[outcome].astype(float)
    matrix = design.to_numpy(dtype=float)
    if len(sample) <= matrix.shape[1] or np.linalg.matrix_rank(matrix) != matrix.shape[1]:
        result["unavailable_reason"] = "collinearity"
        return result, None, sample
    model = sm.OLS(y, design).fit(
        cov_type="cluster", cov_kwds={"groups": sample["bank_code"]}, use_t=True,
    )
    intervals = model.conf_int()
    wild = {}
    if bootstrap:
        groups = pd.get_dummies(sample["bank_code"], dtype=float).to_numpy()
        wild = _wild_pvalues(
            matrix, y.to_numpy(dtype=float), groups, np.linalg.pinv(matrix),
            [design.columns.get_loc(term) for term in used], model.tvalues.to_numpy(dtype=float),
        )
    for term in used:
        location = design.columns.get_loc(term)
        standard_error = float(model.bse[term])
        valid = bool(np.isfinite(standard_error) and standard_error > 1e-12)
        coefficient = float(model.params[term])
        result["terms"][term] = {
            "coefficient": coefficient,
            "se": standard_error if valid else None,
            "ci95": [float(value) for value in intervals.loc[term].tolist()] if valid else None,
            "p": float(model.pvalues[term]) if valid else None,
            "wild_p": wild.get(location) if bootstrap else None,
            "n": result["n"],
            "clusters": result["clusters"],
            "period": result["period"],
            "proportional_pb_gap": float(np.exp(coefficient) - 1.0) if term in BAND_TERMS else None,
        }
    return result, model, sample


def _linear_combo(model, expression, *, n, clusters, period):
    tested = model.t_test(expression)
    effect = float(np.squeeze(tested.effect))
    se = float(np.squeeze(tested.sd))
    interval = np.squeeze(tested.conf_int(0.05))
    return {
        "coefficient": effect,
        "se": se,
        "ci95": [float(interval[0]), float(interval[1])],
        "p": float(np.squeeze(tested.pvalue)),
        "n": n,
        "clusters": clusters,
        "period": period,
        "unit": "log(P/B) per NPL percentage point",
    }


def _threshold(sample, controls):
    y = sample["mean_log_pb"].to_numpy(dtype=float)
    npl = sample["npl_pct"].to_numpy(dtype=float)
    control_matrix = sample[list(controls)].to_numpy(dtype=float) if controls else np.zeros((len(sample), 0))
    periods = sample["period"].astype(str).to_numpy()
    banks = sample["bank_code"].astype(str).to_numpy()
    ssrs = _ssr_grid(y, control_matrix, npl, periods, KINK_GRID)
    best = int(np.argmin(ssrs))
    kink = float(KINK_GRID[best])
    unique, inverse = np.unique(banks, return_inverse=True)
    groups = [np.flatnonzero(inverse == index) for index in range(len(unique))]
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    chosen = []
    for _ in range(KINK_REPS):
        draw = rng.integers(0, len(groups), size=len(groups))
        idx = np.concatenate([groups[item] for item in draw])
        if len(idx) <= control_matrix.shape[1] + 4:
            continue
        draw_ssr = _ssr_grid(y[idx], control_matrix[idx], npl[idx], periods[idx], KINK_GRID)
        chosen.append(float(KINK_GRID[int(np.argmin(draw_ssr))]))
    chosen = np.asarray(chosen, dtype=float)
    ci = [float(value) for value in np.quantile(chosen, [0.025, 0.975])] if len(chosen) else None
    fitted = sample.copy()
    fitted["kink"] = np.maximum(fitted["npl_pct"] - kink, 0.0)
    result, model, _used = _fit_terms(
        fitted, "mean_log_pb", [*controls, "npl_pct", "kink"], quarter=True, bank=False, bootstrap=True,
    )
    slopes = {}
    if model is not None and "npl_pct" in result["terms"] and "kink" in result["terms"]:
        slopes["below"] = {**result["terms"]["npl_pct"], "unit": "log(P/B) per NPL percentage point"}
        slopes["change"] = {**result["terms"]["kink"], "unit": "change in the log(P/B) slope at k"}
        slopes["above"] = _linear_combo(
            model, "npl_pct + kink", n=result["n"], clusters=result["clusters"], period=result["period"],
        )
    return {
        "k": kink,
        "ci95": ci,
        "bootstrap_reps_requested": KINK_REPS,
        "bootstrap_reps_used": int(len(chosen)),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "share_of_draws_at_k": float(np.mean(np.isclose(chosen, kink))) if len(chosen) else None,
        "n": result["n"],
        "clusters": result["clusters"],
        "period": result["period"],
        "controls": list(controls),
        "fixed_effects": "quarter",
        "ssr": float(ssrs[best]),
        "grid": [{"k": float(point), "ssr": float(value)} for point, value in zip(KINK_GRID, ssrs)],
        "slopes": slopes,
        "unavailable_reason": result.get("unavailable_reason"),
    }


def _complete_month_ends(sessions):
    frame = pd.DataFrame({"date": pd.DatetimeIndex(sessions)})
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    ends = frame.groupby("month", sort=True)["date"].max()
    last = pd.Timestamp(sessions.max()).normalize()
    kept = []
    for month, date in ends.items():
        period = pd.Period(month, freq="M")
        if period.to_timestamp(how="end").normalize() <= last and str(month) >= "2021-01":
            kept.append((str(month), pd.Timestamp(date)))
    return pd.DataFrame(kept, columns=["month", "date"])


def _basket_index(prices, sessions):
    banks = prices.loc[~prices["bank_code"].isin(["VNINDEX", "VN30"])]
    wide = banks.pivot(index="date", columns="bank_code", values="close").reindex(sessions)
    log_price = np.log(wide.where(wide.gt(0)))
    daily = log_price.diff().mean(axis=1, skipna=True).fillna(0.0)
    daily.iloc[0] = 0.0
    index = 100.0 * np.exp(daily.cumsum())
    anchor_month = index.index.to_series().dt.to_period("M").astype(str)
    anchor = index.loc[anchor_month.eq("2020-12")]
    if len(anchor):
        index = index / float(anchor.iloc[-1]) * 100.0
    return index


def _month_frame(panel, public, prices, sessions):
    ends = _complete_month_ends(sessions)
    index = _basket_index(prices, sessions)
    vnindex = prices.loc[prices["bank_code"].eq("VNINDEX")].set_index("date")["close"]
    ends["basket_price"] = index.reindex(pd.DatetimeIndex(ends["date"])).to_numpy()
    ends["vnindex_price"] = vnindex.reindex(pd.DatetimeIndex(ends["date"])).to_numpy()
    ends["basket_ret"] = np.log(ends["basket_price"]).diff()
    ends["vnindex_ret"] = np.log(ends["vnindex_price"]).diff()
    features = monthly_asof_features(panel, public, ends["date"])
    features["feature_month"] = ends["month"].to_numpy()
    target = ends.copy()
    previous = {target["month"].iloc[i]: target["month"].iloc[i - 1] for i in range(1, len(target))}
    target["feature_month"] = target["month"].map(previous)
    merged = target.merge(features, on="feature_month", how="left", suffixes=("", "_feature"))
    lag = ends[["month", "basket_ret", "vnindex_ret"]].rename(columns={
        "month": "feature_month",
        "basket_ret": "basket_lag_ret",
        "vnindex_ret": "vnindex_lag_ret",
    })
    return merged.merge(lag, on="feature_month", how="left")


def _diebold_mariano(model_error, benchmark_error):
    gap = np.asarray(model_error, dtype=float) - np.asarray(benchmark_error, dtype=float)
    gap = gap[np.isfinite(gap)]
    n = int(len(gap))
    result = {
        "n": n,
        "loss": "squared error of the monthly log return",
        "hac": "Newey-West Bartlett",
        "mean_loss_diff": None,
        "hac_lags": None,
        "stat": None,
        "p": None,
        "df": None,
    }
    if n < 3:
        return result
    center = float(gap.mean())
    lags = max(1, int(np.floor(n ** (1.0 / 3.0))))
    demeaned = gap - center
    hac = float(np.dot(demeaned, demeaned) / n)
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1.0)
        gamma = float(np.dot(demeaned[lag:], demeaned[:-lag]) / n)
        hac += 2.0 * weight * gamma
    se = np.sqrt(max(hac, 0.0) / n)
    result.update({
        "mean_loss_diff": center,
        "hac_lags": lags,
        "df": n - 1,
        "reading_vi": "mean_loss_diff âm nghĩa là mô hình có bình phương sai số nhỏ hơn mốc so sánh.",
        "reading_en": "A negative mean_loss_diff means the model has a smaller squared error than the benchmark.",
    })
    if se > 1e-15:
        stat = center / se
        from scipy import stats
        result["stat"] = float(stat)
        result["p"] = float(2.0 * stats.t.sf(abs(stat), n - 1))
    return result


def _errors(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    gap = actual - predicted
    valid = np.isfinite(gap)
    return gap[valid]


def _mae(actual, predicted):
    gap = _errors(actual, predicted)
    return None if len(gap) == 0 else float(np.mean(np.abs(gap)))


def _rmse(actual, predicted):
    gap = _errors(actual, predicted)
    return None if len(gap) == 0 else float(np.sqrt(np.mean(gap ** 2)))


def _hit_rate(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    valid = np.isfinite(actual) & np.isfinite(predicted) & (actual != 0) & (predicted != 0)
    if not valid.any():
        return {"rate": None, "n": 0}
    return {"rate": float(np.mean(np.sign(actual[valid]) == np.sign(predicted[valid]))), "n": int(valid.sum())}


def _score_target(frame, ret_column, price_column, lag_column):
    features = ["median_npl", "median_npl_change", "share_ge3", "median_coverage_lag", "median_loan_growth", "lag_ret"]
    controls = ["median_coverage_lag", "median_loan_growth", "lag_ret"]
    work = frame[[
        "month", price_column, ret_column, "median_npl", "median_npl_change", "share_ge3",
        "median_coverage_lag", "median_loan_growth", lag_column,
    ]].rename(columns={ret_column: "ret", lag_column: "lag_ret"})
    work = work.sort_values("month").dropna(subset=["ret", *features])
    scored = work.loc[work["month"].ge(TEST_START)].copy()
    npl_fit = walk_forward_predictions(work, features).rename(columns={"predicted": "predicted_npl"})
    no_fit = walk_forward_predictions(work, controls).rename(columns={"predicted": "predicted_no_npl"})
    ar_fit = walk_forward_predictions(work, ["lag_ret"]).rename(columns={"predicted": "predicted_ar1"})
    means = []
    for month, train_months in walk_forward_splits(work["month"]):
        train = work.loc[work["month"].isin(train_months), "ret"]
        means.append({"month": month, "predicted_mean": float(train.mean()) if len(train) else np.nan, "train_n_mean": int(len(train))})
    mean_fit = pd.DataFrame(means)
    out = scored.merge(npl_fit, on="month", how="left")
    out = out.merge(no_fit[["month", "predicted_no_npl"]], on="month", how="left")
    out = out.merge(ar_fit[["month", "predicted_ar1"]], on="month", how="left")
    out = out.merge(mean_fit, on="month", how="left")
    out["predicted_rw"] = 0.0
    previous_price = frame[["month", price_column]].sort_values("month").rename(columns={price_column: "previous_price"})
    previous_price["month"] = previous_price["month"].shift(-1)
    out = out.merge(previous_price.dropna(), on="month", how="left")
    for name, column in (
        ("predicted_price_npl", "predicted_npl"),
        ("predicted_price_no_npl", "predicted_no_npl"),
        ("predicted_price_ar1", "predicted_ar1"),
        ("predicted_price_mean", "predicted_mean"),
        ("predicted_price_rw", "predicted_rw"),
    ):
        out[name] = out["previous_price"] * np.exp(out[column])
    actual_ret = out["ret"]
    actual_price = out[price_column]
    metrics = {
        "n": int(out["predicted_npl"].notna().sum()),
        "period": [str(out["month"].min()), str(out["month"].max())] if len(out) else None,
        "mae_return": {
            "npl_model": _mae(actual_ret, out["predicted_npl"]),
            "without_npl": _mae(actual_ret, out["predicted_no_npl"]),
            "random_walk": _mae(actual_ret, out["predicted_rw"]),
            "historical_mean": _mae(actual_ret, out["predicted_mean"]),
            "ar1": _mae(actual_ret, out["predicted_ar1"]),
        },
        "rmse_return": {
            "npl_model": _rmse(actual_ret, out["predicted_npl"]),
            "without_npl": _rmse(actual_ret, out["predicted_no_npl"]),
            "random_walk": _rmse(actual_ret, out["predicted_rw"]),
            "historical_mean": _rmse(actual_ret, out["predicted_mean"]),
            "ar1": _rmse(actual_ret, out["predicted_ar1"]),
        },
        "mae_price": {
            "npl_model": _mae(actual_price, out["predicted_price_npl"]),
            "without_npl": _mae(actual_price, out["predicted_price_no_npl"]),
            "random_walk": _mae(actual_price, out["predicted_price_rw"]),
            "historical_mean": _mae(actual_price, out["predicted_price_mean"]),
            "ar1": _mae(actual_price, out["predicted_price_ar1"]),
        },
        "rmse_price": {
            "npl_model": _rmse(actual_price, out["predicted_price_npl"]),
            "without_npl": _rmse(actual_price, out["predicted_price_no_npl"]),
            "random_walk": _rmse(actual_price, out["predicted_price_rw"]),
            "historical_mean": _rmse(actual_price, out["predicted_price_mean"]),
            "ar1": _rmse(actual_price, out["predicted_price_ar1"]),
        },
        "direction_hit_rate": {
            "npl_model": _hit_rate(actual_ret, out["predicted_npl"]),
            "without_npl": _hit_rate(actual_ret, out["predicted_no_npl"]),
            "ar1": _hit_rate(actual_ret, out["predicted_ar1"]),
            "historical_mean": _hit_rate(actual_ret, out["predicted_mean"]),
            "random_walk": {"rate": None, "n": 0, "note": "The random walk predicts a zero return, so it makes no direction call."},
        },
        "diebold_mariano_vs_random_walk": _diebold_mariano(
            (actual_ret - out["predicted_npl"]) ** 2, (actual_ret - out["predicted_rw"]) ** 2,
        ),
        "diebold_mariano_vs_without_npl": _diebold_mariano(
            (actual_ret - out["predicted_npl"]) ** 2, (actual_ret - out["predicted_no_npl"]) ** 2,
        ),
    }
    npl_mae = metrics["mae_return"]["npl_model"]
    rw_mae = metrics["mae_return"]["random_walk"]
    metrics["npl_mae_below_random_walk"] = None if npl_mae is None or rw_mae is None else bool(npl_mae < rw_mae)
    metrics["timing"] = {
        "vi": "Lợi suất tháng m chạy từ phiên cuối tháng m−1 đến phiên cuối tháng m. NPL, tỷ lệ bao phủ trễ và tăng trưởng tín dụng lấy tại phiên cuối tháng m−1, chỉ từ quý đã công bố. Hệ số của tháng m ước lượng trên các tháng có mục tiêu sớm hơn m.",
        "en": "The month-m return runs from the previous month-end session to the month-m end session. NPL, lagged coverage and loan growth are measured on the previous month-end session and use only quarters already public. Coefficients for month m are fit on earlier target months only.",
    }
    return metrics, out


def _fmt(value, digits=4):
    if value is None or not np.isfinite(value):
        return "n/a"
    if value != 0 and abs(value) < 10 ** (-digits):
        return f"{value:.6f}"
    return f"{value:.{digits}f}"


def _pfmt(value):
    if value is None or not np.isfinite(value):
        return "không có"
    return f"{value:.4f}"


def _band_reading(result, *, english=False):
    if result.get("unavailable_reason"):
        return ("Không ước lượng được phép hồi quy này." if not english else "This regression could not be estimated.")
    names = {
        "b1_2": ("1–2%", "1–2%"),
        "b2_3": ("2–3%", "2–3%"),
        "ge3": ("từ 3% trở lên", "3% and above"),
        "coverage_lag": ("tỷ lệ bao phủ quý trước", "prior-quarter coverage"),
        "loan_growth": ("tăng trưởng tín dụng", "loan growth"),
    }
    sentences = [
        f"n={result['n']}, {result['clusters']} ngân hàng, {result['period'][0]}–{result['period'][1]}."
        if not english else
        f"n={result['n']}, {result['clusters']} banks, {result['period'][0]}–{result['period'][1]}."
    ]
    for term, (vi_name, en_name) in names.items():
        item = result["terms"].get(term)
        if not item or item.get("ci95") is None:
            continue
        low, high = item["ci95"]
        crosses = low < 0 < high
        wild = item.get("wild_p")
        disagrees = (not crosses) and wild is not None and wild > 0.1
        if english:
            sentences.append(
                f"{en_name}: coefficient {_fmt(item['coefficient'])}, 95% CI {_fmt(low)} to {_fmt(high)}, "
                f"cluster p {_pfmt(item['p'])}, wild p {_pfmt(wild)}."
                + (" The interval includes zero." if crosses else "")
                + (" The cluster interval excludes zero, while the wild p does not." if disagrees else "")
            )
        else:
            sentences.append(
                f"{vi_name}: hệ số {_fmt(item['coefficient'])}, KTC 95% {_fmt(low)} đến {_fmt(high)}, "
                f"p cụm {_pfmt(item['p'])}, p wild {_pfmt(wild)}."
                + (" Khoảng tin cậy cắt 0." if crosses else "")
                + (" Khoảng cụm không cắt 0, nhưng p wild không tách khỏi 0." if disagrees else "")
            )
    return " ".join(sentences)


def _threshold_reading(threshold, *, english=False):
    low, high = (None, None) if not threshold.get("ci95") else threshold["ci95"]
    below = threshold["slopes"].get("below", {})
    change = threshold["slopes"].get("change", {})
    above = threshold["slopes"].get("above", {})
    edge = ""
    if high is not None and high >= 3.5 - 1e-9:
        edge = (
            " The upper end sits on the 3.5 edge of the search grid, so the sample does not isolate one threshold."
            if english else
            " Đầu trên chạm mép 3,5 của lưới tìm kiếm, nên mẫu không khoanh được một ngưỡng."
        )
    if english:
        return (
            f"The residual sum of squares is smallest at k={_fmt(threshold['k'], 1)}% "
            f"(bank-cluster bootstrap 95% interval {_fmt(low, 1)} to {_fmt(high, 1)}, "
            f"{threshold['bootstrap_reps_used']} of {threshold['bootstrap_reps_requested']} draws, seed {threshold['bootstrap_seed']})."
            f"{edge} "
            f"These slopes hold lagged coverage and loan growth fixed. "
            f"Slope of log(P/B) per NPL point below k: {_fmt(below.get('coefficient'))} "
            f"(95% CI {_fmt((below.get('ci95') or [None, None])[0])} to {_fmt((below.get('ci95') or [None, None])[1])}, "
            f"cluster p {_pfmt(below.get('p'))}, wild p {_pfmt(below.get('wild_p'))}). "
            f"Slope above k: {_fmt(above.get('coefficient'))} "
            f"(95% CI {_fmt((above.get('ci95') or [None, None])[0])} to {_fmt((above.get('ci95') or [None, None])[1])}, "
            f"cluster p {_pfmt(above.get('p'))}). "
            f"Slope change: {_fmt(change.get('coefficient'))}, cluster p {_pfmt(change.get('p'))}, wild p {_pfmt(change.get('wild_p'))}. "
            f"n={threshold['n']}, {threshold['clusters']} banks."
        )
    return (
        f"Tổng bình phương phần dư nhỏ nhất tại k={_fmt(threshold['k'], 1)}% "
        f"(khoảng bootstrap cụm ngân hàng 95%: {_fmt(low, 1)} đến {_fmt(high, 1)}, "
        f"{threshold['bootstrap_reps_used']}/{threshold['bootstrap_reps_requested']} lần rút, seed {threshold['bootstrap_seed']})."
        f"{edge} "
        f"Các độ dốc này giữ cố định tỷ lệ bao phủ quý trước và tăng trưởng tín dụng. "
        f"Độ dốc log(P/B) theo mỗi điểm phần trăm NPL dưới k: {_fmt(below.get('coefficient'))} "
        f"(KTC 95% {_fmt((below.get('ci95') or [None, None])[0])} đến {_fmt((below.get('ci95') or [None, None])[1])}, "
        f"p cụm {_pfmt(below.get('p'))}, p wild {_pfmt(below.get('wild_p'))}). "
        f"Độ dốc trên k: {_fmt(above.get('coefficient'))} "
        f"(KTC 95% {_fmt((above.get('ci95') or [None, None])[0])} đến {_fmt((above.get('ci95') or [None, None])[1])}, "
        f"p cụm {_pfmt(above.get('p'))}). "
        f"Mức đổi độ dốc: {_fmt(change.get('coefficient'))}, p cụm {_pfmt(change.get('p'))}, p wild {_pfmt(change.get('wild_p'))}. "
        f"n={threshold['n']}, {threshold['clusters']} ngân hàng."
    )


def _forecast_reading(metrics, *, english=False):
    mae = metrics["mae_return"]
    price = metrics["mae_price"]
    dm = metrics["diebold_mariano_vs_random_walk"]
    dm_npl = metrics["diebold_mariano_vs_without_npl"]
    better = metrics["npl_mae_below_random_walk"]
    if english:
        lead = (
            "The NPL model has a lower return MAE than the random walk. "
            if better else
            "The NPL model does not have a lower return MAE than the random walk. "
        )
        return lead + (
            f"Return MAE: NPL model {_fmt(mae['npl_model'])}, without NPL {_fmt(mae['without_npl'])}, "
            f"random walk {_fmt(mae['random_walk'])}, historical mean {_fmt(mae['historical_mean'])}, AR(1) {_fmt(mae['ar1'])}. "
            f"One-step price MAE: NPL model {_fmt(price['npl_model'], 2)}, random walk {_fmt(price['random_walk'], 2)}. "
            f"n={metrics['n']}, {metrics['period'][0]}–{metrics['period'][1]}. "
            f"Diebold-Mariano versus the random walk: stat {_fmt(dm['stat'])}, p {_pfmt(dm['p'])}, "
            f"mean squared-error gap {_fmt(dm['mean_loss_diff'])}. "
            f"Diebold-Mariano versus the model without NPL: p {_pfmt(dm_npl['p'])}."
        )
    lead = (
        "Mô hình có NPL có MAE lợi suất thấp hơn bước ngẫu nhiên. "
        if better else
        "Mô hình có NPL không có MAE lợi suất thấp hơn bước ngẫu nhiên. "
    )
    return lead + (
        f"MAE lợi suất: mô hình NPL {_fmt(mae['npl_model'])}, không NPL {_fmt(mae['without_npl'])}, "
        f"bước ngẫu nhiên {_fmt(mae['random_walk'])}, trung bình lịch sử {_fmt(mae['historical_mean'])}, AR(1) {_fmt(mae['ar1'])}. "
        f"MAE giá một bước: mô hình NPL {_fmt(price['npl_model'], 2)}, bước ngẫu nhiên {_fmt(price['random_walk'], 2)}. "
        f"n={metrics['n']}, {metrics['period'][0]}–{metrics['period'][1]}. "
        f"Diebold-Mariano so với bước ngẫu nhiên: thống kê {_fmt(dm['stat'])}, p {_pfmt(dm['p'])}, "
        f"chênh bình phương sai số {_fmt(dm['mean_loss_diff'])}. "
        f"Diebold-Mariano so với mô hình không NPL: p {_pfmt(dm_npl['p'])}."
    )


def _attach_readings(spec, *, quarter_only):
    label = "spec i, quarter fixed effects" if quarter_only else "spec ii, bank and quarter fixed effects"
    spec["name"] = label
    spec["fixed_effects"] = "quarter" if quarter_only else "bank and quarter"
    spec["reference_band"] = "lt1"
    spec["reading_vi"] = ("So sánh giữa ngân hàng trong cùng quý. " if quarter_only else "So sánh trong cùng ngân hàng qua các quý. ") + _band_reading(spec)
    spec["reading_en"] = ("Cross-bank comparison within a quarter. " if quarter_only else "Within-bank comparison across quarters. ") + _band_reading(spec, english=True)
    spec["what_this_does_not_show"] = CAVEAT
    return spec


def _band_table(sample):
    rows = []
    for band in ("lt1", "b1_2", "b2_3", "ge3"):
        part = sample.loc[sample["band"].eq(band)]
        returns = part["next_quarter_return"].dropna()
        rows.append({
            "band": band,
            "label_vi": BAND_LABELS[band][0],
            "label_en": BAND_LABELS[band][1],
            "n": int(len(part)),
            "median_pb": None if part.empty else float(part["mean_pb"].median()),
            "median_next_quarter_return": None if returns.empty else float(returns.median()),
            "next_quarter_n": int(len(returns)),
            "return_definition": "simple return from the bank close on this quarter's first public session to the close on the next quarter's first public session",
        })
    return rows


def ceiling_note(legal):
    """Cite a 3% phrase in the register prose. Percent-encoded URLs are not a citation."""
    pattern = r"(?<!\d)3\s*(?:%|phần\s*trăm)"
    if legal is None or legal.empty:
        hits = legal
    else:
        prose = legal.drop(columns=[column for column in legal.columns if str(column).lower() in {"url", "source_url"}], errors="ignore")
        decoded = prose.astype(str).replace(r"%[0-9A-Fa-f]{2}", " ", regex=True)
        mask = decoded.apply(lambda row: row.str.contains(pattern, case=False, regex=True).any(), axis=1)
        hits = legal.loc[mask]
    if hits is None or hits.empty:
        return {
            "cited": False,
            "rows": [],
            "reading_vi": "legal_register.csv không có dòng nào ghi trần nợ xấu 3%. Mốc 3% chỉ là ngưỡng chia nhóm được giao, không phải trích dẫn từ sổ này.",
            "reading_en": "legal_register.csv has no row stating a 3% NPL ceiling. The 3% cut is the requested band edge, not a citation from this register.",
        }
    rows = hits[["ref", "title"]].astype(str).to_dict("records") if {"ref", "title"}.issubset(hits.columns) else []
    return {
        "cited": True,
        "rows": rows,
        "reading_vi": "Sổ văn bản có dòng nhắc 3%. Xem rows để trích đúng văn bản, không suy ra trần nếu dòng đó nói việc khác.",
        "reading_en": "The register has a row mentioning 3%. Use the listed rows; do not treat the mention as a ceiling unless that row says so.",
    }


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if value is pd.NaT:
        return None
    return value


def _style(fig):
    fig.patch.set_facecolor("white")
    for axis in fig.axes:
        axis.set_facecolor("white")
        axis.grid(True, color="#e6e6e6", linewidth=0.8)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    fig.text(0.01, 0.012, FOOTER, fontsize=10, color="#333333")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.set_size_inches(16, 9)


def _save(fig, path):
    fig.savefig(path, dpi=100, facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)


def _charts(out, history, basket, vnindex, spec_i, spec_ii, threshold):
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False

    def price_chart(scored, price_column, predicted_column, title, path, rebase_note):
        fig, axis = plt.subplots()
        actual = history[["month", price_column]].dropna()
        actual_dates = pd.to_datetime(actual["month"])
        axis.plot(actual_dates, actual[price_column], color="#1f4e79", linewidth=2.0, label="Giá thực tế")
        test = scored.dropna(subset=[predicted_column])
        test_dates = pd.to_datetime(test["month"])
        axis.plot(test_dates, test[predicted_column], color="#c47b2b", linewidth=2.0, linestyle="--", label="Giá mô hình một bước")
        if len(test_dates):
            axis.axvspan(test_dates.min(), test_dates.max(), color="#f4e2c8", alpha=0.45, label="Giai đoạn kiểm định", zorder=0)
        mae_model = _mae(scored[price_column], scored[predicted_column])
        mae_rw = _mae(scored[price_column], scored["predicted_price_rw"])
        axis.set_title(title, loc="left", fontsize=16)
        axis.set_xlabel("Tháng")
        axis.set_ylabel("Mức giá")
        axis.legend(frameon=False)
        fig.suptitle(
            f"MAE giá một bước: mô hình {_fmt(mae_model, 2)} so với bước ngẫu nhiên {_fmt(mae_rw, 2)}. {rebase_note}",
            x=0.125, ha="left", fontsize=11, color="#333333",
        )
        _style(fig)
        _save(fig, path)

    price_chart(
        basket, "basket_price", "predicted_price_npl",
        "Rổ ngân hàng: giá thực tế và giá mô hình dự báo",
        out / "chart_basket.png",
        "Chỉ số rổ bằng 100 vào phiên cuối tháng 12/2020.",
    )
    price_chart(
        vnindex, "vnindex_price", "predicted_price_npl",
        "VNINDEX: giá thực tế và giá mô hình dự báo",
        out / "chart_vnindex.png",
        "Mức giá là chỉ số đóng cửa.",
    )

    fig, axis = plt.subplots()
    labels = ["1–2%", "2–3%", "Từ 3%"]
    for offset, spec, color, name in (
        (-0.12, spec_i, "#1f4e79", "Cùng quý, khác ngân hàng"),
        (0.12, spec_ii, "#c47b2b", "Cùng ngân hàng qua thời gian"),
    ):
        centers, lows, highs = [], [], []
        for term in BAND_TERMS:
            item = spec["terms"].get(term) or {}
            interval = item.get("ci95") or [np.nan, np.nan]
            centers.append(item.get("coefficient", np.nan))
            lows.append(interval[0])
            highs.append(interval[1])
        x = np.arange(len(labels)) + offset
        y = np.asarray(centers, dtype=float)
        yerr = np.vstack([y - np.asarray(lows, dtype=float), np.asarray(highs, dtype=float) - y])
        axis.errorbar(x, y, yerr=yerr, fmt="o", color=color, capsize=4, label=name, markersize=7)
    axis.axhline(0, color="#666666", linewidth=1)
    axis.set_xticks(np.arange(len(labels)), labels)
    axis.set_title("Chênh log(P/B) so với nhóm nợ xấu dưới 1%", loc="left", fontsize=16)
    axis.set_ylabel("Hệ số log(P/B), KTC 95% cụm ngân hàng")
    crosses = []
    for spec in (spec_i, spec_ii):
        for term in BAND_TERMS:
            interval = (spec["terms"].get(term) or {}).get("ci95")
            if interval:
                crosses.append(interval[0] < 0 < interval[1])
    subtitle = "Đã kiểm soát tỷ lệ bao phủ quý trước và tăng trưởng tín dụng."
    if crosses and all(crosses):
        subtitle += " Khoảng tin cậy 95% của từng nhóm ở cả hai phép đều cắt 0."
    fig.suptitle(subtitle, x=0.125, ha="left", fontsize=11, color="#333333")
    axis.set_xlabel("Nhóm nợ xấu. Nhóm dưới 1% là mốc, nên không có hệ số riêng.")
    axis.legend(frameon=False)
    _style(fig)
    _save(fig, out / "chart_bands.png")

    fig, axis = plt.subplots()
    grid = pd.DataFrame(threshold["grid"])
    axis.plot(grid["k"], grid["ssr"], color="#1f4e79", linewidth=2.0)
    axis.axvline(threshold["k"], color="#c47b2b", linewidth=1.5, label=f"k = {threshold['k']:.1f}%")
    if threshold.get("ci95"):
        axis.axvspan(threshold["ci95"][0], threshold["ci95"][1], color="#f4e2c8", alpha=0.5, label="KTC bootstrap 95% của k")
    axis.set_title("Tổng bình phương phần dư theo ngưỡng nợ xấu", loc="left", fontsize=16)
    axis.set_xlabel("Ngưỡng k (% nợ xấu)")
    axis.set_ylabel("SSR")
    axis.legend(frameon=False)
    _style(fig)
    _save(fig, out / "chart_threshold.png")


def _published_series(history, scored, price_column, ret_column):
    base = history[["month", price_column, ret_column]].rename(columns={
        price_column: "actual_price", ret_column: "actual_log_return",
    })
    predicted = scored[["month", "predicted_npl", "predicted_price_npl"]].rename(columns={
        "predicted_npl": "predicted_log_return", "predicted_price_npl": "predicted_price",
    })
    merged = base.merge(predicted, on="month", how="left")
    merged = merged.loc[merged["month"].ge("2021-01")]
    rows = []
    for record in merged.itertuples(index=False):
        rows.append({
            "month": str(record.month),
            "actual_price": None if pd.isna(record.actual_price) else float(record.actual_price),
            "actual_log_return": None if pd.isna(record.actual_log_return) else float(record.actual_log_return),
            "predicted_log_return": None if pd.isna(record.predicted_log_return) else float(record.predicted_log_return),
            "predicted_price": None if pd.isna(record.predicted_price) else float(record.predicted_price),
            "in_test": bool(str(record.month) >= TEST_START and pd.notna(record.predicted_log_return)),
        })
    return rows


def _series_csv(frame, ret_column, price_column, path):
    columns = {
        "month": "month",
        ret_column: "actual_log_return",
        price_column: "actual_price",
        "predicted_npl": "predicted_log_return",
        "predicted_no_npl": "predicted_log_return_no_npl",
        "predicted_ar1": "predicted_log_return_ar1",
        "predicted_mean": "predicted_log_return_historical_mean",
        "predicted_rw": "predicted_log_return_random_walk",
        "predicted_price_npl": "predicted_price",
        "predicted_price_no_npl": "predicted_price_no_npl",
        "predicted_price_rw": "predicted_price_random_walk",
        "previous_price": "previous_actual_price",
        "train_n": "train_n",
        "train_max": "train_max",
    }
    out = frame.rename(columns=columns)
    keep = [name for name in columns.values() if name in out.columns]
    out[keep].to_csv(path, index=False)


def run(silver, out=None):
    silver = Path(silver)
    import duckdb
    with duckdb.connect() as db:
        raw = db.read_parquet(str(silver / "bank_quarter.parquet")).df()
        price_raw = db.read_parquet(str(silver / "price_daily.parquet")).df()
        valuation_raw = db.read_parquet(str(silver / "valuation_daily.parquet")).df()
    calendar_raw = pd.read_csv(silver / "report_calendar.csv")
    legal_path = silver / "legal_register.csv"
    legal = pd.read_csv(legal_path) if legal_path.is_file() else pd.DataFrame()

    quarters, _clean_log = clean_quarters(raw)
    extra = raw[["ticker", "period"]].copy()
    extra["ticker"] = extra["ticker"].astype(str).str.strip().str.upper().replace({"BIDV": "BID"})
    extra["period"] = extra["period"].astype(str).str.strip().str.upper()
    roe = pd.to_numeric(raw["roe"], errors="coerce") if "roe" in raw.columns else pd.Series(np.nan, index=raw.index)
    extra["roe"] = roe.to_numpy()
    book = raw["valuation_ratios_book_value_per_share"] if "valuation_ratios_book_value_per_share" in raw.columns else np.nan
    extra["bvps"] = pd.to_numeric(book, errors="coerce")
    panel = quarters.merge(extra, on=["ticker", "period"], how="left")
    panel["period"] = panel["period"].astype(str)
    roe_non_null = int(panel["roe"].notna().sum())
    controls = ["coverage_lag", "loan_growth"]
    if roe_non_null:
        controls = ["roe", *controls]

    lag_source = panel[["bank_code", "period", "coverage_pct", "npl_pct"]].rename(columns={
        "period": "prev_period", "coverage_pct": "coverage_lag", "npl_pct": "npl_lag",
    })
    panel["prev_period"] = panel["period"].map(_previous_period)
    panel = panel.merge(lag_source, on=["bank_code", "prev_period"], how="left")
    panel["loan_growth"] = panel["loan_growth_yoy_pct"]
    panel = pd.concat([panel, _band_dummies(panel["npl_pct"])], axis=1)
    panel["band"] = panel["npl_pct"].map(npl_band)

    prices, valuation, sessions = _prepare_market(price_raw, valuation_raw)
    public = publication_dates(_filing_calendar(calendar_raw), sessions)
    outcome = _valuation_outcome(panel, public, prices, valuation, sessions)
    panel = panel.merge(outcome, on=["bank_code", "period"], how="left")
    public_dates = public.set_index("period")["first_public_date"]
    panel["first_public"] = panel["period"].map(public_dates)
    panel["next_public"] = panel["period"].map(_next_period).map(public_dates)
    closes = prices.rename(columns={"date": "first_public", "close": "close_0"})
    panel = panel.merge(closes, on=["bank_code", "first_public"], how="left")
    next_closes = prices.rename(columns={"date": "next_public", "close": "close_1"})
    panel = panel.merge(next_closes, on=["bank_code", "next_public"], how="left")
    panel["next_quarter_return"] = panel["close_1"] / panel["close_0"] - 1.0
    panel.loc[~panel["close_0"].gt(0) | ~panel["close_1"].gt(0), "next_quarter_return"] = np.nan

    valued = panel.dropna(subset=["mean_log_pb", "npl_pct"]).copy()
    regression = valued.dropna(subset=controls).copy()
    spec_i, _, _sample = _fit_terms(regression, "mean_log_pb", [*BAND_TERMS, *controls], quarter=True, bank=False)
    spec_ii, _, _sample = _fit_terms(regression, "mean_log_pb", [*BAND_TERMS, *controls], quarter=True, bank=True)
    bands_only, _, _sample = _fit_terms(regression, "mean_log_pb", list(BAND_TERMS), quarter=True, bank=False)
    spec_i = _attach_readings(spec_i, quarter_only=True)
    spec_ii = _attach_readings(spec_ii, quarter_only=False)
    bands_only = _attach_readings(bands_only, quarter_only=True)
    bands_only["name"] = "quarter fixed effects, band dummies only, same rows as spec i"
    bands_only["controls"] = []
    bands_only["reading_vi"] = (
        "Cùng các dòng với phép có biến kiểm soát, chỉ nhóm nợ xấu và hiệu ứng quý. "
        + _band_reading(bands_only)
        + " Phép này cho thấy chênh P/B thô trong quý. Phép spec i thêm tỷ lệ bao phủ và tăng trưởng tín dụng."
    )
    bands_only["reading_en"] = (
        "Same rows as the controlled fit, with band dummies and quarter effects only. "
        + _band_reading(bands_only, english=True)
        + " This is the within-quarter P/B gap. Spec i then adds lagged coverage and loan growth."
    )
    spec_i["controls"] = controls
    spec_ii["controls"] = controls
    compared = []
    for term in BAND_TERMS:
        controlled = (spec_i["terms"].get(term) or {}).get("coefficient")
        raw = (bands_only["terms"].get(term) or {}).get("coefficient")
        if controlled is not None and raw is not None:
            compared.append(controlled * raw < 0)
    if compared and all(compared):
        spec_i["reading_vi"] += " Dấu hệ số của cả ba nhóm đổi so với phép không kiểm soát trên cùng các dòng."
        spec_i["reading_en"] += " All three band coefficients change sign relative to the no-control fit on the same rows."
    if regression["bank_code"].nunique() < 2:
        threshold = {
            "k": None, "ci95": None, "bootstrap_reps_requested": KINK_REPS, "bootstrap_reps_used": 0,
            "bootstrap_seed": BOOTSTRAP_SEED, "share_of_draws_at_k": None, "n": int(len(regression)),
            "clusters": int(regression["bank_code"].nunique()) if len(regression) else 0, "period": None,
            "controls": list(controls), "fixed_effects": "quarter", "ssr": None, "grid": [], "slopes": {},
            "unavailable_reason": "fewer_than_two_banks",
        }
    else:
        threshold = _threshold(regression, controls)
    threshold["reading_vi"] = _threshold_reading(threshold)
    threshold["reading_en"] = _threshold_reading(threshold, english=True)
    threshold["what_this_does_not_show"] = {
        **CAVEAT,
        "vi": CAVEAT["vi"] + " Ngưỡng k là điểm gãy được chọn trên lưới 1,0–3,5 theo SSR, không phải một ngưỡng chính sách được kiểm định trước.",
        "en": CAVEAT["en"] + " k is the break chosen on the 1.0–3.5 grid by the residual sum of squares, not a pre-registered policy threshold.",
    }

    history = _month_frame(
        panel[["bank_code", "period", "npl_pct", "npl_lag", "coverage_lag", "loan_growth"]],
        public, prices, sessions,
    )
    basket_metrics, basket = _score_target(history, "basket_ret", "basket_price", "basket_lag_ret")
    vnindex_metrics, vnindex = _score_target(history, "vnindex_ret", "vnindex_price", "vnindex_lag_ret")
    for metrics in (basket_metrics, vnindex_metrics):
        metrics["reading_vi"] = _forecast_reading(metrics)
        metrics["reading_en"] = _forecast_reading(metrics, english=True)
        metrics["what_this_does_not_show"] = {
            **CAVEAT,
            "vi": CAVEAT["vi"] + " " + metrics["timing"]["vi"] + " Dự báo một bước dùng giá thực của tháng trước, không phải một đường giá tích lũy từ mô hình.",
            "en": CAVEAT["en"] + " " + metrics["timing"]["en"] + " The one-step price uses the previous actual price, not a path compounded from model prices.",
        }
    basket_metrics["series"] = _published_series(history, basket, "basket_price", "basket_ret")
    vnindex_metrics["series"] = _published_series(history, vnindex, "vnindex_price", "vnindex_ret")

    table = _band_table(valued)
    table_bits = ", ".join(
        f"{row['label_vi']} trung vị P/B {_fmt(row['median_pb'], 2)} (n={row['n']}, lợi suất quý sau {_fmt(row['median_next_quarter_return'], 4)}, n lợi suất={row['next_quarter_n']})"
        for row in table
    )
    table_reading = {
        "reading_vi": "Trung vị P/B và lợi suất quý sau, chưa cố định quý và chưa kiểm soát tỷ lệ bao phủ: " + table_bits + ".",
        "reading_en": "Median P/B and next-quarter return, with no quarter effect and no coverage control. "
        + ", ".join(
            f"{row['label_en']} median P/B {_fmt(row['median_pb'], 2)} (n={row['n']}, next-quarter return {_fmt(row['median_next_quarter_return'], 4)}, return n={row['next_quarter_n']})"
            for row in table
        ) + ".",
        "what_this_does_not_show": CAVEAT,
        "sample": "rows with a 20-session P/B, including quarters that lack lagged coverage",
    }
    pb_rows = int(len(valued))
    results = {
        "association_only": True,
        "as_of": {
            "deadline_column": "report_calendar.disclosure_deadline",
            "rule_vi": "Một quý chỉ được dùng từ phiên giao dịch VNINDEX đầu tiên sau hạn công bố trong report_calendar.csv. Hạn cộng 30 ngày kể từ cuối quý không được dùng ở đây.",
            "rule_en": "A quarter is usable from the first VNINDEX session strictly after its disclosure_deadline in report_calendar.csv. The quarter-end-plus-30-day anchor is not used here.",
            "valuation_window_vi": f"log(P/B) là trung bình log tỷ lệ của tối đa {PB_WINDOW} phiên bắt đầu từ phiên công bố, và chỉ giữ quan sát có ít nhất {MIN_PB_DAYS} phiên.",
            "valuation_window_en": f"log(P/B) is the mean of log ratios over up to {PB_WINDOW} sessions starting on the publication session, keeping rows with at least {MIN_PB_DAYS} sessions.",
        },
        "pb_source": {
            "primary": "valuation_daily.pb",
            "fallback": "close / valuation_ratios_book_value_per_share",
            "rows": pb_rows,
            "rows_valuation_daily_only": int((valued["n_fallback"].eq(0) & valued["n_valuation"].gt(0)).sum()),
            "rows_with_any_fallback": int(valued["n_fallback"].gt(0).sum()),
            "rows_fallback_only": int((valued["n_valuation"].eq(0) & valued["n_fallback"].gt(0)).sum()),
            "reading_vi": "P/B lấy từ valuation_daily. Ngày không có P/B dương thì dùng giá đóng cửa chia giá trị sổ sách mỗi cổ phiếu của quý đó.",
            "reading_en": "P/B comes from valuation_daily. A day without a positive P/B uses the close divided by that quarter's book value per share.",
        },
        "roe_control": {
            "included": bool(roe_non_null),
            "non_null": roe_non_null,
            "reading_vi": "Cột roe có số, nên ROE nằm trong biến kiểm soát." if roe_non_null else
            "Cột roe trong bank_quarter.parquet không có giá trị nào, nên phép hồi quy không kiểm soát ROE. Không thay ROE bằng NIM.",
            "reading_en": "The roe column has values, so ROE is included as a control." if roe_non_null else
            "The roe column in bank_quarter.parquet is entirely empty, so the valuation regression does not control for ROE. NIM is not used as a substitute.",
        },
        "ceiling_3pct": ceiling_note(legal),
        "band_regression": {"spec_i": spec_i, "spec_ii": spec_ii, "quarter_fe_bands_only": bands_only},
        "threshold": threshold,
        "band_table": table,
        "band_table_reading": table_reading,
        "forecast": {
            "train_start": TRAIN_START,
            "test_start": TEST_START,
            "refit_vi": "Mỗi tháng kiểm định được ước lượng lại trên mọi tháng mục tiêu sớm hơn tháng đó, từ 2021-02. Tháng đang chấm và các tháng sau không vào mẫu huấn luyện.",
            "refit_en": "Each test month is refit on every earlier target month from 2021-02. The scored month and every later month stay out of that fit.",
            "basket": basket_metrics,
            "vnindex": vnindex_metrics,
        },
    }
    payload = _jsonable(results)
    if out is None:
        return payload
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if threshold.get("grid"):
        _charts(out, history, basket, vnindex, spec_i, spec_ii, threshold)
    _series_csv(basket, "ret", "basket_price", out / "basket_monthly.csv")
    _series_csv(vnindex, "ret", "vnindex_price", out / "vnindex_monthly.csv")
    pd.DataFrame(table).to_csv(out / "band_table.csv", index=False)
    (out / "results_m8.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description="Liên hệ nợ xấu với P/B và giá chỉ số, ngoài mẫu theo tháng")
    parser.add_argument("--silver", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    run(args.silver, args.out)


if __name__ == "__main__":
    main()
