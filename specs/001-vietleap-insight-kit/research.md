# Research: technology decisions

Each decision: **Decision** · **Rationale** · **Alternatives considered**. Constraints driving all of them: 28-hour contest,
2 CPU / 7 GB laptop, offline-capable, open-source only, judges who value explainable DE + rigorous statistics.

## R1. Warehouse — DuckDB (+ Parquet lake)
- **Decision**: embedded DuckDB file with schemas bronze/silver/gold/meta; every table also COPY'd to Parquet.
- **Rationale**: no server; columnar and fast on millions of rows with 2 threads; reads CSV/Parquet/Excel natively; standard SQL that judges can read; Parquet makes layers portable (Spark/BigQuery/Postgres). Single file is easy to reset.
- **Alternatives**: PostgreSQL (server + ops overhead, slower for analytics on a laptop); SQLite (row store, weak analytics); Spark/Delta (too heavy for 7 GB); pure pandas + CSV (no SQL explorer, no lineage tables).
- **Consequence**: one writer per process → API serialises warehouse access with a lock.

## R2. Transform engine — pandas + scipy/statsmodels/scikit-learn
- **Decision**: pandas for cleaning/VN parsing; scipy for tests; statsmodels for Holt forecast; scikit-learn for KMeans, permutation importance, CV.
- **Rationale**: the statistics judges expect (Kruskal–Wallis, Mann–Whitney, Welch, Spearman, Bonferroni, bootstrap) are first-class; team knows the stack.
- **Alternatives**: Polars (faster but less stats ecosystem; pandas 3 is sufficient at our scale); dbt (great for SQL models but adds a toolchain and Jinja for a 28 h build — models are generated SQL we also save to `out/<ds>/models/*.sql`).

## R3. API — FastAPI + pydantic 2
- **Decision**: FastAPI with pydantic validation, background threads for jobs, SSE for the Python agent.
- **Rationale**: typed validation at the edge (security), automatic OpenAPI (`contracts/openapi.json`), simple to run (`uvicorn`).
- **Alternatives**: Flask (no built-in validation/OpenAPI); Django (heavy); calling Python from Next.js directly (no process isolation).

## R4. Web — Next.js 16 + shadcn/ui dashboard-01
- **Decision**: Next.js App Router; shadcn `dashboard-01` block as the shell, official components only; Recharts via shadcn chart; mermaid for lineage/ERD.
- **Rationale**: polished, accessible UI without design time (constitution IV); `/api/*` rewrite to FastAPI removes CORS; route handlers host the AI SDK.
- **Alternatives**: Streamlit/Dash (fast but looks generic, limited interactivity like driver.js/inspect mode); Superset/Metabase (heavy, harder to embed AI explain-anything); Vite SPA (no server route handlers for the LLM key).

## R5. AI layer — Vercel AI SDK v7 with tools
- **Decision**: `streamText` + zod-typed tools that only call read-only FastAPI endpoints; `generateText` for the story.
- **Rationale**: provider-agnostic, streaming UI hooks (`useChat`), first-class tool calling; numbers stay grounded in tool output.
- **Alternatives**: LangChain (heavier, more abstraction than needed); hand-rolled fetch to OpenAI API (more code, no UI hooks). A Python agent (`api/agent/`) exists too for SSE/offline verification parity.

## R6. LLM provider — Groq or any OpenAI-compatible endpoint; offline fallback
- **Decision**: `GROQ_API_KEY` (free tier, fast Llama 3.3 70B) preferred; else `OPENAI_COMPATIBLE_*` (OpenRouter, Together, Ollama, LM Studio); none → deterministic engine text.
- **Rationale**: no vendor lock-in, local model possible if no Internet, demo never fails because of an LLM.
- **Alternatives**: OpenAI only (cost + key dependency); always-local Ollama (too slow on 2 CPUs for 70B; small models hallucinate more).
- **Risk**: not yet tested with a real key (tasks T075).

## R7. Guided explanation — driver.js
- **Decision**: driver.js for the "Hướng dẫn" tour, "Câu chuyện" walkthrough and highlight in "Hỏi AI" mode.
- **Rationale**: MIT, tiny, no React coupling, supports skipping missing elements.
- **Alternatives**: react-joyride (heavier, React-version sensitive); intro.js (AGPL/commercial licence — rejected under constitution V); shepherd.js (fine, larger).

## R8. Computer vision — YOLOv8n + ByteTrack + supervision LineZone
- **Decision**: ultralytics YOLOv8n detection, ByteTrack tracking (supervision / trackers / ultralytics built-in), supervision `LineZone` for in/out counts → `counts.csv`.
- **Rationale**: nano model runs on CPU; LineZone gives auditable counts; output is a plain CSV ingested by the `cv` connector like any source.
- **Alternatives**: OpenCV background subtraction (no classes, fragile); larger YOLO (too slow on CPU); cloud vision APIs (cost, not open-source).
- **Licence note**: ultralytics is AGPL-3.0 — optional, not installed by default, used only as a separate script; recorded in `docs/licenses.md`.
- **Risk**: not run on a real video yet (T076).

## R9. Brief parsing — rule-based (no LLM)
- **Decision**: keyword/concept scoring over accent-insensitive text, resolved against real columns; 7 YAML scenario packs.
- **Rationale**: deterministic, offline, testable; good enough to map a short đề to target/segments/decision type.
- **Alternatives**: LLM extraction (non-deterministic, needs key) — can be layered later.

## R10. Data modelling — offer OBT, Star, Snowflake, Data Vault 2.0, Conformed
- **Decision**: generate all four for the primary table + conformed bus matrix across sources; recommend one with rationale.
- **Rationale**: contest DE workshop asks teams to justify a model; showing the trade-offs is itself a judging point; OBT feeds the insight engine.
- **Alternatives**: one model only (less explainable); dbt project (see R2).

## R11. Reports — python-pptx + Marp
- **Decision**: python-pptx 15-slide deck with text fitting + overflow checker; Marp markdown for pitch; Chromium headless for PDF.
- **Rationale**: editable PowerPoint for the team; Marp for fast iteration; both filled with engine numbers.
- **Alternatives**: Google Slides API (auth, online), reveal.js (not editable by non-coders).

## R12. Packaging — Makefile now, docker-compose + GitHub Actions (planned T070–T071)
- **Rationale**: Makefile is fastest on the contest laptop; docker/CI give reproducibility for judges/reviewers.

## R13. Reuse vs Build — capability map

Policy (constitution V + user direction): **prefer a free, open-source, ready-made integration over custom code**; adopt a new library
only when it replaces custom code cheaply, fits 2 CPU / 7 GB, and all tests pass. Status: ✅ integrated · 🟡 recommended (evaluate when
the need appears) · ⛔ evaluated and not adopted (reason).

| Capability | Tool | Licence | Status | Why / notes |
|---|---|---|---|---|
| File readers | **DuckDB** readers + pandas (`read_csv/read_excel`) | MIT / BSD-3 | ✅ | native CSV/Parquet/JSON; VN encoding/delimiter sniffing kept in `loader.py` |
| REST ingestion | **httpx + tenacity** | BSD-3 / Apache-2.0 | ✅ | paging, retry/backoff, Retry-After, rate limit, disk cache (`connectors.ingest_api`) |
| Declarative ingestion | dlt (dlthub) | Apache-2.0 | 🟡 | schema evolution + incremental cursors + DuckDB destination out of the box; adopt if contest needs many paginated APIs; current connector already covers WDI-style APIs in ~60 lines |
| DB ingestion | **SQLAlchemy** (JDBC equivalent) | MIT | ✅ | any dialect, chunked, SELECT-only |
| HTML scraping | **httpx + selectolax/lxml**, pandas `read_html` | MIT / BSD | ✅ | robots.txt, throttling, cache |
| JS-rendered pages | **Playwright** (optional) | Apache-2.0 | ✅ optional | only when `render_js: true` |
| Crawl at scale | Scrapy | BSD-3 | ⛔ | heavyweight for a few pages in 28 h; AutoThrottle/robots features already mirrored |
| Article text extraction | trafilatura | Apache-2.0 (≥1.8) | 🟡 | if a theme needs news full-text/sentiment; RSS headlines suffice now |
| Social / trends | **feedparser**, pytrends (optional) | BSD-2 / Apache-2.0 | ✅ | |
| Warehouse | **DuckDB** + Parquet | MIT | ✅ | R1 |
| SQL transforms / models | generated DuckDB SQL (`modeling.py`, `conformed.py`) saved to `out/<ds>/models/*.sql` | — | ✅ (build) | dynamic: models depend on detected column roles at runtime |
| Transform framework | dbt-duckdb / SQLMesh | Apache-2.0 / Apache-2.0 | ⛔ for now | static project files fight runtime schema detection; adds toolchain & compile time; reconsider post-contest by exporting generated SQL as dbt models |
| Data validation | custom checks in `quality.py` (missing/dup/outlier/score) | — | ✅ (build) | VN-specific parsing + scoring needed for the before/after story |
| Validation library | pandera | MIT | 🟡 | lightweight DataFrame schemas — good fit to assert silver contracts in tests; adopt with brief-defined expectations |
| Validation suites | Great Expectations / soda-core | Apache-2.0 / Apache-2.0 | ⛔ | heavy config, slow on 2 CPU; overkill for one-day datasets |
| Profiling | custom `profile.py` | — | ✅ | ydata-profiling (MIT) 🟡 as an optional one-click HTML report; heavy (minutes on 100k rows) |
| Statistics | **scipy, statsmodels, scikit-learn** | BSD-3 | ✅ | R2 |
| Stats convenience | pingouin | GPL-3.0 | ⛔ | copyleft; scipy/statsmodels already provide the tests |
| API | **FastAPI + pydantic** | MIT | ✅ | R3 |
| Dashboard shell | **shadcn/ui dashboard-01** + official components | MIT | ✅ | constitution IV |
| Charts | **Recharts via shadcn chart** | MIT | ✅ | Tremor (Apache-2.0) ⛔ — would restyle away from dashboard-01 |
| Command palette | cmdk via **shadcn Command** | MIT | 🟡 → T050 | official shadcn component |
| Sliders | **shadcn Slider** | MIT | 🟡 → T052 | |
| Vietnam map | d3-geo (ISC) + open GeoJSON; react-simple-maps (MIT) | ISC / MIT | 🟡 → T053 | react-simple-maps is unmaintained (React 19 peer deps); d3-geo projection inside an SVG is lighter |
| Diagrams | **mermaid** | MIT | ✅ | lineage + ERD |
| AI layer | **Vercel AI SDK v7** (+ @ai-sdk/groq, openai-compatible) | Apache-2.0 | ✅ | R5 |
| Guided tour | **driver.js** | MIT | ✅ | R7 |
| Deck / pitch | **python-pptx**, **Marp** markdown | MIT / MIT | ✅ | R11 |
| PDF | Chromium headless (Playwright) | Apache-2.0 | ✅ optional | |
| CV | **ultralytics YOLOv8n + supervision** (+ trackers) | AGPL-3.0 (optional) / MIT / Apache-2.0 | ✅ optional | R8 |
| Contract tests | **jsonschema** | MIT | ✅ | `tests/test_contracts.py` |
| Supply-chain checks | pip-audit, npm audit, gitleaks, Dependabot, CodeQL | Apache-2.0 / — / MIT / GitHub free for public repos | 🟡 → T067/T071 | CI workflow |
