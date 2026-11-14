# Feature Specification: VietLeap Insight Kit — from dataset + đề bài to decision

**Feature Branch**: `main` (single-branch repo; spec id `001-vietleap-insight-kit`)
**Created**: 2026-11-15 · **Status**: Implemented (core) / In progress (wow features) — real status in [tasks.md](tasks.md)
**Input**: "Thả dataset + đề bài của VietLeap Hackathon 2026 → pipeline DE giải thích được, insight có kiểm định, what-if,
khuyến nghị chính sách, dashboard shadcn, AI Analyst, deck pitch — trong 28 giờ, trên laptop yếu, không bịa số."

Related: [plan.md](plan.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) ·
[quickstart.md](quickstart.md) · [tasks.md](tasks.md) · [constitution](../../.specify/memory/constitution.md) · [SRS](../../docs/SRS.md)

## Contest context & priorities
Source: [docs/CONTEST_ANALYSIS.md](../../docs/CONTEST_ANALYSIS.md). Judges are mostly **economists** (UEH School of Public Finance,
World Bank fiscal, LSE, FiinGroup data partner) → every output leads with the **policy question**, then evidence with tests, then the
decision and KPI; DE depth is a differentiator, not the story. Teammates are business/social-science **non-coders** → everything must
be reachable from the browser (tour, Hỏi AI, Câu chuyện, one-click export). Likely themes (inferred): provincial public finance /
fiscal policy ~30%, listed firms / capital markets ~20%, WDI Vietnam vs ASEAN ~15%, energy / EV / data economy ~15%, social ~10%,
traffic CV ~10%. Build window ≈ 27.5 h (20/11 09:30 → 21/11 13:00). Pitch may be judged in English → bilingual deck/pitch.

## Business workflow
Full version with mermaid flow, per-stage input→output→owner, collection notes and model decision matrix: [docs/WORKFLOW.md](../../docs/WORKFLOW.md).
Based on the organizer workshop *"Hướng dẫn xây dựng luồng dữ liệu & dashboard chuyên nghiệp"* (Lưu Đức Cảnh, Tasco, 16/11/2026 19:00)
and Sacha Dray's (World Bank) dashboard workshop (20/11 11:00).

1. **Policy question first** — đề → `brief.json` → one-line decision question (who decides what, measured by which KPI).
2. **Ingestion** by situation — Database/JDBC (read-only account, SELECT only), Public API (rate limit, pagination, retry/backoff, cache,
   keys in env), direct file download (encoding/sheets, record URL + licence), Web scraping (robots.txt, throttling, User-Agent, cache,
   bounded retries, ToS, no captcha/login bypass), Social listening (RSS/Trends, headlines only, sampling bias).
3. **Storage** — DuckDB bronze + Parquet lake with provenance; incremental reloads by `_row_hash`.
4. **Transform** — cleaning (missing, duplicates, outliers flagged not deleted, quality score before/after) → modelling chosen by data
   scale × hackathon time: OBT serves dashboard/insights, Star is the semantic model to present, Snowflake for geographic hierarchies,
   Data Vault to show auditability trade-offs; conformed dims when sources share province/year.
5. **Analysis** — tested insights, drivers, what-if with CI, forecast; association ≠ causation.
6. **Serving** — decision-oriented KPIs (3–5, each with comparison), **one question per view**, uncertainty shown, sources traceable;
   dashboard, AI Analyst, Câu chuyện, deck/pitch.

### User Story 0 — Economist judge evaluates the decision (Priority: P1)
**As** an economist judge (UEH School of Public Finance, World Bank, LSE, FiinGroup) **I want** the policy question first, then
tested evidence (n, p, effect, CI) with causal limits, then the recommendation and KPI, **so that** I can trust the decision.
**Acceptance**: **Given** a finished run, **When** the judge opens the deck or dashboard, **Then** the policy question is stated
up front, every insight shows test/p/effect/n, a Limitations slide exists, and any number can be re-derived with SQL in ≤ 30 s.

### User Story 0b — Non-coder teammate builds the story (Priority: P1)
**As** a business/social-science teammate who does not code **I want** to understand every chart and take numbers for slides from the
browser only, **so that** I contribute without a terminal.
**Acceptance**: **Given** the dashboard, **When** the teammate uses Hướng dẫn, Hỏi AI, Câu chuyện and Export, **Then** every step
works without CLI, in Vietnamese, offline if needed.

## User Scenarios & Testing *(mandatory)*

Actors: **Analyst** (thành viên đội biết code), **Presenter** (thành viên không code, điều khiển dashboard khi pitch),
**Judge** (giám khảo kinh tế / khoa học dữ liệu), **Agent** (Codex/coding agent tiếp tục phát triển).

### User Story 1 — Dataset → pipeline có thể giải thích (Priority: P1)
Analyst thả một file (csv/xlsx/json/parquet/zip) hoặc một `sources.yaml` nhiều nguồn và nhận warehouse bronze/silver/gold,
báo cáo chất lượng trước/sau, 4 mô hình dữ liệu kèm ERD, lineage.

**Why this priority**: không có dữ liệu sạch thì không có gì khác; giám khảo chấm phần Data Engineering.
**Independent Test**: `python de.py file data/practice/synthetic_messy_bds.csv` → `out/<ds>/pipeline.json` hợp lệ theo `contracts/pipeline.schema.json`.

**Acceptance Scenarios**:
1. **Given** một file Excel tiếng Việt có số "2,5 tỷ" và ngày `dd/mm/yyyy`, **When** chạy `de.py file`, **Then** silver có cột số/ngày đúng kiểu và `quality.json` có `score_before`, `score_after`, cleaning log.
2. **Given** `sources.yaml` có 2 nguồn chung cột tỉnh, **When** chạy `de.py run`, **Then** có `gold.<ds>__cdim_geo`, `obt_integrated_<ds>`, `conformed.json` với join coverage và không nhân dòng (`row_explosion=false` khi grain unique).
3. **Given** một nguồn API lỗi, **When** chạy pipeline, **Then** các nguồn khác vẫn được nạp và bước lỗi ghi `status=failed` kèm lỗi.
4. **Given** đã nạp file một lần, **When** chạy lại với `--mode incremental`, **Then** `load.inserted=0`, `load.skipped=<số dòng>`.

### User Story 2 — Insight có kiểm định + drivers + what-if (Priority: P1)
Analyst/Judge thấy insight xếp hạng, mỗi insight có kiểm định, p-value, effect size, n, caveat; drivers có CI; what-if trả % thay đổi + khoảng 90%.

**Why**: lõi "From Data to Decision"; giám khảo kinh tế đòi kiểm định.
**Independent Test**: `--serve` → `results.json` có `insights[*].test/p_value/effect`; `POST /api/datasets/{id}/whatif`.

**Acceptance Scenarios**:
1. **Given** dataset có cột phân loại và target số, **When** engine chạy, **Then** có insight phân khúc với Kruskal–Wallis/ANOVA và effect size.
2. **Given** feature số trong mô hình drivers, **When** POST what-if `pct_change=10`, **Then** trả `target_change_pct` và `ci90_pct` [lo, hi] và câu diễn giải "không phải nhân quả".
3. **Given** chuỗi thời gian ≥ 6 kỳ, **When** engine chạy, **Then** có forecast 3 kỳ với khoảng 80% và holdout MAE.

### User Story 3 — Đề bài → kế hoạch phân tích (Priority: P1)
Analyst dán đề, nhận biến mục tiêu (khớp cột thật), đơn vị, phân khúc, loại quyết định, scenario pack và kế hoạch.

**Independent Test**: `python de.py brief scenarios/briefs/bds_gia_m2.md --data data/practice/synthetic_messy_bds.csv`.

**Acceptance Scenarios**:
1. **Given** đề tiếng Việt hỏi "giá/m2 theo quận", **When** parse kèm cột dataset, **Then** `target.column` là cột thật (hoặc dẫn xuất `price_per_m2`) và `segments` chứa cột quận.
2. **Given** đề không khớp concept nào, **When** parse, **Then** `target=null` và `warnings` hướng dẫn chọn tay.

### User Story 4 — Dashboard + Hỏi AI cho người không code (Priority: P2)
Presenter mở dashboard, chọn dataset, đi qua Pipeline → Chất lượng → Mô hình → Insight → What-if → Quyết định; bật "Hỏi AI"
bấm vào bất kỳ thẻ để có giải thích; bấm "Câu chuyện" để driver.js kể top-5 insight.

**Acceptance Scenarios**:
1. **Given** không có khoá LLM, **When** bấm "Câu chuyện", **Then** câu chuyện offline dùng nguyên văn câu engine (`mode=offline`).
2. **Given** có khoá LLM và mô hình viết một số không có trong engine, **When** merge, **Then** câu đó bị thay bằng câu engine (`source=engine`).
3. **Given** trang thiếu phần tử tour, **When** chạy tour, **Then** bước đó được bỏ qua, không crash; Esc thoát chế độ Hỏi AI.

### User Story 5 — AI Analyst trả lời câu hỏi bằng công cụ (Priority: P2)
Judge hỏi bằng tiếng Việt; AI gọi tool (SQL chỉ đọc, insight, segments, drivers, what-if, quality, lineage, models) và chỉ trích số từ tool.

**Acceptance Scenarios**:
1. **Given** câu hỏi cần số liệu, **When** AI trả lời, **Then** mỗi số xuất hiện trong output tool của lượt đó.
2. **Given** AI sinh SQL `DROP TABLE`, **When** tool chạy, **Then** API trả 403 và không có thay đổi dữ liệu.
3. *(planned)* **Given** câu hỏi tự nhiên, **When** NL→SQL, **Then** hiện SQL, bảng và biểu đồ tự động, câu trả lời dẫn nguồn query.

### User Story 6 — Deck + pitch (Priority: P2)
Presenter tải `deck.pptx` 15 slide và `pitch.md` (Marp) có số engine, không tràn chữ.

**Acceptance**: **Given** pipeline đã `--serve`, **When** mở deck, **Then** có slide Pipeline/Model/Quality/Policy/Limitations/Provenance; `deck_overflow()` trả rỗng.

### User Story 6b — Policy-question-first, bilingual output (Priority: P2)
Presenter exports a deck and pitch that open with the policy question from the brief, in Vietnamese or English.

**Acceptance**: **Given** brief.json with questions and a decision type, **When** exporting with `lang=en`, **Then** slide 2 states the
policy question, all slide text is English, numbers identical to the VI version (planned T080–T081).

### User Story 7 — Wow features (Priority: P3)
Command palette Ctrl+K; NL→SQL + biểu đồ inline; trang what-if sliders; bản đồ 34 tỉnh; nút "Xuất báo cáo"; thẻ join coverage + tab Conformed. Trạng thái trong [tasks.md](tasks.md).

### User Story 8 — CV đếm phương tiện (Priority: P3, lowest — ~10% likely theme)
Analyst chạy `count.py` trên video có giấy phép → `counts.csv` → connector `cv` → warehouse.

### Edge Cases
- File rỗng / chỉ có tiêu đề / nhiều dòng tiêu đề → nguồn bị bỏ qua có ghi log; pipeline không crash khi còn nguồn khác; hết nguồn → lỗi "no source produced data".
- Tên tỉnh cũ (63) lẫn mới (34) trong cùng dữ liệu → chuẩn hoá về cả `province` và `province_2025`; tên lạ → `outside_reference_rows`.
- Nguồn có nhiều dòng mỗi khoá join → không join (tránh nhân dòng) trừ khi `conform.agg` được khai báo.
- Schema thay đổi giữa hai lần nạp incremental → full rebuild có ghi `reason`.
- SQL nhiều câu (`;`), DDL/DML, `read_csv()`, đọc file qua chuỗi `'path'` → bị từ chối (403).
- LLM timeout / sai định dạng / số bịa → rơi về engine text, endpoint không lỗi.
- Không có cột thời gian → bỏ forecast, trang timeseries trả `points=[]`.
- Dataset > 1 triệu dòng → DuckDB xử lý; insight engine lấy mẫu cho clustering (5.000 dòng).

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001** Hệ thống PHẢI nạp nguồn `file` (csv/tsv/txt/xlsx/xls/json/jsonl/parquet/zip), `api` (REST JSON, paging, retry, rate-limit, cache), `sql` (SQLAlchemy, SELECT-only), `scrape` (robots.txt, delay), `social` (RSS/Trends), `cv` (counts CSV).
- **FR-002** PHẢI ghi provenance mỗi nguồn (uri không chứa mật khẩu, thời điểm, giấy phép, fingerprint).
- **FR-003** PHẢI lưu medallion bronze/silver/gold/meta trong DuckDB + Parquet lake; bronze có `_row_hash`, `_src`, `_ingested_at`.
- **FR-004** PHẢI hỗ trợ `--mode replace|append|incremental`; incremental bỏ qua dòng có `_row_hash` đã tồn tại; schema đổi → rebuild; ghi inserted/skipped.
- **FR-005** PHẢI làm sạch kiểu dữ liệu định dạng Việt (số, tiền "tỷ/triệu", ngày, tỉnh, quận/huyện), đo chất lượng trước/sau (0–100), gắn cờ outlier 3×IQR, ghi cleaning log.
- **FR-006** PHẢI dựng OBT, Star, Snowflake, Data Vault 2.0 kèm ERD Mermaid + SQL và lý do khuyến nghị.
- **FR-007** PHẢI dựng conformed dimensions khi ≥2 bảng silver chung khoá; join không nhân dòng; báo join coverage.
- **FR-008** PHẢI ghi lineage nguồn→bronze→silver→gold→serving (JSON + Mermaid).
- **FR-009** PHẢI sinh insight xếp hạng có kiểm định, p-value, effect size, n, caveat, câu VI/EN.
- **FR-010** PHẢI ước lượng drivers (hồi quy chuẩn hoá, bootstrap CI, permutation importance, R² CV) và what-if có CI 90%.
- **FR-011** PHẢI dự báo chuỗi thời gian (Holt vs tuyến tính, chọn theo holdout) có khoảng 80%.
- **FR-012** PHẢI sinh khuyến nghị (so-what, now-what, impact (VI/EN) gắn insight bằng chứng).
- **FR-013** PHẢI parse đề VI/EN → `brief.json` theo `contracts/brief.schema.json`, khớp scenario pack.
- **FR-014** PHẢI cung cấp REST API theo `contracts/openapi.json`.
- **FR-015** PHẢI cung cấp SQL chỉ đọc (một câu SELECT/WITH/DESCRIBE/SUMMARIZE/EXPLAIN), giới hạn dòng.
- **FR-016** Web PHẢI có các trang: Tổng quan, Đề bài, Nguồn, Pipeline, Chất lượng, Mô hình, SQL, Hồ sơ, Insight, Drivers & What-if, Phân khúc, Quyết định, AI Analyst.
- **FR-017** Web PHẢI có tour "Hướng dẫn", chế độ "Hỏi AI" trên mọi phần tử `data-insight-target`, "Câu chuyện" top-5 có kiểm số.
- **FR-018** AI Analyst PHẢI chỉ dùng tool đọc; mọi số trong câu trả lời đến từ tool; offline khi không có khoá.
- **FR-019** PHẢI xuất deck.pptx (15 slide, không tràn chữ), pitch.md, executive summary md/html/pdf, dashboard.html.
- **FR-020** CV: `count.py` PHẢI xuất `counts.csv(timestamp,class,in,out)` từ video (YOLO+ByteTrack+LineZone) hoặc log sự kiện.
- **FR-021** *(planned)* Web PHẢI hiện join coverage (Pipeline) và tab Conformed + ERD (Mô hình); API `GET /api/datasets/{ds}/conformed`.
- **FR-022** *(planned)* Command palette Ctrl+K: điều hướng, "Câu chuyện", hỏi AI, what-if.
- **FR-023** *(planned)* NL→SQL trong chat: soạn SQL DuckDB, kiểm read-only, chạy, bảng + biểu đồ inline, dẫn nguồn query.
- **FR-024** *(planned)* Trang what-if sliders: KPI dự đoán + CI theo thời gian thực từ mô hình engine.
- **FR-025** *(planned)* Bản đồ choropleth 34 tỉnh theo chỉ số chọn; bấm tỉnh → Hỏi AI.
- **FR-026** *(planned)* Nút "Xuất báo cáo" một chạm (deck + pitch.md + PDF).
- **FR-027** *(planned)* Deck/pitch song ngữ `lang=vi|en`, mở đầu bằng câu hỏi chính sách từ brief.json.
- **FR-028** *(planned)* Scenario pack `energy_ev_data_economy`; công thức so sánh WDI Việt Nam vs ASEAN (conformed theo country+year).

### Non-Functional Requirements
- **NFR-001 Hiệu năng**: trên 2 CPU/7 GB, pipeline DE cho file 100k dòng × 30 cột ≤ 60 s (đo thực: Hà Nội 81.681 dòng chạy được trên máy này); DuckDB `threads=2`.
- **NFR-002 Bộ nhớ**: không vượt 4 GB RSS cho dataset ≤ 1 triệu dòng; clustering lấy mẫu 5.000 dòng.
- **NFR-003 Offline**: mọi tính năng AI có đường offline; demo chạy không cần Internet khi dữ liệu đã có/cached.
- **NFR-004 Lịch thi**: từ lúc có đề (20/11 09:00) đến dashboard + deck đầu tiên ≤ 2 giờ; nộp trước 21/11 13:00.
- **NFR-005 Bảo mật**: theo `SECURITY.md` (SQL read-only, SSRF, upload limit, CORS, header bảo mật, không commit secret).
- **NFR-006 Khả dụng**: UI tiếng Việt có dấu, dùng được bởi người không code sau 5 phút đọc PLAYBOOK.
- **NFR-007 Khả bảo trì**: mỗi tính năng có test; contracts có test đồng bộ (`tests/test_contracts.py`); spec/tasks cập nhật mỗi push.
- **NFR-008 Giấy phép**: chỉ open-source; giấy phép dữ liệu/asset ghi trong `docs/licenses.md`/provenance.

### Key Entities
- **Source** (name, kind, uri, options, license_note, conform) → **IngestResult** (frames, provenance).
- **Run** (`meta.runs`: run_id, dataset, step, status, timings, detail incl. inserted/skipped).
- **Table** theo layer bronze/silver/gold; **QualityReport** (before/after/cleaning_log/scores).
- **Model** (OBT/Star/Snowflake/DataVault/Conformed: tables, ERD, SQL, rationale).
- **ConformedDimension** (cdim_geo/date/year/<key>) · **JoinCoverage**.
- **LineageEdge** (from, to, step).
- **Insight** (rank, kind, title/sentence VI/EN, test, p_value, effect, evidence, chart, caveat) · **Recommendation** · **DriverModel** · **WhatIfResult**.
- **Brief** · **ScenarioPack** · **Story/StoryStep** · **Deck**.
Chi tiết: [data-model.md](data-model.md).

## Success Criteria *(mandatory)*
- **SC-001** 100% số trên UI/deck/AI truy được về engine/DuckDB (test kiểm số story + verify agent; review thủ công deck).
- **SC-002** `pytest -q tests` và `npm test`/`lint`/`build` pass ở mỗi commit trên `main` (hiện: 150 pytest pass + 1 skip + 2 xfail; 20 node test).
- **SC-003** Từ file thô đến dashboard + deck ≤ 15 phút trên máy 2 CPU cho dataset ≤ 100k dòng.
- **SC-004** Điểm chất lượng silver ≥ điểm bronze trên mọi dataset luyện tập (Hà Nội: 84,9 → 92,4).
- **SC-005** Người không code hoàn thành tour + Câu chuyện + tải deck trong ≤ 5 phút (diễn tập PLAYBOOK).
- **SC-006** Mọi endpoint ghi/SQL từ chối input độc (DDL/DML, IP nội bộ, file ngoài thư mục cho phép) — test bảo mật pass.
- **SC-007** Chạy incremental lần 2 trên cùng file: `inserted=0`.

## Assumptions & Open Questions
- [NEEDS CLARIFICATION: dataset chính thức của đề — định dạng, kích thước, có nhiều bảng không? BTC công bố 20/11 09:00]
- [NEEDS CLARIFICATION: chủ đề đề bài — tài chính công tỉnh, bất động sản, doanh nghiệp niêm yết, chỉ số phát triển, hay CV quan sát? 7 scenario pack đã chuẩn bị]
- [NEEDS CLARIFICATION: định dạng nộp bài — chỉ deck, hay cần link dashboard/repo/video? Có được dùng LLM trả phí?]
- [NEEDS CLARIFICATION: có Internet ổn định tại địa điểm thi không — quyết định dùng LLM online hay Ollama/offline]
- [NEEDS CLARIFICATION: video CV có được cung cấp và giấy phép sử dụng?]
- Giả định: đội 4–5 người, 1–2 laptop đủ chạy; dữ liệu tiếng Việt; tỉnh có thể theo danh mục 34 đơn vị (sau NQ 202/2025/QH15).
