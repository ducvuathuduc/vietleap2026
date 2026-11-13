# PLAYBOOK hôm thi — VietLeap 2026 "From Data to Decision"

Giờ Việt Nam (Asia/Saigon). Đội ngẫu nhiên 4–5 người, chưa chắc ai biết code. Mục tiêu: **một quyết định rõ ràng, có bằng chứng thống kê, truy được về dữ liệu** — không phải nhiều biểu đồ.

## 0. Trước ngày thi (16–19/11)

| Khi | Việc | Kiểm tra xong khi |
|---|---|---|
| 16/11 19:00 | Nghe workshop Lưu Đức Cảnh (Tasco): Ingestion–Storage–Transform–Serving, nguồn DB/API/file/scraping/social, missing/duplicate/outlier, OBT/Star/Snowflake/Data Vault | Ghi lại thuật ngữ giám khảo dùng → dùng đúng các từ đó trong pitch |
| 17–18/11 | Trên **laptop thi**: `git pull && make setup && make demo`; `make api` + `make web`; mở `http://localhost:3000` | 3 dataset practice có insight + deck; trang Pipeline/Chất lượng/Mô hình hiện đủ |
| 18/11 | Điền `web/.env.local` (Groq key) — thử "Hỏi AI" cả khi rút mạng (chế độ offline) | AI trả lời có số; offline không lỗi |
| 19/11 15:30 | Nghe Chi-Yu Lee (Konstanz) — object tracking. Nếu có thể ra đề video: `pip install ultralytics supervision`, tải sẵn `yolov8n.pt` (xem `scenarios/cv_counting/`) | `count.py --help` chạy |
| 19/11 tối | Sạc pin, mang ổ cắm/USB; mang sẵn `data/practice` & bản build web; ngủ đủ | — |

## 1. Vai trò trong đội ngẫu nhiên (gán trong 10 phút đầu)

| Vai | Ai hợp | Làm gì với kit | Đầu ra |
|---|---|---|---|
| **Captain / Decision owner** | người nói tốt, hiểu chính sách/kinh tế (không cần code) | Dán đề vào **Đề bài**, chốt *câu hỏi quyết định* + *ai là người ra quyết định*; giữ giờ | 1 câu "Chúng tôi khuyến nghị [ai] làm [gì] ở [đâu], đo bằng [KPI]" |
| **Data engineer** | người biết code/terminal | Upload / `de.py run sources.yaml`, bổ sung nguồn (API/scrape/SQL), kiểm tra Pipeline–Chất lượng–Mô hình, sửa lỗi | Pipeline xanh, điểm chất lượng trước/sau, provenance đầy đủ |
| **Analyst** | người biết thống kê/Excel | Đọc **Insight / Drivers & What-if / Phân khúc**, dùng **Hỏi AI** + **SQL Explorer** để kiểm chứng, chọn 3 insight | 3 insight: số, kiểm định, cỡ mẫu, caveat |
| **Storyteller / Designer** (không cần code) | người viết/thiết kế tốt | Dùng **Hướng dẫn** + **Hỏi AI** để hiểu từng biểu đồ; viết lời pitch trên `slides/pitch.md`, chỉnh `deck.pptx` (không đổi số) | Deck 7 phút + kịch bản nói |
| **Domain researcher / QA** (người thứ 5) | ai cũng được | Tìm 2–3 nguồn chính thống (GSO, Bộ Tài chính, World Bank) để đối chiếu & làm bối cảnh; soát "mọi số trên slide truy được về bảng gold" | Slide bối cảnh + checklist mục 7 MASTER_PLAN |

Đội 4 người: gộp Domain researcher vào Storyteller. Người không code **chỉ cần trình duyệt**: mọi bước dưới đây đều có trên dashboard.

## 2. Luồng làm việc trên kit

1. **Đề bài** (`/brief`): dán nguyên văn đề → kit trích câu hỏi, biến mục tiêu, đơn vị phân tích, phân khúc, loại quyết định, gói kịch bản (pack) phù hợp. Chốt target với cả đội.
2. **Upload** (nút *Upload dataset* ở sidebar) hoặc **Nguồn** (`/sources`, thêm API/SQL/scrape/RSS) → job chạy bronze → silver → gold → insight.
3. **Pipeline / Chất lượng / Mô hình**: lấy số cho slide Data pipeline, Data quality trước/sau, Data model (vì sao OBT phục vụ dashboard, Star để trình bày).
4. **Insight → Drivers & What-if → Phân khúc**: chọn insight có effect size lớn, p nhỏ, liên quan trực tiếp tới quyết định. What-if cho con số "nếu tăng X 10% thì Y ±…".
5. **Hỏi AI** (toggle ở thanh trên): bật, bấm vào bất kỳ KPI/biểu đồ/dòng bảng → AI giải thích bằng số liệu thật từ engine. Esc để thoát. **Hướng dẫn** chạy tour từng trang cho người mới.
6. **Câu chuyện** (nút ở thanh trên): một cú bấm → AI (hoặc engine khi offline) kể 5 insight mạnh nhất, tự chuyển sang trang Insight và lần lượt làm nổi bật từng thẻ/biểu đồ (←/→ chuyển, Esc thoát). Lời dẫn của AI chỉ được giữ khi mọi con số khớp với engine — dùng thẳng làm phần demo khi pitch.
7. **Quyết định** (`/decision`): khuyến nghị + mức tin cậy + caveat → chỉnh lời cho đúng ngữ cảnh chính sách.
8. **Exports → deck.pptx**, `executive_summary.html`, `dashboard.html`; lời pitch trong `slides/pitch.md`.

## 3. Lịch theo giờ (20–21/11)

| Giờ | Captain | Data engineer | Analyst | Storyteller | Researcher/QA |
|---|---|---|---|---|---|
| **20/11 09:00–09:30** | Nghe đề, chụp đề, chia vai | Bật `make api` + `make web`, tải dữ liệu đề vào `data/raw/` | Đọc đề cùng Captain | Lập file ghi chú chung | Ghi lại tiêu chí chấm |
| 09:30–10:00 | Dán đề vào **Đề bài**, chốt câu hỏi quyết định | Upload → chạy pipeline; báo lỗi định dạng | Xem **Hồ sơ dữ liệu**, cột mục tiêu đúng chưa | Phác storyline 7 phần | Tìm nguồn chính thống liên quan |
| 10:00–12:00 (talk LSE 10:00, workshop Dashboard World Bank 11:00) | Nghe talk, ghi ý có thể dùng trong pitch | Bổ sung nguồn ngoài (API/scrape) nếu đề cho phép; join theo tỉnh/năm | Lọc insight, kiểm chứng bằng SQL Explorer | Nghe workshop Dashboard → áp dụng vào bố cục demo | Đối chiếu số với nguồn chính thống |
| 12:00–13:00 | Ăn trưa; **checkpoint 1**: câu hỏi + target + dữ liệu đã sạch | — | — | — | — |
| 13:00–16:00 | Chốt 3 insight & khuyến nghị nháp | Sửa chất lượng (impute/outlier), ổn định pipeline, ghi provenance | Drivers, what-if, phân khúc cho 3 insight | Viết slide Problem, Data, Pipeline, Model | Viết slide Bối cảnh, Limitations |
| 16:00–18:00 | **Checkpoint 2**: kể thử câu chuyện 3 phút | Tạo lại deck sau khi chốt dữ liệu | Hỏi AI để rà caveat từng insight | Ráp deck + `pitch.md` | Soát "mỗi số trên slide ↔ bảng gold" |
| 18:00–22:00 | Viết khuyến nghị chính sách: ai/làm gì/ở đâu/KPI | Quay video demo dự phòng (2 phút) | Bổ sung kiểm định ổn định (segment khác, năm khác) | Hoàn thiện slide, hình | Chuẩn bị Q&A (10 câu giám khảo hay hỏi) |
| 22:00 | Về nghỉ — **đừng thức trắng** | Push code, sao lưu `out/` | — | — | — |
| **21/11 08:00–10:00** | Tập pitch lần 1 (bấm giờ 7 phút) | Kiểm tra demo chạy từ đầu trên laptop thi | Rà lại số liệu | Sửa slide theo góp ý | Đóng vai giám khảo hỏi xoáy |
| 10:00–11:00 | Tập pitch lần 2 | **11:00 đóng băng code** | — | Xuất PDF deck | Checklist nộp |
| 11:00–12:30 | Nộp bài (**trước 12:30**, hạn 13:00) | Mở sẵn dashboard + video dự phòng | — | — | Xác nhận BTC đã nhận |
| 13:15 | **Pitch** | Điều khiển demo | Trả lời câu hỏi số liệu | — | Ghi câu hỏi giám khảo |

## 4. Câu chuyện pitch 7 phút (chi tiết trong `slides/pitch.md`)

Vấn đề (0:45) → Dữ liệu & pipeline (1:15) → 3 insight (2:00) → Quyết định đề xuất (1:00) → Tác động/what-if (0:45) → Hạn chế (0:30) → Demo "Câu chuyện" + "Hỏi AI" (0:45).

## 5. Quy tắc vàng

- Mọi số trên slide phải truy được về bảng gold + câu SQL (dùng SQL Explorer). Không làm tròn sai, không bịa.
- Nói "liên quan/đi kèm", không nói "gây ra" trừ khi có thiết kế nhân quả.
- Mỗi insight: hiệu ứng, kiểm định, cỡ mẫu, caveat.
- Có slide **Provenance** (nguồn, ngày tải, giấy phép) — BTC đã đòi ở bài test đầu vào.
- Máy yếu: không chạy `npm run build` cùng lúc với pipeline.

## 6. Khi có sự cố

| Sự cố | Xử lý |
|---|---|
| Upload lỗi định dạng | `python de.py file <file> --serve` để xem log; xlsx nhiều sheet được tách thành nhiều bảng |
| AI không trả lời (mất mạng/hết quota) | Xoá khoá trong `.env.local`, restart `make web` → chế độ offline vẫn trả lời bằng số liệu engine |
| Web build hỏng | `make web-dev` hoặc mở `out/<ds>/dashboard.html` (bản tĩnh) |
| Thiếu thời gian | Bỏ nguồn bổ sung; giữ 1 dataset + 3 insight + 1 khuyến nghị chắc chắn |
