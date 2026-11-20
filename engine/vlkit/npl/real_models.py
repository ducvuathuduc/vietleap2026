"""Panel inference, deadline event study and out-of-sample NPL predictions."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

from .real_data import DEADLINE_SOURCE, RATIOS, _bank_code


BOOTSTRAP_REPS = 999
BOOTSTRAP_SEED = 20261120
QUARTER_TERMS = ["Q2", "Q3", "Q4"]
MARKET_TERMS = ["expected_d_npl_pct", "surprise_d_npl_pct"]
FORECAST_TRAIN_THROUGH = "2024Q4"


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


def seasonal_expectation(panel):
    """Predict each observed change after removing its own bank-quarter from the fit."""
    sample = _quarters(panel.dropna(subset=["d_npl_pct"]))
    expected = pd.Series(np.nan, index=panel.index, dtype=float)
    x = _design(sample, QUARTER_TERMS, bank=True).to_numpy()
    if not len(x) or np.linalg.matrix_rank(x) != x.shape[1]:
        return expected
    inverse = np.linalg.pinv(x)
    y = sample["d_npl_pct"].to_numpy()
    fitted = x @ (inverse @ y)
    # Diagonal of the hat matrix; the deletion formula equals refitting each row.
    leverage = np.einsum("ij,ji->i", x, inverse)
    valid = leverage < 1 - 1e-10
    expected.loc[sample.index[valid]] = (y - (y - fitted) / np.where(valid, 1 - leverage, np.nan))[valid]
    return expected


def _mean_interval(values, banks):
    """95% t interval for an observation-weighted mean with bank clusters."""
    center = values.mean()
    scores = (values - center).groupby(banks).sum()
    clusters = len(scores)
    if clusters < 2:
        return None
    se = np.sqrt(scores.pow(2).sum() * clusters / (clusters - 1)) / len(values)
    margin = stats.t.ppf(.975, clusters - 1) * se
    return [center - margin, center + margin]


def _share_interval(count, n):
    return [100 * bound for bound in proportion_confint(count, n, method="wilson")] if n else None


def _bank_bootstrap_share(indicator, banks):
    """Resample whole bank histories and keep each eligible pair equally weighted."""
    bank_counts = indicator.groupby(banks).agg(["sum", "size"])
    if len(bank_counts) < 2:
        return None
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draw = rng.integers(len(bank_counts), size=(BOOTSTRAP_REPS, len(bank_counts)))
    counts = bank_counts["sum"].to_numpy()[draw].sum(axis=1)
    totals = bank_counts["size"].to_numpy()[draw].sum(axis=1)
    return np.quantile(100 * counts / totals, [.025, .975]).tolist()


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
    q4 = panel.loc[panel.quarter.eq(4), ["bank_code", "year", "period", "d_npl_pct"]].rename(columns={"d_npl_pct": "q4_delta"})
    q1 = panel.loc[panel.quarter.eq(1), ["bank_code", "year", "d_npl_pct"]].rename(columns={"d_npl_pct": "next_q1_delta"})
    pairs = q4.merge(q1.assign(year=q1.year - 1), on=["bank_code", "year"], validate="one_to_one")
    pairs = pairs.dropna()
    pairs["down_then_up"] = pairs.q4_delta.lt(0) & pairs.next_q1_delta.gt(0)
    yearly = pairs.groupby("year")["down_then_up"].agg(n="size", count="sum").reset_index()
    yearly["share_pct"] = 100 * yearly["count"] / yearly["n"]
    n, count = len(pairs), int(pairs["down_then_up"].sum())
    return {"regression": _fit(pairs, "next_q1_delta", ["q4_delta"], bank=True)[0],
            "summary": {"n": n, "reversals": count, "share_pct": 100 * count / n if n else None,
                        "ci95_share_pct": _bank_bootstrap_share(pairs.down_then_up, pairs.bank_code),
                        "ci95_share_pct_wilson": _share_interval(count, n),
                        "period": [pairs.period.min(), f"{pairs.year.max() + 1}Q1"] if n else None,
                        "mean_next_q1_change_pp": pairs.next_q1_delta.mean(),
                        "mean_next_q1_ci95": _mean_interval(pairs.next_q1_delta, pairs.bank_code),
                        "share_ci_method": "95% percentile bank bootstrap; Wilson shown for independent pairs"},
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
        for bank in ([row.bank_code] if hasattr(row, "bank_code") else wide):
            if bank not in wide:
                continue
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


def market_study(panel, market, calendar, disclosure=None):
    bank_quarters = panel[["bank_code", "period", "basis", "quarter", "d_npl_pct"]].copy()
    bank_quarters["expected_d_npl_pct"] = seasonal_expectation(panel)
    bank_quarters["surprise_d_npl_pct"] = panel.d_npl_pct - bank_quarters.expected_d_npl_pct
    events = bank_quarters.merge(calendar, on="period", how="left", validate="many_to_one")
    quarter_end = pd.PeriodIndex(events.period, freq="Q").to_timestamp(how="end").normalize()
    events["quarter_end"] = events["quarter_end"].fillna(pd.Series(quarter_end, index=events.index))
    events["deadline"] = events["deadline"].fillna(events.quarter_end + pd.Timedelta(days=30))
    events["deadline_source_url"] = events["deadline_source_url"].fillna(DEADLINE_SOURCE)
    keys = ["bank_code", "period"]
    if disclosure is not None:
        actual = disclosure[["ticker", "period", "published_at", "url"]].rename(columns={"url": "disclosure_url"})
        actual["bank_code"] = _bank_code(actual.pop("ticker"))
        actual["period"] = actual["period"].astype("string").str.strip().str.upper()
        actual["published_at"] = (pd.to_datetime(actual["published_at"], format="mixed", errors="coerce", utc=True)
                                  .dt.tz_convert("Asia/Ho_Chi_Minh").dt.tz_localize(None).dt.normalize())
        actual = actual.merge(events[keys + ["quarter_end"]], on=keys, how="inner", validate="many_to_one")
        actual = (actual.loc[actual["published_at"].gt(actual["quarter_end"])]
                  .sort_values(["published_at", "disclosure_url"]).drop_duplicates(keys))
        events = events.merge(actual[keys + ["published_at", "disclosure_url"]], on=keys,
                              how="left", validate="one_to_one")
    else:
        events = events.assign(published_at=pd.NaT, disclosure_url=None)

    observed = events.published_at.notna()
    events["anchor_date"] = events["published_at"].fillna(events["deadline"])
    events["anchor_source"] = np.select([observed, events.deadline.notna()], ["actual", "deadline"], default="missing")
    deadline_paths = event_paths(market, events[["period", "deadline"]].drop_duplicates())
    actual_paths = event_paths(market, events.loc[observed, keys + ["anchor_date"]]
                               .rename(columns={"anchor_date": "deadline"}))
    # A known disclosure with no valid trading window remains missing on the preferred clock.
    is_actual = pd.MultiIndex.from_frame(deadline_paths[keys]).isin(pd.MultiIndex.from_frame(events.loc[observed, keys]))
    paths = deadline_paths.loc[~is_actual]
    if not actual_paths.empty:
        paths = actual_paths if paths.empty else pd.concat([paths, actual_paths], ignore_index=True)
    columns = ["event_date", "car_pct", "estimation_n"]
    for source, prefix in [(paths, ""), (deadline_paths, "deadline_")]:
        terminal = source.loc[source.day.eq(10), keys + columns].rename(
            columns={column: prefix + column for column in columns})
        events = events.merge(terminal, on=keys, how="left", validate="one_to_one")
        events[prefix + "event_date"] = pd.to_datetime(events[prefix + "event_date"])
        events[prefix + "estimation_n"] = events[prefix + "estimation_n"].astype("Int64")

    dated = events.loc[events.anchor_source.eq("actual")]
    matched = dated.dropna(subset=["car_pct", "deadline_car_pct"])
    variants = [
        ("reported_or_deadline", events, "car_pct"),
        ("deadline_only", events, "deadline_car_pct"),
        ("reported_or_deadline_q4", events.loc[events.quarter.eq(4)], "car_pct"),
        ("deadline_only_q4", events.loc[events.quarter.eq(4)], "deadline_car_pct"),
        ("actual_dates", dated, "car_pct"),
        ("matched_actual", matched, "car_pct"),
        ("matched_deadline", matched, "deadline_car_pct"),
    ]
    regressions = {label: _fit(sample, outcome, MARKET_TERMS, bootstrap=True)[0]
                   for label, sample, outcome in variants}
    curves = {}
    for label, source in [("reported_or_deadline", paths), ("deadline_only", deadline_paths)]:
        source = source.merge(bank_quarters[keys + ["quarter"]], on=keys, how="inner", validate="many_to_one")
        curves[label] = [
            {"group": name, "day": int(day), "n": len(sample), "mean_car_pct": sample.car_pct.mean(),
             "ci95": _mean_interval(sample.car_pct, sample.bank_code)}
            for name, group in [("all", source), ("Q4", source.loc[source.quarter.eq(4)])]
            for day, sample in group.groupby("day")
        ]
    available = events.loc[events.car_pct.notna()]
    return {
        "regressions": regressions, "car_by_day": curves["reported_or_deadline"],
        "deadline_car_by_day": curves["deadline_only"],
        "events_with_car": len(available), "eligible_bank_quarters": int(events.anchor_date.notna().sum()),
        "period_start": available.period.min() if len(available) else None,
        "period_end": available.period.max() if len(available) else None,
        "coverage": {"bank_quarters_n": len(events), "actual_date_n": len(dated),
                     "actual_date_pct": 100 * len(dated) / len(events) if len(events) else None,
                     "actual_date_car_n": int(dated.car_pct.notna().sum()), "matched_clock_car_n": len(matched),
                     "deadline_fallback_n": int(events.anchor_source.eq("deadline").sum()),
                     "deadline_car_n": int(events.deadline_car_pct.notna().sum()),
                     "period": [events.period.min(), events.period.max()] if len(events) else None},
    }, events


def decision_rule(panel):
    """Use the M7 model and residual quantiles with training strictly before each target."""
    data = _quarters(panel)
    rows = data[["bank_code", "period", "quarter", "year", "d_npl_pct"]].copy()
    rows["expected_change_pp"] = rows["lo80_pp"] = rows["hi80_pp"] = np.nan
    rows["train_n"] = 0
    for period, target in data.groupby("period"):
        train = data.loc[data.period.lt(period) & data.period.le(FORECAST_TRAIN_THROUGH)].dropna(subset=["d_npl_pct"])
        x = _design(train, QUARTER_TERMS, bank=True)
        if len(x) <= len(x.columns) or np.linalg.matrix_rank(x.to_numpy()) != len(x.columns):
            continue
        fit = sm.OLS(train["d_npl_pct"], x).fit()
        predict = _design(target, QUARTER_TERMS, bank=True)
        for column in x.columns.difference(predict.columns):
            bank = column.removeprefix("bank_code_")
            predict[column] = target.bank_code.eq(bank)
        expected = predict[x.columns].astype(float) @ fit.params
        eligible = target.index[target.bank_code.isin(train.bank_code)]
        rows.loc[eligible, "expected_change_pp"] = expected.loc[eligible]
        lo, hi = fit.resid.quantile([.1, .9])
        rows.loc[eligible, ["lo80_pp", "hi80_pp", "train_n"]] = [lo, hi, len(train)]
    rows["adjusted_change_pp"] = rows["d_npl_pct"] - rows["expected_change_pp"]
    residual = rows["adjusted_change_pp"]
    improving = residual.lt(rows["lo80_pp"] - 1e-10)
    deteriorating = residual.gt(rows["hi80_pp"] + 1e-10)
    rows["unusual"] = (improving | deteriorating).astype("boolean").where(residual.notna())
    rows["status"] = np.select([residual.isna(), improving, deteriorating],
                               ["unavailable", "improving", "deteriorating"], default="within_normal_season")
    rows["status_vi"] = rows["status"].map({"unavailable": "Chưa đủ dữ liệu", "improving": "Cải thiện",
                                           "deteriorating": "Xấu đi", "within_normal_season": "Trong mùa vụ bình thường"})
    rows["status_en"] = rows["status"].str.replace("_", " ")
    q4 = rows.loc[rows.quarter.eq(4) & residual.notna()]
    q1 = rows.loc[rows.quarter.eq(1), ["bank_code", "year", "d_npl_pct"]].rename(columns={"d_npl_pct": "q1_delta"})
    pairs = q4.merge(q1.assign(year=q1.year - 1).dropna(), on=["bank_code", "year"], validate="one_to_one")
    pairs["reversed"] = (pairs["d_npl_pct"] * pairs["q1_delta"]).lt(0)
    backtest = {}
    for label, selected in [("unusual", pairs.unusual), ("improving", pairs.status.eq("improving")),
                            ("deteriorating", pairs.status.eq("deteriorating")),
                            ("within_normal_season", pairs.status.eq("within_normal_season"))]:
        sample = pairs.loc[selected]
        n, count = len(sample), int(sample["reversed"].sum())
        backtest[label] = {"n": n, "reversals": count, "share_pct": 100 * count / n if n else None,
                           "clusters": int(sample.bank_code.nunique()),
                           "ci95": _bank_bootstrap_share(sample.reversed, sample.bank_code),
                           "ci95_wilson": _share_interval(count, n),
                           "period": [sample.period.min(), f"{sample.year.max() + 1}Q1"] if n else None}
    fields = ["bank_code", "period", "d_npl_pct", "expected_change_pp", "adjusted_change_pp", "lo80_pp",
              "hi80_pp", "train_n", "unusual", "status", "status_vi", "status_en"]
    latest_period = rows.period.max()
    latest = (rows.loc[rows.period.eq(latest_period), fields].set_index("bank_code")
              .reindex(sorted(rows.bank_code.unique())).reset_index())
    latest["period"] = latest_period
    latest["train_n"] = latest["train_n"].fillna(0).astype(int)
    for column, label in [("status", "unavailable"), ("status_vi", "Chưa đủ dữ liệu"), ("status_en", "unavailable")]:
        latest[column] = latest[column].fillna(label)
    return {
        "latest_period": latest_period,
        "latest": latest.to_dict("records"),
        "q4_backtest": backtest,
        "eligible_q4_n": len(q4),
        "paired_q4_n": len(pairs),
        "band_level_pct": 80,
        "share_ci_method": "95% percentile bank bootstrap; Wilson shown for independent pairs",
        "reading_vi": "So sánh thay đổi NPL thực tế trừ mức dự kiến với dải sai số M7 80%; thấp hơn dải là cải thiện, cao hơn là xấu đi, và trong dải là mùa vụ bình thường.",
        "reading_en": "Compare the actual NPL change minus its expected change with the M7 80% residual band; below is improving, above is deteriorating, and inside is within normal season.",
        "does_not_show_vi": "Cờ khác thường chỉ đặt ưu tiên rà soát; đảo chiều là hai thay đổi NPL thực tế liên tiếp trái dấu và chưa xác định nguyên nhân.",
        "does_not_show_en": "An unusual flag prioritizes review; a reversal is two consecutive actual NPL changes with opposite signs and does not establish a cause.",
    }, rows[fields]


def forecast(panel):
    data = _quarters(panel).copy()
    levels = data.set_index(["bank_code", "quarter_id"])["npl_pct"]

    def lagged(rows, lag):
        keys = pd.MultiIndex.from_arrays([rows["bank_code"], rows["quarter_id"] - lag])
        return levels.reindex(keys).to_numpy()

    train = data.loc[data.period.le(FORECAST_TRAIN_THROUGH)].dropna(subset=["d_npl_pct"])
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
        "train_n": len(train), "train_through": FORECAST_TRAIN_THROUGH, "test_period": ["2025Q1", "2026Q3"],
        "residual_quantiles_pp": [lower_error, upper_error],
        "backtest": {"n": len(common), "mae_pp": errors, "mae_difference_vs": difference_intervals,
                     "interval_coverage_pct": 100 * covered.mean(),
                     "by_period": aggregate.reset_index().to_dict("records")},
        "forecast_2026Q4": future.to_dict("records"),
    }, predict(data)[["seasonally_adjusted_npl_pct"]]
