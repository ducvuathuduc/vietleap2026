"""Publish the analytical Gold database, model results, and presentation artifacts."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from .real_data import DEADLINE_SOURCE, OWNERSHIP_SOURCES, RATIOS, clean_calendar, clean_market, clean_quarters, read_silver, write_star
from .real_models import descriptives, forecast, heterogeneity, linkage, market_study, reversal, seasonal_models
from .snapshot_metrics import dashboard_metrics, json_safe


DICTIONARY = """# Từ điển dữ liệu NPL

`gold.duckdb` là sản phẩm nội bộ. Báo cáo và các tệp xuất mô hình chỉ dùng số liệu phân tích đã tổng hợp hoặc kết quả ước lượng.

| Bảng | Đơn vị quan sát | Khóa và liên kết | Trường và công thức |
|---|---|---|---|
| dim_bank | Một ngân hàng hoặc chỉ số | PK bank_code | ticker là mã niêm yết chuẩn hóa. ownership gồm state (VCB, BID, CTG), private (nhóm ngân hàng niêm yết còn lại) và index (VNINDEX). |
| dim_period | Một quý dương lịch | PK period | period dạng YYYYQn. year, quarter và quarter_end lấy theo lịch dương. |
| dim_date | Một ngày giao dịch hoặc mốc công bố | PK date | year và month theo ngày địa phương Việt Nam. |
| fact_bank_quarter | Ngân hàng × quý × phạm vi BCTC | PK bank_code, period, basis. FK dim_bank và dim_period. | Tỷ lệ làm tròn hai chữ số. Mọi d_* là tỷ lệ quý hiện tại trừ tỷ lệ đúng một quý trước, cùng ngân hàng và phạm vi BCTC (điểm %). Cờ iqr_flag nếu ngoài [P25 − 1,5 IQR, P75 + 1,5 IQR]; z_flag nếu \\|z\\| > 3. |
| fact_bank_market_day | Ngân hàng hoặc chỉ số × phiên giao dịch | PK bank_code, date. FK dim_bank và dim_date. | return_pct = 100 × (giá đóng cửa điều chỉnh / giá đóng cửa điều chỉnh phiên VNINDEX liền trước − 1). pe = giá/lợi nhuận và pb = giá/giá trị sổ sách (lần). foreign_buy_value, foreign_sell_value, foreign_net_value theo giá trị giao dịch nguồn (VND); foreign_room là số cổ phiếu còn có thể mua. |
| fact_report_event | Ngân hàng × quý × phạm vi BCTC | PK bank_code, period, basis. FK fact_bank_quarter và dim_date (deadline, event_date). | deadline là ngày kết thúc quý + 30 ngày theo khoản 3 Điều 14 cho công ty mẹ niêm yết. silver_deadline và các trường silver_* giữ mốc và chú thích đầu vào để đối chiếu. event_date là phiên VNINDEX đầu tiên từ hạn công bố. estimation_n là số phiên khớp trong cửa sổ ước lượng. car_pct = tổng lợi suất bất thường từ phiên −10 đến +10. adjusted_d_npl_pct = d_npl_pct − giá trị khớp M2. |

| Trường tỷ lệ quý | Công thức kinh tế và đơn vị |
|---|---|
| npl_pct | 100 × nợ xấu / tổng dư nợ, %. |
| coverage_pct | 100 × dự phòng tổn thất tín dụng / nợ xấu, %. |
| ldr_pct | 100 × dư nợ / tiền gửi, %. |
| roa_pct | 100 × lợi nhuận sau thuế / tài sản bình quân, %, theo kỳ và cách quy năm của nguồn. |
| nim_pct | 100 × thu nhập lãi thuần / tài sản sinh lãi bình quân, %, theo kỳ và cách quy năm của nguồn. |
| loan_growth_yoy_pct | 100 × (dư nợ bình quân / dư nợ bình quân cùng kỳ năm trước − 1), %. |
| seasonally_adjusted_npl_pct | NPL thực tế trừ hiệu ứng quý M2 đã quy về trung bình 0, ước lượng bằng dữ liệu đến 2024Q4, %. |

Cột tỷ lệ gốc FiinQuant ở dạng phân số được nhân 100. Tên đầu vào chuẩn *_pct đã ở đơn vị %.
Số liệu năm chỉ dùng đối chiếu NPL với Q4 cùng năm và cùng phạm vi. Mô hình dùng BCTC hợp nhất.
Lợi suất thị trường là lợi suất đơn giản. M6 ước lượng hệ số chặn và beta VNINDEX bằng OLS từ phiên −250 đến −30
với ít nhất 120 phiên khớp. Cửa sổ sự kiện cần đủ 21 lợi suất cho cả ngân hàng và VNINDEX.
M7 dùng các phân vị 10% và 90% của sai số huấn luyện cho khoảng dự báo 80%.
Giá trị thiếu xuất dạng NULL trong Gold, null trong JSON và ô trống trong CSV.
"""

ERD = """erDiagram
    dim_bank ||--o{ fact_bank_quarter : bank_code
    dim_period ||--o{ fact_bank_quarter : period
    dim_bank ||--o{ fact_bank_market_day : bank_code
    dim_date ||--o{ fact_bank_market_day : date
    fact_bank_quarter ||--o| fact_report_event : bank_quarter_basis
    dim_date ||--o{ fact_report_event : deadline
    dim_date o|--o{ fact_report_event : event_date
    dim_bank {
        string bank_code PK
        string ticker
        string ownership
    }
    dim_period {
        string period PK
        int year
        int quarter
        date quarter_end
    }
    dim_date {
        date date PK
        int year
        int month
    }
    fact_bank_quarter {
        string bank_code PK, FK
        string period PK, FK
        string basis PK
        double npl_pct
        double d_npl_pct
        double seasonally_adjusted_npl_pct
    }
    fact_bank_market_day {
        string bank_code PK, FK
        date date PK, FK
        double return_pct
    }
    fact_report_event {
        string bank_code PK, FK
        string period PK, FK
        string basis PK, FK
        date deadline FK
        date event_date FK
        double car_pct
    }
"""


def _number(value, digits=2):
    return f"{value:.{digits}f}" if value is not None and np.isfinite(value) else "—"


def _p_text(value):
    return "<0.0001" if value is not None and value < .0001 else f"={_number(value, 4)}"


def _term_text(model, term):
    item = model["terms"].get(term)
    if item is None:
        return f"n={model['n']}, hệ số chưa ước lượng được"
    ci = item["ci95"]
    interval = f"[{_number(ci[0])}, {_number(ci[1])}]" if ci else "—"
    result = (f"{_number(item['coefficient'])} (n={model['n']}, {model['clusters']} cụm ngân hàng, "
              f"KTC 95% {interval}, p{_p_text(item['p'])}")
    if "wild_p" in item:
        result += f", p bootstrap{_p_text(item['wild_p'])}"
    return result + ")"


def _annual_check(annual, panel):
    core = annual.copy()
    if "year" in core:
        year = pd.to_numeric(core["year"], errors="coerce").astype("Int64").astype("string")
    else:
        year = core["period"].astype("string").str.extract(r"^(\d{4})")[0]
    core["period"] = year + "Q4"
    tidy, _ = clean_quarters(core)
    compared = panel[["bank_code", "basis", "period", "npl_pct"]].merge(
        tidy[["bank_code", "basis", "period", "npl_pct"]],
        on=["bank_code", "basis", "period"], suffixes=("_q4", "_annual"), validate="one_to_one",
    ).dropna()
    distance = compared["npl_pct_q4"].sub(compared["npl_pct_annual"]).abs()
    return {"rows": len(annual), "npl_pairs": len(compared), "different_at_2dp": int(distance.gt(.00001).sum()),
            "mean_absolute_difference_pp": distance.mean()}


def _readings(models):
    m1, m2, m3, m4, m5, m6, m7 = (models[f"M{i}"] for i in range(1, 8))
    first = m1["by_period"][0]
    last = m1["by_period"][-1]
    pairs = sum(row["n"] for row in m3["by_year"])
    flips = sum(row["count"] for row in m3["by_year"])
    raw_q4 = m6["regressions"]["raw_q4"]
    adjusted_q4 = m6["regressions"]["adjusted_q4"]
    raw_p = raw_q4["terms"].get("d_npl_pct", {}).get("p")
    adjusted_p = adjusted_q4["terms"].get("adjusted_d_npl_pct", {}).get("p")
    if raw_p is None or adjusted_p is None:
        reaction = "Mẫu hiện có chưa đủ để so sánh hai hồi quy Quý 4."
    elif raw_p < .05 and adjusted_p >= .05:
        reaction = "Ở ngưỡng 5%, chỉ hồi quy dùng biến động NPL gốc cho thấy liên hệ trong Quý 4."
    elif adjusted_p < .05 and raw_p >= .05:
        reaction = "Ở ngưỡng 5%, chỉ hồi quy dùng biến động NPL đã khử mùa vụ cho thấy liên hệ trong Quý 4."
    elif raw_p < .05 and adjusted_p < .05:
        reaction = "Liên hệ trong Quý 4 vẫn có ý nghĩa ở ngưỡng 5% sau khi loại phần biến động NPL dự kiến."
    else:
        reaction = "Hai hồi quy Quý 4 đều chưa phát hiện liên hệ ở ngưỡng 5%."
    errors = m7["backtest"]["mae_pp"]
    roa_n = sum(row["roa_pct_count"] for row in m1["by_period"])
    return [
        (f"NPL trung vị là {_number(first['npl_pct_median'])}% ở {first['period']} "
         f"và {_number(last['npl_pct_median'])}% ở {last['period']}. Có {roa_n} quan sát ROA hợp lệ. "
         "Bảng sở hữu cho mỗi ngân hàng-quý trọng số bằng nhau.",
         "Trung vị và trung bình mẫu không phải tỷ lệ nợ xấu gộp theo dư nợ của toàn hệ thống."),
        (f"So với Quý 1 của cùng ngân hàng, hệ số biến động NPL Quý 4 là {_term_text(m2['baseline'], 'Q4')} điểm %.",
         "Hệ số mùa vụ mô tả biến động báo cáo. Nguyên nhân có thể gồm xử lý nợ, tăng dư nợ hoặc thay đổi chất lượng tín dụng."),
        (f"NPL giảm trong Quý 4 rồi tăng trong Quý 1 kế tiếp ở {flips}/{pairs} cặp. "
         f"Hệ số hồi quy Quý 1 lên Quý 4 là {_term_text(m3['regression'], 'q4_delta')}.",
         "Hai chênh lệch dùng chung mức NPL tại Quý 4. Mối liên hệ không chứng minh nợ đã được chuyển kỳ."),
        (f"Sau 2022, chênh lệch hiệu ứng Quý 4 của nhóm NPL cao so với nhóm còn lại là "
         f"{_term_text(m4['regression'], 'Q4_high_npl')} điểm %. Chênh lệch của nhóm Nhà nước là "
         f"{_term_text(m4['regression'], 'Q4_state')} điểm %.",
         "Tương tác so sánh mẫu hình theo nhóm. Thiết kế không nhận diện tác động nhân quả của sở hữu hoặc NPL ban đầu."),
        (f"So với Quý 1, hệ số Quý 4 của thay đổi bao phủ là "
         f"{_term_text(m5['seasonal']['d_coverage_pct'], 'Q4')} điểm %. Nguồn FiinQuant không trả ROA.",
         "Các thay đổi đồng thời có thể phản ánh mẫu số chung, điều chỉnh kế toán hoặc yếu tố khác chưa đo được."),
        (f"Có {m6['events_with_car']}/{m6['eligible_bank_quarters']} sự kiện có CAR. Hệ số Quý 4 với NPL gốc là "
         f"{_term_text(raw_q4, 'd_npl_pct')}; với NPL đã khử mùa vụ là "
         f"{_term_text(adjusted_q4, 'adjusted_d_npl_pct')}. {reaction}",
         "Cửa sổ lấy hạn công bố làm mốc. Mô hình không quan sát ngày công bố thực tế, kỳ vọng của nhà đầu tư "
         "hoặc loại trừ các tin tức khác trong cùng cửa sổ."),
        (f"Trên {m7['backtest']['n']} ngân hàng-quý giai đoạn 2025Q1–2026Q3, MAE mô hình là "
         f"{_number(errors['model'])} điểm %, so với {_number(errors['naive'])} khi giữ mức gần nhất "
         f"và {_number(errors['seasonal_naive'])} khi dùng cùng quý năm trước.",
         "Kiểm định dùng dữ liệu lịch sử hiện có. Khoảng dự báo thực nghiệm không bảo đảm độ bao phủ trong tương lai."),
    ]


def _insights(models, panel):
    m2, m3, m4, m5, m6, m7 = (models[f"M{i}"] for i in range(2, 8))
    coverage = m5["seasonal"]["d_coverage_pct"]
    coverage_period = panel.loc[panel["d_coverage_pct"].notna(), "period"]
    npl_period = panel.loc[panel["d_npl_pct"].notna(), "period"]
    period = f"{npl_period.min()}–{npl_period.max()}"
    pairs = pd.DataFrame(m3["by_year"])
    if pairs.empty:
        reversal_period = period
    else:
        reversal_period = f"{pairs.year.min()}Q4–{pairs.year.max() + 1}Q1"
    error = m7["backtest"]["mae_pp"]
    comparative_test = []
    for key, label in [("naive", "mức quý trước"), ("seasonal_naive", "cùng quý năm trước")]:
        item = m7["backtest"]["mae_difference_vs"][key]
        low, high = item["ci95"] if item["ci95"] else (None, None)
        comparative_test.append(f"{label} có KTC 95% [{_number(low, 3)}, {_number(high, 3)}]")
    forecast_ci = " và ".join(comparative_test)
    findings = [
        ("Hiệu ứng Quý 4", m2["baseline"], "Q4", period,
         "Dùng cùng quý năm trước và mức điều chỉnh mùa vụ để rà soát chỉ báo cuối năm."),
        ("Diễn biến Quý 1 sau Quý 4", m3["regression"], "q4_delta", reversal_period,
         "Kiểm tra cả dấu thay đổi và hệ số trước khi diễn giải diễn biến Quý 1."),
    ]
    candidates = [
        ("Mức bao phủ", coverage, "Q4", f"{coverage_period.min()}–{coverage_period.max()}",
         "Đọc tỷ lệ bao phủ cùng mức NPL và rà soát mẫu số."),
        ("Chênh lệch theo NPL giai đoạn đầu", m4["regression"], "Q4_high_npl", f"2023Q1–{npl_period.max()}",
         "Kiểm tra riêng các ngân hàng có NPL cao trước 2023."),
        ("Chênh lệch theo sở hữu", m4["regression"], "Q4_state", f"2023Q1–{npl_period.max()}",
         "Duy trì nhóm so sánh riêng theo sở hữu khi đọc biến động Quý 4."),
        ("CAR và NPL đã khử mùa vụ", m6["regressions"]["adjusted"], "adjusted_d_npl_pct",
         "–".join(m6["regressions"]["adjusted"].get("period", [])),
         "Đối chiếu ngày công bố thực tế trước khi diễn giải phản ứng thị trường."),
    ]

    def strength(item):
        _, model, term, *_ = item
        p = model["terms"].get(term, {}).get("p")
        return p if p is not None else 1

    findings.extend(sorted(candidates, key=strength)[:2])
    lines = ["# Năm phát hiện phục vụ ra quyết định", ""]
    for index, (title, model, term, span, decision) in enumerate(findings, start=1):
        supporting = ""
        if term == "q4_delta":
            supporting = f" Có {pairs['count'].sum()}/{pairs['n'].sum()} cặp giảm rồi tăng." if not pairs.empty else ""
        lines.append(f"{index}. **{title} ({span}).** Hệ số {_term_text(model, term)}.{supporting} {decision}")
    best = min(error, key=error.get)
    guidance = {
        "model": "Theo dõi kết quả của mô hình trong các quý mới cùng hai dự báo chuẩn.",
        "naive": "Ưu tiên mức quý trước làm dự báo chuẩn theo sai số quan sát được.",
        "seasonal_naive": "Ưu tiên mức cùng quý năm trước làm dự báo chuẩn theo sai số quan sát được.",
    }[best]
    lines.append(f"5. **Sai số dự báo (2025Q1–2026Q3).** n={m7['backtest']['n']}. MAE lần lượt "
                 f"{_number(error['model'])}, {_number(error['naive'])}, {_number(error['seasonal_naive'])} điểm % "
                 f"cho mô hình, mức quý trước và cùng quý năm trước. Chênh lệch MAE (mô hình trừ chuẩn) "
                 f"theo bootstrap ngân hàng so với {forecast_ci}. {guidance}")
    return "\n".join(lines) + "\n"


def _write_tables(folder, models):
    m1, m2, m3, m4, m5, m6, m7 = (models[f"M{i}"] for i in range(1, 8))
    tables = {f"m1_{key}": rows for key, rows in m1.items() if key.startswith("by_")}
    tables.update({
        "m2_leave_one_bank_out": m2["leave_one_bank_out"]["fits"], "m3_reversal_by_year": m3["by_year"],
        "m6_car_by_day": m6["car_by_day"], "m7_backtest_by_period": m7["backtest"]["by_period"],
        "m7_forecast_2026q4": m7["forecast_2026Q4"],
    })
    for name, rows in tables.items():
        pd.DataFrame(rows).to_csv(folder / f"{name}.csv", index=False)
    pd.DataFrame(m5["correlation"]).to_csv(folder / "m5_change_correlations.csv", index_label="metric")
    regression_groups = {
        "M2": {**{variant: m2[variant] for variant in ["baseline", "year_fe", "drop_2021_2022", "median_regression"]},
               **m2["by_ownership"]},
        "M3": {"baseline": m3["regression"]}, "M4": {"combined": m4["regression"]},
        "M5": m5["seasonal"], "M6": m6["regressions"],
    }
    rows = []
    for model, variants in regression_groups.items():
        for variant, estimates in variants.items():
            if not estimates["terms"]:
                rows.append(dict(model=model, variant=variant, n=estimates["n"], clusters=estimates.get("clusters")))
            for name, term in estimates["terms"].items():
                low, high = term["ci95"] if term["ci95"] else (None, None)
                rows.append(dict(model=model, variant=variant, term=name, n=estimates["n"],
                                 clusters=estimates.get("clusters"), coefficient=term["coefficient"],
                                 ci95_lower=low, ci95_upper=high, p=term["p"], wild_p=term.get("wild_p")))
    pd.DataFrame(rows).to_csv(folder / "model_coefficients.csv", index=False)


def _chart(folder, filename, title, ylabel, draw):
    fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
    draw(ax)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=.25)
    fig.savefig(folder / filename, dpi=160)
    plt.close(fig)


def _plots(folder, models):
    def sawtooth(ax):
        summary = pd.DataFrame(models["M1"]["by_period"])
        levels = summary["npl_pct_median"]
        ax.plot(summary["period"], levels, marker="o")
        q4 = summary["period"].str.endswith("Q4")
        ax.scatter(summary.loc[q4, "period"], levels.loc[q4], color="tab:orange", label="Quý 4", zorder=3)
        ax.tick_params(axis="x", rotation=55)
        ax.legend()

    def coefficient(ax):
        m2 = models["M2"]
        variants = [("Mô hình chính", m2["baseline"]), ("Thêm hiệu ứng năm", m2["year_fe"]),
                    ("Từ năm 2023", m2["drop_2021_2022"]), ("Nhóm Nhà nước", m2["by_ownership"].get("state")),
                    ("Nhóm tư nhân", m2["by_ownership"].get("private"))]
        ax.set_xticks(range(len(variants)), [label for label, _ in variants], rotation=15)
        for position, (_, model) in enumerate(variants):
            term = model["terms"].get("Q4") if model else None
            if not term or not term["ci95"]:
                continue
            y = term["coefficient"]
            low, high = term["ci95"]
            ax.errorbar(position, y, yerr=[[max(0, y - low)], [max(0, high - y)]],
                        fmt="o", color="tab:blue", capsize=4)
            ax.annotate(f"p*={_number(term['wild_p'], 3)}", (position, high), xytext=(0, 7),
                        textcoords="offset points", ha="center", fontsize=8)
        ax.margins(y=.2)
        ax.axhline(0, color="0.4", linewidth=1)
        ax.set_xlabel("KTC 95% theo cụm ngân hàng · p* là p-value wild bootstrap")

    def car(ax):
        frame = pd.DataFrame(models["M6"]["car_by_day"])
        if frame.empty:
            ax.text(.5, .5, "Chưa có cửa sổ sự kiện đủ dữ liệu", transform=ax.transAxes, ha="center")
            return
        for label, sample in frame.groupby("group"):
            line, = ax.plot(sample["day"], sample["mean_car_pct"], label="Tất cả quý" if label == "all" else "Quý 4")
            bands = sample["ci95"].dropna()
            if len(bands):
                low, high = np.asarray(bands.tolist()).T
                ax.fill_between(sample.loc[bands.index, "day"], low, high, color=line.get_color(), alpha=.15)
        ax.axvline(0, color="0.4", linewidth=1)
        ax.axhline(0, color="0.4", linewidth=1, linestyle="--")
        ax.set_xlabel("Phiên giao dịch so với hạn công bố")
        ax.legend()

    def backtest(ax):
        frame = pd.DataFrame(models["M7"]["backtest"]["by_period"])
        if frame.empty:
            ax.text(.5, .5, "Chưa có mẫu kiểm định chung", transform=ax.transAxes, ha="center")
            return
        for name, label in [("npl_pct", "Thực tế"), ("predicted_npl_pct", "Mô hình"),
                            ("last_value", "Quý trước"), ("seasonal_naive", "Cùng quý năm trước")]:
            ax.plot(frame["period"], frame[name], marker="o", label=label)
        ax.legend()

    _chart(folder, "npl_median_by_quarter.png", "Tỷ lệ nợ xấu trung vị theo quý", "NPL (%)", sawtooth)
    _chart(folder, "q4_coefficient.png", "Chênh lệch biến động NPL giữa Quý 4 và Quý 1", "Điểm phần trăm", coefficient)
    _chart(folder, "event_study_car.png", "Lợi suất bất thường tích lũy quanh hạn công bố", "CAR trung bình (%)", car)
    _chart(folder, "forecast_backtest.png", "NPL trung bình trong mẫu kiểm định", "NPL (%)", backtest)


def run_real(silver, out):
    tables = read_silver(Path(silver))
    panel, steps = clean_quarters(tables["bank_quarter"])
    main = panel.loc[panel["basis"].eq("consolidated")].copy()
    if main["npl_pct"].count() == 0:
        raise ValueError("Không có NPL hợp nhất hợp lệ")
    calendar = clean_calendar(tables["report_calendar"])
    market = clean_market(tables, panel["bank_code"].unique())
    m1 = descriptives(main)
    m1["annual_q4_check"] = _annual_check(tables["bank_annual"], main)
    m1["source_rows"] = {table: len(frame) for table, frame in tables.items()}
    m1["banks"] = int(main["bank_code"].nunique())
    m1["period"] = [main["period"].min(), main["period"].max()]
    m2, fitted = seasonal_models(main)
    m1["dashboard"] = dashboard_metrics(main.assign(adjusted_d_npl_pct=main.d_npl_pct - fitted))
    m3 = reversal(main)
    m4 = heterogeneity(main)
    m5 = linkage(main)
    m6, events = market_study(main, market, calendar, fitted)
    m7, adjusted = forecast(main)
    panel["seasonally_adjusted_npl_pct"] = adjusted["seasonally_adjusted_npl_pct"]
    models = {f"M{i}": result for i, result in enumerate([m1, m2, m3, m4, m5, m6, m7], start=1)}
    for result, (reading, limit) in zip(models.values(), _readings(models)):
        result.update(reading=reading, what_this_does_not_show=limit)
    changed = int(calendar["deadline"].ne(calendar["silver_deadline"]).sum())
    audit = ["# Nhật ký làm sạch dữ liệu NPL", "", "| Bước | Dòng trước | Dòng sau | Thực hiện |", "|---|---:|---:|---|"]
    # Avoid treating literal pipes in thresholds as Markdown cell separators.
    for step in steps:
        detail = step["detail"].replace("|", "\\|")
        audit.append(f"| {step['step']} | {step['before']} | {step['after']} | {detail} |")
    audit.extend(["", f"Lịch sự kiện có {changed}/{len(calendar)} mốc khác lịch Silver khi áp dụng hạn 30 ngày "
                  f"cho báo cáo hợp nhất của công ty mẹ niêm yết. [Khoản 3 Điều 14]({DEADLINE_SOURCE})."])
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".npl-real-", dir=out) as folder:
        stage = Path(folder)
        write_star(stage / "gold.duckdb", panel, market, calendar, events)
        (stage / "results.json").write_text(json.dumps(json_safe(models), indent=2, ensure_ascii=False,
                                                   allow_nan=False) + "\n", encoding="utf-8")
        (stage / "cleaning_log.md").write_text("\n".join(audit) + "\n", encoding="utf-8")
        sources = f"\nSở hữu: {OWNERSHIP_SOURCES}. Hạn công bố: [Khoản 3 Điều 14]({DEADLINE_SOURCE}).\n"
        (stage / "data_dictionary.md").write_text(DICTIONARY + sources, encoding="utf-8")
        (stage / "erd.mmd").write_text(ERD, encoding="utf-8")
        (stage / "insights.md").write_text(_insights(models, main), encoding="utf-8")
        _write_tables(stage, models)
        _plots(stage, models)
        for artifact in stage.iterdir():
            artifact.replace(out / artifact.name)
