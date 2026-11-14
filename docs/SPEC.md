# VietLeap Insight Kit — Đặc tả (SPEC)

> Tài liệu này mô tả **những gì code đang làm** (đối chiếu với mã nguồn, không phải ý định). Mỗi mục ghi đường dẫn file để kiểm chứng.
> Trạng thái công việc: `docs/MASTER_PLAN.md` mục 0. Hướng dẫn hôm thi: `docs/PLAYBOOK.md`. Bối cảnh: `docs/CONTEXT.md`.

## 1. Mục đích

Bộ công cụ cho đội thi **VietLeap Hackathon 2026** (UEH School of Public Finance × AVSE): trong 28 giờ, biến *dataset + đề bài* thành
**pipeline dữ liệu có thể giải thích → insight có kiểm định thống kê → mô phỏng what-if → khuyến nghị chính sách → dashboard + deck pitch**.

Nguyên tắc cứng (AGENTS.md):
1. **Không bịa số** — mọi con số trên UI, deck, câu trả lời AI đều lấy từ engine (pandas/scipy/sklearn) hoặc DuckDB; AI bị kiểm số (mục 9).
2. Chỉ dùng open-source; UI chỉ dùng component shadcn chính thức (block `dashboard-01`, style base-nova), không restyle.
3. Giao diện tiếng Việt có dấu; múi giờ Asia/Saigon (`engine/vlkit/de/sources.py: TZ`).
4. Chạy được trên laptop yếu (2 CPU, 7 GB RAM): DuckDB `threads=2`, không build web song song với engine.
5. Chạy được **offline**: thiếu khoá LLM vẫn có AI Analyst/Câu chuyện bằng văn bản do engine sinh.

## 2. Luồng ngày thi (drop dataset + đề → outputs)

```
20/11 09:00  BTC công bố đề
  ├─ Dán đề vào trang "Đề bài" (POST /api/brief) ──► brief.json: biến mục tiêu, đơn vị, phân khúc, loại quyết định, scenario pack, kế hoạch
  ├─ Thả file (Upload / trang Nguồn) hoặc sources.yaml nhiều nguồn
  │     python de.py file data.xlsx --serve      |  python de.py run sources.yaml --primary <src> --serve
  │     ──► bronze → silver (làm sạch + điểm chất lượng) → gold (OBT/Star/Snowflake/Data Vault [+ conformed])
  │     ──► insight engine trên gold OBT: kiểm định, drivers, what-if, phân khúc, dự báo, khuyến nghị
  ├─ Dashboard (Next.js) đọc API: Pipeline / Chất lượng / Mô hình / Insight / What-if / Quyết định / AI Analyst
  ├─ "Hỏi AI" (bấm vào bất kỳ thẻ) · "Câu chuyện" (top-5 insight, driver.js dẫn từng thẻ) · "Hướng dẫn" (tour)
  └─ Exports: out/<ds>/deck.pptx (15 slide) · pitch.md (Marp) · executive_summary.{md,html,pdf} · dashboard.html
21/11 13:00  nộp  ·  13:15 pitch 7 phút (slides/pitch.md)
```

## 3. Kiến trúc

```mermaid
flowchart LR
  subgraph Ingestion["Ingestion — engine/vlkit/de/connectors.py"]
    F[file csv/xlsx/json/parquet/zip] & A[api REST paging/retry/cache] & Q[sql SELECT-only] & S[scrape robots.txt] & SO[social RSS/Trends] & CV[cv counts.csv]
  end
  subgraph Storage["Storage — DuckDB data/warehouse.duckdb + Parquet data/lake/"]
    B[(bronze.*<br/>+_row_hash,_src,_ingested_at)]
    M[(meta.sources/runs/lineage/quality/join_coverage)]
  end
  subgraph Transform["Transform"]
    SI[(silver.*<br/>quality.py)] --> G1[(gold OBT/Star/Snowflake/DV<br/>modeling.py)]
    SI --> G2[(gold cdim_*/cfact_*/obt_integrated<br/>conformed.py)]
  end
  subgraph Serving["Serving"]
    E[insight engine<br/>vlkit/pipeline.py] --> O[out/&lt;ds&gt;/*.json, deck.pptx, pitch.md, pdf]
    API[FastAPI api/] --> WEB[Next.js 16 web/<br/>shadcn dashboard-01]
    WEB --> AI[AI Analyst /api/chat<br/>Vercel AI SDK + tools]
  end
  F & A & Q & S & SO & CV --> B --> SI
  G1 --> E
  O --> API
  B & SI & G1 & G2 --> API
  AI -->|tool calls| API
```

Thành phần:

| Thư mục | Vai trò | Entry |
|---|---|---|
| `engine/vlkit/` | Engine Python (pandas, scipy, statsmodels/sklearn, duckdb, python-pptx, plotly) | `run.py` (insight 1 file), `de.py` (pipeline DE) |
| `engine/vlkit/de/` | Lớp Data Engineering: connectors, warehouse, quality, modeling, conformed, lineage, flow | `flow.run_flow`, `flow.run_file` |
| `api/` | FastAPI: dataset lifecycle, analysis, DE/pipeline, brief, agent SSE | `uvicorn api.main:app --port 8000` |
| `web/` | Next.js 16 App Router + shadcn/ui + Recharts + mermaid + driver.js + AI SDK v7 | `npm run dev` / `build`+`start` |
| `scenarios/` | `packs/` (7 miền đề), `briefs/` (đề mẫu), `demo/` (5 loại nguồn), `conformed/`, `cv_counting/` | |
| `slides/` | `pitch.md` storyline Marp 7 phút | |
| `tests/` | pytest (engine, DE, deck, CV, brief, VN parsing); `web/src/**/*.test.ts` (node --test) | |

## 4. Module

### 4.1 Ingestion — `engine/vlkit/de/connectors.py`, `sources.py`
`Source(name, kind, uri, options, license_note, conform)`; `KINDS = file, api, sql, scrape, social, cv`. Mỗi lần ingest trả `IngestResult(frames, provenance)` — một nguồn có thể sinh nhiều bảng (sheet Excel, bảng HTML).

| kind | Hành vi |
|---|---|
| `file` | csv (tự dò encoding/dấu phân cách), xlsx (mọi sheet), json, parquet, zip (mọi file bên trong) |
| `api` | httpx GET, `params`, `records_path` (đào vào JSON), `paging` (`worldbank`, page/offset), retry (tenacity) cho lỗi mạng/5xx/429, `min_interval` rate-limit, cache JSON trong `data/cache/` |
| `sql` | SQLAlchemy URI, chỉ chấp nhận `SELECT` |
| `scrape` | kiểm `robots.txt` trước, delay, đọc bảng HTML (`table_index: largest|n`), tuỳ chọn render Playwright; không vượt captcha/đăng nhập |
| `social` | RSS (feedparser), Google Trends (pytrends nếu cài) |
| `cv` | `counts.csv` hoặc log sự kiện vượt vạch từ `scenarios/cv_counting/count.py` |

Provenance mỗi nguồn: `source, kind, uri, options, fetched_at, license_note, tables{rows, cols, fingerprint(sha256)}`.
`sources.yaml`: `dataset`, `keys:` (khoá conformed khai báo), `sources: [{name, kind, uri, options, license, conform}]` (đường dẫn file tương đối theo yaml).

### 4.2 Storage — `engine/vlkit/de/warehouse.py`
DuckDB file `data/warehouse.duckdb`, 4 schema: `bronze` (nguyên trạng + `_row_hash`, `_src`, `_ingested_at`), `silver`, `gold`, `meta`.
Mỗi bảng bronze/silver/gold có bản Parquet `data/lake/<layer>/<name>.parquet`. Bảng meta: `sources`, `runs(run_id, dataset, step, status, started_at, finished_at, detail JSON)`, `lineage`, `quality`, `join_coverage`, `geo_alias`, bảng tham chiếu tỉnh.
`Warehouse.sql()` chỉ đọc: một câu `SELECT/WITH/DESCRIBE/SHOW/SUMMARIZE/EXPLAIN`, chặn DDL/DML/`read_*()`/`glob()`/`COPY`/`ATTACH`…, bọc `LIMIT`.
Chế độ nạp (`mode`): xem mục 4.2.1.

#### 4.2.1 Nạp tăng dần (incremental) — xem mục 13 trạng thái
`--mode replace|append|incremental` (mặc định `replace`). `append`: thêm mọi dòng mới vào bronze; `incremental`: chỉ thêm dòng có `_row_hash` chưa có; schema đổi (khác tập cột) → tự rebuild toàn bộ bảng (`replace`). Số dòng `inserted/skipped` ghi vào `meta.runs.detail` và `pipeline.json.load`.

### 4.3 Transform 1 — chất lượng → silver (`engine/vlkit/de/quality.py`, `vn.py`, `loader.py`)
- Phân tích kiểu & vai trò cột (số, phân loại, thời gian, địa lý, id, text) có xử lý định dạng Việt: số `1.234,5`, "2,5 tỷ", "800 triệu", ngày `dd/mm/yyyy`, tên tỉnh có/không dấu, "TP. HCM", quận/huyện (`normalize_district`).
- Đo trước/sau: missing, ô không hợp lệ, dòng trùng, khoá ứng viên & trùng khoá, outlier 3×IQR (**gắn cờ**, không xoá) → điểm 0–100 (`score_before/after`).
- Cleaning log từng bước; `--impute median` tuỳ chọn. Chuẩn hoá tỉnh 63 → 34 (NQ 202/2025/QH15), vùng GSO.

### 4.4 Transform 2 — mô hình dữ liệu (`engine/vlkit/de/modeling.py`)
Trên bảng silver chính (lớn nhất hoặc `--primary`):
- **OBT** `gold.obt_<ds>` — bảng phẳng cho insight engine/BI.
- **Star** `fact_<ds>` + `dim_*` (dim_geo cấp quận/huyện khi có, dim_date, dim phân loại).
- **Snowflake** dim chuẩn hoá: district → province → province_2025 → region.
- **Data Vault 2.0** `hub_*`, `lnk_*`, `sat_*` (hash key, load_date, record_source).
- Sinh ERD Mermaid + SQL (`out/<ds>/models/*.sql|*.mmd`), `rationale` và `recommended` (vì sao chọn mô hình nào).

### 4.5 Transform 3 — conformed dimensions (`engine/vlkit/de/conformed.py`)
Khi ≥2 bảng silver chung khoá (khai báo trong `keys:` hoặc tự phát hiện: tỉnh, quận/huyện, năm, ngày, mã CK, quốc gia ISO3, khoá bất kỳ):
`gold.<ds>__cdim_geo|cdim_date|cdim_year|cdim_<key>`, `gold.<ds>__cfact_<src>` (mọi dòng + FK), `gold.obt_integrated_<ds>` (LEFT JOIN chỉ khi nguồn kia unique tại grain join, hoặc YAML `conform.agg`; không bao giờ nhân dòng).
Tuỳ chọn mỗi nguồn: `conform: {where, agg: mean|sum|min|max|first, geo_level: "2025", province}`.
Join coverage: matched/unmatched/null mỗi nguồn × khoá, mẫu chưa khớp, overlap Jaccard từng cặp → `meta.join_coverage`, `pipeline.json.conformed`, `conformed.json`, `lineage.json.join_coverage`.

### 4.6 Lineage — `engine/vlkit/de/lineage.py`
`meta.lineage(from_node, to_node, step)` với step `ingest, clean, model, conform, fk, integrate, serve` → `lineage.json {dataset, nodes[{id,label,layer,stage}], edges[{from,to,step}], join_coverage?}` + `lineage.mmd` (subgraph Ingestion/Storage/Transform/Serving).

### 4.7 Insight engine — `engine/vlkit/pipeline.py`, `insights.py`, `stats.py`, `models.py`, `decision.py`, `domains.py`
`run(path, target, time_col, geo_col, domain)` → `out/<ds>/results.json`:
- Hồ sơ dữ liệu (`profile.py`), chọn target/time/geo theo domain (`property`, `public_finance`, `firm`, `generic`; chỉ số dẫn xuất như `price_per_m2`, `roe_pct`).
- Insight xếp hạng (≤12): phân khúc (Kruskal–Wallis + ANOVA, top-vs-bottom Mann–Whitney/Welch t, ε², η², rank-biserial, Cohen d), xu hướng (hồi quy tuyến tính `linregress`, phát hiện điểm gãy hai đoạn, `trend_stats`), tập trung (top-20% share, Gini, HHI), tương quan (Spearman, p hiệu chỉnh Bonferroni), drivers, cụm (KMeans `segment`). Mỗi insight có `test, p_value, effect, evidence, chart, caveat`, câu VI/EN.
- `stat_test`: `auto, mannwhitney, ttest, kruskal, anova, spearman, pearson, chi2`.
- Dự báo (`forecast`, horizon 3): Holt (ExponentialSmoothing trend cộng, statsmodels) so với hồi quy tuyến tính trên tập giữ lại, chọn mô hình tốt hơn.
- **Drivers** (`models.fit_drivers`): hồi quy chuẩn hoá (log target khi lệch), lọc rò rỉ (|r|>0.97), bootstrap CI, permutation importance, R² kiểm định chéo.
- **What-if** (`models.what_if`): đổi biến số x% → % thay đổi target + khoảng 90% bootstrap; `GET whatif/curve` −30…+30%.
- **Khuyến nghị** (`decision.recommend`): hành động, so-what, impact, evidence, KPI/owner.

### 4.8 Brief parser — `engine/vlkit/brief.py`
Rule-based VI/EN (không cần LLM): tách câu hỏi, chấm điểm concept → biến mục tiêu (khớp cột thật nếu có dataset), đơn vị (tỉnh/quận/doanh nghiệp/…), phân khúc, mốc năm, loại quyết định, deliverables, nguồn được nhắc, scenario pack phù hợp nhất, `run_config`, `plan`, `warnings`.

### 4.9 Scenario packs — `scenarios/packs/*.yaml`
7 pack: `cv_observation`, `data_economy_property`, `development_indicators`, `economic_policy`, `listed_firms_market`, `public_finance_province`, `social_impact`. Trường: `id, title, sponsor, domain, keywords, expected_columns, kpis, recipe, decision_template, deck_storyline`. Đề mẫu trong `scenarios/briefs/`.

### 4.10 Báo cáo — `engine/vlkit/report.py`
`deck.pptx` 15 slide (bìa, KPI, insight + biểu đồ Plotly→PNG, drivers, what-if, Data pipeline, Data model, Data quality trước/sau, Policy recommendation, Limitations, Provenance); fit chữ (co ≥10pt rồi cắt) + `deck_overflow()`. `pitch.md` (Marp, số từ engine), `executive_summary.md/html/pdf` (PDF qua Chromium headless nếu có), `dashboard.html` tĩnh.

### 4.11 CV counting — `scenarios/cv_counting/count.py`
YOLOv8n + ByteTrack (supervision / trackers / ultralytics) + `LineZone` → `counts.csv (timestamp,class,in,out)` zero-fill theo `--every`; `--events` gộp log vượt vạch không cần torch; exit 2 thân thiện khi thiếu thư viện; `meta.json` ghi giấy phép. Đầu ra đi qua connector `cv`.

## 5. API (FastAPI, `api/`)

| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/health` | trạng thái, số dataset |
| GET | `/api/datasets` | danh sách dataset (đọc `out/*/results.json`) |
| POST | `/api/datasets` | upload file (multipart: file, target, time, geo, domain, name) → job phân tích nền |
| GET | `/api/jobs/{id}` | trạng thái job upload |
| GET | `/api/datasets/{id}` · `/profile` · `/rows` | tóm tắt, hồ sơ cột, phân trang dòng |
| GET | `/api/datasets/{id}/files/{kind}` | export: `deck, dashboard, summary_pdf, summary_md, results, clean_csv` |
| GET | `/api/datasets/{id}/charts/{name}.png` | biểu đồ PNG |
| GET | `/api/datasets/{id}/insights` | insight + khuyến nghị |
| GET | `/api/datasets/{id}/timeseries` | chuỗi thời gian (metric, agg, freq, group) + trend/forecast |
| GET | `/api/datasets/{id}/segments` | nhóm theo cột + kiểm định + cụm |
| GET | `/api/datasets/{id}/drivers` | drivers + đặc trưng cho what-if |
| POST | `/api/datasets/{id}/whatif` | `{feature, pct_change, target?}` → % thay đổi + CI90 |
| GET | `/api/datasets/{id}/whatif/curve` | đường −30…+30% |
| GET | `/api/agent/config` · POST `/api/datasets/{id}/agent` | agent Python (SSE: plan/tool_call/…/verification) |
| GET | `/api/sources/kinds` | loại nguồn + ví dụ |
| POST | `/api/ingest` | `IngestIn {dataset, sources[], primary?, impute?, serve, mode?}` → job pipeline DE |
| GET | `/api/ingest/{job_id}` | trạng thái job DE |
| GET | `/api/warehouse/tables` · `/tables/{fq}/columns` | danh mục warehouse |
| POST | `/api/sql` | SQL chỉ đọc `{query, limit≤5000}` → `{columns, rows, row_count}`; 403 khi vi phạm |
| GET | `/api/datasets/{ds}/pipeline` · `/quality` · `/lineage` · `/models` · `/provenance` | đầu ra DE |
| GET | `/api/datasets/{ds}/conformed` | conformed.json (dims, facts, joins, coverage, ERD) — mục 13 |
| POST | `/api/brief` · GET `/api/brief/packs` · `/api/brief/samples` | đề → brief.json |

Ghi DuckDB: một writer, mọi request warehouse đi qua `_wh_lock`.

## 6. Web (Next.js 16, `web/`)
Mọi request `/api/*` không phải route Next được rewrite sang FastAPI (`next.config.ts`), không có CORS ở trình duyệt.
Trang (`web/src/app/(dashboard)/`): **Tổng quan** `/`, **Đề bài** `/brief`, **Nguồn dữ liệu** `/sources` (form nhiều nguồn → `/api/ingest`), **Pipeline** `/pipeline` (lineage mermaid, timings, steps), **Chất lượng** `/quality`, **Mô hình** `/model` (Tabs OBT/Star/Snowflake/Data Vault + ERD + SQL), **SQL Explorer** `/sql`, **Hồ sơ** `/profile`, **Insight** `/insights`, **Drivers & What-if** `/drivers`, **Phân khúc** `/segments`, **Quyết định** `/decision`, **AI Analyst** `/analyst`.
Route handler Next: `/api/chat` (AI SDK `streamText` + tools), `/api/story`.
Chọn dataset qua `DatasetProvider`; Exports trong sidebar (deck, dashboard HTML, PDF).

### 6.1 Explain-anything & tour (`web/src/components/insight-inspector.tsx`, `insight-sheet.tsx`, `lib/tour-steps.ts`, `lib/analyst/explain.ts`)
- **Hướng dẫn**: tour driver.js theo trang (bước viết tay + tự phát hiện phần tử `data-insight-target`), một tour tại một thời điểm, huỷ khi đổi route, bỏ phần tử thiếu.
- **Hỏi AI**: bật ở thanh trên, rê/bấm phần tử có `data-insight-target` (+ `data-insight-*` payload) → Sheet AI giải thích (LLM, hoặc offline deterministic `explain.ts`); Esc thoát.
- **Câu chuyện**: `/api/story` kể top-5 insight (LLM hoặc text engine), giữ câu LLM chỉ khi mọi con số khớp output engine (`lib/analyst/story.ts`), driver.js lần lượt highlight từng thẻ insight.

### 6.2 AI Analyst tools (`web/src/lib/analyst/tools.ts`)
`listTables, getColumns, runSql, getInsights, getSegments, getDrivers, whatIf, getQuality, getLineage, getModels` — đều gọi FastAPI; system prompt (`prompt.ts`) cấm tự tính số. Model: Groq (`GROQ_API_KEY`) ưu tiên, hoặc OpenAI-compatible; không có khoá → trả lời offline từ engine. Agent Python song song trong `api/agent/` (`runner.py` + `verify.py` kiểm số, một vòng tự sửa).

## 7. Hợp đồng dữ liệu (out/&lt;ds&gt;/)

### `pipeline.json`
```jsonc
{ "dataset": "demo_multi", "run_id": "a1b2c3d4", "finished_at": "2026-11-14T10:00:00+07:00",
  "timings": {"ingest": 1.2, "clean": 0.8, "model": 0.5, "conform": 0.3, "serve": 4.1},
  "steps": [{"step": "ingest:<src>", "status": "ok|failed", "tables": ["..."], "error": "..."}],
  "bronze": ["bronze.<ds>__<src>"], "silver": ["silver.<ds>__<src>"], "primary": "silver.<ds>__<src>",
  "gold": ["gold.obt_<ds>", "..."],
  "quality": {"silver.<t>": {"score_before": 84.9, "score_after": 92.4, "rows": 81681, "issues": 7}},
  "models": {"obt|star|snowflake|data_vault|conformed": {"tables": ["gold.*"], "erd": "erDiagram ..."}},
  "column_plan": {...}, "rationale": {...}, "recommended": "...",
  "provenance": [{"source": "...", "kind": "...", "uri": "...", "fetched_at": "...", "license_note": "...", "tables": {...}}],
  "conformed": null | <conformed.json>,
  "load": {"mode": "replace|append|incremental", "tables": {"bronze.<t>": {"inserted": 0, "skipped": 0, "rebuilt": false}}},
  "served": true }
```

### `quality.json`
`{ "silver.<t>": { "before": {rows, cols, missing_cells, invalid_cells, duplicate_rows, candidate_key, duplicate_keys, score, columns, issues[]}, "after": {...}, "cleaning_log": [...], "score_before": n, "score_after": n } }`

### `lineage.json`
`{ "dataset", "nodes": [{id, label, layer: source|bronze|silver|gold|serving, stage: Ingestion|Storage|Transform|Serving}], "edges": [{from, to, step}], "join_coverage"?: {joins, sources} }`

### `conformed.json`
```jsonc
{ "shared_keys": ["geo", "year"], "dims": {"geo": "gold.<ds>__cdim_geo", "year": "gold.<ds>__cdim_year"},
  "facts": {"silver.<t>": "gold.<ds>__cfact_<src>"}, "integrated": "gold.obt_integrated_<ds>",
  "integrated_rows": 1234, "base": ["silver.<t>"], "base_rows": 1234, "row_explosion": false,
  "joins": [{"source": "...", "keys": ["year"], "join_on": ["year_key"], "status": "joined|skipped_not_unique|...",
             "aggregated": null, "where": null, "columns_added": 3, "distinct_keys": 20,
             "matched_rows": 1000, "unmatched_rows": 234, "match_pct": 81.0, "unmatched_samples": ["..."], "source_keys_used": 18}],
  "sources": [{"table": "...", "source": "...", "rows": 100, "geo_level": "district|63|2025|null",
               "keys": {"geo": {"column": "...", "matched_rows": 98, "null_key_rows": 1, "unmatched_rows": 1, "match_pct": 98.0, "outside_reference_rows": 0}}}],
  "overlap": [{"key": "year", "a": "...", "b": "...", "a_keys": 20, "b_keys": 30, "shared_keys": 15, "jaccard": 0.43}],
  "detected": {"silver.<t>": {"geo": "<col>", "year": "<col>"}} }
```

### `brief.json`
`{ language: "vi"|"en", title, questions[], target: {concept, label, column, resolved, domain, score}|null, alternatives[], units[], segments[], time: {years[], range}, decision_types: [{id, label, hits}], deliverables[], data_sources_mentioned[], pack: {id, title, sponsor, kpis, recipe, decision_template, deck_storyline, expected_columns}|null, pack_scores, run_config: {target, domain, segment_by}, plan[], warnings[], dataset }`

Khác: `results.json` (insight engine: meta, profile, insights, drivers, timeseries, segments, recommendations, kpis), `whatif.json`, `provenance.json`, `models/*.sql|*.mmd`.

## 8. CLI & Makefile
```
python de.py file <path> [--name DS] [--impute median] [--serve] [--target COL] [--out DIR] [--mode replace|append|incremental]
python de.py run <sources.yaml> [--primary SRC] [... như trên]
python de.py tables | sql "SELECT ..." [--limit N] | brief <đề.md> [--data file] [--out brief.json]
python run.py <file> [--target ...]          # insight engine trực tiếp
python scenarios/cv_counting/count.py --video v.mp4 | --events log.csv
make setup | api | web | web-dev | demo | demo-online | brief F=.. D=.. | test | test-py | test-web | clean-out
```

## 9. Biến môi trường
| Biến | Nơi | Ý nghĩa |
|---|---|---|
| `KIT_OUT_DIR`, `KIT_UPLOAD_DIR` | api | thư mục out/ và upload |
| `CORS_ORIGINS` | api | mặc định localhost:3000 |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`/`OPENAI_API_KEY`, `LLM_TIMEOUT_S`, `AGENT_MAX_STEPS` | api agent | agent Python OpenAI-compatible |
| `REPORTS_ON_UPLOAD` | api | sinh deck/PDF khi upload (mặc định 1) |
| `API_URL` | web (server) | FastAPI cho rewrite + tools (mặc định http://127.0.0.1:8000) |
| `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_API_DOCS_URL` | web (client) | base URL tuỳ chọn, link tài liệu API |
| `GROQ_API_KEY`, `GROQ_MODEL` | web | LLM Groq (ưu tiên) |
| `OPENAI_COMPATIBLE_BASE_URL`, `_MODEL`, `_API_KEY` | web | LLM OpenAI-compatible (Ollama, OpenRouter…) |
| `NO_PROXY=localhost,127.0.0.1` | shell | bắt buộc trên máy có HTTP_PROXY |

## 10. Kiểm thử
- `pytest -q tests` — engine, DE pipeline, conformed, district, deck (tràn chữ), CV counting, brief, số/ngày/tỉnh VN, smoke pipeline.
- `cd web && npm test` (node --test: explain, story, tour-steps …) · `npm run lint` · `npm run build`.
- Không chạy `npm run build` song song pytest (máy 2 CPU).

## 11. Ngoài phạm vi (non-goals)
- Không phải nền tảng BI đa người dùng; không xác thực, không phân quyền (chạy local/demo).
- Không suy luận nhân quả: drivers/what-if là liên hệ có điều kiện, luôn ghi caveat.
- Không streaming/real-time; không orchestrator (Airflow/Dagster) — `flow.py` tuần tự, đủ cho 28 giờ.
- Không vượt captcha/đăng nhập/robots.txt khi scrape.

## 12. Hạn chế đã biết
- **LLM chưa được kiểm thử với khoá thật** trong CI/phiên dev: đường offline có unit test; đường LLM (Groq/OpenAI-compatible) chỉ kiểm qua kiểu và xử lý lỗi.
- **YOLO chưa chạy thật** (cần `pip install ultralytics supervision` + video có giấy phép); test dùng sự kiện tổng hợp/clip tổng hợp.
- DuckDB một writer: job ingest tuần tự qua khoá; đọc trong lúc ghi sẽ chờ.
- Brief parser rule-based: đề diễn đạt lạ có thể không khớp concept → cảnh báo và để engine tự chọn target.
- Chuẩn hoá tỉnh 63→34 theo bảng tham chiếu đóng gói; tên ngoài bảng bị đánh dấu `outside_reference`.
- PDF cần Chromium headless (`make setup`); thiếu thì bỏ qua PDF.

## 13. Wow features — trạng thái

| Tính năng | Trạng thái |
|---|---|
| Pipeline DE 4 tầng + 4 mô hình + ERD + lineage | ✅ done |
| Conformed dimensions đa nguồn + join coverage + dim_geo quận/huyện | ✅ done (engine) |
| "Hỏi AI" bấm vào bất kỳ thẻ · tour driver.js · "Câu chuyện" top-5 có kiểm số | ✅ done |
| Đề → brief.json + 7 scenario pack | ✅ done |
| Deck 15 slide + pitch.md + kiểm tràn chữ | ✅ done |
| CV đếm phương tiện (YOLO + ByteTrack) | ✅ done (chưa chạy model thật) |
| Nạp tăng dần theo `_row_hash` (`--mode`) | ✅ done |
| Pipeline: thẻ join coverage · Mô hình: tab Conformed + ERD · `/api/datasets/{ds}/conformed` | ⏳ planned |
| Command palette Ctrl+K (cmdk) | ⏳ planned |
| NL → SQL trong AI Analyst + bảng + biểu đồ tự động | ⏳ planned |
| Trang what-if sliders (dự báo KPI + CI theo thời gian thực) | ⏳ planned |
| Bản đồ choropleth 34 tỉnh | ⏳ planned |
| Nút "Xuất báo cáo" một chạm | ⏳ planned |
| docker-compose + GitHub Actions CI | ⏳ planned |
