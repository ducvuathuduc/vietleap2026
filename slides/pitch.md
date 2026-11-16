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

<!-- 0:00–0:40 · HOOK. Một con số từ dữ liệu + vì sao quan trọng bây giờ. Một câu mở đầu bằng con người, không bằng dữ liệu. -->

---

## 0 · Câu hỏi quyết định

> *Đề bài:* “[câu hỏi đầu tiên của đề — trích nguyên văn từ brief.json, không sửa, không dịch]”

- **Ai quyết định:** [decision_template.who — Sở Tài chính / UBND tỉnh / doanh nghiệp…; để trống "____" nếu đề không nêu]
- **Quyết định gì:** [decision_template.what]
- **Ở đâu:** [decision_template.where]
- **KPI thành công:** [decision_template.kpi]

<!-- 0:40–1:20 · Ai cần quyết định gì + KPI thành công. Chưa phân tích đề (python de.py brief / trang Đề bài) thì bản tự sinh ghi "(no brief — generic question)". -->

---

## 1 · Dữ liệu & pipeline

- **Ingestion:** [n] nguồn ([file / API / SQL / scraping / social]) — có provenance (nguồn, thời điểm tải, giấy phép)
- **Storage:** DuckDB bronze → silver → gold (giữ dữ liệu thô để audit)
- **Transform:** missing · duplicate · outlier (gắn cờ, không xoá) — điểm chất lượng [trước] → [sau]
- **Mô hình:** OBT phục vụ dashboard; Star schema để trình bày; Snowflake/Data Vault dựng để chứng minh truy vết
- **Serving:** dashboard + AI Analyst chỉ trả lời bằng số từ bảng gold

<!-- 1:20–2:10 · Một slide duy nhất. Nói đúng thuật ngữ workshop 16/11. Một câu "vì sao OBT + Star chứ không Data Vault trong 28 giờ". Mở trang Pipeline nếu demo trực tiếp. -->

---

## 2.1 · [Insight 1 — tiêu đề]

[Câu phát hiện từ engine: nhóm cao nhất/thấp nhất, chênh bao nhiêu lần, n]

*Kiểm định: [test] · [p] · [effect size]*

<!-- 2:10–2:50 · Con số → ý nghĩa cho quyết định → một lưu ý. Insight gắn với khuyến nghị đứng trước; p ≥ 0.05 ghi "bằng chứng yếu". -->

---

## 2.2 · [Insight 2 — tiêu đề]

[Câu phát hiện]

*Kiểm định: [test] · [p]*

<!-- 2:50–3:30 -->

---

## 2.3 · [Insight 3 — tiêu đề]

[Câu phát hiện]

*Kiểm định: [test] · [p]*

<!-- 3:30–4:10 · Chọn 3 insight có effect size lớn, p nhỏ VÀ gắn trực tiếp với quyết định — không phải 3 insight "thú vị nhất". -->

---

<!-- _class: lead -->
## Demo: Câu chuyện insight + Hỏi AI

Dashboard → nút **Câu chuyện** (bước đầu = câu hỏi quyết định, bước cuối = hạn chế) → bấm **Hỏi AI** vào một biểu đồ

<!-- 4:10–5:00 · Nếu mạng lỗi: chế độ offline vẫn chạy; luôn có video dự phòng 2 phút. -->

---

## 3 · Quyết định đề xuất

**[Ai] nên [làm gì] ở [đâu/cho nhóm nào], bắt đầu từ [khi nào]**

- Vì sao: [so what — từ trang Quyết định; bằng chứng không được là insight "bằng chứng yếu"]
- Tác động ước tính: [impact — từ engine]
- Ai thực hiện: [who] · Ở đâu: [where] · KPI theo dõi: [kpi] · Kiểm chứng: thí điểm rồi chạy lại pipeline

<!-- 5:00–6:10 · Đây là slide giám khảo nhớ. Một quyết định, không phải năm. -->

---

## 4 · Tác động

[Câu what-if từ trang Drivers & What-if: tăng X thêm k% → Y thay đổi … (khoảng 90%)]

<!-- 5:00–6:10 · What-if lượng hoá khuyến nghị; minh hoạ bằng thanh trượt What-if nếu thời gian cho phép. -->

---

## 5 · Hạn chế

- Dữ liệu quan sát → liên đới, không phải nhân quả (luôn là ý đầu tiên)
- [Dữ liệu còn thiếu sau làm sạch / dòng không ghép được — số thật từ pipeline.json, quality.json]
- [Đại diện mẫu / giá chào ≠ giá giao dịch / 63→34 tỉnh…]
- Bước tiếp: ghép dữ liệu ngoài (thu nhập, dân số, hạ tầng), thí điểm

<!-- 6:10–6:40 · Nói trước khi giám khảo hỏi — hội đồng học thuật đánh giá cao sự trung thực về phương pháp. -->

---

<!-- _class: lead -->
## Kết

**[Nhắc lại một câu khuyến nghị số 1]**

<!-- 6:40–7:00 · Một câu khuyến nghị + cảm ơn. -->
