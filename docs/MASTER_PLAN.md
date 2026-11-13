# VietLeap Insight Kit — MASTER PLAN (bản giao cho Codex)

> Mục tiêu: hôm thi (20/11 09:00 nhận đề → 21/11 13:00 nộp → 13:15 pitch) đội chỉ cần **thả dataset + đề bài** vào kit là có ngay: pipeline dữ liệu chuẩn Data Engineering, dashboard shadcn, insight có kiểm định thống kê, khuyến nghị chính sách, AI Analyst, deck + báo cáo. Người code tiếp: Codex. Đọc `AGENTS.md` ở gốc repo trước khi code.

---

## 0. TRẠNG THÁI (cập nhật 14/11/2026) — đọc mục này trước

**Lịch BTC đã xác nhận (giờ Việt Nam):** 16/11 19:00 workshop online (Lưu Đức Cảnh, Tasco) · **19/11 15:30** Chi-Yu Lee (Konstanz) *From observation to data* (object tracking CV) · **20/11 09:00** công bố đề + chia đội ngẫu nhiên · **20/11 10:00** Viet Nguyen-Tien (LSE) *Unlocking the Data Economy* · **20/11 11:00** Sacha Dray (World Bank VN) workshop Dashboard · **21/11 13:00** hạn nộp · **21/11 13:15** pitch.

### Đã xong & đã push (pytest 104 pass; `npm run lint`, `npm test`, `npm run build` pass)

| Task | Nội dung | Commit |
|---|---|---|
| T1–T5 Lớp DE | Ingestion `engine/vlkit/de/connectors.py` (file csv/xlsx/json/parquet/zip, api có paging/retry/rate-limit/cache, sql SELECT-only, scrape tôn trọng robots.txt, social RSS/Trends, cv) → Storage DuckDB bronze/silver/gold/meta + Parquet lake → Transform `quality.py` (missing/duplicate/outlier 3×IQR gắn cờ, điểm 0–100 trước/sau, cleaning log) + `modeling.py` (OBT, Star, Snowflake, Data Vault 2.0, ERD Mermaid) → Serving `flow.py` (pipeline/quality/lineage/provenance JSON) + API FastAPI | 2e9674c |
| T6 Web | shadcn dashboard-01 (không restyle): Tổng quan, Nguồn, Pipeline (lineage mermaid), Chất lượng, Mô hình (Tabs 4 mô hình + ERD + SQL), SQL Explorer, Hồ sơ, Insight, Drivers & What-if, Phân khúc, Quyết định | 0e8be9b |
| T7 AI Analyst | Vercel AI SDK v7 `/api/chat` (streamText + 11 tool gọi FastAPI, Groq hoặc OpenAI-compatible qua env, offline không cần key) + trang Analyst | 953057a |
| Explain-anything | driver.js tour "Hướng dẫn" + chế độ "Hỏi AI" (rê/bấm phần tử `data-insight-target` → Sheet AI giải thích, offline deterministic có unit test) | b225042 |
| T8 Đề → brief | `engine/vlkit/brief.py` rule-based VI/EN, 7 scenario pack (`scenarios/packs/`), 11 đề mẫu (`scenarios/briefs/`), `POST /api/brief`, trang Đề bài | 2609808 |
| Fix + Makefile | không chuẩn hoá tỉnh 2 lần; `make setup/api/web/web-dev/demo/demo-online/brief/test` | 757df0c, a4483a2 |

Đã chạy thật: `scenarios/demo/sources.yaml` (5 loại nguồn: CSV, SQLite, World Bank API, Wikipedia, RSS VnExpress); Hà Nội 81.681 tin (điểm chất lượng 84,9 → 92,4); 3 dataset practice (`data/practice/`).

Lệnh: `make api` · `make web` · `make demo` · `python de.py file <path> --serve` · `python de.py run <sources.yaml> --primary <ds> --serve` · `python de.py brief <đề.md> --data <file>` · `python de.py sql "SELECT ..."`.
Môi trường: máy có HTTP_PROXY → luôn `NO_PROXY=localhost,127.0.0.1`. Máy yếu: không chạy `npm run build` song song với pytest/engine.

### Còn lại (theo thứ tự)
1. ✅ **T11 docs** (xong 14/11) — `docs/PLAYBOOK.md` (lịch theo giờ, vai trò đội 4–5 người kể cả người không code), `docs/CONTEXT.md` (bối cảnh, nhà tài trợ → miền đề có thể ra), README quickstart 1 trang.
2. **AI layer wow/robustness** — tour/inspect không crash khi thiếu phần tử, Esc thoát, chạy mọi trang; nút **"Câu chuyện insight"**: agent (hoặc engine offline) kể top-5 insight, driver.js lần lượt highlight thẻ/biểu đồ tương ứng.
3. **T10 deck** — slide Data pipeline, Data model (OBT vs Star vs Snowflake vs Data Vault & vì sao), Data quality trước/sau, Provenance, Limitations, Policy recommendation; `slides/pitch.md` (Marp) 7 phút; kiểm tra tràn chữ.
4. **T9 CV** — `scenarios/cv_counting/count.py` (YOLOv8n + ByteTrack + LineZone → `counts.csv`), báo lỗi thân thiện khi thiếu ultralytics; README; test không tải model lớn.
5. **T12 (tuỳ chọn)** — docker-compose, GitHub Actions.

**Việc nhỏ còn mở cho lớp DE:** conformed dimension giữa nhiều nguồn (join theo tỉnh/năm khi ≥2 bảng silver chung khoá — `load_sources` đã đọc `keys:` nhưng chưa dùng); dim_geo cho quận/huyện; incremental load theo `_row_hash` (hiện ghi đè); screenshot `docs/screenshots/` cho T6.

---

## 1. Ban tổ chức đã hé lộ gì (và suy ra gì)

| Tín hiệu từ BTC | Nguồn | Suy ra cho đề thi | Kit phải có |
|---|---|---|---|
| Tên: *From Data to Decision*; 2 track: **Data & Analytics** (dashboard + data pipeline) và **Presentation** | vietleap2026.com | Chấm cả pipeline lẫn dashboard lẫn câu chuyện ra quyết định | Pipeline có lineage nhìn thấy được, dashboard, trang "Decision" |
| Workshop 16/11 19:00 online — *Hướng dẫn xây dựng luồng dữ liệu & dashboard chuyên nghiệp* (Lưu Đức Cảnh, Data Engineer – Tasco): **Ingestion → Storage → Transform → Serving**; nguồn **Database/JDBC, Public API, file tải trực tiếp, Web Scraping, Social listening** (quyền truy cập, giới hạn API, chống chặn); làm sạch **missing, duplicate, outlier**; mô hình **OBT / Star Schema / Snowflake / Data Vault** "phù hợp quy mô và thời gian hackathon" | poster BTC | Đề rất có thể cho **dữ liệu rải rác nhiều nguồn/nhiều file**, yêu cầu tự thu thập bổ sung, và giám khảo hỏi "các bạn mô hình dữ liệu thế nào, vì sao" | Connector đủ 5 loại nguồn, DuckDB bronze/silver/gold, nhật ký làm sạch, sinh **OBT + Star schema** tự động, sơ đồ lineage + ERD trên dashboard |
| Talk Chi-Yu Lee (Konstanz) **19/11 15:30**: *From observation to data — object tracking in computer vision* | agenda | Có thể có đề đếm/đếm luồng (giao thông, người) từ video/ảnh | `scenarios/cv_counting` (YOLO + ByteTrack → CSV đếm theo thời gian → đưa vào pipeline) |
| Talk Viet Nguyen-Tien (LSE) **20/11 10:00**: *Unlocking the Data Economy* (dữ liệu mở, kinh tế dữ liệu; từng làm open property data) | agenda | Giá trị của dữ liệu mở/dữ liệu thay thế; có thể là dữ liệu BĐS (giá/m², quận, diện tích) | Domain pack BĐS (đã có, Hà Nội 81.681 tin đã chạy) |
| Sacha Dray (World Bank VN) **20/11 11:00** — workshop Dashboard | agenda | Dữ liệu vĩ mô/WDI, chỉ số phát triển | Domain pack vĩ mô (đã có, WDI Asia) |
| Host: UEH **School of Public Finance** + AVSE **Economic Policy Network** | website | Ngôn ngữ chính sách công, tài khóa, ngân sách tỉnh; khuyến nghị phải "evidence-based" | Trang Decision: khuyến nghị + mức tin cậy + caveat nhân quả; chuẩn hoá 63→34 tỉnh (NQ 202/2025/QH15) |
| Partner **FiinGroup** (dữ liệu thị trường VN), RAF | poster | Có thể là dữ liệu doanh nghiệp niêm yết/tài chính | Domain pack tài chính DN (đã có, HOSE vs UPCoM ROE) |
| Sponsor Goodenough College / **Goodstart Fellow** (dự án tác động cộng đồng: y tế, giáo dục, môi trường, wellbeing) | website | Đề có thể mang màu "social impact" | Template câu chuyện tác động xã hội trong deck |
| Bài test đầu vào: tự thu thập Google Trends + ghi **provenance** (nguồn, ngày tải, cài đặt) | bài anh đã nộp | BTC coi trọng **nguồn gốc dữ liệu & minh bạch phương pháp** | Mọi dataset sinh `provenance.json` + trang "Data sources" |
| Giám khảo: UEH, Western Sydney, Coventry, Roehampton, FiinGroup | website | Hội đồng học thuật → hỏi về kiểm định, nhân quả, hạn chế | Mỗi insight kèm p-value/effect size/CI; slide "Limitations" |
| 20/11 09:00 công bố đề + lập đội ngẫu nhiên; ~28 giờ build; nộp 21/11 13:00, pitch từ 13:15 | agenda | Kit phải chạy được trên máy yếu, setup < 10 phút, đồng đội không biết code vẫn dùng được | `make demo`, README 1 trang, UI upload kéo-thả |

**Kết luận:** đề có xác suất cao là *"đây là dữ liệu (thô, nhiều nguồn) về một vấn đề kinh tế/xã hội VN — hãy xây pipeline + dashboard và đưa ra khuyến nghị quyết định"*. Kit thắng nhờ: (1) pipeline DE chuẩn đúng 4 giai đoạn diễn giả dạy, (2) dashboard shadcn chuyên nghiệp, (3) insight có thống kê, (4) khuyến nghị chính sách rõ ràng, (5) câu chuyện pitch sẵn khung.

---

## 2. Kiến trúc tổng (map đúng 4 giai đoạn workshop)

```
 INGESTION                STORAGE (DuckDB)            TRANSFORM                         SERVING
 ─────────                ────────────────            ─────────                         ───────
 file  (csv/xlsx/json/    bronze.*  (thô, + _src,     silver.* (typed, VN-parsed,       FastAPI :8000  /api/*
        parquet/zip)      _ingested_at, _row_hash)    dedup, missing/outlier xử lý,     Next.js :3000  shadcn dashboard-01
 api   (REST, paging,                                 tỉnh 63→34, cleaning_log)         AI Analyst (Vercel AI SDK, tool-calls)
        rate-limit)       data/warehouse.duckdb       gold.obt_<ds>  (One Big Table)    deck.pptx / report.pdf / dashboard.html
 sql   (SQLAlchemy =      data/lake/<ds>/*.parquet    gold.fact_<ds>, gold.dim_*        Marp slides
        "JDBC" Python)                                (Star schema tự sinh)
 scrape(httpx+selectolax,                             quality_report.json
        Playwright fallback)                          lineage.json, erd.mmd
 social (RSS/Reddit/YouTube
        comments, Google Trends)
 cv    (video → YOLO+ByteTrack → counts.csv)
```

Lý do chọn (để trả lời giám khảo):
- **DuckDB + Parquet** thay vì Postgres: không cần server, chạy trên laptop, SQL chuẩn, đọc CSV/Parquet/Excel trực tiếp, nhanh với vài triệu dòng — đúng "quy mô và thời gian hackathon".
- **OBT** cho dashboard/ML (1 bảng phẳng, nhanh); **Star schema** để trình bày mô hình dữ liệu chuẩn và cho phép slice theo dim. Snowflake/Data Vault: nêu trong slide là *không chọn* vì overhead > lợi ích trong 28 giờ (giám khảo sẽ thích lập luận này).
- **Medallion bronze/silver/gold**: tái lập được, audit được (giữ thô, mọi biến đổi có log).

---

## 3. Công nghệ (toàn bộ open-source)

| Lớp | Công nghệ | Trạng thái |
|---|---|---|
| Engine phân tích | Python 3.11, pandas, numpy, scipy, statsmodels, scikit-learn, plotly, python-pptx | ✅ có, đã chạy 4 dataset |
| Ingestion | httpx + tenacity (retry/backoff/rate-limit), SQLAlchemy 2 (+ psycopg / pymysql tuỳ chọn), selectolax, Playwright (fallback JS), feedparser (RSS), pytrends (tuỳ chọn) | ⬜ T1 |
| Storage | DuckDB ≥ 1.1, pyarrow Parquet | ⬜ T2 |
| Data quality | pandera (contract) + báo cáo tự viết (missing/dup/outlier IQR & MAD) | 🟡 có một phần trong loader.py → T3 |
| Modelling | sinh OBT + Star schema bằng SQL DuckDB; ERD xuất Mermaid | ⬜ T4 |
| CV | ultralytics YOLOv8n + supervision (ByteTrack, LineZone) — CPU được | ⬜ T9 |
| API | FastAPI, uvicorn | 🟡 có, mới gọi thử 4 endpoint |
| Web | Next.js 16 (App Router), **shadcn/ui dashboard-01 chính thức** (base-nova), Recharts, TanStack Table, next-themes | 🟡 5 trang đã viết, chưa build |
| AI Analyst | **Vercel AI SDK** (`ai` v7, `@ai-sdk/react`, `@ai-sdk/groq`, `@ai-sdk/openai-compatible`), tool-calls gọi FastAPI, không cho LLM bịa số | 🟡 dependency đã cài, route chưa viết → T7 |
| Báo cáo | python-pptx deck 10 slide, HTML/PDF summary, Marp template | 🟡 deck có, chưa soát hình → T10 |
| Test/CI | pytest, eslint, `next build`, GitHub Actions (tuỳ chọn) | 🟡 4 file test → T11 |

---

## 4. Tính năng — đã có / phải làm

**Đã có (đã kiểm chứng):** parse số/ngày/đơn vị kiểu VN ("1,2 tỷ", "15tr/m²", "dd/mm/yyyy"); chuẩn hoá tỉnh 63→34; leakage guard; insight xếp hạng EN+VI (Kruskal/Mann-Whitney/Spearman + effect size); drivers; what-if; deck 10 slide; summary MD/HTML/PDF; dashboard.html tĩnh. Mỗi dataset 12–19 s.

**Phải làm (theo thứ tự ưu tiên):**
1. Lớp DE: connectors + DuckDB medallion + quality report + OBT/Star + lineage (T1–T4) — *đây là thứ workshop 16/11 nói tới, đang thiếu.*
2. API mới cho pipeline: `/api/sources`, `/api/ingest`, `/api/warehouse/tables`, `/api/quality`, `/api/lineage`, `/api/sql` (read-only) (T5).
3. Web: trang **Pipeline** (lineage 4 giai đoạn + trạng thái), **Data Quality**, **Data Model** (ERD Mermaid), **SQL Explorer**, **Decision** (khuyến nghị) — dùng component shadcn có sẵn, không tự restyle (T6).
4. AI Analyst bằng Vercel AI SDK: `/api/chat` `streamText` + tools `listTables`, `runSql`, `getInsights`, `whatIf`, `segment` → mọi con số trong câu trả lời phải đến từ tool (T7).
5. Problem-statement parser: dán đề bài → trích câu hỏi, biến mục tiêu, đơn vị phân tích, gợi ý KPI → cấu hình chạy pipeline (T8, chạy offline bằng rule, LLM là tuỳ chọn).
6. CV counting scenario (T9). 7. Deck/report soát hình + slide Data Model/Limitations (T10). 8. Test + README + PLAYBOOK + `make demo` (T11). 9. Docker compose tuỳ chọn (T12).

---

## 5. Danh sách task cho Codex (mỗi task nhỏ, độc lập, có tiêu chí xong)

> Quy tắc chung: máy yếu (2 CPU, 7 GB RAM) → chạy **một** job nặng mỗi lần (`npm run build` hoặc engine, không song song). Sau mỗi task: `pytest -q` (và `npm run lint && npm run build` nếu đụng `web/`), commit 1 commit/task.

### T1 — Ingestion connectors `engine/vlkit/ingest/`
- `base.py`: `Source` dataclass (`name, kind, uri, options`), `IngestResult(df, provenance)`; provenance = `{source, kind, uri, fetched_at (Asia/Saigon), rows, cols, sha256, settings, license_note}`.
- `file.py`: csv (tự dò encoding utf-8/utf-8-sig/cp1258/latin1 và delimiter), xlsx (mọi sheet → nhiều bảng), json/jsonl, parquet, zip (giải nén rồi đệ quy).
- `api.py`: GET JSON REST với paging (`page`/`offset`/`next` link), `tenacity` retry exponential trên 429/5xx, tôn trọng `Retry-After`, giới hạn req/s cấu hình được, cache đĩa `data/cache/`.
- `sql.py`: SQLAlchemy URL bất kỳ (sqlite/postgres/mysql) → `read_sql` theo chunk; chỉ SELECT.
- `scrape.py`: httpx + selectolax lấy bảng HTML (`<table>` → DataFrame) hoặc CSS selector list; User-Agent rõ ràng, delay ngẫu nhiên 1–3 s, đọc robots.txt và **dừng nếu bị cấm**; Playwright chỉ khi trang cần JS. Không vượt captcha.
- `social.py`: RSS/Atom (feedparser), Google Trends (pytrends, tuỳ chọn, bắt lỗi 429).
- `registry.py`: `ingest(source) -> IngestResult` dispatch theo `kind`; YAML `sources.yaml` mô tả nhiều nguồn.
- **Xong khi:** `python run.py ingest --sources scenarios/demo_sources.yaml` tải ≥ 3 nguồn khác loại (file local + 1 API công khai như World Bank API `api.worldbank.org/v2/country/VN/indicator/NY.GDP.PCAP.CD?format=json` + 1 bảng HTML Wikipedia) và test `tests/test_ingest.py` pass offline (dùng fixture + `respx` mock).

### T2 — Storage DuckDB medallion `engine/vlkit/warehouse.py`
- `Warehouse(path="data/warehouse.duckdb")`: `write_bronze(name, df, provenance)` thêm cột `_src, _ingested_at, _row_hash`; ghi đồng thời Parquet `data/lake/bronze/<name>.parquet`.
- Schema `bronze`, `silver`, `gold`, bảng meta `meta.sources`, `meta.runs`, `meta.lineage(from_table, to_table, step, at)`.
- `tables()` liệt kê bảng + số dòng + layer; `sql(query, limit=1000)` read-only (từ chối DDL/DML).
- **Xong khi:** test tạo bronze → đọc lại khớp số dòng, `sql("DROP ...")` bị từ chối.

### T3 — Transform + Data quality `engine/vlkit/quality.py`
- Tái dùng `loader.load_and_clean` cho parse VN; thêm: phát hiện duplicate (toàn dòng & theo khoá đề xuất), missing theo cột (% + pattern MCAR-đơn giản: missing có tương quan cột khác?), outlier (IQR 1.5 và MAD z>3.5, **đánh dấu không xoá**), kiểu sai, giá trị âm vô lý.
- Mỗi biến đổi ghi `cleaning_log` (bước, cột, số dòng ảnh hưởng, lý do). Xuất `quality_report.json` + điểm chất lượng 0–100 trước/sau.
- Ghi `silver.<ds>`.
- **Xong khi:** synthetic_messy_bds.csv cho báo cáo có cả 3 loại lỗi và điểm sau > trước.

### T4 — Data modelling `engine/vlkit/model_builder.py`
- `build_obt(ds)`: `gold.obt_<ds>` = silver + cột dẫn xuất (năm/tháng/quý, tỉnh_2025, nhóm kích thước).
- `build_star(ds)`: tự chọn dim: thời gian (`dim_date` sinh đủ ngày), địa lý (`dim_geo`: tỉnh cũ, tỉnh mới, vùng), mỗi cột phân loại có 2–200 giá trị → `dim_<col>` với surrogate key; còn lại numeric → `fact_<ds>`. Nếu có ≥ 2 bảng silver chung khoá (tỉnh/năm/mã CK) → join làm conformed dimension.
- Xuất `erd.mmd` (Mermaid erDiagram) + `lineage.json` (nút: nguồn → bronze → silver → gold, cạnh có tên bước).
- **Xong khi:** với hanoi_housing tạo được fact + ≥ 3 dim, ERD render được trên mermaid.live.

### T5 — API pipeline `api/routes/pipeline.py`
- `GET /api/sources`, `POST /api/ingest` (body: list Source, chạy nền qua `api/jobs.py` có sẵn), `GET /api/warehouse/tables`, `POST /api/sql` (read-only, limit), `GET /api/datasets/{id}/quality`, `GET /api/datasets/{id}/lineage`, `GET /api/datasets/{id}/erd`.
- Upload dataset hiện có phải tự đi qua bronze→silver→gold rồi mới chạy engine insight như cũ.
- **Xong khi:** `tests/test_api_pipeline.py` (FastAPI TestClient) pass.

### T6 — Web: thêm trang trong shadcn dashboard-01
- Giữ nguyên block `dashboard-01` (sidebar, site-header, section-cards, chart-area-interactive, data-table). **Không tự đổi màu/font/spacing.** Chỉ thêm bằng `npx shadcn@latest add <component>` khi cần (vd `chart`, `tabs`, `badge`, `alert`, `textarea`).
- Trang mới trong `src/app/(dashboard)/`: `pipeline/` (4 cột Ingestion/Storage/Transform/Serving dạng Card + bảng runs), `quality/` (SectionCards điểm trước/sau + DataTable cleaning_log + bar chart missing%), `model/` (render `erd.mmd` bằng `mermaid` npm), `sql/` (Textarea + DataTable kết quả), `decision/` (khuyến nghị: Card mỗi khuyến nghị có Badge mức tin cậy, bằng chứng, caveat).
- Thêm vào `app-sidebar.tsx` nav. `next.config.ts` rewrite `/engine/:path*` → `http://localhost:8000/api/:path*` (giữ nếu đã có).
- **Xong khi:** `npm run lint` sạch, `npm run build` pass, screenshot 1440×900 của 5 trang trong `docs/screenshots/`.

### T7 — AI Analyst (Vercel AI SDK)
- `src/app/api/chat/route.ts`: `streamText({ model, system, messages, tools, stopWhen: stepCountIs(8) })`. Model: `GROQ_API_KEY` → `@ai-sdk/groq` (`llama-3.3-70b-versatile`), else `OPENAI_COMPATIBLE_BASE_URL`+`KEY`. Không có key → trả lời bằng chế độ offline: gọi `/api/insights` và render top insight (không lỗi).
- Tools (zod schema) gọi FastAPI: `listTables`, `runSql`, `getInsights`, `getSegments`, `whatIf`, `getQuality`.
- System prompt: tiếng Việt, mọi con số phải lấy từ kết quả tool, ghi rõ nguồn bảng; nói rõ tương quan ≠ nhân quả.
- `src/app/(dashboard)/analyst/page.tsx`: `useChat` + hiển thị tool-call dạng Card thu gọn.
- **Xong khi:** chạy offline không key trả lời được câu "insight quan trọng nhất là gì"; có key thì 1 câu hỏi gọi ≥ 1 tool.

### T8 — Problem-statement parser `engine/vlkit/brief.py`
- Input: text đề (VI/EN). Rule-based: trích câu hỏi (dấu ?/"hãy", "phân tích", "đề xuất"), biến mục tiêu (so khớp tên cột bằng `ascii_key`), đơn vị (tỉnh/năm/DN), loại quyết định (phân bổ ngân sách, chính sách giá, ưu tiên khu vực). Xuất `brief.json` → pipeline dùng để chọn target/segment.
- Trang web `brief/` dán đề → hiện kế hoạch phân tích.
- **Xong khi:** 5 đề mẫu trong `scenarios/briefs/*.md` cho target đúng với dataset practice.

### T9 — CV counting `scenarios/cv_counting/`
- `count.py --video in.mp4 --line x1,y1,x2,y2 --classes car,motorcycle,person --every 60s` → `counts.csv (timestamp, class, in, out)` dùng YOLOv8n + supervision ByteTrack + LineZone; CPU, bỏ khung (`--stride 3`) cho nhanh.
- Kết quả đi vào pipeline như nguồn `file`.
- **Xong khi:** chạy được trên 1 video mẫu ngắn công khai, ghi rõ license nguồn video.

### T10 — Deck & report
- Thêm slide: Data pipeline (4 giai đoạn), Data model (OBT vs Star, vì sao không Snowflake/Data Vault), Data quality (trước/sau), Limitations & next steps, Policy recommendation.
- Render deck → PNG (LibreOffice headless nếu có) và **tự xem từng slide**: không chữ tràn, không trùng màu nền.
- Marp `slides/pitch.md` 7 phút: Vấn đề → Dữ liệu & pipeline → 3 insight → Quyết định đề xuất → Tác động → Hạn chế → Demo.

### T11 — Test, docs, một lệnh demo
- `Makefile`: `setup`, `api`, `web`, `demo` (chạy 4 practice dataset tuần tự → mở dashboard), `test`.
- `README.md` 1 trang; `docs/PLAYBOOK.md` (lịch theo giờ hôm thi, ai làm gì trong đội ngẫu nhiên 4–5 người); `docs/CONTEXT.md` (mục 1 của file này).
- **Xong khi:** máy sạch `make setup && make demo` chạy hết < 10 phút.

### T12 — (tuỳ chọn) `docker-compose.yml` api + web; GitHub Actions chạy pytest + lint.

---

## 6. Runbook hôm thi (đề xuất)

| Thời điểm | Việc |
|---|---|
| 19/11 | 15:30 nghe Chi-Yu Lee (CV tracking); tối: `git pull`, `make setup`, `make demo` trên laptop thi; tải sẵn model YOLOv8n; kiểm tra wifi UEH |
| 20/11 09:00 | Nghe briefing, chụp đề. Dán đề vào trang **Brief** |
| 20/11 10:00–12:00 | Talk LSE *Unlocking the Data Economy* (10:00) + workshop Dashboard World Bank (11:00): 1–2 người nghe & ghi ý giám khảo, phần còn lại chạy pipeline |
| +30' | Thả dataset (Upload) → pipeline chạy bronze/silver/gold + insight. Đọc Quality & Data Model |
| +2h | Bổ sung nguồn ngoài (API/scrape) nếu đề cho phép → join conformed dim |
| Chiều 20/11 | Chọn 3 insight mạnh nhất (effect size lớn, p nhỏ, liên quan quyết định); what-if; viết khuyến nghị |
| Tối 20/11 | Tinh chỉnh dashboard, deck, kịch bản pitch; ghi hình demo dự phòng |
| 21/11 sáng | Tập pitch 2 lần, đóng băng code 11:00, nộp trước 12:30 (hạn 13:00) |

## 7. Tiêu chí tự chấm trước khi nộp
- Mọi con số trên slide truy được về bảng gold + câu SQL.
- Mỗi insight: hiệu ứng, kiểm định, cỡ mẫu, caveat.
- Có 1 slide "Data provenance" (nguồn, ngày tải, license) — BTC đã đòi điều này ở bài test đầu vào.
- Khuyến nghị nói rõ *ai* làm *gì*, *ở đâu*, đo bằng KPI nào.
- Không bịa số, không hứa nhân quả từ dữ liệu quan sát.
