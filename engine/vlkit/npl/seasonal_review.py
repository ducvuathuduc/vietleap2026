"""Bank-clustered checks for quarter effects, matched rebounds and confounders."""

from numbers import Real

import numpy as np
import pandas as pd
from scipy import stats
from scipy.linalg import null_space
import statsmodels.api as sm

from .real_context import _forbearance_timeline
from .real_models import BOOTSTRAP_REPS, BOOTSTRAP_SEED, QUARTER_TERMS, _bank_bootstrap_share, _design, _fit, _quarters


def _wald(estimates, covariance):
    """Wald F with one row per draw; singular draws do not supply a statistic."""
    valid = np.linalg.eigvalsh(covariance)[:, 0] > 1e-18
    statistic = np.full(len(estimates), np.nan)
    vectors = estimates[valid, :, None]
    if len(vectors):
        solved = np.linalg.solve(covariance[valid], vectors)
        statistic[valid] = (vectors * solved).sum(axis=(1, 2)) / estimates.shape[1]
    return statistic


def _wild_contrast(x, y, inverse, groups, weights, contrast, observed, alternative):
    """Restricted Rademacher wild cluster bootstrap, with CR1 re-studentisation."""
    restricted = x @ null_space(contrast)
    fitted = restricted @ (np.linalg.pinv(restricted) @ y)
    draws = fitted[:, None] + (y - fitted)[:, None] * (groups @ weights)
    beta = inverse @ draws
    residuals = draws - x @ beta
    scores = np.stack([groups.T @ (effect[:, None] * residuals) for effect in contrast @ inverse], axis=1)
    n, k = x.shape
    g = groups.shape[1]
    correction = (g / (g - 1)) * ((n - 1) / (n - k))
    estimated = (contrast @ beta).T
    covariance = correction * np.einsum("gik,gjk->kij", scores, scores)
    if len(contrast) == 1:
        se = np.sqrt(covariance[:, 0, 0])
        values = np.divide(estimated[:, 0], se, out=np.full(len(se), np.nan), where=se > 1e-12)
        if alternative == "less":
            values, observed = -values, -observed
        elif alternative == "two-sided":
            values, observed = np.abs(values), abs(observed)
    else:
        values = _wald(estimated, covariance)
    values = values[np.isfinite(values)]
    if not len(values) or not np.isfinite(observed):
        return None
    extreme = (values >= observed) | np.isclose(values, observed, rtol=1e-10, atol=1e-12)
    return float((1 + extreme.sum()) / (1 + len(values)))


def _test_contrasts(data, terms, restrictions):
    """Fit once and evaluate the requested linear and joint restrictions."""
    columns = ["constant", *terms]
    data = data.dropna(subset=["d_npl_pct", *terms])
    n, clusters = len(data), data.bank_code.nunique()
    maps = {key: {"n": n, "clusters": clusters, "p": None, "wild_p": None, "ci95": None}
            for key in restrictions}
    if clusters < 2:
        return maps
    design = _design(data, terms, bank=True)
    x = design.to_numpy()
    if n <= x.shape[1] or np.linalg.matrix_rank(x) < x.shape[1]:
        return maps
    y = data.d_npl_pct.to_numpy()
    fit = sm.OLS(y, x).fit(cov_type="cluster", cov_kwds={"groups": data.bank_code}, use_t=True)
    inverse = np.linalg.pinv(x)
    groups = pd.get_dummies(data.bank_code, dtype=float).to_numpy()
    weights = np.random.default_rng(BOOTSTRAP_SEED).choice([-1., 1.], (clusters, BOOTSTRAP_REPS))
    df = clusters - 1
    for key, (vectors, alternative) in restrictions.items():
        contrast = np.array([[vector.get(column, 0.) if column in columns else vector.get("bank_average", 0.) / clusters
                              for column in design.columns] for vector in vectors])
        estimate = contrast @ fit.params
        cov = contrast @ fit.cov_params() @ contrast.T
        se = np.sqrt(np.maximum(np.diag(cov), 0))
        result = maps[key]
        if len(vectors) == 1:
            value = estimate[0]
            result["coefficient"] = float(value)
            result["alternative"] = alternative
            if not np.isfinite(se[0]) or se[0] <= 1e-12:
                continue
            observed = value / se[0]
            margin = stats.t.ppf(.975, df) * se[0]
            p = (2 * stats.t.sf(abs(observed), df) if alternative == "two-sided"
                 else stats.t.sf(observed if alternative == "greater" else -observed, df))
            result.update(se=float(se[0]), ci95=[float(value - margin), float(value + margin)], p=float(p))
        else:
            observed = _wald(estimate[None, :], cov[None, :, :])[0]
            if not np.isfinite(observed):
                continue
            q = len(vectors)
            margins = stats.t.ppf(1 - .05 / (2 * q), df) * se
            simultaneous = {next(iter(vector)): [float(value - margin), float(value + margin)]
                            for vector, value, margin in zip(vectors, estimate, margins)}
            result.update(statistic=float(observed), df_num=q, df_den=df,
                          p=float(stats.f.sf(observed, q, df)), simultaneous_ci95=simultaneous)
        result["wild_p"] = _wild_contrast(x, y, inverse, groups, weights, contrast, observed, alternative)
    return maps


def seasonal_hypotheses(panel):
    """Directional contrasts in percentage points and a joint quarter Wald test."""
    average_bank = {"constant": 1., "bank_average": 1.}
    restrictions = {
        "q4_below_zero": ([{**average_bank, "Q4": 1.}], "less"),
        "q1_above_zero": ([average_bank], "greater"),
        "q4_vs_q2_q3": ([{"Q4": 1., "Q2": -.5, "Q3": -.5}], "less"),
        "q4_vs_q1_q3": ([{"Q4": 1., "Q2": -1 / 3, "Q3": -1 / 3}], "less"),
        "joint_quarters": ([{quarter: 1.} for quarter in QUARTER_TERMS], "two-sided"),
    }
    readings = {
        "q4_below_zero": ("Mức thay đổi bình quân Quý 4 có thấp hơn 0 không?",
                          "Is the average change in Q4 below zero?"),
        "q1_above_zero": ("Mức thay đổi bình quân Quý 1 có cao hơn 0 không?",
                          "Is the average change in Q1 above zero?"),
        "q4_vs_q2_q3": ("So Quý 4 với trung bình của Quý 2 và Quý 3.",
                         "Compare Q4 with the average of Q2 and Q3."),
        "q4_vs_q1_q3": ("So Quý 4 với trung bình ba quý đầu năm.",
                         "Compare Q4 with the average of the first three quarters."),
        "joint_quarters": ("Kiểm định chung ba hệ số so với Quý 1. Các khoảng đồng thời thuộc về từng hệ số.",
                           "Test all three coefficients relative to Q1 jointly. The simultaneous intervals are for the individual coefficients."),
    }
    tests = _test_contrasts(_quarters(panel), QUARTER_TERMS, restrictions)
    for name, (vi, en) in readings.items():
        tests[name].update(reading_vi=vi, reading_en=en)
    return {
        "tests": tests,
        "mean_weights": "equal bank weights for fitted quarter means",
        "reading_vi": "Kiểm định riêng mức bình quân Quý 4 âm, Quý 1 dương và Quý 4 thấp hơn hai mốc trong năm. Wald kiểm định chung ba hệ số quý so với Quý 1. Khoảng đồng thời của Wald dùng hiệu chỉnh Bonferroni.",
        "reading_en": "Test separately whether the Q4 mean is negative, the Q1 mean positive, and Q4 below two in-year benchmarks. The Wald test compares all three quarter coefficients jointly with Q1. Its simultaneous intervals use Bonferroni coverage.",
    }


def loan_size_subgroups(panel, amounts):
    """Classify banks by their median reported customer-loan stock over the panel."""
    sizes = pd.Series(dtype=float)
    if amounts is not None:
        usable = amounts.loc[amounts.bank_code.isin(panel.bank_code) & amounts.customer_loans.gt(0)]
        sizes = usable.groupby("bank_code").customer_loans.median()
    cutoff = float(sizes.median()) if len(sizes) else None
    data = _quarters(panel)
    groups = {label: _fit(data.loc[data.bank_code.isin(banks)], "d_npl_pct", QUARTER_TERMS,
                          bank=True, bootstrap=True)[0]
              for label, banks in [("large", sizes.index[sizes.ge(cutoff)] if len(sizes) else []),
                                   ("small", sizes.index[sizes.lt(cutoff)] if len(sizes) else [])]}
    return {
        **groups, "median_customer_loans_bn": cutoff, "banks_with_size": len(sizes),
        "reading_vi": "Xếp ngân hàng theo trung vị dư nợ khách hàng của từng ngân hàng trong mẫu. Điểm chia là trung vị giữa các ngân hàng. Hệ số Quý 4 so với Quý 1 được ước lượng riêng cho từng nhóm.",
        "reading_en": "Rank banks by their own median customer-loan stock over the sample. Split at the median across banks. Estimate the Q4 effect relative to Q1 separately in each group.",
    }


def policy_robustness(panel, register):
    """Mark quarter-end eligibility from the documented restructuring cutoffs."""
    refs = {"14/2021/TT-NHNN", "02/2023/TT-NHNN", "06/2024/TT-NHNN"}
    windows = [item for item in _forbearance_timeline(register) if item["ref"] in refs]
    periods = pd.PeriodIndex(sorted(panel.period.unique()), freq="Q")
    end = periods.to_timestamp(how="end").normalize()
    active = np.zeros(len(periods), dtype=bool)
    for item in windows:
        active |= (end >= pd.Timestamp(item["effective_from"])) & (end <= pd.Timestamp(item["restructuring_until"]))
    flags = dict(zip(periods.astype(str), active.tolist())) if windows else {}
    data = _quarters(panel)
    terms = [*QUARTER_TERMS, "regime", *(f"{quarter}_regime" for quarter in QUARTER_TERMS)]
    design = data.assign(regime=data.period.map(flags).astype(float))
    for quarter in QUARTER_TERMS:
        design[f"{quarter}_regime"] = design[quarter] * design.regime
    effects = {
        "outside": ([{"Q4": 1.}], "two-sided"),
        "inside": ([{"Q4": 1., "Q4_regime": 1.}], "two-sided"),
        "difference": ([{"Q4_regime": 1.}], "two-sided"),
    }
    return {
        "windows": windows, "quarter_regime": flags,
        "interaction": _test_contrasts(design, terms, effects),
        "drop_2024": _fit(data.loc[data.year.ne(2024)], "d_npl_pct", QUARTER_TERMS, bank=True, bootstrap=True)[0],
        "reading_vi": "Đánh dấu quý có cơ chế giữ nguyên nhóm nợ còn hiệu lực tại ngày cuối quý. So sánh hệ số Quý 4 so với Quý 1 trong và ngoài các giai đoạn đó, rồi ước lượng lại khi bỏ năm 2024. So sánh này chưa xác định tác động của chính sách.",
        "reading_en": "Mark quarters where loan-group retention was in force at quarter end. Compare the Q4 effect relative to Q1 inside and outside those windows, and refit excluding 2024. This comparison does not identify a policy effect.",
    }


def _paired_changes(panel):
    columns = ["bank_code", "period", "quarter", "d_npl_pct"]
    data = panel[columns].sort_values(["bank_code", "period"]).copy()
    ordinal = pd.PeriodIndex(data.period, freq="Q").asi8
    data["ordinal"] = ordinal
    bank = data.groupby("bank_code", sort=False)
    consecutive = bank.ordinal.shift(-1).eq(data.ordinal + 1)
    data["next_change"] = bank.d_npl_pct.shift(-1).where(consecutive)
    data = data.dropna(subset=["d_npl_pct", "next_change"])
    return data.assign(rise=data.next_change.gt(0))


def _rise_rate(sample):
    n, rises = len(sample), int(sample.rise.sum())
    return {
        "n": n, "clusters": int(sample.bank_code.nunique()), "rises": rises,
        "share_pct": 100 * rises / n if n else None,
        "ci95": _bank_bootstrap_share(sample.rise, sample.bank_code),
        "mean_next_change_pp": float(sample.next_change.mean()) if n else None,
    }


def _compare_rises(first, second):
    """Resample the same whole-bank histories for both rates."""
    sample = pd.concat([first.assign(in_first=1), second.assign(in_first=0)], ignore_index=True)
    result = {"difference_pp": None, "ci95": None,
              "bank_fe": _fit(sample.assign(rise_pct=100 * sample.rise), "rise_pct", ["in_first"],
                              bank=True, bootstrap=True)[0]}
    if not len(first) or not len(second):
        return result
    result["difference_pp"] = float(100 * (first.rise.mean() - second.rise.mean()))
    groups = sample.groupby(["bank_code", "in_first"]).rise.agg(["sum", "size"]).unstack(fill_value=0)
    if len(groups) < 2:
        return result
    index = np.random.default_rng(BOOTSTRAP_SEED).integers(len(groups), size=(BOOTSTRAP_REPS, len(groups)))
    rates = []
    for label in (1, 0):
        numerator = groups["sum"][label].to_numpy()[index].sum(axis=1)
        denominator = groups["size"][label].to_numpy()[index].sum(axis=1)
        rates.append(np.divide(numerator, denominator, out=np.full(BOOTSTRAP_REPS, np.nan), where=denominator > 0))
    differences = 100 * (rates[0] - rates[1])
    valid = differences[np.isfinite(differences)]
    if len(valid):
        result["ci95"] = np.quantile(valid, [.025, .975]).tolist()
    return result


def rebound_baselines(panel):
    """Compare next-quarter rises with and without a preceding Q4 decline."""
    paired = _paired_changes(panel)
    q4 = paired.loc[paired.quarter.eq(4)]
    fell = q4.loc[q4.d_npl_pct.lt(0)]
    nonfall = q4.loc[q4.d_npl_pct.ge(0)]
    other = paired.loc[paired.quarter.ne(4) & paired.d_npl_pct.lt(0)]
    cutoff = float(fell.d_npl_pct.median()) if len(fell) else None
    large = fell.loc[fell.d_npl_pct.le(cutoff)] if cutoff is not None else fell
    small = fell.loc[fell.d_npl_pct.gt(cutoff)] if cutoff is not None else fell
    rates = {key: _rise_rate(group) for key, group in [
        ("any_q4", q4), ("q4_fell", fell), ("q4_not_fell", nonfall), ("other_quarter_fell", other),
        ("q4_large_fall", large), ("q4_small_fall", small),
    ]}
    contrasts = {
        "q4_fall_vs_nonfall": _compare_rises(fell, nonfall),
        "q4_fall_vs_other_fall": _compare_rises(fell, other),
        "q4_large_vs_small_fall": _compare_rises(large, small),
    }
    vi = "Dùng số gốc trước khi làm tròn để so tỷ lệ tăng ở quý kế tiếp sau khi Quý 4 giảm, Quý 4 không giảm và các quý khác giảm."
    en = "Use the source precision to compare next-quarter rises after Q4 falls, after Q4 holds or increases, and after falls in other quarters."
    a, b, c = (rates[key] for key in ("q4_fell", "q4_not_fell", "other_quarter_fell"))
    if a["n"] and b["n"] and c["n"]:
        vi += (f" Tỷ lệ lần lượt là {a['share_pct']:.1f}%, {b['share_pct']:.1f}% và {c['share_pct']:.1f}%.")
        en += (f" The rates are {a['share_pct']:.1f}%, {b['share_pct']:.1f}% and {c['share_pct']:.1f}%, respectively.")
        interval = contrasts["q4_fall_vs_nonfall"]["ci95"]
        if interval and interval[0] <= 0 <= interval[1]:
            vi += " Khoảng chênh lệch bao gồm 0. Tăng vào Quý 1 phù hợp với nhịp theo quý và chưa cho thấy hiệu ứng bù lại mức giảm Quý 4."
            en += " The difference interval spans zero. The Q1 rise fits a calendar pattern, with no evidence here of a distinct payback after Q4 falls."
    a, b = rates["q4_large_fall"], rates["q4_small_fall"]
    if a["n"] and b["n"]:
        vi += f" Với mức giảm lớn và nhỏ, tỷ lệ tăng lại lần lượt là {a['share_pct']:.1f}% và {b['share_pct']:.1f}%."
        en += f" After larger and smaller Q4 falls, the rise rates are {a['share_pct']:.1f}% and {b['share_pct']:.1f}%."
    return {
        **rates, "fall_median_pp": cutoff, "comparisons": contrasts,
        "reading_vi": vi, "reading_en": en,
    }


def _with_base_rate(entry, rate, baseline):
    entry.update(q1_rises=rate["rises"], q1_rise_pct=rate["share_pct"], q1_rise_ci95=rate["ci95"],
                 baseline_q1_rise_pct=baseline["share_pct"])


def add_rebound_baseline(rule, panel, decisions, baselines):
    """Use Q1 rises for the comparison alongside the existing opposite-sign outcome."""
    q4 = _paired_changes(panel).loc[lambda data: data.quarter.eq(4)]
    baseline = baselines["any_q4"]
    classified = q4.merge(decisions.loc[decisions.adjusted_change_pp.notna(),
                                       ["bank_code", "period", "status", "unusual", "d_npl_pct"]].rename(
        columns={"d_npl_pct": "decision_change"}), on=["bank_code", "period"], validate="one_to_one")
    holdout = rule["q4_oos"]
    held_period = holdout["scored_period"]
    held_base = _rise_rate(q4.loc[q4.period.eq(held_period)])
    for label, entry in rule["q4_backtest"].items():
        selected = classified.unusual.eq(True) if label == "unusual" else classified.status.eq(label)
        _with_base_rate(entry, _rise_rate(classified.loc[selected]), baseline)
        if label in holdout:
            sample = classified.loc[selected & classified.period.eq(held_period) & classified.decision_change.lt(0)]
            _with_base_rate(holdout[label], _rise_rate(sample), held_base)
    rule["q1_rise_baseline"] = baseline
    holdout["q1_rise_baseline"] = held_base
    vi = "Đối chiếu cùng biến cố tăng vào Quý 1 với mức nền sau mọi Quý 4, kể cả quý không giảm. Bảng giữ riêng tỷ lệ đảo chiều trái dấu."
    en = "Compare the same event, a Q1 rise, with the base rate after any Q4, including Q4s without declines. The table retains the separate opposite-sign reversal rate."
    rule["baseline_reading_vi"], rule["baseline_reading_en"] = vi, en
    holdout["baseline_reading_vi"], holdout["baseline_reading_en"] = vi, en


RAW_P_NAMES = ("p", "raw_p", "p_raw", "p_value", "pvalue", "cluster_p", "p_cluster")
WILD_P_NAMES = ("wild_p", "p_wild", "wild_pvalue", "wild_p_value", "p_wild_bootstrap", "wild_bootstrap_p")


def _valid_p(value):
    return isinstance(value, Real) and not isinstance(value, bool) and 0 <= value <= 1


def _pvalue_rows(value, path):
    if isinstance(value, dict):
        main = {}
        for key, item in value.items():
            if not _valid_p(item):
                continue
            if key in RAW_P_NAMES:
                column = "raw_p"
            elif key in WILD_P_NAMES:
                column = "wild_p"
            else:
                column = None
            if column and column not in main:
                main[column] = float(item)
            elif column or key.endswith(("_p", "_pvalue", "_p_value")) or key.startswith("p_"):
                label = key.removesuffix("_p").removeprefix("p_")
                yield {"test_id": f"{path}.{label}", (column or "raw_p"): float(item)}
        if main:
            yield {"test_id": path, **main}
        for key, item in value.items():
            yield from _pvalue_rows(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _pvalue_rows(item, f"{path}[{index}]")


def adjust_pvalues(models):
    """Apply one BH correction to every reported raw or wild p in M2 through M8."""
    rows = sorted(
        (row for number in range(2, 9) for key in [f"M{number}"]
         for row in _pvalue_rows(models.get(key), key)),
        key=lambda row: row["test_id"],
    )
    observed = [(row, column, row[column]) for row in rows for column in ("raw_p", "wild_p") if column in row]
    adjusted = stats.false_discovery_control([value for _, _, value in observed], method="bh") if observed else []
    for (row, column, _), value in zip(observed, adjusted):
        row[f"{column}_bh_adjusted"] = float(value)
    for row in rows:
        row.setdefault("raw_p", None)
        row.setdefault("wild_p", None)
        row["bh_adjusted"] = row.get("wild_p_bh_adjusted", row.get("raw_p_bh_adjusted"))
        row["reject_at_q"] = row["bh_adjusted"] <= .05
    return {
        "q": .05, "n_pvalues": len(observed), "rows": rows,
        "reading_vi": "Hiệu chỉnh Benjamini–Hochberg trên toàn bộ giá trị p được báo cáo trong M2–M8. Cột kết quả ưu tiên p wild bootstrap đã hiệu chỉnh nếu có.",
        "reading_en": "Apply Benjamini–Hochberg to all reported raw and wild p-values in M2–M8. The primary adjusted value is the wild-bootstrap result when available.",
    }
