"""Rule-based insight engine: generate candidate insights, attach evidence + a chart spec, rank them.

score = effect (0..1) × significance weight × business relevance
Every sentence uses association language; causal verbs are never used.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import fmt, stats
from .models import fit_drivers, what_if


def _lt(pv, a):
    return pv is not None and pv < a


def _sigw(pv):
    if pv is None:
        return 0.6
    return 1.0 if pv < 0.001 else 0.85 if pv < 0.01 else 0.7 if pv < 0.05 else 0.25


def _rel(cols, target, domain_metrics, geo, time):
    rel = 1.0 if target in cols else (0.85 if any(c in domain_metrics for c in cols) else 0.6)
    if geo in cols or time in cols:
        rel = min(1.1, rel + 0.1)
    return rel


def _mk(kind, title_en, title_vi, en, vi, value, test, effect, pv, rel, chart, evidence, cols, caveat=None):
    score = float(min(1.0, min(1.0, max(0.0, effect)) * _sigw(pv) * rel))
    return {"type": kind, "title_en": title_en, "title_vi": title_vi, "sentence_en": en, "sentence_vi": vi,
            "value": value, "test": test, "effect": stats.r(effect), "p_value": stats.r(pv), "relevance": stats.r(rel),
            "score": round(score, 4), "chart": chart, "evidence": evidence, "columns": cols, "caveat": caveat}


def segment_insights(df, target, cats, ctx):
    out = []
    for c in cats:
        res = stats.compare_groups(df, c, target)
        if not res:
            continue
        kw, tb = res["kruskal"], res["top_vs_bottom"]
        eps2 = kw["epsilon2"] or 0
        effect = max(min(1, eps2 / 0.14), min(1, abs(tb["rank_biserial"] or 0) / 0.6) * 0.8)
        top, bot = res["top"], res["bottom"]
        ratio = tb["median_ratio"]
        en = (f"Median {target} is highest in {c} = {top['group']} ({fmt.num(top['median'], target)}, n={top['n']}) and lowest in "
              f"{bot['group']} ({fmt.num(bot['median'], target)}, n={bot['n']})" + (f", a {ratio:.2f}× gap" if ratio else "") +
              f"; differences across {res['k_groups']} groups are {'statistically significant' if _lt(kw['p'], 0.05) else 'not significant'} "
              f"(Kruskal–Wallis H={kw['H']}, {fmt.p(kw['p'])}, ε²={eps2:.3f}).")
        vi = (f"Trung vị {target} cao nhất ở {c} = {top['group']} ({fmt.num(top['median'], target, 'vi')}, n={top['n']}) và thấp nhất ở "
              f"{bot['group']} ({fmt.num(bot['median'], target, 'vi')}, n={bot['n']})" + (f", chênh {ratio:.2f} lần".replace(".", ",") if ratio else "") +
              f"; khác biệt giữa {res['k_groups']} nhóm {'có ý nghĩa thống kê' if _lt(kw['p'], 0.05) else 'không có ý nghĩa thống kê'} "
              f"(Kruskal–Wallis H={kw['H']}, {fmt.p(kw['p'])}, ε²={eps2:.3f}).")
        meds = res["medians"]
        chart = {"kind": "bar", "x": list(meds.keys()), "series": [{"name": f"median {target}", "data": list(meds.values())}],
                 "x_label": c, "y_label": f"median {target}"}
        out.append(_mk("segment_gap", f"{target} differs by {c}", f"{target} khác biệt theo {c}", en, vi,
                       {"top_median": top["median"], "bottom_median": bot["median"], "ratio": ratio},
                       "Kruskal–Wallis + Mann–Whitney (top vs bottom)", effect, kw["p"],
                       _rel([c, target], target, ctx["domain_metrics"], ctx["geo"], ctx["time"]), chart, res, [c, target],
                       "Group differences can reflect composition (e.g. size, type) rather than the grouping itself."))
    return out


def trend_insights(df, target, time_col, ctx):
    if not time_col:
        return [], None
    additive = ctx["additive"]
    agg = "sum" if additive and ctx.get("panel_entities") is None else "median"
    ts = stats.time_series(df, time_col, target, agg=agg)
    pts = ts["points"]
    if len(pts) < 4:
        return [], ts
    periods = [p["period"] for p in pts]
    vals = [p["value"] for p in pts]
    tr = stats.trend_stats(periods, vals)
    ts["trend"] = tr
    out = []
    if tr:
        effect = min(1, abs(tr["total_change_pct"] or 0) / 50) * 0.6 + min(1, tr["r2"] or 0) * 0.4
        growth = f"CAGR {tr['cagr_pct']:.1f}%/period" if tr["cagr_pct"] is not None else f"slope {tr['slope_per_period']}/period"
        direction = "risen" if (tr["last"] or 0) > (tr["first"] or 0) else "fallen"
        en = (f"{agg.title()} {target} has {direction} from {fmt.num(tr['first'], target)} ({periods[0]}) to {fmt.num(tr['last'], target)} "
              f"({periods[-1]}), {fmt.pct(tr['total_change_pct'])} overall ({growth}); monotonic trend Spearman ρ={tr['spearman_rho']}, {fmt.p(tr['spearman_p'])}.")
        vi = (f"{target} ({agg}) {'tăng' if direction == 'risen' else 'giảm'} từ {fmt.num(tr['first'], target, 'vi')} ({periods[0]}) lên/xuống "
              f"{fmt.num(tr['last'], target, 'vi')} ({periods[-1]}), {fmt.pct(tr['total_change_pct'], 'vi')} toàn kỳ; xu hướng đơn điệu ρ={tr['spearman_rho']}, {fmt.p(tr['spearman_p'])}.")
        chart = {"kind": "line", "x": periods, "series": [{"name": f"{agg} {target}", "data": vals}], "x_label": time_col, "y_label": target}
        out.append(_mk("trend", f"Trend in {target}", f"Xu hướng {target}", en, vi, {"cagr_pct": tr["cagr_pct"], "total_change_pct": tr["total_change_pct"]},
                       "Spearman trend test + OLS slope", effect, tr["spearman_p"], _rel([target, time_col], target, ctx["domain_metrics"], ctx["geo"], ctx["time"]),
                       chart, tr, [time_col, target], "Aggregates over time can shift because the mix of records changes."))
        b = tr.get("break")
        if b and b["p"] is not None and b["p"] < 0.05:
            en = (f"The trend in {target} changes around {b['at']}: slope {b['slope_before']} per period before vs {b['slope_after']} after (Chow-type F={b['F']}, {fmt.p(b['p'])}).")
            vi = (f"Xu hướng {target} đổi chiều/tốc độ quanh {b['at']}: độ dốc {b['slope_before']}/kỳ trước so với {b['slope_after']}/kỳ sau (F={b['F']}, {fmt.p(b['p'])}).")
            out.append(_mk("trend_break", f"Trend break at {b['at']}", f"Điểm gãy xu hướng {b['at']}", en, vi, b, "piecewise-linear F test",
                           0.7, b["p"], _rel([target, time_col], target, ctx["domain_metrics"], ctx["geo"], ctx["time"]), chart, b, [time_col, target]))
        if tr["anomalies"]:
            a = tr["anomalies"][0]
            en = f"{len(tr['anomalies'])} period(s) deviate strongly from the trend in {target}, e.g. {a['period']} ({fmt.num(a['value'], target)}, robust z={a['robust_z']})."
            vi = f"{len(tr['anomalies'])} kỳ lệch mạnh khỏi xu hướng {target}, ví dụ {a['period']} ({fmt.num(a['value'], target, 'vi')}, z={a['robust_z']})."
            out.append(_mk("anomaly", f"Anomalous periods in {target}", f"Kỳ bất thường của {target}", en, vi, a, "robust z-score of detrended series (|z|>3)",
                           0.45, None, 0.8, chart, tr["anomalies"], [time_col, target]))
    fc = stats.forecast(periods, vals, horizon=3)
    if fc:
        ts["forecast"] = fc
        en = (f"A simple {fc['model']} extrapolation projects {target} at {fmt.num(fc['forecast'][0], target)} next period "
              f"(80% interval {fmt.num(fc['lower80'][0], target)}–{fmt.num(fc['upper80'][0], target)}); holdout MAE {fmt.num(fc['holdout_mae'][fc['model']], target)}.")
        vi = (f"Dự báo đơn giản ({fc['model']}): {target} kỳ tới khoảng {fmt.num(fc['forecast'][0], target, 'vi')} "
              f"(khoảng 80%: {fmt.num(fc['lower80'][0], target, 'vi')}–{fmt.num(fc['upper80'][0], target, 'vi')}).")
        chart = {"kind": "line", "x": periods + [f"+{i + 1}" for i in range(3)],
                 "series": [{"name": "actual", "data": vals + [None] * 3},
                            {"name": "forecast", "data": [None] * (len(vals) - 1) + [vals[-1]] + fc["forecast"]},
                            {"name": "lower80", "data": [None] * len(vals) + fc["lower80"]},
                            {"name": "upper80", "data": [None] * len(vals) + fc["upper80"]}],
                 "x_label": time_col, "y_label": target}
        out.append(_mk("forecast", f"Forecast of {target}", f"Dự báo {target}", en, vi, fc["forecast"][0], f"{fc['model']} (chosen by holdout MAE)",
                       0.45, None, 0.9, chart, fc, [time_col, target], fc["note"]))
    return out, ts


def concentration_insights(df, target, geo, ctx):
    out = []
    if not geo:
        return out
    if ctx["additive"]:
        s = df.groupby(geo)[target].sum()
        what_en, what_vi = f"total {target} is", f"tổng {target}"
    else:
        s = df.groupby(geo).size()
        what_en, what_vi = "records are", "số bản ghi"
    c = stats.concentration(s, pd.Series(s.index, index=s.index))
    if not c:
        return out
    en = (f"{what_en[0].upper() + what_en[1:]} concentrated: the top 20% of {geo} values ({max(1, int(np.ceil(0.2 * c['n'])))} of {c['n']}) hold "
          f"{c['top20_share'] * 100:.1f}% (Gini {c['gini']:.2f}, HHI {c['hhi']:.0f}); largest: {', '.join(c['top_labels'][:3])}.")
    vi = (f"{what_vi.capitalize()} tập trung: 20% {geo} đứng đầu ({max(1, int(np.ceil(0.2 * c['n'])))}/{c['n']}) chiếm "
          f"{c['top20_share'] * 100:.1f}% (Gini {c['gini']:.2f}, HHI {c['hhi']:.0f}); lớn nhất: {', '.join(c['top_labels'][:3])}.".replace(".", ",", 0))
    chart = {"kind": "bar", "x": c["top_labels"], "series": [{"name": "share", "data": c["top_shares"]}], "x_label": geo, "y_label": "share of total"}
    out.append(_mk("concentration", f"Concentration across {geo}", f"Mức độ tập trung theo {geo}", en, vi, c["top20_share"],
                   "Pareto share, Gini, HHI", min(1, max(0, c["gini"])), None, _rel([geo, target], target, ctx["domain_metrics"], ctx["geo"], ctx["time"]) * 0.9,
                   chart, c, [geo], "Concentration of listings/records reflects data coverage as well as the market itself."))
    return out


def correlation_insights(df, target, nums, ctx):
    res = stats.correlations(df, [target] + [c for c in nums if c != target], target=target)
    out = []
    for pr in [p for p in res["pairs"] if target in (p["a"], p["b"])][:3]:
        other = pr["b"] if pr["a"] == target else pr["a"]
        if abs(pr["rho"] or 0) < 0.15 or not _lt(pr["p_bonferroni"], 0.05):
            continue
        partial = res.get("partial_with_target", {}).get(other)
        caution = ""
        if partial is not None and abs(partial) < abs(pr["rho"]) * 0.5:
            caution = f" After controlling for the other numeric variables the (rank) partial correlation drops to {partial}, so much of it is shared with other factors."
        en = (f"{other} is {'positively' if pr['rho'] > 0 else 'negatively'} associated with {target} (Spearman ρ={pr['rho']}, Bonferroni-adjusted {fmt.p(pr['p_bonferroni'])}, n={pr['n']}).{caution} Association, not causation.")
        vi = (f"{other} có tương quan {'thuận' if pr['rho'] > 0 else 'nghịch'} với {target} (Spearman ρ={pr['rho']}, {fmt.p(pr['p_bonferroni'])} sau hiệu chỉnh Bonferroni, n={pr['n']}). Đây là tương quan, không phải nhân quả.")
        d = df[[other, target]].dropna()
        d = d.sample(min(400, len(d)), random_state=1)
        chart = {"kind": "scatter", "x": [stats.r(v) for v in d[other]], "series": [{"name": target, "data": [stats.r(v) for v in d[target]]}],
                 "x_label": other, "y_label": target}
        out.append(_mk("correlation", f"{other} vs {target}", f"{other} và {target}", en, vi, pr["rho"], "Spearman rank correlation (Bonferroni)",
                       min(1, abs(pr["rho"]) / 0.7), pr["p_bonferroni"], _rel([other, target], target, ctx["domain_metrics"], ctx["geo"], ctx["time"]),
                       chart, {**pr, "partial": partial}, [other, target], "Correlation does not imply causation; confounders are likely."))
    return out, res


def driver_insights(df, target, nums, cats, ctx):
    m = fit_drivers(df, target, nums, cats, exclude=ctx.get("exclude_from_drivers"))
    if not m:
        return [], None
    imp = [i for i in m["importance"] if (i["importance"] or 0) > 0][:5]
    if not imp:
        return [], m
    best = max(m["cv_r2"]["ridge_mean"] or -1, m["cv_r2"]["gb_mean"] or -1)
    coef = {c["feature"]: c for c in m["coefficients"]}
    names = ", ".join(f"{i['feature']} ({coef.get(i['feature'], {}).get('direction', '?')})" for i in imp[:3])
    en = (f"A model of {target} on {len(m['features'])} features explains {best * 100:.0f}% of out-of-sample variation (5-fold CV R², gradient boosting "
          f"{m['cv_r2']['gb_mean']}, ridge {m['cv_r2']['ridge_mean']}); the strongest associated drivers are {names} by permutation importance.")
    vi = (f"Mô hình {target} với {len(m['features'])} biến giải thích {best * 100:.0f}% biến động ngoài mẫu (R² kiểm định chéo 5 lần); "
          f"các yếu tố gắn mạnh nhất: {names} (permutation importance). Không phải quan hệ nhân quả.")
    chart = {"kind": "hbar", "x": [i["feature"] for i in imp], "series": [{"name": "permutation importance", "data": [i["importance"] for i in imp]}],
             "x_label": "feature", "y_label": "importance (drop in R²)"}
    out = [_mk("drivers", f"Drivers of {target}", f"Yếu tố gắn với {target}", en, vi, best, "Ridge + HistGradientBoosting, 5-fold CV, permutation importance",
               max(0, min(1, best)), None if best <= 0 else 0.0005, 1.0, chart, {k: m[k] for k in ("cv_r2", "importance", "leakage_excluded")}, [target] + [i["feature"] for i in imp],
               m["note"])]
    # strongest stable numeric what-if
    numeric_feats = [f for f in m["whatif"]["features"] if f["numeric"]]
    stable = [c for c in m["coefficients"] if c["stable"] and any(f["name"] == c["feature"] for f in numeric_feats)]
    if stable:
        f = stable[0]["feature"]
        w = what_if(m, f, 10)
        en = (f"Holding other features fixed, a 10% higher {f} is associated with {fmt.pct(w['target_change_pct'])} in {target} "
              f"(bootstrap 90% interval {fmt.pct(w['ci90_pct'][0])} to {fmt.pct(w['ci90_pct'][1])}).")
        vi = (f"Giữ các yếu tố khác cố định, {f} cao hơn 10% gắn với {target} thay đổi {fmt.pct(w['target_change_pct'], 'vi')} "
              f"(khoảng tin cậy bootstrap 90%: {fmt.pct(w['ci90_pct'][0], 'vi')} đến {fmt.pct(w['ci90_pct'][1], 'vi')}).")
        steps = [-20, -10, 0, 10, 20]
        ws = [what_if(m, f, s) for s in steps]
        chart = {"kind": "line", "x": [f"{s:+d}%" for s in steps], "series": [{"name": f"Δ {target} %", "data": [x["target_change_pct"] for x in ws]},
                 {"name": "low 90%", "data": [x["ci90_pct"][0] for x in ws]}, {"name": "high 90%", "data": [x["ci90_pct"][1] for x in ws]}],
                 "x_label": f"change in {f}", "y_label": f"change in {target} (%)"}
        out.append(_mk("what_if", f"What if {f} changes", f"Kịch bản thay đổi {f}", en, vi, w["target_change_pct"], "bootstrapped ridge (200 resamples)",
                       min(1, abs(w["target_change_pct"] or 0) / 10) * 0.8, 0.01, 0.95, chart, w, [f, target], w["interpretation"]))
    return out, m


def segmentation_insights(df, nums, target, ctx):
    seg = stats.segment(df, [target] + [c for c in nums if c != target])
    if not seg:
        return [], None
    labels = seg.pop("_labels")
    p0 = seg["profiles"]
    desc = "; ".join(f"cluster {p['cluster']} ({p['share'] * 100:.0f}%): " + ", ".join(f"{d['feature']} {'high' if d['z'] > 0 else 'low'}" for d in p["distinctive"][:2]) for p in p0[:3])
    en = f"k-means on {len(seg['features'])} scaled variables finds {seg['k']} segments (silhouette {seg['silhouette']}): {desc}."
    vi = f"Phân cụm k-means trên {len(seg['features'])} biến chuẩn hoá cho {seg['k']} nhóm (silhouette {seg['silhouette']}): " + desc.replace("high", "cao").replace("low", "thấp") + "."
    chart = {"kind": "bar", "x": [f"C{p['cluster']}" for p in p0], "series": [{"name": f"median {target}", "data": [p["medians"].get(target) for p in p0]}],
             "x_label": "segment", "y_label": f"median {target}"}
    ins = _mk("segmentation", f"{seg['k']} natural segments", f"{seg['k']} phân khúc tự nhiên", en, vi, seg["silhouette"], "k-means (k by silhouette)",
              min(1, (seg["silhouette"] or 0) / 0.5), None, 0.75, chart, seg, seg["features"], "Clusters are descriptive groupings, sensitive to the variables chosen.")
    seg["labels_index"] = labels
    return [ins], seg


def generate(df, roles, target, time_col, geo_col, domain_info, max_insights=12):
    nums = [c for c, r in roles.items() if r == "numeric" and df[c].notna().mean() > 0.3]
    cats = [c for c, r in roles.items() if r in ("category", "geo") and 2 <= df[c].nunique() <= 60 and not c.endswith("__province_2025")]
    if geo_col and geo_col not in cats and df[geo_col].nunique() >= 2:
        cats.insert(0, geo_col)
    tkey = target.lower()
    additive = not any(w in tkey for w in ["pct", "%", "per", "/m", "ratio", "rate", "margin", "gia", "price", "median", "mean", "avg", "index", "growth", "roe", "roa"])
    ctx = {"domain_metrics": set(domain_info.get("metrics", [])), "geo": geo_col, "time": time_col, "additive": additive,
           "panel_entities": geo_col, "exclude_from_drivers": domain_info.get("exclude_from_drivers", []),
           "skip_segments": domain_info.get("skip_segments", [])}
    cand, extras = [], {}
    cand += segment_insights(df, target, [c for c in cats if c not in ctx.get('skip_segments', ())][:8], ctx)
    t_ins, ts = trend_insights(df, target, time_col, ctx); cand += t_ins; extras["timeseries"] = ts
    cand += concentration_insights(df, target, geo_col, ctx)
    c_ins, corr = correlation_insights(df, target, [c for c in nums if c not in ctx['exclude_from_drivers']], ctx); cand += c_ins; extras["correlations"] = corr
    d_ins, model = driver_insights(df, target, nums, [c for c in cats if df[c].nunique() <= 40][:3], ctx); cand += d_ins; extras["drivers"] = model
    s_ins, seg = segmentation_insights(df, nums, target, ctx); cand += s_ins; extras["segments"] = seg
    # outlier share as a data-quality insight
    if "_outlier_any" in df:
        share = float(df["_outlier_any"].mean())
        if share > 0.02:
            cand.append(_mk("data_quality", "Extreme values present", "Có giá trị cực đoan",
                            f"{share * 100:.1f}% of rows carry at least one extreme value (robust z>3.5 or 3×IQR); medians and rank tests are used so results are robust to them.",
                            f"{share * 100:.1f}% dòng có ít nhất một giá trị cực đoan; báo cáo dùng trung vị và kiểm định hạng nên kết quả ít bị ảnh hưởng.".replace(".", ",", 1),
                            share, "robust z / IQR flags", min(1, share * 3), None, 0.5, None, {"outlier_share": stats.r(share)}, []))
    cand.sort(key=lambda x: -x["score"])
    # diversity: at most 3 per type
    seen, ranked = {}, []
    for c in cand:
        seen[c["type"]] = seen.get(c["type"], 0) + 1
        if seen[c["type"]] <= 3:
            ranked.append(c)
    for i, c in enumerate(ranked[:max_insights]):
        c["rank"] = i + 1
        c["id"] = f"I{i + 1}"
    return ranked[:max_insights], extras
