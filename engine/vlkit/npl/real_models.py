"""Panel inference, deadline event study and out-of-sample NPL predictions."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from .real_data import RATIOS


BOOTSTRAP_REPS = 999
BOOTSTRAP_SEED = 20261120
QUARTER_TERMS = ["Q2", "Q3", "Q4"]


def _design(panel, terms, *, bank=False, year=False):
    x = panel[terms].astype(float).copy()
    x.insert(0, "constant", 1.0)
    for enabled, name in [(bank, "bank_code"), (year, "year")]:
        if enabled:
            effects = pd.get_dummies(panel[name], prefix=name, drop_first=True, dtype=float)
            x = x.join(effects)
    return x


def _wild_pvalues(x, y, groups, inverse, term_indices, observed):
    """Restricted wild cluster bootstrap-t for each coefficient's zero null."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    weights = rng.choice([-1., 1.], size=(groups.shape[1], BOOTSTRAP_REPS))
    n, k = x.shape
    g = groups.shape[1]
    correction = (g / (g - 1)) * ((n - 1) / (n - k))
    result = {}
    for idx in term_indices:
        # With the tested column removed, residuals come from the restricted null.
        restricted = np.delete(x, idx, axis=1)
        null_fitted = restricted @ (np.linalg.pinv(restricted) @ y)
        draws = null_fitted[:, None] + (y - null_fitted)[:, None] * (groups @ weights)
        coefficients = inverse @ draws
        residuals = draws - x @ coefficients
        scores = groups.T @ (inverse[idx, :, None] * residuals)
        standard_error = np.sqrt(correction * np.square(scores).sum(axis=0))
        t_draws = np.divide(coefficients[idx], standard_error,
                            out=np.full(BOOTSTRAP_REPS, np.nan), where=standard_error > 1e-12)
        valid = np.isfinite(t_draws)
        if valid.any() and np.isfinite(observed[idx]):
            absolute = np.abs(t_draws[valid])
            target = abs(observed[idx])
            # Equal-sign draws reproduce the observed statistic up to floating-point error.
            extreme = (absolute >= target) | np.isclose(absolute, target, rtol=1e-10, atol=1e-12)
            result[idx] = (1 + int(extreme.sum())) / (1 + int(valid.sum()))
    return result


def _fit(panel, outcome, terms, *, bank=False, year=False, bootstrap=False):
    data = panel.dropna(subset=[outcome, *terms])
    n = len(data)
    g = data["bank_code"].nunique()
    result = {"n": n, "clusters": g, "terms": {}}
    if n and "period" in data:
        result["period"] = [data.period.min(), data.period.max()]
    predictions = pd.Series(np.nan, index=panel.index, dtype=float)
    if g < 2:
        result["unavailable_reason"] = "no_observations" if n == 0 else "fewer_than_two_banks"
        return result, predictions
    x = _design(data, terms, bank=bank, year=year)
    if n <= x.shape[1] or np.linalg.matrix_rank(x.to_numpy()) != x.shape[1]:
        result["unavailable_reason"] = "insufficient_degrees_of_freedom_or_collinearity"
        return result, predictions
    model = sm.OLS(data[outcome], x).fit(cov_type="cluster",
                                         cov_kwds={"groups": data["bank_code"]}, use_t=True)
    intervals = model.conf_int()
    valid = np.isfinite(model.bse) & model.bse.gt(1e-12)
    wild = {}
    if bootstrap:
        wild = _wild_pvalues(
            x.to_numpy(), data[outcome].to_numpy(dtype=float),
            pd.get_dummies(data["bank_code"], dtype=float).to_numpy(),
            np.linalg.pinv(x.to_numpy()), [x.columns.get_loc(term) for term in terms],
            model.tvalues.to_numpy(),
        )
    for term in terms:
        result["terms"][term] = {
            "coefficient": float(model.params[term]),
            "se": float(model.bse[term]) if valid[term] else None,
            "ci95": intervals.loc[term].tolist() if valid[term] else None,
            "p": float(model.pvalues[term]) if valid[term] else None,
        }
        if bootstrap:
            result["terms"][term]["wild_p"] = wild.get(x.columns.get_loc(term))
    predictions.loc[data.index] = model.fittedvalues
    return result, predictions


def _quarters(panel):
    return panel.assign(**{term: panel["quarter"].eq(int(term[1])) for term in QUARTER_TERMS})


def descriptives(panel):
    metrics = ["npl_pct", "coverage_pct", "ldr_pct", "roa_pct"]
    result = {}
    for column in ["period", "bank_code", "ownership"]:
        summary = panel.groupby(column)[metrics].agg(["count", "median", "mean"])
        summary.columns = [f"{metric}_{statistic}" for metric, statistic in summary]
        result[f"by_{column}"] = summary.reset_index().to_dict("records")
    return result


def seasonal_models(panel):
    data = _quarters(panel)
    baseline, fitted = _fit(data, "d_npl_pct", QUARTER_TERMS, bank=True, bootstrap=True)
    model_year, _ = _fit(data, "d_npl_pct", QUARTER_TERMS, bank=True, year=True, bootstrap=True)
    recent, _ = _fit(data.loc[data.year.ge(2023)], "d_npl_pct", QUARTER_TERMS, bank=True, bootstrap=True)
    omission = []
    for bank in sorted(data.loc[data["d_npl_pct"].notna(), "bank_code"].unique()):
        result, _ = _fit(data.loc[data.bank_code.ne(bank)], "d_npl_pct", QUARTER_TERMS, bank=True)
        if "Q4" in result["terms"]:
            omission.append({"omitted_bank": bank, **result["terms"]["Q4"], "n": result["n"]})
    groups = {ownership: _fit(group, "d_npl_pct", QUARTER_TERMS, bank=True, bootstrap=True)[0]
              for ownership, group in data.groupby("ownership")}
    sample = data.dropna(subset=["d_npl_pct"])
    x = _design(sample, QUARTER_TERMS, bank=True)
    median = {"n": len(sample), "terms": {}, "inference": "asymptotic, observation-robust; not bank-clustered"}
    if len(sample) > x.shape[1] and np.linalg.matrix_rank(x.to_numpy()) == x.shape[1]:
        fit = sm.QuantReg(sample["d_npl_pct"], x).fit(q=.5, max_iter=5000)
        intervals = fit.conf_int()
        median["terms"] = {term: {"coefficient": float(fit.params[term]), "ci95": intervals.loc[term].tolist(),
                                  "p": float(fit.pvalues[term])} for term in QUARTER_TERMS}
    values = [row["coefficient"] for row in omission]
    return {
        "baseline": baseline, "year_fe": model_year, "drop_2021_2022": recent, "by_ownership": groups,
        "leave_one_bank_out": {"q4_range": [min(values), max(values)] if values else None, "fits": omission},
        "median_regression": median, "reference_quarter": "Q1",
        "bootstrap": {"reps": BOOTSTRAP_REPS, "seed": BOOTSTRAP_SEED, "weights": "Rademacher", "test": "restricted t"},
    }, fitted


def reversal(panel):
    q4 = panel.loc[panel.quarter.eq(4), ["bank_code", "year", "d_npl_pct"]].rename(columns={"d_npl_pct": "q4_delta"})
    q1 = panel.loc[panel.quarter.eq(1), ["bank_code", "year", "d_npl_pct"]].rename(columns={"d_npl_pct": "next_q1_delta"})
    pairs = q4.merge(q1.assign(year=q1.year - 1), on=["bank_code", "year"], validate="one_to_one")
    pairs = pairs.dropna()
    pairs["down_then_up"] = pairs.q4_delta.lt(0) & pairs.next_q1_delta.gt(0)
    yearly = pairs.groupby("year")["down_then_up"].agg(n="size", count="sum").reset_index()
    yearly["share_pct"] = 100 * yearly["count"] / yearly["n"]
    return {"regression": _fit(pairs, "next_q1_delta", ["q4_delta"], bank=True)[0],
            "by_year": yearly.to_dict("records")}


def heterogeneity(panel):
    pre = panel.loc[panel.year.between(2021, 2022)].groupby("bank_code")["npl_pct"].mean().dropna()
    # Exactly the upper half; bank code resolves ties at the cutoff reproducibly.
    ranks = pre.sort_index().sort_values(ascending=False, kind="stable")
    high = ranks.index[:len(ranks) // 2]
    data = _quarters(panel.loc[panel.year.ge(2023) & panel.bank_code.isin(pre.index)]).copy()
    data["Q4_high_npl"] = data.Q4 & data.bank_code.isin(high)
    data["Q4_state"] = data.Q4 & data.ownership.eq("state")
    terms = [*QUARTER_TERMS, "Q4_high_npl", "Q4_state"]
    return {"pre_period": "2021Q1–2022Q4", "high_banks": high.tolist(),
            "regression": _fit(data, "d_npl_pct", terms, bank=True)[0]}


def linkage(panel):
    data = _quarters(panel)
    outcomes = ["d_coverage_pct", "d_nim_pct", "loan_growth_yoy_pct"]
    changes = [f"d_{name}" for name in RATIOS if name != "roa_pct"]
    core = data[changes]
    matrix = core.corr()
    present = core.notna().astype(int)
    counts = present.T @ present
    return {
        "seasonal": {outcome: _fit(data, outcome, QUARTER_TERMS, bank=True)[0] for outcome in outcomes},
        "correlation": matrix.to_dict(), "correlation_n": counts.to_dict(),
        "roa_note": "Nguồn FiinQuant không trả ROA. / The FiinQuant feed does not return ROA.",
    }


def event_paths(market, calendar):
    """Calculate cumulative market-model residuals on the VNINDEX session clock."""
    wide = market.pivot(index="date", columns="bank_code", values="return_pct").sort_index()
    benchmark = wide.pop("VNINDEX").to_numpy()
    dates = wide.index
    records = []
    for row in calendar.itertuples(index=False):
        event = dates.searchsorted(row.deadline)
        if event < 250 or event + 10 >= len(dates):
            continue
        train = slice(event - 250, event - 29)
        window = slice(event - 10, event + 11)
        x = benchmark[train]
        x_event = benchmark[window]
        if not np.isfinite(x_event).all():
            continue
        for bank in wide:
            y = wide[bank].to_numpy()
            jointly_observed = np.isfinite(x) & np.isfinite(y[train])
            if jointly_observed.sum() < 120 or not np.isfinite(y[window]).all():
                continue
            x_fit = np.column_stack([np.ones(jointly_observed.sum()), x[jointly_observed]])
            if np.linalg.matrix_rank(x_fit) != 2:
                continue
            alpha, beta = np.linalg.lstsq(x_fit, y[train][jointly_observed], rcond=None)[0]
            abnormal = y[window] - alpha - beta * x_event
            records.extend((bank, row.period, dates[event], day, ar, car, int(jointly_observed.sum()))
                           for day, ar, car in zip(range(-10, 11), abnormal, abnormal.cumsum()))
    return pd.DataFrame(records, columns=["bank_code", "period", "event_date", "day", "abnormal_return_pct",
                                          "car_pct", "estimation_n"])


def market_study(panel, market, calendar, fitted):
    paths = event_paths(market, calendar)
    bank_quarters = panel[["bank_code", "period", "basis", "quarter", "d_npl_pct"]].copy()
    bank_quarters["adjusted_d_npl_pct"] = panel.d_npl_pct - fitted
    events = bank_quarters.merge(calendar, on="period", how="left", validate="many_to_one")
    terminal = paths.loc[paths.day.eq(10), ["bank_code", "period", "event_date", "car_pct", "estimation_n"]]
    events = events.merge(terminal, on=["bank_code", "period"], how="left", validate="one_to_one")
    events["estimation_n"] = events["estimation_n"].astype("Int64")
    if terminal.empty:
        events["event_date"] = pd.NaT
    # Descriptive mean curve and bank-clustered confidence intervals.
    paths = paths.merge(bank_quarters[["bank_code", "period", "quarter"]],
                        on=["bank_code", "period"], how="inner", validate="many_to_one")
    means = []
    for group_name, group in [("all", paths), ("Q4", paths.loc[paths.quarter.eq(4)])]:
        for day, sample in group.groupby("day"):
            n = len(sample)
            mean = sample.car_pct.mean()
            cluster_sums = (sample.car_pct - mean).groupby(sample.bank_code).sum()
            clusters = len(cluster_sums)
            if clusters > 1:
                se = np.sqrt((cluster_sums ** 2).sum() * clusters / (clusters - 1)) / n
                margin = stats.t.ppf(.975, clusters - 1) * se
                ci = [mean - margin, mean + margin]
            else:
                ci = None
            means.append({"group": group_name, "day": int(day), "n": n, "mean_car_pct": mean, "ci95": ci})
    regressions = {}
    for label, predictor in [("raw", "d_npl_pct"), ("adjusted", "adjusted_d_npl_pct")]:
        regressions[label] = _fit(events, "car_pct", [predictor])[0]
        regressions[f"{label}_q4"] = _fit(events.loc[events.quarter.eq(4)], "car_pct", [predictor])[0]
    return {"regressions": regressions, "car_by_day": means, "events_with_car": int(events.car_pct.notna().sum()),
            "eligible_bank_quarters": int(events.deadline.notna().sum()),
            "period_start": events.loc[events.car_pct.notna(), "period"].min() if not terminal.empty else None,
            "period_end": events.loc[events.car_pct.notna(), "period"].max() if not terminal.empty else None}, events


def forecast(panel):
    data = _quarters(panel).copy()
    levels = data.set_index(["bank_code", "quarter_id"])["npl_pct"]

    def lagged(rows, lag):
        keys = pd.MultiIndex.from_arrays([rows["bank_code"], rows["quarter_id"] - lag])
        return levels.reindex(keys).to_numpy()

    train = data.loc[data.year.le(2024)].dropna(subset=["d_npl_pct"])
    design = _design(train, QUARTER_TERMS, bank=True)
    if train.empty or np.linalg.matrix_rank(design.to_numpy()) != design.shape[1]:
        raise ValueError("Mẫu huấn luyện dự báo thiếu biến thiên hoặc không đủ quý")
    fit = sm.OLS(train["d_npl_pct"], design).fit()
    lower_error, upper_error = fit.resid.quantile([.1, .9])
    trained_banks = train.bank_code.unique()

    def predict(rows):
        x = _design(rows, QUARTER_TERMS)
        for bank in trained_banks:
            term = f"bank_code_{bank}"
            if term in fit.params:
                x[term] = rows.bank_code.eq(bank)
        shift = x[fit.params.index].astype(float) @ fit.params
        rows["last_value"] = lagged(rows, 1)
        rows["seasonal_naive"] = lagged(rows, 4)
        rows["predicted_npl_pct"] = rows["last_value"] + shift.where(rows.bank_code.isin(trained_banks))
        rows["lower80"] = rows["predicted_npl_pct"] + lower_error
        rows["upper80"] = rows["predicted_npl_pct"] + upper_error
        # Center effects across quarters so the adjustment preserves their average level.
        seasonal = rows[QUARTER_TERMS].astype(float) @ fit.params[QUARTER_TERMS]
        rows["seasonally_adjusted_npl_pct"] = rows["npl_pct"] - (seasonal - fit.params[QUARTER_TERMS].sum() / 4)
        return rows

    test = predict(data.loc[data.period.between("2025Q1", "2026Q3")].copy())
    common = test.dropna(subset=["npl_pct", "predicted_npl_pct", "last_value", "seasonal_naive"])
    baseline_columns = {"naive": "last_value", "seasonal_naive": "seasonal_naive"}
    columns = {"model": "predicted_npl_pct", **baseline_columns}
    absolute_errors = common[list(columns.values())].sub(common["npl_pct"], axis=0).abs()
    errors = {label: float(absolute_errors[column].mean()) for label, column in columns.items()}
    errors_by_bank = absolute_errors.groupby(common["bank_code"])
    cluster_totals = errors_by_bank.sum()
    cluster_sizes = errors_by_bank.size()
    difference_intervals = {}
    for label, column in baseline_columns.items():
        estimate = errors["model"] - errors[label]
        interval = None
        if len(cluster_sizes) > 1:
            rng = np.random.default_rng(BOOTSTRAP_SEED)
            sample = rng.integers(len(cluster_sizes), size=(BOOTSTRAP_REPS, len(cluster_sizes)))
            totals = (cluster_totals[columns["model"]] - cluster_totals[column]).to_numpy()
            draws = totals[sample].sum(axis=1) / cluster_sizes.to_numpy()[sample].sum(axis=1)
            interval = np.quantile(draws, [.025, .975]).tolist()
        difference_intervals[label] = {"difference_pp": estimate, "ci95": interval}
    covered = common["npl_pct"].between(common["lower80"], common["upper80"])
    aggregate = common.groupby("period")[["npl_pct", "predicted_npl_pct", "last_value", "seasonal_naive"]].mean()
    aggregate["n"] = common.groupby("period").size()
    future = _quarters(pd.DataFrame({
        "bank_code": sorted(data.bank_code.unique()), "period": "2026Q4", "quarter": 4,
        "quarter_id": 2026 * 4 + 4, "npl_pct": np.nan,
    }))
    future = predict(future)
    future["unavailable_reason"] = np.select(
        [future.last_value.isna(), ~future.bank_code.isin(trained_banks)],
        ["missing_previous_quarter", "bank_not_in_training"], default="",
    )
    future = future[["bank_code", "period", "last_value", "predicted_npl_pct", "lower80", "upper80",
                     "unavailable_reason"]]
    return {
        "train_n": len(train), "train_through": "2024Q4", "test_period": ["2025Q1", "2026Q3"],
        "residual_quantiles_pp": [lower_error, upper_error],
        "backtest": {"n": len(common), "mae_pp": errors, "mae_difference_vs": difference_intervals,
                     "interval_coverage_pct": 100 * covered.mean(),
                     "by_period": aggregate.reset_index().to_dict("records")},
        "forecast_2026Q4": future.to_dict("records"),
    }, predict(data)[["seasonally_adjusted_npl_pct"]]
