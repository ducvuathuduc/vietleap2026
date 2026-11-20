"""Build the versioned NPL dashboard seed from analytical results and Gold data."""

import argparse
import json
import os
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import duckdb
from jsonschema import Draft202012Validator, FormatChecker
import yaml

from .decoder import VENDOR_LEVEL_FIELDS
from .real_data import DEADLINE_SOURCE, RATIOS
from .snapshot_metrics import dashboard_metrics, json_safe


SCHEMA_PATH = Path(__file__).with_name("schema") / "snapshot.schema.json"
LOCAL_TIME = ZoneInfo("Asia/Ho_Chi_Minh")
FIIN = "https://docs.fiinquant.vn"
RATIO_SOURCE = FIIN + "/ham-va-cong-thuc/3.-phan-tich-co-ban-and-dinh-gia/3.2.-ham-chi-so-bao-cao-tai-chinh"
TCB_SOURCE = "https://techcombank.com/content/dam/techcombank/public-site/documents/3q26-press-release-vie.pdf"
TCB_DISCLOSED_PCT = 1.36  # 2026Q3 issuer disclosure, including the CIC effect.
CALIBRATION_TOLERANCE_BP = 10
ROA_NOTE = "Nguồn FiinQuant không trả ROA. / The FiinQuant feed does not return ROA."
BANK_NAMES = {
    "BVB": ("Ngân hàng TMCP Bản Việt", "Viet Capital Commercial Joint Stock Bank"),
    "NVB": ("Ngân hàng TMCP Quốc Dân", "National Citizen Commercial Joint Stock Bank"),
    "VAB": ("Ngân hàng TMCP Việt Á", "Vietnam–Asia Commercial Joint Stock Bank"),
}
SERIES_FIELDS = {"npl_pct": "npl_pct", "coverage_pct": "coverage_pct", "ldr_pct": "ldr_pct",
                 "nim_pct": "nim_pct", "loan_growth_yoy_pct": "loan_growth_pct"}
SOURCE_SPECS = {
    "bank_quarter": ("FiinQuant · Chỉ số theo quý / quarterly ratios", RATIO_SOURCE),
    "bank_annual": ("FiinQuant · Chỉ số theo năm / annual ratios", RATIO_SOURCE),
    "price_daily": ("FiinQuant · Giá điều chỉnh / adjusted prices",
                    FIIN + "/fiinquant-en/function-and-formula/historical-data-function"),
    "valuation_daily": ("FiinQuant · Định giá / valuation", FIIN + "/ham-va-cong-thuc/3.-phan-tich-co-ban-and-dinh-gia"),
    "foreign_daily": ("FiinQuant · Giao dịch nước ngoài / foreign trading",
                      FIIN + "/ham-va-cong-thuc/1.-danh-muc-and-thong-tin-co-ban/1.5.-lay-du-lieu-room-ndtnn"),
    "report_calendar": ("Lịch hạn công bố / disclosure deadline calendar", DEADLINE_SOURCE),
}
EXTRA_SOURCES = {
    "disclosure_dates": ("Công bố BCTC / filing disclosures", "https://api.hsx.vn/n/api/v1/News/NewsFeed", ".csv"),
    "legal_register": ("Sổ văn bản / legal register", "https://congbao.chinhphu.vn", ".csv"),
    "sbv_system": ("Số liệu hệ thống NHNN / SBV system data", "https://sbv.gov.vn", ".parquet"),
    "case_tcb": ("BCTC Techcombank / Techcombank financial statements",
                 "https://techcombank.com/nha-dau-tu/thong-tin-tai-chinh/bao-cao-tai-chinh-vas", ".csv"),
    "wdi_bank": ("World Development Indicators · FB.AST.NPER.ZS",
                 "https://data.worldbank.org/indicator/FB.AST.NPER.ZS", ".parquet"),
}


def _sources(silver, counts):
    sources = []
    for key, (name, url) in SOURCE_SPECS.items():
        calendar = key == "report_calendar"
        file = silver / (f"{key}.csv" if calendar else f"{key}.parquet")
        timestamp = datetime.fromtimestamp(file.stat().st_mtime, LOCAL_TIME)
        sources.append(dict(id=key, name=name, method="file" if calendar else "api", url=url,
                            licence="Văn bản pháp luật công khai / public legal text" if calendar else
                            "FiinGroup · điều khoản dữ liệu / commercial data terms",
                            retrieved_at=timestamp.isoformat(timespec="seconds"), rows=counts[key]))
    for key, (name, url, suffix) in EXTRA_SOURCES.items():
        file = silver / f"{key}{suffix}"
        if key in counts and file.is_file():
            timestamp = datetime.fromtimestamp(file.stat().st_mtime, LOCAL_TIME)
            sources.append(dict(id=key, name=name, method="file", url=url,
                                licence="Nguồn công khai / public source",
                                retrieved_at=timestamp.isoformat(timespec="seconds"), rows=counts[key]))
    return sources


def _quality(panel, raw):
    def gate(id, name, status, detail):
        return dict(id=id, name=name, status=status, detail=detail)

    quality = []
    for metric in RATIOS:
        count = int(panel[metric].notna().sum())
        detail = f"{count}/{len(panel)} ({count / len(panel):.1%})."
        if metric == "roa_pct" and count == 0:
            detail += " " + ROA_NOTE
        quality.append(gate(metric, f"Độ phủ / Coverage · {metric}", "pass" if count == len(panel) else "warn", detail))

    keys = raw[["ticker", "period"]].copy()
    keys["ticker"] = keys["ticker"].astype("string").str.strip().str.upper().replace({"BIDV": "BID"})
    keys["period"] = keys["period"].astype("string").str.strip().str.upper()
    keys["basis"] = raw["basis"].astype("string").str.strip().str.lower() if "basis" in raw else "consolidated"
    duplicates = int(keys.duplicated().sum())
    quality.append(gate("duplicates", "Trùng khóa / Duplicate keys", "fail" if duplicates else "pass",
                        f"{duplicates} · ticker × period × basis (Silver)."))

    ordered = panel.sort_values(["bank_code", "period"])
    ordinal = ordered.period.str[:4].astype(int) * 4 + ordered.period.str[-1].astype(int)
    gaps = int(ordinal.groupby(ordered.bank_code).diff().gt(1).sum())
    quality.append(gate("gaps", "Quý gián đoạn / Quarter gaps", "warn" if gaps else "pass",
                        f"{gaps} khoảng trống trong chuỗi ngân hàng / gaps within bank series."))

    observed = panel.loc[panel.bank_code.eq("TCB") & panel.period.eq("2026Q3"), "npl_pct"].dropna()
    status = "warn"
    detail = f"TCB 2026Q3 · công bố / disclosed {TCB_DISCLOSED_PCT:.2f}%."
    if observed.empty:
        detail += " Thiếu số đối chiếu / vendor comparison unavailable."
    else:
        vendor = observed.item()
        difference = round(abs(TCB_DISCLOSED_PCT - vendor) * 100, 6)
        status = "pass" if difference <= CALIBRATION_TOLERANCE_BP else "fail"
        detail += f" FiinQuant {vendor:.2f}%; Δ {difference:g} bp; ngưỡng / tolerance {CALIBRATION_TOLERANCE_BP} bp."
    quality.append(gate("calibration", "Đối chiếu NPL / NPL calibration", status, detail))
    return quality


def _names(silver):
    names = BANK_NAMES.copy()
    for directory in silver.parents:
        register = directory / "scenarios" / "ratewatch" / "banks.yaml"
        if register.is_file():
            for record in yaml.safe_load(register.read_bytes())["banks"]:
                ticker = record.get("ticker")
                if ticker:
                    names["BID" if ticker == "BIDV" else ticker] = (record["name_vi"], record["name_en"])
            break
    return names


def _read_gold(gold):
    with duckdb.connect(str(gold), read_only=True) as db:
        panel = db.execute("""
            SELECT q.*, e.adjusted_d_npl_pct
            FROM fact_bank_quarter q
            LEFT JOIN fact_report_event e USING (bank_code, period, basis)
            WHERE q.basis = 'consolidated'
            ORDER BY bank_code, period
        """).df()
        banks = db.execute("""
            SELECT bank_code, ticker, ownership FROM dim_bank WHERE ownership IN ('state', 'private')
            ORDER BY bank_code
        """).df()
    return panel, banks


def _bank_cards(panel, banks, derived, models, names, publish):
    forecasts = {row["bank_code"]: row for row in models["M7"]["forecast_2026Q4"]}
    decisions = {row["bank_code"]: row for row in models["M7"].get("decision_rule", {}).get("latest", [])}
    series = {}
    if publish:
        for bank, rows in panel.groupby("bank_code", sort=False):
            series[bank] = rows[["period", *SERIES_FIELDS]].rename(columns=SERIES_FIELDS).to_dict("records")
    cards = []
    for bank in banks.itertuples(index=False):
        if bank.bank_code not in derived["banks"]:
            continue
        name_vi, name_en = names.get(bank.ticker, (bank.ticker, bank.ticker))
        metrics = derived["banks"][bank.bank_code]
        prediction = forecasts.get(bank.bank_code)
        next_quarter = None
        if prediction and prediction["predicted_npl_pct"] is not None:
            next_quarter = dict(period=prediction["period"], npl_pct=prediction["predicted_npl_pct"],
                                lo80=prediction["lower80"], hi80=prediction["upper80"])
        card = dict(code=bank.bank_code, ticker=bank.ticker, name_vi=name_vi, name_en=name_en,
                    ownership=bank.ownership, **metrics)
        card["latest"] = {**card["latest"], "forecast_next": next_quarter}
        if bank.bank_code in decisions:
            card["latest"]["decision"] = {key: value for key, value in decisions[bank.bank_code].items()
                                          if key != "bank_code"}
        if publish:
            card["series"] = series[bank.bank_code]
        cards.append(card)
    return cards


def _headline(models):
    baseline = models["M2"]["baseline"]
    q4 = baseline["terms"]["Q4"]["coefficient"]
    start, end = baseline.get("period", models["M1"]["period"])
    banks, observations = baseline["clusters"], baseline["n"]
    pairs = sum(row["n"] for row in models["M3"]["by_year"])
    reversals = sum(row["count"] for row in models["M3"]["by_year"])
    amount = f"{abs(q4):.2f}"
    if q4 < 0:
        vi_effect, en_effect = (f"thấp hơn {amount.replace('.', ',')} điểm phần trăm", f"{amount} percentage points lower than")
    elif q4 > 0:
        vi_effect, en_effect = (f"cao hơn {amount.replace('.', ',')} điểm phần trăm", f"{amount} percentage points higher than")
    else:
        vi_effect, en_effect = "bằng", "equal to"
    return {
        "vi": (f"Từ {start} đến {end}, mức thay đổi tỷ lệ nợ xấu quý 4 {vi_effect} quý 1 "
               f"({banks} ngân hàng, {observations} quan sát). Tỷ lệ này giảm rồi tăng trong {reversals}/{pairs} cặp quý 4–quý 1."),
        "en": (f"From {start} to {end}, the Q4 change in the NPL ratio was {en_effect} the Q1 change "
               f"({banks} banks, {observations} observations). The NPL ratio fell then rose in "
               f"{reversals} of {pairs} matched Q4–Q1 pairs."),
        "keys": ["M2.baseline.terms.Q4.coefficient", "M2.baseline.clusters", "M2.baseline.n",
                 "M2.baseline.period" if "period" in baseline else "M1.period", "M3.by_year"],
    }


def _methods(models):
    m1, m2, m3, m4, m5, m6, m7 = (models[f"M{i}"] for i in range(1, 8))
    benchmark = m2["baseline"]["terms"]["Q4"]
    mae = m7["backtest"]["mae_pp"]
    joint = "reported_or_deadline" in m6["regressions"]
    market_spec = (
        "CAR ±10 phiên quanh ngày công bố thực tế hoặc hạn; hồi quy đồng thời phần dự kiến loại quan sát đang xét "
        "và phần bất ngờ, chuẩn VNINDEX / CAR ±10 sessions around actual dates or deadlines; joint regression "
        "on leave-one-out expected change and surprise, benchmarked to VNINDEX."
        if joint else "CAR ±10 phiên quanh hạn công bố, chuẩn VNINDEX / CAR ±10 sessions around the deadline, benchmarked to VNINDEX."
    )
    definitions = [
        ("Mô tả", "Descriptives", "Trung vị và trung bình theo quý, ngân hàng và sở hữu / medians and means by quarter, bank and ownership.",
         sum(row["npl_pct_count"] for row in m1["by_period"]),
         "The panel summarizes reported NPL, coverage and loan-to-deposit ratios.", "It does not estimate a loan-weighted system-wide ratio."),
        ("Mùa vụ", "Seasonality", "Hiệu ứng cố định ngân hàng, quý; SE cụm và wild bootstrap / bank and quarter fixed effects, clustered SEs and wild bootstrap.",
         m2["baseline"]["n"],
         f"The Q4 coefficient relative to Q1 is {benchmark['coefficient']:.2f} pp.", "A seasonal pattern does not identify its cause."),
        ("Đảo chiều", "Reversal", "Thay đổi Q1 sau Q4, hiệu ứng cố định ngân hàng / next Q1 change on Q4 change, bank fixed effects.",
         m3["regression"]["n"],
         f"{sum(row['count'] for row in m3['by_year'])} matched pairs show a fall followed by a rise.",
         "The two changes share the Q4 level and cannot show that loans were moved across quarters."),
        ("Khác biệt theo nhóm", "Heterogeneity", "Tương tác Q4 × NPL cao và Q4 × sở hữu / Q4 interactions with high baseline NPL and ownership.",
         m4["regression"]["n"], "The interactions measure differences in Q4 seasonality across groups.",
         "The estimates do not identify a causal effect of ownership or initial NPL."),
        ("Liên hệ", "Linkage", "Mô hình mùa vụ cho bao phủ, NIM, tăng trưởng dư nợ / seasonal models for coverage, NIM and loan growth.",
         m5["seasonal"]["d_coverage_pct"]["n"], "The model links coverage, NIM and loan growth to the reporting quarter. The feed lacks ROA.",
         "Association can reflect common denominators or other unobserved factors."),
        ("Phản ứng thị trường", "Market response", market_spec,
         m6["regressions"]["reported_or_deadline" if joint else "raw"]["n"],
         f"{m6['events_with_car']} bank-quarter events have usable cumulative abnormal returns.",
         "The deadline is a proxy for the actual announcement date. Concurrent news may affect returns."),
        ("Dự báo", "Forecast", f"Kiểm định dự báo trước một quý, huấn luyện đến {m7['train_through']} / "
         f"one-quarter-ahead backtest, trained through {m7['train_through']}.",
         m7["backtest"]["n"], f"MAE was {mae['model']:.2f} pp for the model and {mae['naive']:.2f} pp for the previous-quarter benchmark.",
         "Historical accuracy and interval coverage do not carry a guarantee for future quarters."),
    ]
    return [
        dict(id=f"M{index}", name_vi=vi, name_en=en, spec=spec, n=n,
             reading_vi=models[f"M{index}"]["reading"], reading_en=models[f"M{index}"].get("reading_en", reading),
             does_not_show_vi=models[f"M{index}"]["what_this_does_not_show"],
             does_not_show_en=models[f"M{index}"].get("what_this_does_not_show_en", limit))
        for index, (vi, en, spec, n, reading, limit) in enumerate(definitions, start=1)
    ]


def _linkage(m5):
    linkage = {**m5, "seasonal": {key: fit for key, fit in m5["seasonal"].items() if key != "d_roa_pct"}}
    for measure in ("correlation", "correlation_n"):
        linkage[measure] = {key: {name: value for name, value in row.items() if name != "d_roa_pct"}
                            for key, row in m5[measure].items() if key != "d_roa_pct"}
    linkage["roa_note"] = ROA_NOTE
    return linkage


def build_snapshot(results, gold, silver):
    silver = Path(silver).resolve()
    models = json.loads(Path(results).read_bytes())
    panel, banks = _read_gold(gold)
    with duckdb.connect() as db:
        raw = db.read_parquet(str(silver / "bank_quarter.parquet")).df()
    m1, m2, m3, m4, m5, m6, m7 = (models[f"M{i}"] for i in range(1, 8))
    derived = m1.get("dashboard")
    if derived is None:
        derived = dashboard_metrics(panel)
    latest = derived["median_by_period"][-1]
    baseline = m2["baseline"]
    q4 = baseline["terms"]["Q4"]
    leave_out = m2["leave_one_bank_out"]["q4_range"]
    publish = os.getenv("NPL_PUBLISH_BANK_SERIES") != "0"
    quality = _quality(panel, raw)
    for signal, status in derived["signal_availability"].items():
        absent = ", ".join(status["missing"]) or "chưa có mẫu ghép hợp lệ / no matched inputs"
        detail = (f"{status['eligible']} quan sát đủ điều kiện / eligible; {status['fired']} tín hiệu / signals."
                  if status["eligible"] else f"Thiếu dữ liệu / missing data: {absent}.")
        quality.append(dict(id=signal, name=f"Tín hiệu / Signal {signal}", status="pass" if status["eligible"] else "warn",
                            detail=detail))
    meta = dict(period_start=m1["period"][0], period_end=m1["period"][-1],
                n_banks=int(panel.bank_code.nunique()), n_bank_quarters=len(panel), publish_bank_series=publish,
                sources=_sources(silver, m1["source_rows"]), quality=quality)
    payload = json_safe({
        "meta": meta,
        "headline": _headline(models),
        "kpis": {
            "level": {key: latest[key] for key in ["npl_median_pct", "period", "n_banks"]},
            "benchmark": dict(q4_coef_pp=q4["coefficient"], ci95=q4["ci95"], p=q4["p"],
                              p_wild_bootstrap=q4["wild_p"], n=baseline["n"], clusters=baseline["clusters"]),
            "trend": dict(down_then_up=[{key: row[key] for key in ["year", "share_pct", "n"]} for row in m3["by_year"]],
                          npl_4q_avg_median_pct=derived["npl_4q_avg_median_pct"], period=latest["period"]),
        },
        "series": {"median_by_period": derived["median_by_period"]},
        "quarter_effects": [
            dict(quarter=quarter, coef_pp=term["coefficient"], ci95=term["ci95"], p=term["p"],
                 p_wild_bootstrap=term["wild_p"])
            for quarter in (2, 3, 4) for term in [baseline["terms"][f"Q{quarter}"]]
        ],
        "banks": _bank_cards(panel, banks, derived, models, _names(silver), publish),
        "heterogeneity": m4,
        "linkage": _linkage(m5),
        "market": {key: m6[key] for key in ["car_by_day", "regressions", "deadline_car_by_day", "coverage",
                                           "events_with_car", "eligible_bank_quarters", "period_start", "period_end",
                                           "reading_en"] if key in m6},
        "forecast": {"backtest": m7["backtest"]["by_period"],
                     "mae": {key: m7["backtest"]["mae_pp"][source] for key, source in
                             [("model", "model"), ("last_value", "naive"), ("seasonal_naive", "seasonal_naive")]}},
        "robustness": {"leave_one_bank_out": dict(zip(["min", "max"], leave_out or [None, None])),
                       "drop_2021_2022": m2["drop_2021_2022"], "state_vs_private": m2["by_ownership"],
                       "median_regression": m2["median_regression"]},
        "method": _methods(models),
        "limitations": [
            dict(vi="Mẫu gồm các ngân hàng niêm yết có dữ liệu hợp nhất. Trung bình và trung vị cho ngân hàng trọng số bằng nhau.",
                 en="The sample covers listed banks with consolidated data. Means and medians weight banks equally."),
            dict(vi="Chỉ báo 4 quý lấy trung vị của bình quân NPL 4 quý liên tiếp theo từng ngân hàng.",
                 en="The four-quarter statistic is the median of each bank’s average NPL ratio over four consecutive quarters."),
            dict(vi="FiinQuant không trả ROA. Hai tín hiệu về nợ nhóm 2 và xóa nợ cần dữ liệu ghi chú BCTC.",
                 en="FiinQuant does not return ROA. The group 2 and write-off flags require financial statement notes."),
            dict(vi="Đọc nghiên cứu thị trường cùng độ phủ ngày công bố thực tế. Khoảng dự báo lấy từ sai số lịch sử.",
                 en="Read market estimates alongside actual disclosure date coverage. Prediction intervals use historical residuals."),
            dict(vi="Thời điểm nguồn ghi theo lần sửa tệp Silver cuối cùng.",
                 en="Source timestamps reflect the last modification of each Silver file."),
        ],
        "legal": [
            dict(ref=DEADLINE_SOURCE, text_vi="Khoản 3 Điều 14, Thông tư 96/2020/TT-BTC. Hạn dùng trong mô hình là 30 ngày đối với báo cáo quý hợp nhất của công ty mẹ niêm yết.",
                 text_en="Article 14(3), Circular 96/2020/TT-BTC. The model uses the 30-day deadline for listed parent companies’ consolidated quarterly statements."),
            dict(ref=TCB_SOURCE, text_vi="Công bố kết quả kinh doanh Quý 3/2026 của Techcombank dùng để đối chiếu NPL.",
                 text_en="Techcombank’s Q3 2026 earnings release provides the NPL calibration reference."),
            dict(ref=FIIN, text_vi="Nguồn: FiinQuant (FiinGroup). Chuỗi theo từng ngân hàng được công bố mặc định.",
                 text_en="Source: FiinQuant (FiinGroup). Bank-level series are published by default."),
        ],
        "ai_use": [
            dict(vi="Bản công bố lấy số liệu từ DuckDB và kết quả mô hình. Câu tiêu đề được định dạng bằng mã.",
                 en="Published figures come from DuckDB and model outputs. Code formats the headline."),
        ],
    })
    if "coverage" in m6:
        payload["market"]["reading_vi"] = m6["reading"]
    for key, model in [("findings", m1), ("context", m1), ("mechanism", m1), ("decision_rule", m7)]:
        if key in model:
            payload[key] = model[key]
    if "summary" in m3:
        payload["reversal"] = m3["summary"]
    if "decoder" in models:
        decoder = models["decoder"]
        if not publish:
            fields = dict.fromkeys(VENDOR_LEVEL_FIELDS)
            decoder = {**decoder}
            for key in ("rows", "focus") if "focus" in decoder else ("fiinquant_rows",):
                decoder[key] = [{**row, **fields} for row in decoder[key]]
        payload["decoder"] = decoder
    snapshot_hash = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8"))
    payload["meta"]["snapshot_id"] = f"npl-{latest['period']}-{snapshot_hash.hexdigest()[:12]}"
    payload["meta"]["generated_at"] = datetime.now(LOCAL_TIME).isoformat(timespec="seconds")
    schema = json.loads(SCHEMA_PATH.read_bytes())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
    return payload


def _write_snapshot(payload, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    file = NamedTemporaryFile(mode="w", encoding="utf-8", dir=out.parent, prefix=".snapshot-", delete=False)
    temporary = Path(file.name)
    try:
        with file:
            json.dump(payload, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
        temporary.replace(out)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("results", "gold", "silver", "out"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    _write_snapshot(build_snapshot(args.results, args.gold, args.silver), args.out)


if __name__ == "__main__":
    main()
