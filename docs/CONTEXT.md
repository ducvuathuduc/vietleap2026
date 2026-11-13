# Bối cảnh cuộc thi — VietLeap Hackathon 2026 "From Data to Decision"

Tổng hợp từ website/poster/agenda BTC (vietleap2026.com) và bài test đầu vào. Phần "suy ra" là **giả thuyết** để chuẩn bị, không phải thông tin BTC công bố.

## 1. Tổ chức & lịch

- **Đồng tổ chức:** UEH School of Public Finance (Trường Tài chính công, ĐH Kinh tế TP.HCM) và AVSE Global — Economic Policy Network.
- **Đối tác / nhà tài trợ:** FiinGroup (dữ liệu thị trường & doanh nghiệp VN), Goodenough College / Goodstart Fellow (dự án tác động cộng đồng).
- **Giải nhất:** 25.000.000 VND.
- **Hai track:** Data & Analytics (pipeline + dashboard) và Presentation (câu chuyện ra quyết định).

| Thời gian (giờ VN) | Sự kiện |
|---|---|
| 16/11 19:00 (online) | Workshop *Hướng dẫn xây dựng luồng dữ liệu & dashboard chuyên nghiệp* — Lưu Đức Cảnh, Data Engineer, Tasco |
| 19/11 15:30 | Chi-Yu Lee (University of Konstanz) — *From observation to data*: object tracking trong computer vision |
| 20/11 09:00 | Công bố đề + chia đội ngẫu nhiên |
| 20/11 10:00 | Viet Nguyen-Tien (LSE) — *Unlocking the Data Economy* |
| 20/11 11:00 | Sacha Dray (World Bank Việt Nam) — workshop Dashboard |
| 21/11 13:00 | Hạn nộp bài |
| 21/11 13:15 | Pitch |

Hội đồng giám khảo có thành viên từ UEH, Western Sydney, Coventry, Roehampton, FiinGroup → thiên học thuật + thực tiễn dữ liệu: sẽ hỏi về kiểm định, nhân quả, hạn chế, mô hình dữ liệu.

## 2. Nội dung workshop 16/11 (khung chấm phần pipeline)

- **4 giai đoạn:** Ingestion → Storage → Transform → Serving.
- **Nguồn:** Database/JDBC, Public API, file tải trực tiếp, Web Scraping, Social listening (quyền truy cập, giới hạn API, chống chặn).
- **Làm sạch:** missing, duplicate, outlier.
- **Mô hình dữ liệu:** OBT, Star Schema, Snowflake, Data Vault — chọn "phù hợp quy mô và thời gian hackathon".

Kit đáp ứng: connector đủ loại nguồn (`engine/vlkit/de/connectors.py`), DuckDB bronze/silver/gold, báo cáo chất lượng trước/sau, sinh cả 4 mô hình + ERD, lineage và provenance hiển thị trên dashboard.

## 3. Nhà tài trợ/diễn giả → miền đề có thể ra

| Tín hiệu | Miền đề có thể ra | Câu hỏi quyết định điển hình | Pack trong kit | Đề mẫu |
|---|---|---|---|---|
| UEH School of Public Finance | Ngân sách tỉnh, thu–chi NSNN, thuế, chuyển giao, tự chủ ngân sách (63 → 34 tỉnh theo NQ 202/2025/QH15) | Ưu tiên phân bổ ngân sách/đầu tư công cho tỉnh/vùng nào? | `public_finance_province` | `ngan_sach_tinh.md` |
| AVSE Economic Policy Network | Chính sách vĩ mô: tăng trưởng, lạm phát, việc làm, lương tối thiểu, FDI, thương mại | Chính sách nào gắn với kết quả tốt hơn, cho nhóm nào? | `economic_policy` | `chinh_sach_luong.md` |
| FiinGroup | Doanh nghiệp niêm yết, báo cáo tài chính, ngành, sàn (HOSE/HNX/UPCoM) | Ngành/nhóm DN nào hiệu quả (ROE, đòn bẩy) — khuyến nghị cho nhà đầu tư/cơ quan quản lý | `listed_firms_market` | `firms_roe.md` |
| LSE — *Unlocking the Data Economy* | Dữ liệu mở/dữ liệu thay thế, tin đăng BĐS, giá nhà–khả năng chi trả, giá trị của dữ liệu | Khu vực nào kém khả năng chi trả; dữ liệu mở giúp chính sách nhà ở thế nào | `data_economy_property` | `bds_gia_m2.md`, `bds_gia_thue.md`, `du_lieu_mo_bds.md` |
| World Bank VN — Dashboard | Chỉ số phát triển WDI, so sánh quốc tế/ASEAN, nghèo, bất bình đẳng, nợ công, thu thuế | Việt Nam lệch bao xa so với nhóm so sánh; ưu tiên cải thiện chỉ số nào | `development_indicators` | `wdi_tax_revenue.md`, `wdi_no_cong.md`, `chi_so_phat_trien.md` |
| Goodstart Fellow | Y tế, giáo dục, môi trường (PM2.5), wellbeing, cộng đồng | Can thiệp ở đâu/cho ai đem lại tác động xã hội lớn nhất | `social_impact` | `tac_dong_xa_hoi.md` |
| Chi-Yu Lee — object tracking | Video/camera → đếm xe/người, lưu lượng, ùn tắc | Điều chỉnh tín hiệu/hạ tầng ở nút nào, giờ nào | `cv_observation` | `dem_xe_giao_thong.md` |

## 4. Điều BTC coi trọng (suy ra)

1. **Provenance & minh bạch phương pháp** — bài test đầu vào yêu cầu tự thu thập Google Trends và ghi nguồn, ngày tải, cài đặt.
2. **Từ dữ liệu tới quyết định** — tên cuộc thi; khuyến nghị phải nói rõ ai, làm gì, ở đâu, đo bằng KPI nào.
3. **Pipeline chuyên nghiệp** — workshop 16/11 dạy đúng 4 giai đoạn và các mô hình dữ liệu; nhiều khả năng giám khảo hỏi "vì sao chọn mô hình này".
4. **Ngôn ngữ chính sách công, evidence-based** — nói liên đới, không khẳng định nhân quả từ dữ liệu quan sát; luôn có slide Limitations.
5. **Dùng được bởi đội ngẫu nhiên** — kit phải chạy trên laptop yếu, người không code vẫn dùng dashboard.
