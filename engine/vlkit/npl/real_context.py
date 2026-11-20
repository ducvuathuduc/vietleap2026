"""Financial statement mechanism and external context for the consolidated panel."""

import numpy as np
import pandas as pd

from .ingest.extra_wdi import COUNTRIES
from .real_data import _bank_code
from .real_models import _fit


NOTES_FIELDS = {
    "customer_loans": ("customer_loans", "loans_customer", "total_loans", "loans_total", "loans",
                       "loans_vnd_bn", "loans_customer_bn_vnd"),
    "group2_loans": ("group2_loans", "group_2_loans", "loans_group_2", "group2", "group_2", "group2_vnd_bn",
                     "npl_group_2_watch", "group_2_watch"),
    "groups345_loans": ("groups345_loans", "groups_3_5", "loans_groups_3_5", "group345", "group_345", "npl",
                        "npl_vnd_bn"),
    "group3": ("group3", "group_3", "loans_group_3", "npl_group_3_substandard", "group_3_substandard"),
    "group4": ("group4", "group_4", "loans_group_4", "npl_group_4_doubtful", "group_4_doubtful"),
    "group5": ("group5", "group_5", "loans_group_5", "npl_group_5_loss", "group_5_loss"),
    "provision_balance": ("provision_balance", "provision_end", "provision_closing", "provisions_closing",
                          "closing_provision", "provision", "provision_vnd_bn", "provision_balance_bn_vnd"),
    "writeoffs": ("writeoffs", "write_offs", "write_off", "writeoff", "writeoff_vnd_bn", "quarterly_writeoffs",
                  "writeoff_period"),
}
# Effective dates and restructuring cutoffs as stated in the texts. Amendments
# can supersede an earlier cutoff, which is distinct from the document's expiry.
FORBEARANCE_DOCS = {
    "01/2020/TT-NHNN": ("Cơ cấu nợ và giữ nguyên nhóm nợ do COVID-19", "2020-03-13", None,
                        "https://congbao.chinhphu.vn/van-ban/thong-tu-so-01-2020-tt-nhnn-30958.htm"),
    "03/2021/TT-NHNN": ("Sửa đổi cơ chế cơ cấu nợ do COVID-19", "2021-05-17", "2021-12-31",
                        "https://vbpl.vn/Toaannhandantoicao/Pages/vbpq-toanvan.aspx?ItemID=147215"),
    "14/2021/TT-NHNN": ("Gia hạn cơ cấu nợ do COVID-19", "2021-09-07", "2022-06-30",
                        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2021/09/12nhnn.signed.pdf"),
    "02/2023/TT-NHNN": ("Cơ cấu nợ và giữ nguyên nhóm nợ cho khách hàng gặp khó khăn", "2023-04-24", "2024-06-30",
                        "https://congbao.chinhphu.vn/van-ban/thong-tu-so-02-2023-tt-nhnn-39232.htm"),
    "06/2024/TT-NHNN": ("Gia hạn cơ cấu nợ theo Thông tư 02/2023", "2024-06-18", "2024-12-31",
                        "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/7/06-nhnn.pdf"),
}


def _forbearance_timeline(register):
    if register is None:
        return []
    entries = {}
    for row in register.itertuples(index=False):
        ref = "03/2021/TT-NHNN" if row.ref == "03/2020/TT-NHNN" else row.ref
        if ref not in FORBEARANCE_DOCS or (ref in entries and ref != row.ref):
            continue
        title, start, cutoff, url = FORBEARANCE_DOCS[ref]
        entries[ref] = {"ref": ref, "title": title, "effective_from": start, "restructuring_until": cutoff,
                        "url": url, "register_ref": row.ref, "register_effective_from": row.effective_from,
                        "register_effective_to": row.effective_to, "register_url": row.url}
    return sorted(entries.values(), key=lambda row: row["effective_from"])


def statement_amounts(notes, tcb=None):
    """Resolve statement fields by verification grade and preserve their sources."""
    keys = ["bank_code", "period", "source"]
    aliases = {alias: field for field, names in NOTES_FIELDS.items() for alias in names}
    inputs = []
    if notes is not None and not notes.empty:
        basis = notes["basis"].astype("string").str.strip().str.lower()
        scope = notes.get("statement_type", pd.Series(pd.NA, index=notes.index, dtype="string"))
        consolidated = scope.astype("string").str.strip().str.lower().eq("consolidated")
        writeoff = notes["field"].astype("string").str.strip().str.lower().isin(NOTES_FIELDS["writeoffs"])
        quarterly = (basis.eq("point") & ~writeoff) | (basis.eq("quarterly") & writeoff)
        accepted = basis.eq("consolidated") | (consolidated & quarterly)
        data = notes.loc[accepted & notes.grade.isin(["verified", "single"])].copy()
        data = data.rename(columns={"bank": "bank_code", "value_vnd_bn": "value"})
        data["priority"] = data.grade.eq("verified").astype(int)
        inputs.append(data.assign(source="notes_bank_quarter"))
    if tcb is not None and not tcb.empty:
        # The case extractor's provision-used value does not identify a quarterly write-off.
        case = tcb.rename(columns={"quarter": "period", "metric": "field", "value_bn_vnd": "value",
                                   "url": "source_url"})
        case = case.loc[case["field"].isin(aliases)]
        case = case.loc[case.groupby("period")["source_url"].transform("nunique").eq(1)]
        inputs.append(case.assign(bank_code="TCB", source="case_tcb", priority=0))

    amounts = pd.DataFrame(columns=[*keys, *NOTES_FIELDS])
    used = pd.DataFrame(columns=[*keys, "field", "value", "page", "source_url"])
    if inputs:
        long = pd.concat(inputs, ignore_index=True)
        long["bank_code"] = _bank_code(long["bank_code"])
        long["period"] = long["period"].astype("string").str.strip().str.upper()
        long["field"] = long["field"].astype("string").str.strip().str.lower().map(aliases)
        long["value"] = pd.to_numeric(long["value"], errors="coerce").replace([np.inf, -np.inf], np.nan)
        signed_amount = long.field.isin(["writeoffs", "provision_balance"])
        long.loc[signed_amount, "value"] = long.loc[signed_amount, "value"].abs()
        long = long.loc[long.period.str.fullmatch(r"\d{4}Q[1-4]", na=False) & long.value.ge(0)]
        if "page" not in long:
            long["page"] = None
        if "source_url" not in long:
            long["source_url"] = None
        long["page"] = pd.to_numeric(long["page"], errors="coerce")
        long = long.loc[long.page.gt(0) & long.source_url.astype("string").str.match(r"^https?://", na=False)]
        fields = [*keys, "field"]
        long = long.dropna(subset=fields + ["source_url"])
        long = long.loc[long["priority"].eq(long.groupby(fields)["priority"].transform("max"))]
        unambiguous = long.groupby(fields)["value"].transform("nunique").eq(1)
        provenance_columns = [column for column in ["basis", "statement_type", "grade", "reader", "raw_sha256"]
                              if column in long]
        used = long.loc[unambiguous, [*fields, "value", "page", "source_url", *provenance_columns]].drop_duplicates()
        if not used.empty:
            amounts = used.drop_duplicates(fields).pivot(index=keys, columns="field", values="value").reset_index()
            amounts = amounts.reindex(columns=[*keys, *NOTES_FIELDS])

    amounts = amounts.sort_values(keys).reset_index(drop=True)
    amounts[list(NOTES_FIELDS)] = amounts[list(NOTES_FIELDS)].astype(float)
    amounts["customer_loans"] = amounts["customer_loans"].where(amounts["customer_loans"].gt(0))
    parts = amounts[["group3", "group4", "group5"]].sum(axis=1, min_count=3)
    amounts["groups345_loans"] = amounts["groups345_loans"].fillna(parts)
    return amounts, used


def mechanism(notes, tcb):
    """Use reported statement amounts with an unbroken quarterly reporting basis."""
    amounts, used = statement_amounts(notes, tcb)
    keys = ["bank_code", "period", "source"]
    amounts["group2_ratio_pct"] = 100 * amounts["group2_loans"] / amounts["customer_loans"]
    period = pd.PeriodIndex(amounts.period, freq="Q")
    amounts["ordinal"] = period.asi8
    group = amounts.groupby(["bank_code", "source"])
    consecutive = group.ordinal.diff().eq(1)
    amounts["loan_growth_qoq_pct"] = (100 * group.customer_loans.pct_change(fill_method=None)).where(consecutive)
    amounts["npl_formation_bn"] = (group.groups345_loans.diff() + amounts["writeoffs"]).where(consecutive)

    annual = amounts.assign(year=period.year, quarter=period.quarter)
    complete = annual.groupby(["bank_code", "source", "year"])["writeoffs"].agg(n="count", total="sum").reset_index()
    q4 = annual.loc[annual.quarter.eq(4), ["bank_code", "source", "year", "writeoffs"]].merge(complete)
    q4 = q4.loc[q4.n.eq(4) & q4.total.gt(0)].copy()
    q4["q4_share_pct"] = 100 * q4["writeoffs"] / q4["total"]
    metrics = ["npl_formation_bn", "group2_ratio_pct", "loan_growth_qoq_pct"]
    usable = amounts[metrics].notna().any(axis=1) | amounts["writeoffs"].notna()
    quarterly = amounts.loc[usable, [*keys, *metrics, "writeoffs"]]
    cover = quarterly.groupby(["bank_code", "source"]).period.agg(n="size", start="min", end="max")
    labels = {"Q3": "before_q4", "Q4": "q4", "Q1": "after_q4"}
    windows = quarterly.loc[quarterly.period.str[-2:].isin(labels)].copy()
    windows["position"] = windows.period.str[-2:].map(labels)
    windows["q4_year"] = windows.period.str[:4].astype(int) - windows.position.eq("after_q4").astype(int)
    group_keys = ["bank_code", "source", "q4_year"]
    window_years = windows.loc[windows.position.eq("q4"), group_keys]
    windows = windows.merge(window_years, on=group_keys, how="inner")
    return {
        "quarterly": quarterly.to_dict("records"),
        "q4_windows": windows.to_dict("records"),
        "annual_writeoffs": q4.rename(columns={"writeoffs": "q4_writeoffs_bn", "total": "annual_writeoffs_bn"})
        .to_dict("records"),
        "provenance": used.drop(columns="value").to_dict("records"),
        "coverage": {"n": len(quarterly), "banks": sorted(quarterly.bank_code.unique()),
                     "period": [quarterly.period.min(), quarterly.period.max()] if len(quarterly) else None,
                     "by_bank_source": cover.reset_index().to_dict("records"),
                     "n_by_metric": {metric: int(quarterly[metric].count()) for metric in [*metrics, "writeoffs"]}},
        "inference": "descriptive statement values; no sampling interval",
        "reading_vi": ("Với các BCTC đủ dữ liệu, đọc dòng phát sinh nợ xấu ròng trước xóa nợ, tỷ trọng xóa nợ Quý 4 "
                       "và tỷ lệ nhóm 2 cùng tăng trưởng dư nợ từng quý." if len(quarterly)
                       else "Chưa có ghi chú BCTC đủ trường để tính các chỉ tiêu cơ chế."),
        "reading_en": ("For covered statements, read net NPL formation before write-offs, Q4 write-off share, "
                       "and the group 2 ratio alongside quarterly loan growth." if len(quarterly)
                       else "No financial statement notes have enough fields to calculate the mechanism metrics."),
        "does_not_show_vi": "Phát sinh ròng còn phản ánh thu hồi và chuyển nhóm, và kết quả chỉ áp dụng cho ngân hàng và quý có dữ liệu.",
        "does_not_show_en": "Net formation can include recoveries and reclassifications, and the results apply only to the covered banks and quarters.",
    }


def policy_context(panel, wdi, legal):
    """Compare annual WDI observations and display the legal register beside annual seasonality."""
    fields = ["iso3", "country", "year", "npl_to_gross_loans_pct"]
    external = pd.DataFrame(columns=fields) if wdi is None else wdi[fields].copy()
    external["npl_to_gross_loans_pct"] = pd.to_numeric(external["npl_to_gross_loans_pct"], errors="coerce")
    external["year"] = pd.to_numeric(external["year"], errors="coerce")
    external = external.loc[external.iso3.isin(COUNTRIES) & external.npl_to_gross_loans_pct.between(0, 100)]
    external = external.dropna(subset=["year"]).drop_duplicates().sort_values(["year", "iso3"])
    if external.duplicated(["iso3", "year"]).any():
        raise ValueError("WDI has conflicting country-year observations")
    external["year"] = external["year"].astype(int)
    by_year = []
    for year, group in external.groupby("year"):
        vn = group.loc[group.iso3.eq("VNM"), "npl_to_gross_loans_pct"]
        peers = group.loc[group.iso3.ne("VNM"), "npl_to_gross_loans_pct"]
        by_year.append({"year": int(year), "n": len(group), "n_peers": len(peers),
                        "vietnam_npl_pct": vn.item() if len(vn) else None,
                        "asean_peer_median_pct": peers.median() if len(peers) else None,
                        "asean_peer_range_pct": [peers.min(), peers.max()] if len(peers) else None})
    latest = next((row for row in reversed(by_year) if row["vietnam_npl_pct"] is not None and row["n_peers"]), None)
    if latest:
        year, vn, peers, median = (latest[key] for key in ["year", "vietnam_npl_pct", "n_peers", "asean_peer_median_pct"])
        wdi_vi = (f"Năm {year}, tỷ lệ nợ xấu Việt Nam là {vn:.2f}%, so với trung vị {median:.2f}% của "
                  f"{peers} nước ASEAN có số cùng năm trong bảng WDI Silver.")
        wdi_en = (f"In {year}, Viet Nam's NPL ratio was {vn:.2f}%, versus a median of {median:.2f}% "
                  f"across the {peers} ASEAN peers with data for that year in the WDI Silver table.")
    else:
        wdi_vi = "Chưa có năm mà cả Việt Nam và ít nhất một nước ASEAN có số liệu NPL để so sánh."
        wdi_en = "No year has NPL data for both Viet Nam and at least one ASEAN peer."
    timeline = _forbearance_timeline(legal)
    yearly = []
    for year, data in panel.groupby("year"):
        pairs = data.loc[data.quarter.isin([1, 4])].dropna(subset=["d_npl_pct"]).copy()
        pairs = pairs.loc[pairs.groupby("bank_code")["quarter"].transform("nunique").eq(2)]
        fit, _ = _fit(pairs.assign(Q4=pairs.quarter.eq(4)), "d_npl_pct", ["Q4"], bank=True)
        yearly.append({"year": int(year), **fit})
    return {
        "wdi": {"indicator": "FB.AST.NPER.ZS", "n": len(external),
                "period": [int(external.year.min()), int(external.year.max())] if len(external) else None,
                "observations": external.to_dict("records"), "by_year": by_year, "latest_comparison": latest,
                "inference": "published annual observations and descriptive peer ranges; no sampling interval",
                "reading_vi": wdi_vi, "reading_en": wdi_en,
                "does_not_show_vi": "Số liệu cấp quốc gia theo năm có định nghĩa và độ phủ riêng, nên không đo biến động theo quý của các ngân hàng niêm yết.",
                "does_not_show_en": "Annual country figures have their own definitions and coverage and do not measure quarter-to-quarter changes among listed banks."},
        "policy": {"timeline": timeline, "q4_by_year": yearly,
                   "n": sum(row["n"] for row in yearly), "timeline_n": len(timeline),
                   "period": [int(panel.year.min()), int(panel.year.max())],
                   "reading_vi": "Đọc ngày có hiệu lực và hạn cơ cấu nợ đã đối chiếu văn bản gốc bên cạnh chênh lệch NPL Quý 4 và Quý 1 trong từng năm.",
                   "reading_en": "Read the verified effective dates and restructuring cutoffs alongside the Q4–Q1 NPL change for matched banks in each year.",
                   "does_not_show_vi": "Hạn cơ cấu theo từng phiên bản văn bản có thể được gia hạn; trùng thời điểm không xác định tác động của chính sách.",
                   "does_not_show_en": "A later amendment can extend a restructuring cutoff. The timing does not identify a policy effect."},
    }
