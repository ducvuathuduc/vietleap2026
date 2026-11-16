# Tasks: 006 NL→SQL in AI Analyst

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Pure modules (test-first)
- [ ] T601 [P] `web/src/lib/analyst/sql-chart.test.ts` (≥ 6 shape cases) → `sql-chart.ts`.
- [ ] T602 [P] `web/src/lib/analyst/sql-guard.test.ts` (≥ 8 cases: comments, trailing `;`, `WITH`, `DELETE`, two statements, `read_csv`, empty) → `sql-guard.ts`.
- [ ] T603 [P] `web/src/lib/analyst/nl2sql-offline.test.ts` (topN, byTime, compare, diacritics, no-match, N clamp) → `nl2sql-offline.ts`.
- [ ] T604 [P] `tests/test_security.py` regression cases for LLM-likely escapes (`read_parquet`, `COPY … TO`, `PRAGMA`, `INSTALL httpfs`, `LOAD`), expect 403.
- [ ] T605 Commit + push "feat(analyst): T601–T604 SQL chart/guard/offline templates (pure, tested)".

## Phase B — Wiring
- [ ] T606 `web/src/lib/analyst/tools.ts` runSql output `{query, query_id, columns, rows, row_count, chart}`; `types.ts` → T601, T602.
- [ ] T607 `web/src/lib/analyst/prompt.ts` citation + descriptive-label + retry rules; `web/src/app/api/chat/route.ts` post-answer number guard (reuse `ungroundedNumbers`) and offline template branch → T603, T606.
- [ ] T608 `web/src/components/chat-messages.tsx` runSql card (CodeBlock + ResultTable + InsightChart + "Mở trong SQL Explorer" + guard badge) → T606.
- [ ] T609 [P] `web/src/app/(dashboard)/sql/page.tsx` `?q=` pre-fill.
- [ ] T610 Headless Chromium offline test: "top 5 … theo …" on a practice dataset → SQL card + chart; 0 console/CSP errors; screenshot `docs/screenshots/analyst-sql.png`.
- [ ] T611 Commit + push "feat(analyst): T606–T610 NL→SQL with inline chart and cited query"; tick; `specs/README.md`.

## Phase C — Real-key validation (with feature 011)
- [ ] T612 Run the 5 scripted questions in `specs/011-real-key-validation/checklists/llm-run.md` against Groq; record latency, cited queries, ungrounded numbers (target 0) → T611.

## Dependencies
Phase A tasks parallel → Phase B (T606→T607/T608) → T610 → T611 → T612.
