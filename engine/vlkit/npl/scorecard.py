"""Bank-quarter indicator system for the question behind a falling NPL ratio.

The asset-quality score is the mean of direction-adjusted percentile ranks inside
the quarter. It needs five of the eight asset-quality indicators. P/B is reported
and is not scored.
"""

import numpy as np
import pandas as pd

ASSET = (
    ("npl", "NPL (nhóm 3-5 / dư nợ)", "NPL (groups 3-5 / loans)", "ratio", "higher_worse", "FiinQuant screening, hoặc npl_pct khi thiếu nhóm nợ"),
    ("group2", "Nhóm 2 / dư nợ", "Group 2 / loans", "ratio", "higher_worse", "FiinQuant screening"),
    ("broad", "Nhóm 2-5 / dư nợ", "Groups 2-5 / loans", "ratio", "higher_worse", "FiinQuant screening"),
    ("severity", "Nhóm 5 / nhóm 3-5", "Group 5 / groups 3-5", "ratio", "higher_worse", "FiinQuant screening"),
    ("coverage", "Dự phòng / NPL", "Provisions / NPL", "ratio", "higher_better", "FiinQuant screening, hoặc coverage_pct khi thiếu số dư"),
    ("provisions_to_loans", "Dự phòng / dư nợ", "Provisions / loans", "ratio", "higher_better", "FiinQuant screening"),
    ("writeoff_proxy", "Dự phòng đã dùng / dư nợ đầu kỳ", "Provisions used / opening loans", "ratio", "higher_worse", "Dòng quý đã xác minh của provision_used_writeoff"),
    ("credit_cost", "Chi phí dự phòng / dư nợ bình quân", "Provision expense / average loans", "ratio", "higher_worse", "Dòng quý của provision_expense"),
)
OTHER = (
    ("nim", "NIM", "NIM", "ratio", "higher_better", "bank_quarter.nim_pct", False),
    ("ldr", "LDR", "LDR", "ratio", "higher_worse", "bank_quarter.ldr_pct", False),
    ("loan_growth_qoq", "Tăng trưởng dư nợ theo quý", "Quarter-on-quarter loan growth", "ratio", "higher_faster", "FiinQuant loans_customer", False),
    ("pb", "P/B", "P/B", "times", "not_scored", "valuation_daily, phiên cuối quý", False),
)
ASSET_IDS = [item[0] for item in ASSET]
CATALOG = [
    {"id": name, "name_vi": vi, "name_en": en, "unit": unit, "direction": direction, "source": source, "scored": True}
    for name, vi, en, unit, direction, source in ASSET
] + [
    {"id": name, "name_vi": vi, "name_en": en, "unit": unit, "direction": direction, "source": source, "scored": scored}
    for name, vi, en, unit, direction, source, scored in OTHER
]
POINT_FIELDS = {
    "loans_customer": "loans", "group_2_watch": "g2_stock", "group_3_substandard": "g3",
    "group_4_doubtful": "g4", "group_5_loss": "g5", "groups_3_5": "npl_reported",
    "provision_total": "provision_total", "provision_balance_sheet": "provision_bs",
    "provision_closing": "provision_close",
}
FLOW_FIELDS = ("provision_used_writeoff", "provision_expense")
MIN_ASSET = 5


def _num(value):
    if value is None or not np.isfinite(value):
        return None
    return float(value)


def _better(series, direction):
    valid = series.dropna()
    out = pd.Series(np.nan, index=series.index, dtype=float)
    if len(valid) < 2 or direction == "not_scored":
        return out
    ranked = valid.rank(method="average", pct=True)
    if direction in {"higher_worse"}:
        ranked = 1 - ranked
    out.loc[valid.index] = ranked
    return out


def _direction(name):
    return next(item["direction"] for item in CATALOG if item["id"] == name)


def _pca(block):
    scores = pd.Series(np.nan, index=block.index, dtype=float)
    usable = block.dropna(axis=1, thresh=3)
    filled = usable.dropna()
    if usable.shape[1] < 2 or len(filled) < 3:
        return scores
    standard = (filled - filled.mean()) / filled.std(ddof=0).replace(0, np.nan)
    standard = standard.dropna(axis=1)
    if standard.shape[1] < 2:
        return scores
    _, _, vt = np.linalg.svd(standard.to_numpy(dtype=float), full_matrices=False)
    component = standard.to_numpy(dtype=float) @ vt[0]
    anchor = filled.mean(axis=1).to_numpy(dtype=float)
    if len(component) >= 3 and np.std(component) > 0 and np.std(anchor) > 0:
        if np.corrcoef(component, anchor)[0, 1] < 0:
            component = -component
    scores.loc[standard.index] = component
    return scores


def summarize(frame):
    """Rank one indicator table. `frame` already holds the ratios, not the raw stocks."""
    data = frame.copy()
    if "d_npl" not in data:
        data["d_npl"] = np.nan
    percentiles = pd.DataFrame(index=data.index)
    for item in CATALOG:
        column = item["id"]
        if column not in data:
            data[column] = np.nan
        percentiles[column] = data.groupby("period", sort=False)[column].transform(
            lambda series, direction=item["direction"]: _better(series, direction))
    asset = percentiles[ASSET_IDS]
    data["n_asset"] = asset.notna().sum(axis=1)
    data["composite"] = asset.mean(axis=1).where(data["n_asset"].ge(MIN_ASSET))
    data["pca"] = np.nan
    for _, index in data.groupby("period", sort=False).groups.items():
        data.loc[index, "pca"] = _pca(asset.loc[index]).to_numpy()
    rows = []
    for row, pct in zip(data.itertuples(index=False), percentiles.itertuples(index=False)):
        values = {item["id"]: _num(getattr(row, item["id"])) for item in CATALOG}
        ranks = {item["id"]: _num(getattr(pct, item["id"])) for item in CATALOG}
        composite = _num(row.composite)
        rows.append({
            "bank_code": row.bank_code, "period": str(row.period), "values": values, "percentiles": ranks,
            "n_asset": int(row.n_asset), "composite": composite, "pca": _num(row.pca),
            "composite_status": "đủ" if composite is not None else "Thiếu dữ liệu",
        })
    by_quarter, gaps = [], {"2025Q4": [], "latest": []}
    scored = data.loc[data.composite.notna(), ["bank_code", "period", "npl", "composite"]].copy()
    latest = None if scored.empty else str(scored.period.max())
    for period, block in scored.groupby("period", sort=False):
        places = block.copy()
        places["npl_place"] = places.npl.rank(ascending=True, method="min")
        places["composite_place"] = places.composite.rank(ascending=False, method="min")
        spearman = None
        if len(places) >= 3 and places.npl.nunique() > 1 and places.composite.nunique() > 1:
            spearman = _num(places.npl_place.corr(places.composite_place, method="spearman"))
        by_quarter.append({"period": str(period), "n": int(len(places)), "spearman": spearman})
        movers = []
        pct = percentiles.loc[places.index]
        for item, pct_row in zip(places.itertuples(index=False), pct.itertuples(index=False)):
            shift = float(item.composite_place - item.npl_place)
            if abs(shift) < 5:
                continue
            better = shift > 0
            npl_pct = getattr(pct_row, "npl")
            drivers = []
            for name in ASSET_IDS:
                if name == "npl" or not np.isfinite(getattr(pct_row, name)) or not np.isfinite(npl_pct):
                    continue
                if better and getattr(pct_row, name) < npl_pct - 0.10:
                    drivers.append(name)
                if not better and getattr(pct_row, name) > npl_pct + 0.10:
                    drivers.append(name)
            movers.append({
                "bank_code": item.bank_code, "period": str(period),
                "npl_place": int(item.npl_place), "composite_place": int(item.composite_place),
                "places": int(abs(shift)),
                "direction": "npl_looks_better" if better else "npl_looks_worse",
                "drivers": drivers,
            })
        if str(period) == "2025Q4":
            gaps["2025Q4"] = movers
        if str(period) == latest:
            gaps["latest"] = movers
    by_quarter.sort(key=lambda item: item["period"])
    ordered = data.sort_values(["bank_code", "period"])
    ordinal = pd.PeriodIndex(ordered.period.astype(str), freq="Q").asi8
    ordered = ordered.assign(_ord=ordinal)
    ordered["prev_composite"] = ordered.groupby("bank_code").composite.shift().where(
        ordered.groupby("bank_code")._ord.diff().eq(1))
    compared = ordered.loc[ordered.d_npl.lt(0) & ordered.composite.notna() & ordered.prev_composite.notna()]
    worsened = int(compared.composite.lt(compared.prev_composite).sum())
    n_fell = int(len(compared))
    disagreement = {"n_fell": n_fell, "n_worsened": worsened,
                    "share": None if not n_fell else worsened / n_fell}
    loo = {}
    full_place = scored.copy()
    if len(full_place):
        full_place["place"] = full_place.groupby("period").composite.rank(ascending=False, method="min")
    for name in ASSET_IDS:
        kept = [item for item in ASSET_IDS if item != name]
        count = asset[kept].notna().sum(axis=1)
        alt = asset[kept].mean(axis=1).where(count.ge(MIN_ASSET))
        moves = 0
        if len(full_place):
            paired = full_place.assign(alt=alt).dropna(subset=["alt"])
            if len(paired):
                paired["alt_place"] = paired.groupby("period").alt.rank(ascending=False, method="min")
                moves = int((paired.alt_place - paired.place).abs().ge(5).sum())
        loo[name] = {"rank_moves_ge_5": moves}
    pca_spearman = None
    both = data.loc[data.composite.notna() & data.pca.notna()]
    if len(both) >= 3 and both.composite.nunique() > 1 and both.pca.nunique() > 1:
        pca_spearman = _num(both.composite.corr(both.pca, method="spearman"))
    share = disagreement["share"]
    share_vi = "không đủ cặp" if share is None else f"{100 * share:.1f}%"
    share_en = "too few pairs" if share is None else f"{100 * share:.1f}%"
    n_2025 = len(gaps["2025Q4"])
    n_latest = len(gaps["latest"])
    latest_label = latest or "chưa có"
    reading_vi = (
        f"Điểm chất lượng tài sản là trung bình thứ bậc trong quý, đã chỉnh chiều, và cần ít nhất 5/8 chỉ tiêu. "
        f"Ở các ngân hàng-quý mà NPL giảm và cả hai quý đều có điểm, điểm tổng xấu đi trong {share_vi} trường hợp "
        f"({worsened}/{n_fell}). 2025Q4 có {n_2025} ngân hàng lệch ít nhất 5 bậc giữa hạng NPL và hạng điểm tổng; "
        f"quý mới nhất ({latest_label}) có {n_latest}."
    )
    reading_en = (
        f"The asset-quality score is the within-quarter mean of direction-adjusted percentile ranks and needs at least 5 of 8 indicators. "
        f"Where NPL fell and both quarters have a score, the score worsened in {share_en} of cases ({worsened}/{n_fell}). "
        f"2025Q4 has {n_2025} banks whose NPL rank and score rank differ by at least 5 places; "
        f"the latest quarter ({latest_label}) has {n_latest}."
    )
    return {
        "indicators": CATALOG, "rows": rows, "by_quarter": by_quarter, "rank_gaps": gaps,
        "disagreement": disagreement, "sensitivity": {"pca_spearman": pca_spearman, "leave_one_out": loo},
        "reading_vi": reading_vi, "reading_en": reading_en,
        "what_this_does_not_show_vi": "Điểm này không phải xếp hạng tín nhiệm và không chứng minh chất lượng tín dụng đã tốt hơn. P/B chỉ để xem bối cảnh, không vào điểm.",
        "what_this_does_not_show_en": "This score is not a credit rating and does not show that credit quality improved. P/B is context and is not scored.",
    }


def _stocks(screening):
    if screening is None or len(screening) == 0:
        return pd.DataFrame(columns=["bank_code", "period"])
    data = screening.copy()
    data["bank_code"] = data["bank"].astype("string").str.strip().str.upper().replace({"BIDV": "BID"})
    point = data.loc[data.flow_basis.eq("point") & data.field.isin(POINT_FIELDS)]
    wide = point.pivot_table(index=["bank_code", "period"], columns="field", values="value_vnd_bn", aggfunc="first")
    wide = wide.rename(columns=POINT_FIELDS).reset_index()
    flows = data.loc[data.flow_basis.eq("quarterly") & data.field.isin(FLOW_FIELDS)]
    if len(flows):
        flow_wide = flows.pivot_table(index=["bank_code", "period"], columns="field", values="value_vnd_bn", aggfunc="first")
        wide = wide.merge(flow_wide.reset_index(), on=["bank_code", "period"], how="left")
    return wide


def _ratios(wide):
    if "loans" not in wide:
        wide["loans"] = np.nan
    for name in ("g2_stock", "g3", "g4", "g5", "npl_reported", "provision_total", "provision_bs", "provision_close"):
        if name not in wide:
            wide[name] = np.nan
    parts = wide[["g3", "g4", "g5"]]
    complete = parts.notna().all(axis=1)
    wide["npl_stock"] = parts.sum(axis=1).where(complete, wide["npl_reported"])
    loans = wide["loans"].replace(0, np.nan)
    wide["npl"] = wide["npl_stock"] / loans
    wide["group2"] = wide["g2_stock"] / loans
    wide["broad"] = (wide["npl_stock"] + wide["g2_stock"]) / loans
    wide["severity"] = wide["g5"] / wide["npl_stock"].replace(0, np.nan)
    provision = wide["provision_total"].fillna(wide["provision_bs"]).fillna(wide["provision_close"])
    wide["coverage"] = provision / wide["npl_stock"].replace(0, np.nan)
    wide["provisions_to_loans"] = provision / loans
    ordered = wide.sort_values(["bank_code", "period"]).copy()
    ordinal = pd.PeriodIndex(ordered.period.astype(str), freq="Q").asi8
    ordered["_ord"] = ordinal
    previous = ordered.groupby("bank_code").loans.shift().where(ordered.groupby("bank_code")._ord.diff().eq(1))
    used = ordered["provision_used_writeoff"] if "provision_used_writeoff" in ordered else np.nan
    expense = ordered["provision_expense"] if "provision_expense" in ordered else np.nan
    ordered["writeoff_proxy"] = used / previous.replace(0, np.nan)
    ordered["credit_cost"] = expense / ((previous + ordered.loans) / 2).replace(0, np.nan)
    ordered["loan_growth_qoq"] = ordered.loans / previous.replace(0, np.nan) - 1
    return ordered.drop(columns="_ord")


def _valuation(valuation):
    if valuation is None or len(valuation) == 0 or "pb" not in valuation:
        return pd.DataFrame(columns=["bank_code", "period", "pb"])
    data = valuation.copy()
    data["bank_code"] = data["ticker"].astype("string").str.strip().str.upper().replace({"BIDV": "BID"})
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date", "pb"])
    data["period"] = data.date.dt.to_period("Q").astype(str)
    last = data.sort_values("date").groupby(["bank_code", "period"], sort=False).tail(1)
    return last[["bank_code", "period", "pb"]]


def publish_audit(screening, notes):
    """Comparable PDF matches are the headline. Every overlapping row stays as the secondary count."""
    from .ingest.fiin_screening import audit

    empty = {"headline": {"matched": 0, "comparable": 0, "rate": None},
             "all_rows": {"matched": 0, "rows": 0, "rate": None}}
    summary = empty
    if screening is not None and notes is not None and len(screening) and len(notes):
        summary, _ = audit(screening, notes)
    headline, all_rows = summary["headline"], summary["all_rows"]

    def text(block, numerator, denominator):
        if block["rate"] is None:
            return "chưa có cặp", "no pairs"
        shown = f"{100 * block['rate']:.1f}% ({block[numerator]}/{block[denominator]})"
        return shown, shown

    main_vi, main_en = text(headline, "matched", "comparable")
    side_vi, side_en = text(all_rows, "matched", "rows")
    return {
        "headline": headline, "all_rows": all_rows,
        "reading_vi": (f"Số chính của đối chiếu PDF là các dòng so được (hợp nhất, grade single hoặc verified): {main_vi}. "
                       f"Toàn bộ dòng chồng lấn, kể cả dòng không so được, là {side_vi}."),
        "reading_en": (f"The PDF audit headline is the comparable rows only (consolidated, grade single or verified): {main_en}. "
                       f"The secondary count, every overlapping row, is {side_en}."),
    }


def build_scorecard(panel, screening, valuation, register):
    """One row per bank-quarter. `register` is accepted so the caller can pass the legal table; the score does not use it."""
    del register
    base = panel[["bank_code", "period"]].drop_duplicates().copy()
    base["period"] = base["period"].astype(str)
    for source, target, scale in (
        ("npl_pct", "panel_npl", 100), ("coverage_pct", "panel_coverage", 100),
        ("nim_pct", "nim", 100), ("ldr_pct", "ldr", 100), ("d_npl_pct", "d_npl", 100),
    ):
        base[target] = panel[source] / scale if source in panel else np.nan
    ratios = _ratios(_stocks(screening))
    keep = ["bank_code", "period", "npl", "group2", "broad", "severity", "coverage",
            "provisions_to_loans", "writeoff_proxy", "credit_cost", "loan_growth_qoq"]
    if len(ratios):
        base = base.merge(ratios[[column for column in keep if column in ratios]], on=["bank_code", "period"], how="left")
    for column in keep:
        if column not in base:
            base[column] = np.nan
    base["npl"] = base["npl"].fillna(base["panel_npl"])
    base["coverage"] = base["coverage"].fillna(base["panel_coverage"])
    if "d_npl" not in base or base["d_npl"].isna().all():
        ordered = base.sort_values(["bank_code", "period"])
        ordinal = pd.PeriodIndex(ordered.period.astype(str), freq="Q").asi8
        ordered = ordered.assign(_ord=ordinal)
        base["d_npl"] = ordered.groupby("bank_code").npl.diff().where(
            ordered.groupby("bank_code")._ord.diff().eq(1)).to_numpy()
    prices = _valuation(valuation)
    if len(prices):
        base = base.merge(prices, on=["bank_code", "period"], how="left")
    else:
        base["pb"] = np.nan
    return summarize(base)
