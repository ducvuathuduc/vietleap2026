# Business workflow — từ nguồn dữ liệu rời rạc đến dashboard/báo cáo ra quyết định

Dựa trên workshop của BTC **"Hướng dẫn xây dựng luồng dữ liệu & dashboard chuyên nghiệp"** (Lưu Đức Cảnh, Tasco — 16/11/2026 19:00)
— vòng đời dữ liệu end-to-end qua **4 giai đoạn Ingestion – Storage – Transform – Serving** — và nguyên tắc dashboard của workshop
**Sacha Dray (World Bank Việt Nam, 20/11 09:30 — lịch vietleap2026.com, 17/11)**: KPI hướng quyết định, **mỗi view trả lời một câu hỏi**.
Spec chính thức: [`specs/001-vietleap-insight-kit/spec.md`](../specs/001-vietleap-insight-kit/spec.md) §Business workflow ·
Lịch theo giờ & vai trò chi tiết: [`PLAYBOOK.md`](PLAYBOOK.md) · Lệnh: [`quickstart.md`](../specs/001-vietleap-insight-kit/quickstart.md).

> Mục 0 dựa trên slide mentor phát sau buổi 16/11; các mục 1–7 dựng từ poster/đề cương đã công bố trước đó (thuật ngữ giám khảo dùng → dùng đúng trong pitch).

## 0. Phạm vi hackathon 6 bước (slide mentor Data Engineering, 16/11) → nơi kit hiện thực

Slide mentor (phần 2, "Scope áp dụng trong Hackathon — 6 bước") yêu cầu **mỗi bước có sản phẩm cụ thể: code, báo cáo EDA, data dictionary, dashboard**
và "không bỏ qua bước nào". Bảng dưới ánh xạ từng bước vào chỗ kit đã làm, và ghi rõ **khoảng trống** (danh sách đầy đủ: [`MASTER_PLAN.md`](MASTER_PLAN.md) §0 "Gaps").

| # | Bước (mentor) | Sản phẩm mentor đòi | Kit hiện thực ở đâu | Khoảng trống |
|---|---|---|---|---|
| 1 | **Chọn domain** (ưu tiên kinh tế; team hiểu nghiệp vụ, có API/open data, phạm vi vừa đủ) | Lý do chọn domain | 7 scenario pack `scenarios/packs/*.yaml` (tài chính công tỉnh, DN niêm yết, chỉ số phát triển, chính sách kinh tế, BĐS/dữ liệu mở, tác động xã hội, CV); trang **Đề bài** / `de.py brief` chọn pack theo từ khoá → `brief.json` | Chưa có pack riêng cho ngân hàng–tín dụng–tỷ giá, thương mại/XNK, lao động–dân số, bán lẻ, du lịch (engine vẫn chạy với domain `generic`); pack vĩ mô theo tháng chưa có |
| 2 | **Xác định nguồn & cách lấy** (A DB/JDBC · B Public API · C file · D scraping · E social) + job chuẩn DE (idempotent, watermark, retry/backoff, logging, giữ raw) | Code thu thập chạy lại được | `engine/vlkit/de/connectors.py` (`file`, `api` có paging/rate-limit/retry `tenacity` exponential + `Retry-After`/cache `data/cache/`, `sql` SELECT-only, `scrape` tôn trọng robots.txt, `social` RSS/Trends, `cv`); `sources.yaml` + `de.py run`; bronze giữ thô kèm `_src`, `_ingested_at`, `_row_hash`; `--mode incremental` bỏ dòng có `_row_hash` đã nạp; nhật ký chạy `meta.runs` + `pipeline.json` (timings, inserted/skipped); `provenance.json` | Incremental theo **hash nội dung**, chưa có watermark/cursor theo thời gian cho API; chưa có workflow lịch `collect_data.yml` (GitHub Actions cron); chưa có recipe UN SDG / tỷ giá open.er-api / Open-Meteo archive; chưa có gói dữ liệu offline dựng sẵn |
| 3 | **EDA — thống kê mô tả** (profiling, business validation, outlier IQR/Z, correlation, time consistency) | Báo cáo EDA | `engine/vlkit/profile.py` (shape, dtype, % missing, unique, phân phối, skew, outlier), tương quan Spearman/partial (`stats.py`), `quality.json`; trang **Hồ sơ dữ liệu**, **Chất lượng**, **Insight** | **Chưa xuất báo cáo EDA thành file** (HTML/MD); chưa có kiểm tra khoảng trống thời gian (time gap) riêng |
| 4 | **Làm sạch & mô hình hoá** (7 bước làm sạch, gắn cờ thay vì xoá; Medallion; Star schema mặc định) | Code + **data dictionary** | `engine/vlkit/de/quality.py` (kiểu VN, missing, trùng dòng + khoá ứng viên, outlier 3×IQR **gắn cờ**, điểm 0–100 trước/sau, cleaning log); DuckDB bronze/silver/gold + Parquet; `modeling.py` dựng OBT, **Star**, Snowflake, Data Vault 2.0 + ERD; conformed dims tỉnh/năm (63→34) | **Chưa có xuất data dictionary** (cột, kiểu, đơn vị, nguồn, công thức). Mentor khuyến nghị Star làm mô hình chính; kit khuyến nghị OBT cho serving + Star cho trình bày (cả hai đều dựng) |
| 5 | **Serving — dashboard** (Overview → Drill-down → Detail; chọn chart đúng mục đích, có choropleth; 1 câu hỏi business + 1 khuyến nghị) | Dashboard | Next.js + shadcn dashboard-01 (Tổng quan, Pipeline, Chất lượng, Mô hình, SQL Explorer, Insight, Drivers & What-if, Phân khúc, Quyết định, AI Analyst); `dashboard.html` tĩnh; FastAPI; export deck/pitch VI/EN, executive summary | Bản đồ choropleth 34 tỉnh mới ở mức spec (008); chưa dùng nhãn Overview/Drill-down/Detail trên giao diện |
| 6 | **Insight → quyết định** | Khuyến nghị hành động | Insight có kiểm định (test, p, effect, n), drivers/what-if có khoảng bootstrap, `decision.py` (So what → Now what), trang **Quyết định**, slide câu hỏi quyết định + khuyến nghị chính sách + hạn chế (002), deck/pitch song ngữ (003) | — |

## 1. Luồng tổng thể

```mermaid
flowchart LR
  Q["0 · Câu hỏi chính sách<br/>(Đề bài → brief.json)"] --> I
  subgraph I["1 · Ingestion"]
    I1[Database / JDBC] & I2[Public API] & I3[Tải file trực tiếp] & I4[Web scraping] & I5[Social listening]
  end
  I --> S[("2 · Storage<br/>DuckDB bronze + Parquet lake<br/>provenance, _row_hash")]
  S --> T1["3a · Transform: làm sạch<br/>missing · duplicate · outlier<br/>điểm chất lượng trước/sau"]
  T1 --> T2["3b · Transform: mô hình<br/>OBT · Star · Snowflake · Data Vault<br/>+ conformed theo tỉnh/năm"]
  T2 --> A["3c · Phân tích<br/>kiểm định · drivers · what-if · dự báo"]
  A --> V["4 · Serving<br/>Dashboard 1 câu hỏi/view · AI Analyst<br/>deck · pitch · executive summary"]
  V --> D["Quyết định: ai làm gì, ở đâu, KPI nào"]
  D -. phản hồi .-> Q
```

## 2. Từng giai đoạn: đầu vào → việc làm → đầu ra → ai làm

| Giai đoạn | Đầu vào | Việc làm (kit) | Đầu ra | Ai (vai PLAYBOOK) |
|---|---|---|---|---|
| 0 Câu hỏi | Đề BTC | Trang **Đề bài** / `de.py brief` → target, đơn vị, phân khúc, loại quyết định, scenario pack | `brief.json`, câu hỏi quyết định 1 dòng | Captain (không code) + cả đội |
| 1 Ingestion | Dataset BTC + nguồn bổ sung | Upload / `de.py file` / `sources.yaml` + `de.py run` (file, api, sql, scrape, social, cv) | `bronze.*`, `provenance.json` (nguồn, thời điểm, giấy phép) | Data engineer |
| 2 Storage | bronze | DuckDB medallion + Parquet; `--mode incremental` khi nạp lại | warehouse, `meta.runs` (inserted/skipped) | Data engineer |
| 3a Làm sạch | bronze | `quality.py`: kiểu VN, missing, trùng, outlier 3×IQR (gắn cờ, không xoá), impute tuỳ chọn | `silver.*`, `quality.json` (điểm trước/sau, cleaning log) | Data engineer + Analyst kiểm tra |
| 3b Mô hình | silver | 4 mô hình + conformed; chọn theo ma trận §4 | `gold.*`, ERD, SQL, `conformed.json` (join coverage) | Data engineer |
| 3c Phân tích | gold OBT | insight có kiểm định, drivers, what-if, dự báo, phân khúc | `results.json`, `whatif.json` | Analyst |
| 4 Serving | gold + results | Dashboard, Hỏi AI, Câu chuyện, SQL Explorer, deck/pitch | dashboard, `deck.pptx`, `pitch.md`, PDF | Storyteller (không code) + Presenter |
| QA | mọi số | đối chiếu số slide ↔ SQL trên gold; nguồn chính thống | checklist "mọi số truy được" | Researcher/QA |

## 3. Thu thập theo tình huống (workshop phần 1) — ghi chú kỹ thuật

| Tình huống | Khi nào | Connector kit | Ghi chú kỹ thuật bắt buộc |
|---|---|---|---|
| **Database / JDBC** | BTC/đối tác cấp quyền truy cập CSDL (Postgres, MySQL, SQL Server, SQLite) | `kind: sql` (SQLAlchemy — tương đương JDBC của Python) | Quyền truy cập: chỉ tài khoản **read-only**, chỉ `SELECT`; không ghi mật khẩu vào yaml (dùng biến môi trường); provenance tự che mật khẩu; đọc theo `chunksize` để không tràn RAM |
| **Public API** | World Bank WDI, IMF, GSO API, dữ liệu mở | `kind: api` (httpx + tenacity) | **Rate limit** (`rate_per_sec`), **phân trang** (`page`/`offset`/`next`/`worldbank`), **retry + exponential backoff** cho 429/5xx, tôn trọng `Retry-After`; **cache** đĩa `data/cache/` để chạy lại không tốn quota; khoá API qua `auth_env`, không hard-code |
| **Tải file trực tiếp** | file CSV/XLSX từ cổng dữ liệu, BTC, Bộ Tài chính | `kind: file` (csv/xlsx/json/parquet/zip) | Dò encoding & dấu phân cách, bỏ dòng tiêu đề, Excel nhiều sheet → nhiều bảng; ghi URL gốc + ngày tải + giấy phép vào `license:` |
| **Web scraping** | bảng trên trang web không có API | `kind: scrape` (httpx + selectolax/lxml; Playwright khi `render_js`) | **robots.txt** kiểm trước mỗi URL; **throttling** delay ngẫu nhiên 1–3 s; **User-Agent** định danh có liên hệ; cache; retry có giới hạn; **không** vượt captcha/đăng nhập/paywall; đọc **ToS** — nếu cấm thì không scrape; chỉ lấy dữ liệu công khai, không dữ liệu cá nhân |
| **Social listening** | dư luận, tin tức, xu hướng tìm kiếm | `kind: social` (RSS/Atom, Google Trends tuỳ chọn) | Ưu tiên RSS chính thức; Trends giới hạn rất gắt → cache; chỉ lưu tiêu đề/link/ngày (không sao chép toàn văn); lưu ý thiên lệch mẫu (người dùng mạng ≠ dân số) |
| **CV quan sát** (đề video) | video giao thông/đám đông | `count.py` → `kind: cv` | Chỉ lưu số đếm, không lưu ảnh/khuôn mặt/biển số; ghi giấy phép video |

Pháp lý chung: ghi nguồn + giấy phép cho **mọi** bảng (slide Provenance tự sinh); dữ liệu cá nhân → loại bỏ định danh trước khi nạp (xem `SECURITY.md`).

## 4. Làm sạch & chọn mô hình (workshop phần 2)

**Làm sạch** (tự động trong `quality.py`, giải thích được trên trang Chất lượng):
- *Missing*: đo theo cột; mặc định giữ nguyên (minh bạch), `--impute median` khi mô hình cần; báo % trong caveat.
- *Duplicates*: trùng toàn dòng bị loại ở silver; trùng **khoá ứng viên** được báo (không tự xoá — có thể là cập nhật hợp lệ).
- *Outliers*: 3×IQR **gắn cờ** `_outlier_any`, không xoá; insight dùng trung vị / kiểm định phi tham số nên bền với outlier.

**Ma trận chọn mô hình** (theo quy mô dữ liệu × thời gian hackathon):

| Tiêu chí | OBT | Star | Snowflake | Data Vault 2.0 |
|---|---|---|---|---|
| Quy mô phù hợp | ≤ vài triệu dòng, 1 nguồn chính | nhiều chiều phân tích, 1–3 nguồn | chiều có phân cấp sâu (quận→tỉnh→vùng) | nhiều nguồn thay đổi theo thời gian, cần lịch sử |
| Thời gian dựng (với kit) | phút | phút (tự sinh) | phút (tự sinh) | phút (tự sinh) — nhưng giải thích tốn thời gian pitch |
| Tốc độ query dashboard | ★★★ nhanh nhất (không join) | ★★ | ★ (nhiều join) | ★ (cần mart phía trên) |
| Dễ giải thích cho giám khảo kinh tế | ★★★ | ★★★ (fact = sự kiện, dim = góc nhìn) | ★★ | ★ |
| Kiểm toán/lịch sử nguồn | ★ | ★ | ★ | ★★★ (hub/link/sat, load_dts, record_source) |
| Tích hợp nhiều nguồn | qua `obt_integrated` | qua **conformed dims** | ★★ | ★★★ |
| **Khuyến nghị 28 giờ** | **Phục vụ dashboard + insight** | **Mô hình ngữ nghĩa để trình bày** | phụ lục khi có địa lý phân cấp | phụ lục "chúng tôi biết trade-off" |

Kit dựng cả bốn và ghi `rationale` + `recommended` (trang Mô hình); đội chỉ cần **chọn và giải thích**.

## 5. Nguyên tắc dashboard (Sacha Dray, World Bank)
1. **Bắt đầu từ quyết định**: mỗi KPI gắn với một quyết định/người ra quyết định (trang Quyết định: ai làm gì, ở đâu, KPI).
2. **Mỗi view một câu hỏi**: tiêu đề view = câu hỏi ("Tỉnh nào chi đầu tư công/người thấp nhất so với nhu cầu?"), một biểu đồ chính trả lời nó.
3. **Ít KPI, có ngữ cảnh**: 3–5 KPI, mỗi KPI có so sánh (kỳ trước, trung vị, mục tiêu) và đơn vị rõ.
4. **Minh bạch bất định**: hiện p-value/khoảng tin cậy/caveat cạnh con số; nói "liên quan", không "gây ra".
5. **Truy được nguồn**: nguồn + ngày + giấy phép ở chân view/slide Provenance; mọi số có SQL kiểm chứng.
6. **Thiết kế cho người dùng thật**: tiếng Việt, ít thuật ngữ; người không code đi được bằng tour "Hướng dẫn" và "Hỏi AI".

## 6. User stories theo người dùng thật
- **Giám khảo kinh tế (UEH Tài chính công, World Bank, LSE, FiinGroup)**: *"Là giám khảo, tôi muốn thấy câu hỏi chính sách trước, rồi bằng chứng có kiểm định (n, p, effect, CI) và giới hạn nhân quả, để tin khuyến nghị."* — Chấp nhận: slide 2 nêu câu hỏi; mỗi insight có test/p/effect/n; slide Limitations; SQL kiểm chứng bất kỳ số nào trong ≤ 30 s (SQL Explorer).
- **Giám khảo dữ liệu**: *"Tôi muốn thấy pipeline và lý do chọn mô hình."* — Chấp nhận: trang Pipeline (lineage, timings, join coverage), Chất lượng (trước/sau), Mô hình (ERD + ma trận §4).
- **Đồng đội kinh doanh/khoa học xã hội không code**: *"Tôi muốn hiểu từng biểu đồ và tự lấy số cho slide mà không mở terminal."* — Chấp nhận: tour Hướng dẫn, Hỏi AI trên mọi thẻ, Câu chuyện top-5, nút Xuất báo cáo; mọi thao tác trên trình duyệt.
- **Captain**: *"Tôi muốn một câu khuyến nghị: ai làm gì, ở đâu, đo bằng KPI nào, mức tin cậy."* — Chấp nhận: trang Quyết định + slide Policy recommendation.

## 7. Checkpoint go/no-go (rút gọn từ PLAYBOOK)
- 20/11 12:00 — câu hỏi + target + dữ liệu đã sạch (điểm chất lượng sau ≥ trước).
- 20/11 16:00 — 3 insight có kiểm định + 1 khuyến nghị nháp; kể thử 3 phút.
- 21/11 11:00 — đóng băng code; deck cuối từ engine; nộp trước 12:30 (hạn 13:00).
