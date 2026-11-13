---
marp: true
paginate: true
title: VietLeap 2026 — Pitch 7 phút (khung)
---

<!--
KHUNG PITCH 7 PHÚT — From Data to Decision.
Bản có số liệu thật được sinh tự động cho từng dataset: out/<dataset>/pitch.md (cùng thứ tự slide).
Quy tắc: không gõ số bằng tay — mọi con số copy từ pitch.md tự sinh, trang Insight hoặc SQL Explorer.
Xem trước / xuất: npx @marp-team/marp-cli slides/pitch.md --pdf   (hoặc extension Marp cho VS Code)
-->

<!-- _class: lead -->
# [Câu hỏi quyết định, ≤ 10 từ]
### Từ [số bản ghi] bản ghi đến một quyết định

Đội [tên] · VietLeap 2026 · From Data to Decision

<!-- 0:00–0:45 · VẤN ĐỀ. Ai đang phải quyết định (Sở Tài chính / UBND tỉnh / doanh nghiệp…)? Quyết định gì? Sai thì mất gì? Một câu mở đầu bằng con người, không bằng dữ liệu. -->

---

## 1 · Dữ liệu & pipeline

- **Ingestion:** [n] nguồn ([file / API / SQL / scraping / social]) — có provenance (nguồn, thời điểm tải, giấy phép)
- **Storage:** DuckDB bronze → silver → gold (giữ dữ liệu thô để audit)
- **Transform:** missing · duplicate · outlier (gắn cờ, không xoá) — điểm chất lượng [trước] → [sau]
- **Mô hình:** OBT phục vụ dashboard; Star schema để trình bày; Snowflake/Data Vault dựng để chứng minh truy vết
- **Serving:** dashboard + AI Analyst chỉ trả lời bằng số từ bảng gold

<!-- 0:45–2:00 · Nói đúng thuật ngữ workshop 16/11. Một câu "vì sao OBT + Star chứ không Data Vault trong 28 giờ". Mở trang Pipeline nếu demo trực tiếp. -->

---

## 2.1 · [Insight 1 — tiêu đề]

[Câu phát hiện từ engine: nhóm cao nhất/thấp nhất, chênh bao nhiêu lần, n]

*Kiểm định: [test] · [p] · [effect size]*

<!-- 2:00–2:40 · Con số → vì sao người ra quyết định nên quan tâm → một lưu ý. -->

---

## 2.2 · [Insight 2 — tiêu đề]

[Câu phát hiện]

*Kiểm định: [test] · [p]*

<!-- 2:40–3:20 -->

---

## 2.3 · [Insight 3 — tiêu đề]

[Câu phát hiện]

*Kiểm định: [test] · [p]*

<!-- 3:20–4:00 · Chọn 3 insight có effect size lớn, p nhỏ VÀ gắn trực tiếp với quyết định — không phải 3 insight "thú vị nhất". -->

---

## 3 · Quyết định đề xuất

**[Ai] nên [làm gì] ở [đâu/cho nhóm nào], bắt đầu từ [khi nào]**

- Vì sao: [so what — từ trang Quyết định]
- Tác động ước tính: [impact — từ engine]
- KPI theo dõi: [chỉ số mục tiêu theo phân khúc] · Kiểm chứng: thí điểm rồi chạy lại pipeline

<!-- 4:00–5:00 · Đây là slide giám khảo nhớ. Một quyết định, không phải năm. -->

---

## 4 · Tác động

[Câu what-if từ trang Drivers & What-if: tăng X thêm k% → Y thay đổi … (khoảng 90%)]

<!-- 5:00–5:45 · Minh hoạ trực tiếp bằng thanh trượt What-if nếu thời gian cho phép. -->

---

## 5 · Hạn chế

- Dữ liệu quan sát → liên đới, không phải nhân quả
- [Đại diện mẫu / giá chào ≠ giá giao dịch / thiếu nguồn bổ sung…]
- [Dữ liệu còn thiếu sau làm sạch; outlier đã gắn cờ]
- Bước tiếp: ghép dữ liệu ngoài (thu nhập, dân số, hạ tầng), thí điểm

<!-- 5:45–6:15 · Nói trước khi giám khảo hỏi — hội đồng học thuật đánh giá cao sự trung thực về phương pháp. -->

---

<!-- _class: lead -->
## Demo: Câu chuyện insight + Hỏi AI

Dashboard → nút **Câu chuyện** → bấm **Hỏi AI** vào một biểu đồ

<!-- 6:15–7:00 · Nếu mạng lỗi: chế độ offline vẫn chạy; luôn có video dự phòng 2 phút. Kết bằng một câu nhắc lại quyết định. -->
