# Trả lời các câu hỏi mở (research 16/11/2026)

Chưa có đề (công bố 20/11 09:00). Mục tiêu: chuẩn bị sẵn nguồn dữ liệu, license và mặc định để ngày thi chỉ việc chạy.
Nhãn: [XÁC NHẬN] = đọc từ nguồn; [MẶC ĐỊNH] = quyết định của đội khi BTC chưa nói.

## 1. Dữ liệu ngân sách tỉnh nên thu thập (cho spec 004, gói public finance)
- [XÁC NHẬN] Mọi tỉnh phải công khai theo **Thông tư 343/2016/TT-BTC** với biểu mẫu chuẩn:
  - Dự toán: Biểu 46 (cân đối NSĐP), 47, 49 (chi NSĐP theo cơ cấu), 50 (chi cấp tỉnh theo lĩnh vực).
  - Thực hiện quý/6 tháng/năm: Biểu 59–61.
  - **Quyết toán: Biểu 62 (cân đối NSĐP), 63 (quyết toán thu NSNN), 64–68 (chi).** ← ưu tiên số 1, đã được HĐND phê chuẩn.
- [XÁC NHẬN] Nhiều tỉnh đăng kèm file **.xlsx/.xls** (ví dụ Nghệ An `DT-2026-N-B46-TT343-40.xlsx`, Vĩnh Long `B62.xls`, Thanh Hóa trên opendata.thanhhoa.gov.vn).
- [XÁC NHẬN] Cổng tổng hợp của Bộ Tài chính: https://ckns.mof.gov.vn/ (NSNN + NSĐP, có hướng dẫn khai thác Excel/PDF).
- [XÁC NHẬN] Kiểm toán Nhà nước công khai kết quả kiểm toán quyết toán NSĐP (ví dụ Quảng Ninh 2025: tổng thu 81.191.006 triệu đồng, tổng chi 66.521.780 triệu đồng) → dùng để **đối chiếu chất lượng** số liệu tỉnh.
- [MẶC ĐỊNH] Thu thập trước: Biểu 62 + 63 + 65 (quyết toán) năm 2022–2024 cho càng nhiều tỉnh càng tốt; chuẩn hóa về 34 tỉnh mới bằng bảng ánh xạ 63→34 có sẵn trong kit; đơn vị triệu đồng.
- Rủi ro: biểu mẫu mỗi tỉnh lệch cột/hàng gộp → dùng connector `file` + bước làm sạch header nhiều tầng; tỉnh chỉ có PDF thì bỏ qua (không OCR trong ngày thi).

## 2. License dữ liệu
| Nguồn | Kết luận | Ghi chú |
|---|---|---|
| IEA Global EV Data Explorer | [XÁC NHẬN] **CC BY 4.0** (ghi trên trang explorer) | Trích dẫn: "IEA (2026), Global EV Data Explorer, Licence: CC BY 4.0". Riêng gói "Global EV Outlook 2026 data" ghi "Terms of Use for Non-CC Material" → **chỉ dùng bản Explorer**. |
| vnstock | [XÁC NHẬN] **Không phải open-source OSI**; bản Community miễn phí cho cá nhân, học tập, nghiên cứu; không cấp quyền dữ liệu nguồn bên thứ ba | Dùng được cho bài thi (học tập/nghiên cứu), **không đóng gói/phân phối lại**; ghi rõ trong docs/licenses.md. Phương án thay thế: BCTC công bố trên HOSE/HNX (file PDF/Excel công khai). |
| FiinGroup | [XÁC NHẬN] Dữ liệu thương mại, có điều khoản sử dụng website riêng (hiệu lực 01/01/2026) | **Chỉ dùng khi BTC cấp** và theo điều kiện BTC đưa ra; không cào FiinTrade. |
| HDX COD-AB Việt Nam | [XÁC NHẬN] 34 tỉnh (admin 1), ranh giới 01/07/2025 | Mô tả không nhắc Hoàng Sa, Trường Sa → **chưa đạt** để chiếu công khai. |

## 3. Bản đồ 34 tỉnh (spec 008)
- [XÁC NHẬN] HDX chỉ có ranh giới cấp tỉnh, không đảm bảo thể hiện Hoàng Sa, Trường Sa.
- [MẶC ĐỊNH] Bắt buộc **thêm lớp Hoàng Sa (Đà Nẵng) và Trường Sa (Khánh Hòa)** dạng điểm/vùng có nhãn trên bản đồ; nếu không kịp thì **không chiếu bản đồ**, dùng bar chart xếp hạng 34 tỉnh.
- Ứng viên dữ liệu tham khảo: repo `lamngockhuong/vietnam-3d-map` (có Hoàng Sa, Trường Sa) — **kiểm tra license trước khi dùng**; bảng tỉnh/xã `chuongkt/vietnam-administrative-units` (Hugging Face) cho mã tỉnh.

## 4. Video cho YOLO (spec 011, ưu tiên thấp vì đề CV chỉ ~10%)
- [XÁC NHẬN] Wikimedia Commons `File:Traffic.webm` — "traffic and motos", 20 s, 1280×720, **CC BY-SA 4.0** (tác giả Anggggggela). Hợp nhất với giao thông xe máy kiểu Việt Nam.
- [XÁC NHẬN] Wikimedia `File:Dashcam_Recording_(urban).ogv` — **CC0**.
- [XÁC NHẬN] **Ultralytics YOLO (code + trọng số) là AGPL-3.0** → chạy nội bộ cho bài thi thì được; nếu public demo trên web phải công bố mã nguồn (repo đã public nên ổn), ghi vào docs/licenses.md.

## 5. Thể thức thi (chưa có thông tin công khai)
| Câu hỏi | [MẶC ĐỊNH] cho tới khi BTC trả lời |
|---|---|
| Thời lượng pitch | Chuẩn bị bản 5 phút + bản 7 phút (timeline Marp có sẵn) |
| Ngôn ngữ | Nói tiếng Việt, slide song ngữ (deck EN + pitch VI; spec 003) |
| Định dạng nộp | Nộp cả 3: link repo/dashboard, deck .pptx + PDF, báo cáo PDF 2–4 trang |
| Tiêu chí chấm | Dùng rubric suy luận trong docs/CONTEST_ANALYSIS.md (60% câu hỏi chính sách + bằng chứng + hạn chế) |
| BTC có cấp dữ liệu? | Có thể (FiinGroup là đối tác dữ liệu) → kit phải nạp được Excel nhiều sheet nhanh |
| Được dùng AI? | Khai báo minh bạch; mọi con số truy về DuckDB; chế độ offline không cần key |

Câu hỏi gửi BTC (vietleap2026@gmail.com hoặc nhóm Zalo): thời lượng và ngôn ngữ pitch, định dạng nộp, tiêu chí chấm, dữ liệu được cấp, chính sách dùng AI.

## Nguồn
- https://ckns.mof.gov.vn/ ; https://www.nghean.gov.vn/cong-khai-ngan-sach-stc ; https://vinhlong.gov.vn/ckns/cong-khai-ngan-sach-%C4%91ia-phuong-va-ngan-sach-cap-tinh/quyet-toan-ngan-sach
- https://www.sav.gov.vn/vi/bai-viet/cong-khai-ket-qua-kiem-toan-ngan-sach-dia-phuong-bao-cao-quyet-toan-ngan-sach-dia-phuong-nam-2025-cua-tinh-quang-ninh
- http://iea.org/data-and-statistics/data-tools/global-ev-data-explorer ; http://iea.org/terms
- https://github.com/thinh-vu/vnstock/blob/main/README.md ; https://fiingroup.vn/Data/pdf/FG/FGVN-Dieu-khoan-va-Dieu-kien-ENG.pdf
- https://data.humdata.org/dataset/cod-ab-vnm ; https://github.com/lamngockhuong/vietnam-3d-map ; https://huggingface.co/datasets/chuongkt/vietnam-administrative-units
- https://commons.wikimedia.org/wiki/File:Traffic.webm ; https://commons.wikimedia.org/wiki/File:Dashcam_Recording_(urban).ogv ; https://github.com/safdar-hussain1/trafficlens (ghi chú AGPL của YOLO)
