---
duration: 90
steps:
  - {at: 0, route: /, action: overview}
  - {at: 10, route: /insights, action: story}
  - {at: 35, route: /, action: inspect}
  - {at: 55, route: /pipeline, action: pipeline}
  - {at: 70, route: /decision, action: decision}
  - {at: 85, route: /report, action: export}
---

# Kịch bản demo dự phòng

| Giây | Thao tác | Thuyết minh VI | English narration |
| --- | --- | --- | --- |
| 0–10 | Tổng quan và KPI | Mở câu hỏi quyết định và chỉ tiêu chính từ đề bài. | Start with the decision question and the primary KPI. |
| 10–35 | Câu chuyện | Đọc bằng chứng, kiểm định và hành động đề xuất. | Review the finding, the test and the proposed action. |
| 35–55 | Hỏi AI trên một thẻ KPI | Hỏi chỉ số này đo gì và xem nguồn trả lời. | Inspect the KPI and review the evidence behind the explanation. |
| 55–70 | Pipeline | Truy ngược bảng gold về nguồn và đọc độ phủ ghép. | Trace the gold table to its sources and review join coverage. |
| 70–85 | Quyết định | Nêu người ra quyết định, bước tiếp theo và hạn chế. | Identify the decision maker, next action and limitation. |
| 85–90 | Xuất báo cáo | Mở hộp thoại ZIP song ngữ để chuẩn bị bàn giao. | Open the bilingual ZIP export dialog. |

Chạy API và web trước. Chọn dataset công khai, chạy `make screenshots` và `make demo-video`, rồi kiểm tra clip trong `out/demo/demo.webm`. Dùng lời đọc song ngữ trong bảng để thu âm riêng. Khi dữ liệu thi được công bố, chạy lại với `DATASET=<id>` và chọn ảnh phù hợp cho phụ lục deck. Đội trưởng chia sẻ clip theo thể thức của BTC.
