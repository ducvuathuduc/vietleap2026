"""Publish the analytical Gold database, model results, and presentation artifacts."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from .decoder import build_decoder
from .decompose import decompose_screening
from .early_warning import early_warning
from .event_windows import window_study
from .market_model import run as run_market_model
from .real_data import DEADLINE_SOURCE, OWNERSHIP_SOURCES, RATIOS, clean_calendar, clean_market, clean_quarters, read_silver, write_star
from .real_context import mechanism, policy_context, statement_amounts
from .real_models import (
    SCREENING_LINKAGE, decision_rule, descriptives, forecast, heterogeneity, linkage, market_study, reversal,
    seasonal_models,
)
from .seasonal_review import (
    add_rebound_baseline, adjust_pvalues, loan_size_subgroups, policy_robustness, rebound_baselines, seasonal_hypotheses,
)
from .scorecard import build_scorecard, publish_audit
from .seasonal_adjust import seasonal_adjustment
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
| fact_report_event | Ngân hàng × quý × phạm vi BCTC | PK bank_code, period, basis. FK fact_bank_quarter và dim_date. | deadline là ngày kết thúc quý + 30 ngày theo quy tắc nghiên cứu. published_at và disclosure_url ghi ngày và nguồn công bố quan sát được. anchor_date ưu tiên ngày thực tế, sau đó dùng deadline. event_date là phiên VNINDEX đầu tiên từ anchor_date. deadline_event_date và deadline_car_pct dùng hạn cho mọi sự kiện. estimation_n đếm số phiên khớp trong cửa sổ ước lượng. car_pct cộng lợi suất bất thường từ phiên −10 đến +10. |

| Trường tỷ lệ quý | Công thức kinh tế và đơn vị |
|---|---|
| npl_pct | 100 × nợ xấu / tổng dư nợ, %. |
| coverage_pct | 100 × dự phòng tổn thất tín dụng / nợ xấu, %. |
| ldr_pct | 100 × dư nợ / tiền gửi, %. |
| roa_pct | 100 × lợi nhuận sau thuế / tài sản bình quân, %, theo kỳ và cách quy năm của nguồn. |
| nim_pct | 100 × thu nhập lãi thuần / tài sản sinh lãi bình quân, %, theo kỳ và cách quy năm của nguồn. |
| loan_growth_yoy_pct | 100 × (dư nợ bình quân / dư nợ bình quân cùng kỳ năm trước − 1), %. |
| seasonally_adjusted_npl_pct | Mức NPL thực tế trừ hiệu ứng quý được quy về trung bình 0, ước lượng bằng dữ liệu đến 2024Q4, %. |
| expected_d_npl_pct, surprise_d_npl_pct | M6. Thay đổi NPL dự kiến từ hiệu ứng cố định ngân hàng và quý sau khi loại quan sát đang xét. Phần bất ngờ = d_npl_pct trừ phần dự kiến, điểm %. |
| expected_change_pp, adjusted_d_npl_pct | Quy tắc quyết định M7. Thay đổi dự kiến ước lượng bằng dữ liệu trước quý xét, tối đa đến 2024Q4. Thay đổi điều chỉnh = d_npl_pct trừ phần dự kiến, điểm %. |
| lo80_pp, hi80_pp, decision_status | Phân vị 10% và 90% của phần dư M7 trong mẫu huấn luyện. Phần dư dưới hoặc trên dải lần lượt là cải thiện hoặc xấu đi khác thường. |

| Tệp Silver | Đơn vị quan sát và khóa nguồn | Trường và mục đích |
|---|---|---|
| bank_quarter.parquet | ticker × period × basis | Tỷ lệ theo quý FiinQuant; các tỷ lệ hiệu chỉnh và thay đổi liên quý dùng BCTC hợp nhất. |
| bank_annual.parquet | ticker × year × basis | Tỷ lệ theo năm FiinQuant, đối chiếu cùng Q4. |
| field_map_ratios.csv | vendor_name | column và alias ánh xạ trường gốc sang tên Silver; dùng kiểm kê, giữ nguyên giá trị tỷ lệ. |
| price_daily.parquet | ticker × date | Giá điều chỉnh; dùng phiên VNINDEX để tính lợi suất liền phiên. |
| valuation_daily.parquet | ticker × date | PE, PB ghép vào bảng ngày theo cùng mã và phiên. |
| foreign_daily.parquet | ticker × date | Giá trị mua, bán, ròng và số lượng room ghép theo mã và phiên. |
| report_calendar.csv | period | quarter_end, hạn và căn cứ nguồn; tạo đồng hồ theo hạn cho mọi sự kiện. |
| disclosure_dates.csv | ticker × period | published_at và url từ sổ công bố; lấy ngày địa phương sớm nhất sau cuối quý. |
| legal_register.csv | ref | title, effective_from, effective_to và url. Dòng thời gian giữ các trường register_* để đối chiếu, dùng văn bản gốc cho ngày có hiệu lực và hạn cơ cấu theo từng phiên bản, bên cạnh ước lượng Q4 so với Q1 từng năm. |
| sbv_system.parquet | month | Dư nợ, tiền gửi, tăng trưởng YTD và LDR toàn hệ thống; kiểm kê Silver, không ghép dữ liệu tháng vào mẫu ngân hàng-quý. |
| wdi_bank.parquet | iso3 × year | NPL/dư nợ gộp (%) và vốn/tài sản (%); so sánh NPL Việt Nam với trung vị và khoảng quan sát của các nước ASEAN có dữ liệu cùng năm. |
| case_tcb.csv | quarter × metric × url | Số liệu TCB với trang BCTC; dòng dự phòng sử dụng thiếu căn cứ về kỳ xóa nợ nên chỉ dùng trường dư nợ và nhóm nợ. |
| notes_bank_quarter.parquet | bank × period × basis × field × reader | value_vnd_bn, trang, URL, nguồn đọc, grade và SHA-256. Dùng số dư point, số phát sinh quarterly và phạm vi hợp nhất đã xác nhận. Ưu tiên verified, chấp nhận single, loại contested và các giá trị xung đột cùng hạng. |
| notes_links.csv | bank × period × url | statement_type theo đường dẫn BCTC, dùng xác nhận phạm vi hợp nhất cho số dư và dòng từ thuyết minh. |
| notes_gate.csv | bank × period × gate | Trạng thái đối chiếu tổng dư nợ, dự phòng và NPL với nguồn ngoài; ghi nhận trong kiểm kê. |

Cột tỷ lệ gốc FiinQuant ở dạng phân số được nhân 100. Tên đầu vào chuẩn *_pct đã ở đơn vị %.
Số liệu năm chỉ dùng đối chiếu NPL với Q4 cùng năm và cùng phạm vi. Mô hình dùng BCTC hợp nhất.
Lợi suất thị trường là lợi suất đơn giản. M6 ước lượng hệ số chặn và beta VNINDEX bằng OLS từ phiên −250 đến −30
với ít nhất 120 phiên khớp. Cửa sổ sự kiện cần đủ 21 lợi suất cho cả ngân hàng và VNINDEX.
M6 hồi quy đồng thời CAR theo phần dự kiến và bất ngờ, với sai số cụm ngân hàng và wild bootstrap dưới giả thuyết hệ số bằng 0.
So sánh thêm hai đồng hồ trên cùng mẫu có cửa sổ giao dịch hợp lệ quanh cả hai mốc.
M7 dùng các phân vị 10% và 90% của sai số huấn luyện cho khoảng dự báo 80%.
Đảo chiều khi hai thay đổi NPL thực tế ở Q4 rồi Q1 trái dấu. Khoảng của tỷ lệ dùng bootstrap theo ngân hàng; khoảng Wilson tham khảo giả định các cặp độc lập.
Phát sinh nợ xấu ròng = thay đổi số dư nhóm 3–5 liền quý + xóa nợ trong quý. Tỷ trọng xóa nợ Q4 cần đủ bốn quý và tổng dương.
Tỷ lệ nhóm 2 = 100 × dư nợ nhóm 2 / dư nợ khách hàng. Tăng trưởng dư nợ quý = 100 × (dư nợ hiện tại / dư nợ quý trước − 1).

Bộ giải mã dùng tỷ lệ (dạng phần số): NPL = N/L, nhóm 2 = G2/L, bao phủ = P/N,
xóa nợ = W/L quý trước, phát sinh = (N hiện tại − N quý trước + W)/L quý trước, và nợ có vấn đề rộng = (N + G2)/L.
Dự phòng cuối kỳ và xóa nợ dùng độ lớn khi BCTC trình bày dưới dạng số âm.
S1, S2 và S3 lần lượt kiểm tra nhóm 2 tăng, xóa nợ tăng và bao phủ giảm sau khi NPL giảm.
S4 kiểm tra khoản giảm NPL trong Quý 4 nằm trong dải mùa vụ M7. Trạng thái Cải thiện có cơ sở cần đủ các kiểm tra áp dụng.
Hồi quy có hiệu ứng cố định ngân hàng, sai số cụm và wild bootstrap, dùng tỷ lệ xóa nợ,
thay đổi nhóm 2, tăng trưởng dư nợ và bao phủ đúng một quý trước. FiinQuant dùng tăng trưởng cùng kỳ năm trước.
Ghi chú BCTC dùng tăng trưởng theo quý. Kết quả FiinQuant rút gọn ghi rõ các trường không có dữ liệu.
Giá trị thiếu xuất dạng NULL trong Gold, null trong JSON và ô trống trong CSV.
"""

ERD = """erDiagram
    dim_bank ||--o{ fact_bank_quarter : bank_code
    dim_period ||--o{ fact_bank_quarter : period
    dim_bank ||--o{ fact_bank_market_day : bank_code
    dim_date ||--o{ fact_bank_market_day : date
    fact_bank_quarter ||--o| fact_report_event : bank_quarter_basis
    dim_date o|--o{ fact_report_event : deadline
    dim_date o|--o{ fact_report_event : event_date
    dim_date o|--o{ fact_report_event : deadline_event_date
    dim_date o|--o{ fact_report_event : published_at
    dim_date o|--o{ fact_report_event : anchor_date
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
        date published_at FK
        date anchor_date FK
        date event_date FK
        date deadline_event_date FK
        string anchor_source
        double car_pct
        double deadline_car_pct
        double expected_d_npl_pct
        double surprise_d_npl_pct
        double expected_change_pp
        double adjusted_d_npl_pct
        double lo80_pp
        double hi80_pp
        string decision_status
    }
"""


def _number(value, digits=2):
    return f"{value:.{digits}f}" if value is not None and np.isfinite(value) else "—"


def _p_text(value):
    return "<0.0001" if value is not None and value < .0001 else f"={_number(value, 4)}"


def _term_text(model, term, *, english=False, digits=2):
    item = model["terms"].get(term)
    if item is None:
        missing = "coefficient unavailable" if english else "hệ số chưa ước lượng được"
        return f"{missing} (n={model['n']})"
    ci = item["ci95"]
    interval = f"[{_number(ci[0], digits)}, {_number(ci[1], digits)}]" if ci else "—"
    clusters = "bank clusters" if english else "cụm ngân hàng"
    ci_name = "95% CI" if english else "KTC 95%"
    result = (f"{_number(item['coefficient'], digits)} (n={model['n']}, {model['clusters']} {clusters}, "
              f"{ci_name} {interval}, p{_p_text(item['p'])}")
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
    summary = m3["summary"]
    rebound = m3["baselines"]
    span = "–".join(summary["period"] or [])
    mean_change = summary["mean_next_q1_change_pp"]
    mean_vi = (f"Quý 1 bình quân tăng {_number(mean_change)} điểm %" if mean_change > 0 else
               f"thay đổi Quý 1 bình quân {_number(mean_change)} điểm %")
    mean_en = (f"Q1 rose by {_number(mean_change)} pp on average" if mean_change > 0 else
               f"the average Q1 change was {_number(mean_change)} pp")
    slope = m3["regression"]["terms"].get("q4_delta", {}).get("coefficient")
    m3_direction = ("Hệ số dương cho thấy trong cùng ngân hàng, lần giảm sâu hơn ở Quý 4 đi cùng mức tăng nhỏ hơn ở Quý 1 "
                    "(giảm một phần vẫn kéo dài sang quý sau)." if slope is not None and slope > 0 else
                    "Dấu của ước lượng chưa cho thấy mức giảm Quý 4 kéo dài một phần sang Quý 1.")
    m3_direction_en = ("The positive slope indicates partial persistence: within a bank, a larger Q4 fall goes with a smaller Q1 rise."
                       if slope is not None and slope > 0 else
                       "The slope does not point to partial persistence of Q4 falls into Q1.")
    dates = m6["coverage"]
    event_span = "–".join(value for value in [m6["period_start"], m6["period_end"]] if value is not None)
    deadline = m6["regressions"]["deadline_only"]
    preferred = m6["regressions"]["reported_or_deadline"]
    expected = "expected_d_npl_pct"
    surprise = "surprise_d_npl_pct"
    preferred_wild = [preferred["terms"].get(term, {}).get("wild_p") for term in [expected, surprise]]
    if None in preferred_wild:
        interpretation = ("Mẫu không đủ để kiểm định cả hai hệ số.", "The sample cannot support a test of both slopes.")
    elif preferred_wild[0] >= .05 and preferred_wild[1] < .05:
        interpretation = ("Ở ngưỡng 5%, chỉ phát hiện liên hệ của phần bất ngờ; cần xem độ rộng KTC của phần dự kiến.",
                          "At 5%, only the surprise association is detected; check the width of the expected component's interval.")
    else:
        interpretation = ("Ở ngưỡng 5%, mẫu chưa cho thấy phản ứng chỉ tập trung vào phần bất ngờ.",
                          "At 5%, the estimates do not show a reaction confined to the surprise component.")
    surprise_term = preferred["terms"].get(surprise, {})
    if (surprise_term.get("p") is not None and surprise_term.get("wild_p") is not None
            and surprise_term["p"] < .05 <= surprise_term["wild_p"]):
        interpretation = (
            "Khoảng theo cụm của phần bất ngờ loại 0, nhưng wild bootstrap không bác bỏ hệ số bằng 0 ở ngưỡng 5%.",
            "The clustered interval for surprise excludes zero, but the wild bootstrap does not reject a zero slope at 5%.",
        )
    errors = m7["backtest"]["mae_pp"]
    roa_n = sum(row["roa_pct_count"] for row in m1["by_period"])
    screening_fits = m5.get("screening_seasonal", {})
    screening_vi = " ".join(
        f"Quý 4 so với Quý 1, {SCREENING_LINKAGE[key][0]}: {_term_text(fit, 'Q4')}, điểm %."
        for key, fit in screening_fits.items()
    )
    screening_en = " ".join(
        f"Q4 versus Q1, {SCREENING_LINKAGE[key][1]}: {_term_text(fit, 'Q4', english=True)}, pp."
        for key, fit in screening_fits.items()
    )
    vi = [
        (f"NPL trung vị là {_number(first['npl_pct_median'])}% ở {first['period']} "
         f"và {_number(last['npl_pct_median'])}% ở {last['period']}. Có {roa_n} quan sát ROA hợp lệ. "
         "Bảng sở hữu cho mỗi ngân hàng-quý trọng số bằng nhau.",
         "Trung vị và trung bình mẫu không phải tỷ lệ nợ xấu gộp theo dư nợ của toàn hệ thống."),
        (f"So với Quý 1 của cùng ngân hàng, hệ số biến động NPL Quý 4 là {_term_text(m2['baseline'], 'Q4')} điểm %.",
         "Hệ số mùa vụ mô tả biến động báo cáo. Nguyên nhân có thể gồm xử lý nợ, tăng dư nợ hoặc thay đổi chất lượng tín dụng."),
        (f"Giai đoạn {span}, NPL giảm rồi tăng ở {summary['reversals']}/{summary['n']} cặp Quý 4–Quý 1 "
         f"({_number(summary['share_pct'], 1)}%) và {mean_vi}. "
         f"Hệ số Quý 1 theo Quý 4 là {_term_text(m3['regression'], 'q4_delta')}. {m3_direction} {rebound['reading_vi']}",
         "Hai chênh lệch dùng chung mức NPL tại Quý 4. Mối liên hệ không chứng minh nợ đã được chuyển kỳ."),
        (f"Sau 2022, chênh lệch hiệu ứng Quý 4 của nhóm NPL cao so với nhóm còn lại là "
         f"{_term_text(m4['regression'], 'Q4_high_npl')} điểm %. Chênh lệch của nhóm Nhà nước là "
         f"{_term_text(m4['regression'], 'Q4_state')} điểm %.",
         "Tương tác so sánh mẫu hình theo nhóm. Thiết kế không nhận diện tác động nhân quả của sở hữu hoặc NPL ban đầu."),
        (f"So với Quý 1, hệ số Quý 4 của thay đổi bao phủ là "
         f"{_term_text(m5['seasonal']['d_coverage_pct'], 'Q4')} điểm %. Nguồn FiinQuant không trả ROA. {screening_vi}".strip(),
         "Các thay đổi đồng thời có thể phản ánh mẫu số chung, điều chỉnh kế toán hoặc yếu tố khác chưa đo được."),
        (f"Từ {event_span or 'mẫu hiện có'}, có {dates['actual_date_n']}/{dates['bank_quarters_n']} ngân hàng-quý có ngày thực tế, "
         f"{dates['actual_date_car_n']} có CAR quanh ngày đó. Ưu tiên ngày thực tế cho hệ số dự kiến "
         f"{_term_text(preferred, expected)} và bất ngờ {_term_text(preferred, surprise)}; "
         f"dùng hạn cho mọi sự kiện cho hệ số tương ứng {_term_text(deadline, expected)} và {_term_text(deadline, surprise)}. "
         f"{interpretation[0]}",
         "Mô hình ước lượng mùa vụ từ toàn mẫu sau khi bỏ sự kiện đang xét, khác với kỳ vọng của nhà đầu tư tại ngày công bố. "
         "Sổ công bố thiếu giờ và phạm vi BCTC. Tin khác trong cửa sổ có thể ảnh hưởng CAR."),
        (f"Trên {m7['backtest']['n']} ngân hàng-quý giai đoạn 2025Q1–2026Q3, MAE mô hình là "
         f"{_number(errors['model'])} điểm %, so với {_number(errors['naive'])} khi giữ mức gần nhất "
         f"và {_number(errors['seasonal_naive'])} khi dùng cùng quý năm trước.",
         "Kiểm định dùng dữ liệu lịch sử hiện có. Khoảng dự báo thực nghiệm không bảo đảm độ bao phủ trong tương lai."),
    ]
    en = [
        (f"Median NPL was {_number(first['npl_pct_median'])}% in {first['period']} "
         f"and {_number(last['npl_pct_median'])}% in {last['period']}; {roa_n} observations had usable ROA.",
         "The sample median and mean do not measure the loan-weighted NPL ratio of the banking system."),
        (f"The Q4 change relative to Q1 in the same bank is {_term_text(m2['baseline'], 'Q4', english=True)} pp.",
         "The seasonal pattern cannot distinguish debt resolution, loan growth and changes in credit quality."),
        (f"In {span}, NPL fell then rose in {summary['reversals']} of {summary['n']} Q4–Q1 pairs "
         f"({_number(summary['share_pct'], 1)}%) and {mean_en}. The slope is "
         f"{_term_text(m3['regression'], 'q4_delta', english=True)}. {m3_direction_en} {rebound['reading_en']}",
         "The changes share the Q4 level and do not show that loans moved across reporting quarters."),
        (f"From 2023, the Q4 effect differs by {_term_text(m4['regression'], 'Q4_high_npl', english=True)} pp "
         f"for banks with high starting NPL and by {_term_text(m4['regression'], 'Q4_state', english=True)} pp for state banks.",
         "The design does not identify a causal effect of ownership or starting NPL."),
        (f"The Q4 change in coverage relative to Q1 is {_term_text(m5['seasonal']['d_coverage_pct'], 'Q4', english=True)} pp; "
         f"FiinQuant has no ROA observations. {screening_en}".strip(),
         "Common denominators, accounting adjustments and unmeasured factors may contribute."),
        (f"In {event_span or 'the available sample'}, {dates['actual_date_n']}/{dates['bank_quarters_n']} bank-quarters have "
         f"actual dates and {dates['actual_date_car_n']} have CAR on those dates. Using actual dates when available gives "
         f"expected {_term_text(preferred, expected, english=True)} and surprise {_term_text(preferred, surprise, english=True)}; "
         f"the all-deadline estimates are {_term_text(deadline, expected, english=True)} and "
         f"{_term_text(deadline, surprise, english=True)}, respectively. {interpretation[1]}",
         "The model uses the full sample excluding the event, so it does not estimate real-time investor expectations. "
         "The register omits intraday timing and filing basis. Concurrent news can affect CAR."),
        (f"In the 2025Q1–2026Q3 test (n={m7['backtest']['n']}), model MAE is {_number(errors['model'])} pp, "
         f"versus {_number(errors['naive'])} for the last value and {_number(errors['seasonal_naive'])} for the same quarter a year earlier.",
         "Historical errors and interval coverage do not guarantee future performance."),
    ]
    return zip(vi, en)


def _findings(models):
    m2, m3, m6, m7 = (models[f"M{i}"] for i in [2, 3, 6, 7])
    q4 = m2["baseline"]
    pairs = m3["summary"]
    market = m6["regressions"]["reported_or_deadline"]
    dates = m6["coverage"]
    flags = m7["decision_rule"]["q4_backtest"]["unusual"]
    forecasts = m7["backtest"]
    errors = forecasts["mae_pp"]
    best = min(errors, key=lambda key: errors[key] if np.isfinite(errors[key]) else np.inf)
    vi_names = {"model": "mô hình", "naive": "mức quý trước", "seasonal_naive": "cùng quý năm trước"}
    en_names = {"model": "the model", "naive": "the last value", "seasonal_naive": "the same quarter last year"}
    vi, en = [], []
    regression = models["decoder"]["regression"]
    notes_fit = regression["notes"]["full"]
    vendor = regression["fiinquant"]
    decoder_fit = notes_fit if notes_fit["terms"] else (vendor["available"] or vendor["full"])
    if decoder_fit["terms"].get("lagged_coverage", {}).get("ci95"):
        span = "–".join(decoder_fit["period"])
        source = (("ghi chú BCTC", "financial statement notes") if decoder_fit is notes_fit else
                  ("rút gọn FiinQuant", "reduced FiinQuant") if vendor["available"] else ("FiinQuant", "FiinQuant"))
        vi.append(f"Trong {span}, hồi quy {source[0]} có hệ số bao phủ quý trước "
                  f"{_term_text(decoder_fit, 'lagged_coverage', digits=4)}, vì vậy hãy dùng thay đổi bao phủ hiện tại để rà soát "
                  "cờ vàng và đọc hệ số quý trước như liên hệ trong dữ liệu.")
        en.append(f"In {span}, the {source[1]} regression gave a lagged-coverage slope of "
                  f"{_term_text(decoder_fit, 'lagged_coverage', english=True, digits=4)}, so use the current change in coverage "
                  "for flagging and read the lagged estimate as an association.")
        if decoder_fit is notes_fit:
            vi[-1] += " Mẫu ghi chú chỉ gợi ý chiều liên hệ."
            en[-1] += " The notes sample supports directional interpretation."
    if q4["terms"].get("Q4", {}).get("ci95"):
        span = "–".join(q4["period"])
        vi.append(f"Trong {span}, hệ số thay đổi NPL Quý 4 so với Quý 1 là {_term_text(q4, 'Q4')} điểm phần trăm, "
                  "vì vậy hãy kiểm tra mùa vụ khi rà soát NPL cuối năm.")
        en.append(f"In {span}, the Q4 NPL change relative to Q1 was {_term_text(q4, 'Q4', english=True)} percentage points, "
                  "so account for seasonality when reviewing year-end NPL.")
    if pairs["n"] and m3["regression"]["terms"].get("q4_delta", {}).get("ci95"):
        span = "–".join(pairs["period"])
        slope = m3["regression"]
        vi.append(f"Trong {span}, {pairs['reversals']}/{pairs['n']} cặp giảm rồi tăng, với hệ số Quý 1 theo Quý 4 "
                  f"{_term_text(slope, 'q4_delta')} và thay đổi Quý 1 bình quân {_number(pairs['mean_next_q1_change_pp'])} "
                  "điểm phần trăm, vì vậy hãy đọc diễn biến của từng ngân hàng bên cạnh mức bình quân.")
        en.append(f"In {span}, {pairs['reversals']}/{pairs['n']} pairs fell then rose, with a Q1-on-Q4 slope of "
                  f"{_term_text(slope, 'q4_delta', english=True)} and a mean Q1 change of "
                  f"{_number(pairs['mean_next_q1_change_pp'])} percentage points, so review each bank alongside the average.")
    expected, surprise = "expected_d_npl_pct", "surprise_d_npl_pct"
    if all(market["terms"].get(term, {}).get("ci95") for term in [expected, surprise]):
        span = "–".join(market["period"])
        coverage = f"{dates['actual_date_n']}/{dates['bank_quarters_n']}"
        vi.append(f"Trong {span}, CAR có hệ số phần dự kiến {_term_text(market, expected)} và phần bất ngờ "
                  f"{_term_text(market, surprise)} với độ phủ ngày công bố thực tế {coverage}, vì vậy hãy đối chiếu "
                  "kết quả quanh ngày thực tế trước khi kết luận về phản ứng của nhà đầu tư.")
        en.append(f"In {span}, CAR slopes were {_term_text(market, expected, english=True)} for expected change "
                  f"and {_term_text(market, surprise, english=True)} for surprise with {coverage} actual-date coverage, "
                  "so check the result around actual dates before drawing a conclusion about investor reactions.")
    if flags["ci95"]:
        span = "–".join(flags["period"])
        bounds = ", ".join(_number(bound, 1) for bound in flags["ci95"])
        amount = f"{_number(flags['share_pct'], 1)}%"
        vi.append(f"Trong {span}, {amount} cờ khác thường Quý 4 đảo chiều ở Quý 1 "
                  f"(n={flags['n']}, KTC bootstrap theo ngân hàng 95% [{bounds}]%), vì vậy hãy dùng cờ để ưu tiên rà soát.")
        en.append(f"In {span}, {amount} of unusual Q4 flags reversed in Q1 "
                  f"(n={flags['n']}, bank-bootstrap 95% CI [{bounds}]%), so use flags to prioritize review.")
    intervals = forecasts["mae_difference_vs"]
    if forecasts["n"] and all(intervals[key]["ci95"] for key in ["naive", "seasonal_naive"]):
        span = "–".join(m7["test_period"])
        bounds = ["[" + ", ".join(_number(bound, 3) for bound in intervals[key]["ci95"]) + "]"
                  for key in ["naive", "seasonal_naive"]]
        vi.append(f"Trong {span}, MAE mô hình là {_number(errors['model'], 3)} điểm phần trăm "
                  f"(n={forecasts['n']}, KTC 95% chênh lệch MAE so với mức quý trước {bounds[0]} và cùng quý năm trước "
                  f"{bounds[1]}), vì vậy hãy ưu tiên {vi_names[best]} theo sai số quan sát được.")
        en.append(f"In {span}, model MAE was {_number(errors['model'], 3)} percentage points "
                  f"(n={forecasts['n']}, 95% CI for the MAE difference versus last value {bounds[0]} and versus "
                  f"the same quarter last year {bounds[1]}), so favor {en_names[best]} based on observed errors.")
    return [dict(vi=local, en=english) for local, english in zip(vi, en)]


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
        "M5": {**m5["seasonal"], **m5.get("screening_seasonal", {})}, "M6": m6["regressions"],
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
    _chart(folder, "event_study_car.png", "Lợi suất bất thường tích lũy quanh mốc công bố", "CAR trung bình (%)", car)
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
    m2, _ = seasonal_models(main)
    m3 = reversal(main)
    m4 = heterogeneity(main)
    screening = tables.get("fiin_screening")
    screening_amounts = statement_amounts(None, screening=screening)[0] if screening is not None else None
    m2["h1"] = seasonal_hypotheses(main)
    m2["by_size"] = loan_size_subgroups(main, screening_amounts)
    m2["policy_robustness"] = policy_robustness(main, tables.get("legal_register"))
    precise, _ = clean_quarters(tables["bank_quarter"], round_digits=None)
    rebound_panel = precise.loc[precise.basis.eq("consolidated")]
    m3["baselines"] = rebound_baselines(rebound_panel)
    m5 = linkage(main, screening_amounts)
    m7, adjusted = forecast(main)
    m7["decision_rule"], decisions = decision_rule(main)
    add_rebound_baseline(m7["decision_rule"], rebound_panel, decisions, m3["baselines"])
    regimes = {period for period, active in (m2["policy_robustness"].get("quarter_regime") or {}).items() if active}
    decoder = build_decoder(main, decisions, tables.get("notes_bank_quarter"), screening, regimes=regimes)
    disclosure = tables.get("disclosure_dates")
    if disclosure is not None and "valid" in getattr(disclosure, "columns", []):
        disclosure = disclosure.loc[disclosure["valid"].map(lambda value: str(value).strip().lower() in {"1", "true", "yes"})]
    m6, events = market_study(main, market, calendar, None if disclosure is None or not len(disclosure) else disclosure)
    decision_data = decisions.drop(columns=["d_npl_pct", "status_vi", "status_en"]).rename(
        columns={"adjusted_change_pp": "adjusted_d_npl_pct", "status": "decision_status"})
    events = events.merge(decision_data, on=["bank_code", "period"], validate="one_to_one")
    m1["dashboard"] = dashboard_metrics(main.assign(adjusted_d_npl_pct=decisions["adjusted_change_pp"]))
    signals = {bank: [] for bank in m1["dashboard"]["banks"]}
    for row in decoder["rows"]:
        if row["period"] in decoder["periods"]:
            signals[row["bank_code"]].extend({**signal, "period": row["period"]} for signal in row["signals"])
    for bank, card in m1["dashboard"]["banks"].items():
        card["signals"] = signals[bank]
    m1["dashboard"]["signal_availability"] = decoder["signal_availability"]
    m1["mechanism"] = mechanism(tables.get("notes_bank_quarter"), tables.get("case_tcb"))
    m1["context"] = policy_context(main, tables.get("wdi_bank"), tables.get("legal_register"))
    panel["seasonally_adjusted_npl_pct"] = adjusted["seasonally_adjusted_npl_pct"]
    models = {f"M{i}": result for i, result in enumerate([m1, m2, m3, m4, m5, m6, m7], start=1)}
    for result, ((vi, vi_limit), (en, en_limit)) in zip(models.values(), _readings(models)):
        result.update(reading=vi, what_this_does_not_show=vi_limit,
                      reading_en=en, what_this_does_not_show_en=en_limit)
    vendor_fit = decoder["regression"]["fiinquant"]
    if vendor_fit["available"] is not None:
        m5["reading"] += " " + vendor_fit["reading_vi"]
        m5["reading_en"] += " " + vendor_fit["reading_en"]
    models["decoder"] = decoder
    models["M8"] = run_market_model(silver)
    models["decomposition"] = decompose_screening(screening, tables.get("notes_bank_quarter"))
    models["scorecard"] = build_scorecard(main, screening, tables.get("valuation_daily"), tables.get("legal_register"))
    models["pdf_audit"] = publish_audit(screening, tables.get("notes_bank_quarter"))
    models["M9"] = early_warning(rebound_panel, screening, models["decomposition"]["quarantine"])
    models["M10"] = seasonal_adjustment(rebound_panel)
    legacy = m6["regressions"].get("deadline_only", {}).get("terms", {}).get("surprise_d_npl_pct")
    m6["windows"] = window_study(market, events, legacy_surprise=legacy)
    models["multiple_testing"] = adjust_pvalues(models)
    m1["findings"] = _findings(models)
    changed = int(calendar["deadline"].ne(calendar["silver_deadline"]).sum())
    audit = ["# Nhật ký làm sạch dữ liệu NPL", "", "| Bước | Dòng trước | Dòng sau | Thực hiện |", "|---|---:|---:|---|"]
    # Avoid treating literal pipes in thresholds as Markdown cell separators.
    for step in steps:
        detail = step["detail"].replace("|", "\\|")
        audit.append(f"| {step['step']} | {step['before']} | {step['after']} | {detail} |")
    audit.extend(["", f"Lịch sự kiện có {changed}/{len(calendar)} mốc khác lịch Silver khi áp dụng hạn 30 ngày "
                  f"cho báo cáo hợp nhất của công ty mẹ niêm yết. [Khoản 3 Điều 14]({DEADLINE_SOURCE})."])
    audits = {
        "bank_quarter": f"{len(panel)} khóa chuẩn, {len(main)} dòng hợp nhất dùng trong mô hình.",
        "bank_annual": f"{m1['annual_q4_check']['npl_pairs']} cặp NPL năm–Q4 cùng phạm vi.",
        "field_map_ratios": "Kiểm kê ánh xạ tên trường; các tỷ lệ đi qua quy tắc chuẩn hóa của bảng quý.",
        "price_daily": f"{len(market)} dòng theo phiên VNINDEX; {market.return_pct.count()} lợi suất liền phiên.",
        "valuation_daily": f"Kiểm tra trùng khóa ngày; {(market.pe.notna() | market.pb.notna()).sum()} dòng giá có PE hoặc PB.",
        "foreign_daily": f"Kiểm tra trùng khóa ngày; {market.filter(like='foreign_').notna().any(axis=1).sum()} dòng giá ghép được.",
        "report_calendar": f"{len(calendar)} quý hợp lệ với hạn chuẩn, giữ hạn Silver để đối chiếu.",
        "disclosure_dates": f"{m6['coverage']['actual_date_n']} ngày hợp lệ sau cuối quý ghép được theo ngân hàng và quý.",
        "legal_register": f"{m1['context']['policy']['timeline_n']} văn bản giữ nguyên nhóm nợ, đối chiếu ngày với văn bản gốc và lưu các mốc Silver.",
        "sbv_system": "Kiểm kê bảng hệ thống theo tháng; các mô hình ngân hàng-quý không dùng trường này.",
        "wdi_bank": f"{m1['context']['wdi']['n']} quan sát NPL quốc gia–năm hợp lệ trong nhóm so sánh.",
        "case_tcb": "Chỉ dùng trường số dư xác định được trang và URL, giữ riêng nguồn TCB.",
        "notes_bank_quarter": "Giữ BCTC hợp nhất có trang và nguồn, lấy số dư cuối kỳ và xóa nợ theo quý, loại contested và số xung đột.",
        "notes_links": "Ghép phạm vi BCTC theo ngân hàng, quý và URL; dòng phạm vi không xác định chưa dùng cho bộ giải mã.",
        "notes_gate": "Kiểm kê các kết quả đối chiếu từ B5.",
        "fiin_screening": "Dùng trường đã qua đối chiếu. Dự phòng sử dụng trong quý là chỉ báo thay thế cho xóa nợ.",
    }
    audit += ["", "## Kiểm kê Silver", "", "| Tệp | Dòng đọc | Xử lý |", "|---|---:|---|"]
    for name, detail in audits.items():
        count = len(tables[name]) if name in tables else "Chưa có tệp"
        audit.append(f"| {name} | {count} | {detail} |")
    for name in ("case_tcb", "notes_bank_quarter"):
        count = sum(row["source"] == name for row in m1["mechanism"]["provenance"])
        audit.append(f"\n- {name}: {count} trường có nguồn sử dụng được cho phân tích cơ chế.")
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
        insights = ["# Phát hiện phục vụ ra quyết định / Findings for decisions", ""]
        insights += [f"{i}. {row['vi']}\n\n   {row['en']}\n" for i, row in enumerate(m1["findings"], start=1)]
        (stage / "insights.md").write_text("\n".join(insights), encoding="utf-8")
        _write_tables(stage, models)
        _plots(stage, models)
        for artifact in stage.iterdir():
            artifact.replace(out / artifact.name)
