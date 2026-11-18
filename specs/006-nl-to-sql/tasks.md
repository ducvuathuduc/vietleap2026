# Tasks: 006 NL→SQL in AI Analyst

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Pure modules (test-first)
- [x] T601 [P] `web/src/lib/analyst/sql-chart.test.ts` (≥ 6 shape cases) → `sql-chart.ts`.
- [x] T602 [P] `web/src/lib/analyst/sql-guard.test.ts` (≥ 8 cases: comments, trailing `;`, `WITH`, `DELETE`, two statements, `read_csv`, empty) → `sql-guard.ts`.
- [x] T603 [P] `web/src/lib/analyst/nl2sql-offline.test.ts` (topN, byTime, compare, diacritics, no-match, N clamp) → `nl2sql-offline.ts`.
- [x] T604 [P] `tests/test_security.py` regression cases for LLM-likely escapes (`read_parquet`, `COPY … TO`, `PRAGMA`, `INSTALL httpfs`, `LOAD`), expect 403 (`py_compile` ok; `pytest` pending Python env).
- [ ] T605 Commit + push "feat(analyst): T601–T604 SQL chart/guard/offline templates (pure, tested)".

## Phase B — Wiring
- [x] T606 `web/src/lib/analyst/tools.ts` runSql output `{query, query_id, columns, rows, row_count, chart}`; `types.ts` → T601, T602.
- [x] T607 `web/src/lib/analyst/prompt.ts` citation + descriptive-label + retry rules; `web/src/app/api/chat/route.ts` post-answer number guard (`sqlTruthNumbers`/`ungroundedNumbers`) and offline template branch → T603, T606.
- [x] T608 `web/src/components/chat-messages.tsx` runSql card (CodeBlock + ResultTable + InsightChart + "Mở trong SQL Explorer" + guard badge) → T606.
- [x] T609 [P] `web/src/app/(dashboard)/sql/page.tsx` `?q=` pre-fill (Suspense-wrapped, no auto-run).
- [x] T610 Headless Chromium offline test: `"top 5 price_per_m2 theo tinh"` on `synthetic_messy_bds` → expanded SQL card + chart + `"đã kiểm số"` + `/sql?q=` prefill; 0 console/CSP errors.
- [ ] T611 Commit + push "feat(analyst): T606–T610 NL→SQL with inline chart and cited query"; tick; `specs/README.md`.

## Phase C — Real-key validation (with feature 011)
- [ ] T612 Run the 5 scripted questions in `specs/011-real-key-validation/checklists/llm-run.md` against Groq; record latency, cited queries, ungrounded numbers (target 0) → T611.

## Dependencies
Phase A tasks parallel → Phase B (T606→T607/T608) → T610 → T611 → T612.
