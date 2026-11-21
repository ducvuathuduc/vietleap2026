"""Quarter-ahead bank-panel forecasts and lead-lag checks from published Silver data."""

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .decompose import GROUPS
from .real_models import BOOTSTRAP_REPS, BOOTSTRAP_SEED, FORECAST_TRAIN_THROUGH, _fit


HORIZONS = {"change_h1": 1, "change_h2": 2, "change_h4": 4, "rise_in_four": 4}
EVENT_THRESHOLD_PP = .5
CREDIT_FIELDS = [*GROUPS, "loans_customer", "provision_closing", "provision_expense"]
NPL_ONLY = ("npl_pct",)
WITH_GROUP2 = (*NPL_ONLY, "group2_pct", "change_group2_pp")
# broad_problem_pct equals NPL plus Group 2, so it stays on the panel and out of the regression.
FULL = (*WITH_GROUP2, "severity_pct", "loan_growth_qoq_pct", "loan_growth_4q_pct",
        "lagged_coverage_pct", "provisions_to_loans_pct", "credit_cost_pct")
SPECIFICATIONS = {"npl_only": NPL_ONLY, "npl_group2": WITH_GROUP2, "full": FULL}


def _screening_input(screening, quarantine):
    columns = ["bank_code", "period", *CREDIT_FIELDS]
    if screening is None or screening.empty:
        return pd.DataFrame(columns=columns)
    expense = screening.field.eq("provision_expense")
    valid = (expense & screening.flow_basis.eq("quarterly")) | (
        ~expense & screening.field.isin(CREDIT_FIELDS) & screening.flow_basis.eq("point")
    )
    rows = screening.loc[valid, ["bank", "period", "field", "value_vnd_bn"]].rename(columns={"bank": "bank_code"})
    if quarantine:
        keys = [(row["bank_code"], row["period"]) for row in quarantine]
        rows = rows.loc[~pd.MultiIndex.from_frame(rows[["bank_code", "period"]]).isin(keys)]
    wide = rows.drop_duplicates().pivot(index=["bank_code", "period"], columns="field", values="value_vnd_bn")
    return wide.reset_index().reindex(columns=columns)


def build_warning_panel(panel, screening, quarantine=None):
    """Use exact bank-quarter keys for all leads, lagged inputs and flow denominators."""
    data = panel[["bank_code", "period", "npl_pct", "coverage_pct"]].merge(
        _screening_input(screening, quarantine), on=["bank_code", "period"], how="left", validate="one_to_one",
    ).sort_values(["bank_code", "period"]).reset_index(drop=True)
    data[CREDIT_FIELDS] = data[CREDIT_FIELDS].apply(pd.to_numeric, errors="coerce")
    dates = pd.PeriodIndex(data.period, freq="Q")
    data["year"] = dates.year
    data["quarter_id"] = dates.asi8
    loans = data.loans_customer.where(data.loans_customer.gt(0))
    data["loans_customer"] = loans
    bad = data[GROUPS[2:]].sum(axis=1, min_count=3)
    data["group2_pct"] = 100 * data.group_2_watch / loans
    data["broad_problem_pct"] = 100 * (bad + data.group_2_watch) / loans
    data["severity_pct"] = 100 * data.group_5_loss / bad.where(bad.gt(0))
    data["provisions_to_loans_pct"] = 100 * data.provision_closing.abs() / loans
    lookup = data.set_index(["bank_code", "quarter_id"])

    def at_offset(field, offset):
        keys = pd.MultiIndex.from_arrays([data.bank_code, data.quarter_id + offset])
        return pd.Series(lookup[field].reindex(keys).to_numpy(), index=data.index, dtype=float)

    opening = at_offset("loans_customer", -1)
    data["change_group2_pp"] = data.group2_pct - at_offset("group2_pct", -1)
    data["lagged_coverage_pct"] = at_offset("coverage_pct", -1)
    data["loan_growth_qoq_pct"] = 100 * (loans / opening - 1)
    data["loan_growth_4q_pct"] = 100 * (loans / at_offset("loans_customer", -4) - 1)
    # The vendor reports expenses as negative. Keep reversals signed.
    data["credit_cost_pct"] = -100 * data.provision_expense / ((loans + opening) / 2)

    future = {0: data.npl_pct, **{h: at_offset("npl_pct", h) for h in range(1, 5)}}
    for outcome, horizon in HORIZONS.items():
        if outcome != "rise_in_four":
            data[outcome] = future[horizon] - data.npl_pct
    for h in range(1, 5):
        data[f"lead_h{h}"] = future[h] - future[h - 1]
    path = pd.DataFrame({h: future[h] - data.npl_pct for h in range(1, 5)})
    data["rise_in_four"] = path.max(axis=1, skipna=False).ge(EVENT_THRESHOLD_PP - 1e-12).astype(float).where(path.notna().all(axis=1))
    return data


def temporal_split(frame, outcome, horizon):
    """Keep only labels observable by the cutoff in training, with strictly later test origins."""
    cutoff = pd.Period(FORECAST_TRAIN_THROUGH, freq="Q").ordinal
    observed = frame.loc[frame[outcome].notna()]
    return (observed.loc[observed.quarter_id.add(horizon).le(cutoff)],
            observed.loc[observed.quarter_id.gt(cutoff)])


def _max_vif(frame, features):
    """Largest variance-inflation factor among one specification's predictors."""
    columns = list(features)
    used = frame[columns].dropna()
    if len(columns) <= 1:
        return 1.0 if len(used) else None
    if len(used) <= len(columns):
        return None
    values = used.to_numpy(dtype=float)
    scores = []
    for index in range(values.shape[1]):
        y = values[:, index]
        x = np.column_stack([np.ones(len(used)), np.delete(values, index, axis=1)])
        beta, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
        residual = y - x @ beta
        total = float(np.square(y - y.mean()).sum())
        if total <= 1e-18:
            scores.append(np.inf)
            continue
        r2 = 1 - float(np.square(residual).sum()) / total
        scores.append(np.inf if r2 >= 1 - 1e-10 else 1 / (1 - r2))
    return float(max(scores))


def _forecast_design(rows, features, center, scale, banks):
    effects = np.column_stack([rows.bank_code.eq(bank) for bank in banks[1:]]) if len(banks) > 1 else np.empty((len(rows), 0))
    features = (rows[list(features)] - center) / scale
    return np.column_stack((np.ones(len(rows)), features, effects)).astype(float)


def holdout_predictions(frame, outcome, horizon, specifications):
    """Train all specifications on shared complete rows; score the same held-out bank-quarters."""
    fields = list(dict.fromkeys(field for features in specifications.values() for field in features))
    train, test = temporal_split(frame.dropna(subset=fields), outcome, horizon)
    banks = sorted(train.bank_code.unique())
    # A fixed effect for a bank without training observations is unidentified.
    test = test.loc[test.bank_code.isin(banks)]
    predictions = {}
    binary = outcome == "rise_in_four"
    if not len(test) or len(train) <= len(fields) + len(banks) or (binary and train[outcome].nunique() < 2):
        return train, test, predictions
    for name, features in specifications.items():
        x = train[list(features)]
        center, scale = x.mean(), x.std(ddof=0).replace(0., 1.)
        training = _forecast_design(train, features, center, scale, banks)
        # Least squares still gives a forecast if two predictors are algebraically redundant.
        beta, _, _, _ = np.linalg.lstsq(training, train[outcome].to_numpy(), rcond=None)
        estimate = _forecast_design(test, features, center, scale, banks) @ beta
        predictions[name] = np.clip(estimate, 0, 1) if binary else estimate
    return train, test, predictions


def _scores(truth, estimate, weights, binary):
    if not binary:
        return {"mae": float(np.average(np.abs(truth - estimate), weights=weights))}
    positive = weights[truth == 1].sum()
    negative = weights[truth == 0].sum()
    return {
        "auc": float(roc_auc_score(truth, estimate, sample_weight=weights)) if positive and negative else None,
        "brier": float(np.average((truth - estimate) ** 2, weights=weights)),
    }


def _interval(estimate, draws):
    values = [value for value in draws if value is not None]
    return {"estimate": estimate, "ci95": np.quantile(values, [.025, .975]).tolist() if values else None,
            "bootstrap_draws": len(values)}


def _gain(baseline, candidate, metric):
    if baseline is None or candidate is None:
        return None
    return candidate - baseline if metric == "auc" else baseline - candidate


def compare_forecasts(frame, outcome, horizon, specifications=SPECIFICATIONS, *, reps=BOOTSTRAP_REPS):
    train, test, predictions = holdout_predictions(frame, outcome, horizon, specifications)
    binary = outcome == "rise_in_four"
    result = {
        "n_train": len(train), "n_test": len(test), "train_banks": int(train.bank_code.nunique()),
        "test_banks": int(test.bank_code.nunique()), "last_training_origin": train.period.max() if len(train) else None,
        "last_training_label": str(pd.Period(ordinal=int(train.quarter_id.max()) + horizon, freq="Q")) if len(train) else None,
        "test_origins": [test.period.min(), test.period.max()] if len(test) else None,
        "fits": {}, "gains_vs_npl": {},
    }
    if not predictions:
        return {**result, "unavailable_reason": "insufficient_matched_training_or_test_data"}
    truth = test[outcome].to_numpy(dtype=float)
    if binary:
        result["test_events"] = int(truth.sum())
    codes, banks = pd.factorize(test.bank_code)
    metrics = {name: _scores(truth, estimate, np.ones(len(test)), binary) for name, estimate in predictions.items()}
    draws = []
    if len(banks) >= 2:
        sampled = np.random.default_rng(BOOTSTRAP_SEED).integers(len(banks), size=(reps, len(banks)))
        for selection in sampled:
            weights = np.bincount(selection, minlength=len(banks))[codes]
            draws.append({name: _scores(truth, estimate, weights, binary) for name, estimate in predictions.items()})
    result["fits"] = {name: {
        metric: _interval(value, [draw[name][metric] for draw in draws])
        for metric, value in scores.items()
    } for name, scores in metrics.items()}

    def gains(baseline, candidates):
        return {name: {
            metric: _interval(_gain(metrics[baseline][metric], value, metric),
                              [_gain(draw[baseline][metric], draw[name][metric], metric) for draw in draws])
            for metric, value in metrics[name].items()
        } for name in candidates}

    result["gains_vs_npl"] = gains("npl_only", [name for name in metrics if name != "npl_only"])
    if "full" in metrics and "npl_group2" in metrics:
        result["full_vs_group2"] = gains("npl_group2", ["full"])["full"]
    return result


def _standardized_fits(panel, outcome):
    fields = list(FULL)
    data = panel.dropna(subset=[outcome, *fields]).copy()
    x = data[fields]
    center, scale = x.mean(), x.std(ddof=0)
    data[fields] = (x - center) / scale.replace(0., 1.)
    if outcome == "rise_in_four":
        data[outcome] *= 100
    return {
        "bank_fe": _fit(data, outcome, fields, bank=True, bootstrap=True)[0],
        "bank_year_fe": _fit(data, outcome, fields, bank=True, year=True, bootstrap=True)[0],
        "predictor_sd": scale.to_dict() if len(data) else {},
        "n": len(data),
    }


def _lead_profile(panel):
    profile = [
        {"horizon": h, **_fit(panel, f"lead_h{h}", ["change_group2_pp"], bank=True, bootstrap=True)[0]}
        for h in range(1, 5)
    ]
    vi = ("Hệ số cho biết thay đổi tỷ lệ nợ xấu trong từng quý tương lai đi cùng mức tăng một điểm phần trăm "
          "của tỷ lệ nợ nhóm 2 hôm nay như thế nào trong cùng ngân hàng.")
    en = ("Each slope relates the change in NPL in one future quarter to a one-point increase in today's "
          "Group 2 ratio within the same bank.")
    first, second = (row["terms"].get("change_group2_pp") for row in profile[:2])
    if first and second:
        first_vi = f"{first['coefficient']:+.3f}".replace(".", ",")
        second_vi = f"{second['coefficient']:+.3f}".replace(".", ",")
        vi += f" Ước lượng sau một và hai quý lần lượt là {first_vi} và {second_vi} điểm phần trăm."
        en += f" The one- and two-quarter slopes are {first['coefficient']:+.3f} and {second['coefficient']:+.3f} pp."
        if all(term["wild_p"] is not None and term["wild_p"] >= .05 for term in (first, second)):
            vi += " Kiểm định bootstrap theo cụm ngân hàng chưa tách được hai hệ số này khỏi 0 ở mức 5%."
            en += " The bank-cluster bootstrap does not separate either slope from zero at 5%."
    return {
        "profile": profile,
        "reading_vi": vi,
        "reading_en": en,
        "what_this_does_not_show": {
            "vi": "Các tỷ lệ gộp theo ngân hàng không theo dõi cùng một khoản vay khi khoản đó chuyển nhóm.",
            "en": "Aggregate bank ratios do not track individual loans moving between categories.",
        },
    }


def _positive_gains(backtests, model, english):
    def label(outcome, metric):
        if outcome == "rise_in_four":
            return f"four-quarter event {metric.upper()}" if english else f"{metric.upper()} của biến cố trong 4 quý"
        return f"{outcome[-1]}-quarter MAE" if english else f"MAE ở kỳ hạn {outcome[-1]} quý"

    return [
        label(outcome, metric) for outcome, report in backtests.items()
        for metric, gain in report["gains_vs_npl"].get(model, {}).items()
        if gain["ci95"] and gain["ci95"][0] > 0
    ]


def _backtest_reading(backtests, *, english):
    if not any(report["fits"] for report in backtests.values()):
        return ("There are too few matched bank-quarters for a held-out comparison." if english else
                "Chưa đủ ngân hàng-quý có cùng đầu vào để so sánh dự báo ngoài mẫu.")
    group2 = _positive_gains(backtests, "npl_group2", english)
    full = _positive_gains(backtests, "full", english)
    event_fits = backtests["rise_in_four"]["fits"]
    event_scores = [event_fits.get(name, {}).get("auc", {}).get("estimate") for name in SPECIFICATIONS]
    if english:
        if group2:
            group_text = f"Adding Group 2 improves these held-out measures with positive paired intervals: {', '.join(group2)}."
        else:
            group_text = "Adding Group 2 shows no clear improvement over NPL alone on the matched held-out quarters."
        full_text = (f"The full set improves {', '.join(full)} as a bundle." if full else
                     "The full set also shows no clear improvement over NPL alone.")
        result = f"{group_text} {full_text}"
        if all(score is not None for score in event_scores):
            base, group, complete = event_scores
            result += f" For a rise within four quarters, AUC is {base:.3f} for NPL alone, {group:.3f} with Group 2, and {complete:.3f} with the full set."
        return result
    if group2:
        group_text = f"Nợ nhóm 2 cải thiện dự báo ngoài mẫu ở các phép đo {', '.join(group2)} với khoảng chênh lệch dương."
    else:
        group_text = "Thông tin nợ nhóm 2 chưa cải thiện rõ dự báo so với chỉ dùng tỷ lệ nợ xấu trên cùng mẫu kiểm định."
    full_text = (f"Nhóm chỉ báo đầy đủ cải thiện các phép đo {', '.join(full)} khi dùng chung." if full else
                 "Nhóm chỉ báo đầy đủ cũng chưa cải thiện rõ dự báo.")
    result = f"{group_text} {full_text}"
    if all(score is not None for score in event_scores):
        base, group, complete = (f"{score:.3f}".replace(".", ",") for score in event_scores)
        result += (f" Với biến cố nợ xấu tăng trong 4 quý, AUC lần lượt là {base} khi chỉ dùng tỷ lệ nợ xấu, "
                   f"{group} khi thêm nợ nhóm 2 và {complete} với đầy đủ chỉ báo.")
    return result


def early_warning(panel, screening, quarantine=None):
    """Publish model coefficients, fair holdout comparisons and the Group 2 lead profile."""
    data = build_warning_panel(panel, screening, quarantine)
    models = {name: _standardized_fits(data, name) for name in HORIZONS}
    backtests = {name: compare_forecasts(data, name, horizon) for name, horizon in HORIZONS.items()}
    return {
        "outcome_horizons": HORIZONS,
        "event_threshold_pp": EVENT_THRESHOLD_PP,
        "train_through": FORECAST_TRAIN_THROUGH,
        "predictors": {name: list(features) for name, features in SPECIFICATIONS.items()},
        "vif": {name: value if value is not None and np.isfinite(value) else None
                for name, value in ((name, _max_vif(data, features)) for name, features in SPECIFICATIONS.items())},
        "predictor_availability": {field: int(data[field].count()) for field in FULL},
        "standardized_coefficients": models,
        "backtests": backtests,
        "lead_lag": _lead_profile(data),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_reps": BOOTSTRAP_REPS,
        "method": {
            "outcomes": "Point-to-point changes require both endpoints. The binary event requires all four forward quarters.",
            "coefficients": "Bank and bank-plus-year fixed-effects OLS. Outcome points per one predictor SD. Binary coefficients are linear probability effects in percentage points. The broad problem ratio equals NPL plus Group 2 and is excluded from the predictors.",
            "holdout": "Bank fixed effects with training-only scaling and known training banks. Three specifications use the same complete rows for each outcome. The binary model clips probabilities to [0, 1].",
            "flow": "Credit cost is signed quarterly provision expense divided by the mean of opening and closing customer loans, as a percent. Annual and uncertain flows are excluded.",
            "uncertainty": "Bank-clustered SE and restricted wild bootstrap for slopes. Percentile bank bootstrap resamples the matched held-out histories for scores and score differences. AUC intervals use draws with both event classes.",
        },
        "reading_vi": _backtest_reading(backtests, english=False),
        "reading_en": _backtest_reading(backtests, english=True),
        "what_this_does_not_show": {
            "vi": "So sánh dự báo áp dụng cho ngân hàng và quý có đủ đầu vào. Kết quả của nhóm chỉ báo đầy đủ chưa tách được đóng góp của từng chỉ báo hoặc nguyên nhân tăng nợ xấu.",
            "en": "Forecast comparisons cover bank-quarters with all inputs. Results for the full set do not isolate contributions from individual indicators or causes of rising NPL.",
        },
    }
