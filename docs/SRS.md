# Software Requirements Specification — VietLeap Insight Kit

IEEE 830-style. Version 1.0 · 2026-11-15. Authoritative feature spec: [`specs/001-vietleap-insight-kit/spec.md`](../specs/001-vietleap-insight-kit/spec.md);
this SRS restates the requirements formally and traces each one to code and tests.

## 1. Introduction
### 1.1 Purpose
Specify the behaviour of the VietLeap Insight Kit so that any team member or coding agent can verify, operate and extend it.
### 1.2 Scope
The kit turns a dataset (or several sources) plus a contest problem statement into a documented data pipeline, statistically
tested insights, what-if simulations, policy recommendations, a Vietnamese dashboard with an AI analyst, and a pitch deck.
It runs locally on a modest laptop and works offline. It is not a multi-user BI platform (see §2.5).
### 1.3 Definitions
| Term | Meaning |
|---|---|
| Bronze / Silver / Gold | medallion layers: raw / cleaned & typed / analytical models |
| OBT | One Big Table — single wide analytical table |
| Star / Snowflake | Kimball dimensional model / normalised dimensions |
| Data Vault 2.0 | hubs (business keys), links (relationships), satellites (attributes + history) |
| Conformed dimension | one dimension shared by facts from several sources (bus matrix) |
| Đề / brief | contest problem statement; `brief.json` is its parsed form |
| Scenario pack | YAML describing a likely contest domain: KPIs, recipe, decision template, storyline |
| What-if | model-based change in target for a % change in one feature, with a bootstrap 90% interval |
| Hỏi AI | inspect mode: click any tagged UI element for an explanation |
| Câu chuyện | narrated walkthrough of the top-5 insights |
| `_row_hash` | per-row hash of source columns used for incremental loads |
### 1.4 References
Constitution `.specify/memory/constitution.md`; plan, data model, contracts in `specs/001-vietleap-insight-kit/`; `SECURITY.md`;
`docs/security/threat-model.md`; `docs/CONTEST_ANALYSIS.md`; `docs/PLAYBOOK.md`.

## 2. Overall description
### 2.1 Product perspective
Self-contained repository: Python engine (`engine/vlkit`), FastAPI service (`api/`), Next.js web app (`web/`). Storage is an embedded
DuckDB file plus a Parquet lake. Optional external services: public data APIs/web pages (ingestion) and an LLM endpoint.
### 2.2 Product functions
Ingest → store → clean & score quality → model (4 patterns + conformed) → lineage → insights/drivers/what-if/forecast/recommendations →
brief parsing → API → dashboard, AI analyst, explain mode, story → deck/pitch/summary exports → CV counting.
### 2.3 User classes
Analyst (codes), Presenter (non-coder), Judge (economist/data scientist, reads outputs), Coding agent (extends the kit).
### 2.4 Operating environment
Linux/macOS (Windows via WSL2), Python ≥ 3.11, Node ≥ 20, 2 CPU / 7 GB RAM, optional Chromium for PDF.
### 2.5 Constraints
Open-source only; shadcn dashboard-01 UI unmodified; no fabricated numbers; offline fallback; no concurrent build + tests;
contest timeline 20/11 09:00 → 21/11 13:00 (Asia/Saigon).
### 2.6 Assumptions & dependencies
Contest data is tabular (csv/xlsx/json) or obtainable from public APIs; Vietnamese place names; LLM key optional.

## 3. Specific requirements
### 3.1 Functional requirements (traceability in §4)
FR-001 … FR-028 as defined in `spec.md` §Requirements (ingestion kinds, provenance, medallion storage, load modes, VN cleaning and
quality scoring, four models, conformed dimensions, lineage, ranked tested insights, drivers & what-if, forecast, recommendations,
brief parsing, REST API, read-only SQL, web pages, explain/tour/story, AI analyst read-only tools, exports, CV counting, planned
wow features and contest-fit features).
### 3.2 Non-functional requirements
NFR-001 performance (100k rows ≤ 60 s DE on 2 CPU) · NFR-002 memory (≤ 4 GB RSS for ≤ 1M rows) · NFR-003 offline ·
NFR-004 contest timeline (first dashboard + deck ≤ 2 h after brief) · NFR-005 security (`SECURITY.md`) · NFR-006 usability
(Vietnamese UI, non-coder in 5 min) · NFR-007 maintainability (tests per feature, contract tests) · NFR-008 licensing.
### 3.3 External interface requirements
- **User interface**: Next.js dashboard on :3000, Vietnamese; pages listed in FR-016; shadcn components only.
- **Software interfaces**: REST/JSON on :8000 per `contracts/openapi.json`; output files per `contracts/*.schema.json`;
  LLM via Groq or any OpenAI-compatible chat-completions endpoint; DuckDB SQL (read-only for users/AI).
- **CLI**: `de.py file|run|tables|sql|brief`, `run.py`, `scenarios/cv_counting/count.py`, Makefile targets.
- **Communications**: HTTPS to public data sources (robots.txt respected), HTTP between web server and API on localhost.
### 3.4 Design constraints
DuckDB single-writer (API lock); Next 16 breaking changes (read `web/node_modules/next/dist/docs/`); Vercel AI SDK v7 APIs.

## 4. Traceability matrix (FR → code → tests)
| FR | Code | Tests |
|---|---|---|
| FR-001 ingestion kinds | `engine/vlkit/de/connectors.py`, `sources.py` | `tests/test_de_pipeline.py`, `tests/test_cv_counting.py` |
| FR-002 provenance | `de/sources.py make_provenance`, `connectors.ingest_sql` (masked uri) | `tests/test_de_pipeline.py`, `tests/test_deck.py` (provenance slide) |
| FR-003 medallion | `de/warehouse.py` | `tests/test_de_pipeline.py` |
| FR-004 load modes | `Warehouse.write_bronze`, `flow.run_flow(mode)`, `de.py --mode`, `IngestIn.mode` | `tests/test_incremental.py` |
| FR-005 cleaning & quality | `de/quality.py`, `vn.py`, `loader.py` | `tests/test_vn_numbers.py`, `test_vn_dates.py`, `test_provinces.py`, `test_district.py`, `test_de_pipeline.py` |
| FR-006 models | `de/modeling.py` | `tests/test_de_pipeline.py::test_flow_builds_all_models`, `test_district.py` |
| FR-007 conformed | `de/conformed.py` | `tests/test_conformed.py`, `tests/test_contracts.py` |
| FR-008 lineage | `de/lineage.py`, `flow.py` | `tests/test_contracts.py` (lineage schema), `test_conformed.py` |
| FR-009 insights | `insights.py`, `stats.py` | `tests/test_pipeline_smoke.py::test_pipeline_runs` (insights present with rank/type/score) |
| FR-010 drivers & what-if | `models.py`, `tools.py`, `api/routes/analysis.py` | indirect via `tests/test_pipeline_smoke.py` — **gap: no dedicated what-if/CI assertions** (add with T052) |
| FR-011 forecast | `stats.forecast` | indirect via smoke run — **gap: no dedicated forecast test** |
| FR-012 recommendations | `decision.py` | `tests/test_pipeline_smoke.py`, `test_deck.py` |
| FR-013 brief | `brief.py`, `scenarios/packs/`, `api/routes/brief.py` | `tests/test_brief.py`, `tests/test_contracts.py` |
| FR-014 REST API | `api/` | `tests/test_contracts.py::test_openapi_in_sync_with_app`, `test_de_pipeline.py` (API) |
| FR-015 read-only SQL | `Warehouse.sql`, `api/routes/pipeline.py /sql` | `tests/test_de_pipeline.py` (403 on DDL) |
| FR-016 web pages | `web/src/app/(dashboard)/*` | `npm run build`, `npm run lint` |
| FR-017 explain/tour/story | `insight-inspector.tsx`, `insight-sheet.tsx`, `lib/tour-steps.ts`, `lib/analyst/{explain,story}.ts`, `app/api/story` | `web/src/lib/analyst/explain.test.ts`, `story.test.ts`, `lib/tour-steps.test.ts`, `tests/test_contracts.py` (story schema) |
| FR-018 AI analyst | `web/src/lib/analyst/tools.ts`, `app/api/chat/route.ts`, `api/agent/` | `explain.test.ts` (offline); real-LLM test pending T075 |
| FR-019 exports | `report.py` | `tests/test_deck.py` |
| FR-020 CV | `scenarios/cv_counting/count.py` | `tests/test_cv_counting.py` (real YOLO run pending T076) |
| FR-021…FR-028 | planned | tasks T043–T055, T080–T083 |

| NFR | Verification |
|---|---|
| NFR-001/002 | practice runs `make demo` (`out/_logs/times.txt`), Hà Nội 81,681 rows on the dev machine |
| NFR-003 | offline unit tests (`explain.test.ts`, `story.test.ts`), API cache in `connectors._get_json` |
| NFR-005 | `docs/security/threat-model.md` control table; security tests (T061–T066) |
| NFR-007 | `tests/test_contracts.py`, CI (T071) |
| NFR-008 | `docs/licenses.md`, provenance `license_note` |
