# Tasks: VietLeap Insight Kit

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/](contracts/) · **Contest analysis**: [docs/CONTEST_ANALYSIS.md](../../docs/CONTEST_ANALYSIS.md)
**Legend**: `[x]` done & pushed (commit) · `[ ]` pending · `[P]` can run in parallel with other `[P]` tasks of the same phase (different files) ·
`[USn]` user story · `→ Tn` depends on.
**Rule (constitution VIII)**: one task (or tightly coupled group) = one commit; run `pytest -q tests`, then `cd web && npm test && npm run lint && npm run build`
(sequentially), commit as `thanhdicode`, push to `origin main`, tick the box here with the commit hash in the same push.

**Priorities from contest analysis (2026-11-15)**: judges are mostly economists (UEH School of Public Finance, World Bank fiscal, LSE,
FiinGroup data partner); teammates are business/social-science non-coders; likely themes: provincial public finance/fiscal policy ~30%,
listed firms/capital markets ~20%, WDI Vietnam vs ASEAN ~15%, energy/EV/data economy ~15%, social ~10%, traffic CV ~10%.
Build window ≈ 27.5 h (20/11 09:30 → 21/11 13:00). ⇒ policy-question-first storytelling, bilingual deck, fiscal/firm packs first; CV last.

## Phase 1 — Setup (done)
- [x] T001 Repo import: engine, api, web scaffold (`1d7c925`)
- [x] T002 MASTER_PLAN + AGENTS.md for coding agents (`cedbfbb`)
- [x] T003 Makefile (setup/api/web/demo/test), `tools/run_practice.sh` (`a4483a2`)

## Phase 2 — Foundational DE layer [US1] (done)
- [x] T010 Connectors file/api/sql/scrape/social/cv + provenance (`2e9674c`)
- [x] T011 DuckDB medallion warehouse + Parquet lake + meta tables (`2e9674c`)
- [x] T012 Quality → silver (VN parsing, scores before/after, cleaning log) (`2e9674c`)
- [x] T013 OBT / Star / Snowflake / Data Vault + ERD + SQL (`2e9674c`)
- [x] T014 Lineage graph JSON + Mermaid, `flow.run_flow`, `de.py` CLI (`2e9674c`)
- [x] T015 Fix: don't re-normalise province columns from gold (`757df0c`)
- [x] T016 Conformed dimensions across sources + join coverage (`726fe1c`) → T013
- [x] T017 District-level dim_geo (`74d2d98`) → T016

## Phase 3 — Insight, brief, AI, web, deck [US2–US6] (done)
- [x] T020 Insight engine: stat tests, drivers, what-if, forecast, segments, recommendations (`1d7c925`)
- [x] T021 Web pages (shadcn dashboard-01): Tổng quan, Nguồn, Pipeline, Chất lượng, Mô hình, SQL, Hồ sơ, Insight, Drivers & What-if, Phân khúc, Quyết định (`0e8be9b`)
- [x] T022 AI Analyst `/api/chat` (AI SDK v7, 10 read-only tools, Groq/OpenAI-compatible, offline) (`953057a`)
- [x] T023 Explain-anything: driver.js tour + "Hỏi AI" inspect mode (`b225042`)
- [x] T024 Đề → brief.json, 7 scenario packs, 11 sample briefs, `/api/brief`, page Đề bài (`2609808`)
- [x] T025 "Câu chuyện" auto-insight story with number verification (`253f761`)
- [x] T026 Deck 15 slides + text fitting + overflow check + `pitch.md` (`d3208b3`)
- [x] T027 [US8] CV counting `count.py` (YOLOv8n + ByteTrack + LineZone) (`8024f92`)
- [x] T028 Docs: README quickstart, PLAYBOOK, CONTEXT (`a712972`)

## Phase 4 — DE hardening & surfacing [US1, US4]
- [x] T040 Incremental load by `_row_hash`: `--mode replace|append|incremental`, inserted/skipped in meta.runs, API `IngestIn.mode`, schema change → rebuild, tests (`1b3a40d`)
- [x] T041 Spec Kit docs: constitution, spec/plan/research/data-model/contracts/quickstart/tasks/checklist, SRS, contract tests (`aef4d05`)
- [x] T042 Copy `docs/CONTEST_ANALYSIS.md` from contest research (`b6e6b6b`)
- [ ] T043 API `GET /api/datasets/{ds}/conformed` + `keys` in models response; regenerate `contracts/openapi.json` → T016
- [ ] T044 Pipeline page: join-coverage Card + Table + Progress (shadcn), `data-insight-target` tags → T043
- [ ] T045 Model page: "Conformed" tab with ERD + SQL + coverage, Hỏi AI offline explanation for conformed/join kinds → T043

## Phase 5 — Security [NFR-005] (see docs/security/threat-model.md)
- [x] T060 SECURITY.md + STRIDE threat model with verified control status (`2444157`)
- [x] T061 SQL guard (+ prompt-injection rule in both system prompts) (`1147a5d`): block file-path string table refs (`FROM 'x.csv'`), external access off on read-only connection, statement timeout → T060
- [x] T062 SSRF guard (this commit) for api/scrape/social sources submitted via API (block private/loopback/link-local/metadata IPs, http(s) only, re-check redirects) → T060
- [x] T063 Path guard + cv option allowlist + zip-bomb limit (this commit): API-submitted `file`/`cv`/`sql` sources limited to allowed dirs (data/, scenarios/, uploads) → T060
- [ ] T064 Upload limits streamed (no full read before size check), CORS methods/headers restricted → T060
- [ ] T065 Security headers: FastAPI middleware + Next `headers()` (CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy) → T060
- [ ] T066 Simple in-memory rate limit on `/api/sql`, `/api/ingest`, `POST /api/datasets`, agent, `/api/chat` → T060
- [ ] T067 `.gitignore` all `.env*` (except `.env.example`); gitleaks + pip-audit + npm audit in CI → T071

## Phase 6 — Contest-fit features (HIGH priority, from contest analysis)
- [ ] T080 [P] Policy-question-first storytelling: deck + story open with the policy question (from brief.json), then evidence → decision → KPI
- [ ] T081 [P] Bilingual deck/pitch: `--lang vi|en` (deck currently English text from `*_en` fields; pitch.md VI) + web toggle on Export
- [ ] T082 [P] Verify/extend packs `public_finance_province` and `listed_firms_market` with real-data dry runs (`data/practice/wdi_fiscal`, `firms_2021`); add `energy_ev_data_economy` pack + sample brief
- [ ] T083 WDI Vietnam vs ASEAN comparison recipe (World Bank API sources.yaml with ASEAN ISO3 list, conformed on country+year)

## Phase 7 — Wow features [US7] (each its own commit)
- [ ] T050 Command palette Ctrl+K (shadcn Command/cmdk): pages, "Câu chuyện", ask AI, what-if
- [ ] T051 NL→SQL in AI Analyst: draft DuckDB SQL, validate read-only, run, inline table + auto chart (shadcn chart), answer cites the query → T061
- [ ] T052 What-if sliders page (shadcn Slider): real-time predicted KPI + CI90 from engine drivers model
- [ ] T053 Vietnam 34-province choropleth (open GeoJSON, licence recorded in docs/licenses.md), click → Hỏi AI
- [ ] T054 One-click "Xuất báo cáo" (deck + pitch.md + PDF)
- [ ] T055 [P] Screenshots `docs/screenshots/` for README/deck

## Phase 8 — Ops & validation
- [ ] T070 Dockerfiles (api, web) + docker-compose
- [ ] T071 GitHub Actions CI: pytest + web lint/test/build (+ T067 audits)
- [ ] T075 Test AI Analyst / Câu chuyện with a real LLM key (Groq) — record results in MASTER_PLAN
- [ ] T076 (LOW) Run YOLO counting on a real licensed video (needs `pip install ultralytics supervision`)
- [ ] T077 Update MASTER_PLAN §0, README, SPEC index, this file after each phase

## Dependencies & order
Phase 4 (T042–T045) → Phase 5 security quick fixes (T060–T066) → Phase 6 contest-fit (T080–T083) → Phase 7 wow (T050–T055) → Phase 8.
T051 needs T061 (hardened SQL). T071 needs T070 optional. `[P]` tasks touch different files and can be split between agents.
