# Implementation Plan: NL→SQL in AI Analyst

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 5 h · **Owner role**: DE (AN tests questions)

## Technical context
- Vercel AI SDK 7 (`ai`, `streamText`, `tool`, `stopWhen: isStepCount(8)` in `web/src/app/api/chat/route.ts`), zod 4, Groq / OpenAI-compatible (`web/src/lib/analyst/model.ts`).
- Tools `web/src/lib/analyst/tools.ts` (`runSql` → `POST /api/sql`, `compact()` in `backend.ts`), prompt `web/src/lib/analyst/prompt.ts`, number helpers `web/src/lib/analyst/story.ts` (`numbersIn`, `ungroundedNumbers`).
- UI `web/src/components/chat-messages.tsx` (tool Cards, `isSqlResult`, `ResultTable`), `web/src/components/result-table.tsx` (`ResultTable`, `CodeBlock`), `web/src/components/insight-chart.tsx` (`ChartSpec`: `bar|hbar|line|scatter`), `web/src/app/(dashboard)/sql/page.tsx` (no `?q=` support today).
- Server: `api/routes/pipeline.py` `POST /api/sql` (`SqlIn {query ≤ 10 000 chars, limit ≤ 5000}`), `engine/vlkit/de/warehouse.py` (`readonly()`, `sql()` denylist + timeout), `api/security.py` rate limit; `/api/datasets/{ds}/models` → `column_plan {time, province, cats, measures, ids}`.

## Constitution check
| Principle | Compliance |
|---|---|
| I Real numbers | every number in the answer must be in tool output or query literals; guard + warning badge; chart renders rows unchanged |
| II | answers from raw SQL are descriptive — the prompt requires "mô tả, chưa kiểm định" label unless numbers come from `getInsights` |
| III | prompt keeps "liên đới, không nhân quả" rule |
| IV | shadcn chart (Recharts) via existing `InsightChart`; Card/Collapsible as today |
| VI Security | server read-only guard authoritative; client pre-check UX only; offline templates quote identifiers from allowlist; rate limits unchanged |
| VII Offline | template NL→SQL path |
| VIII | test-first for pure modules |

## Design
1. `sql-chart.ts`: `chartFromResult(columns, rows): ChartSpec | null` (type sniffing: numeric if ≥ 90% of non-null cells are numbers; time if column name matches `/(year|nam|date|ngay|thang|quarter|ky)/` or values are 4-digit years).
2. `sql-guard.ts`: `isReadOnlySql(q)` (strip comments, single statement, leading `SELECT|WITH`), `quoteIdent(name)`.
3. `nl2sql-offline.ts`: `planOfflineSql(question, plan: ColumnPlan, table, columns)` → `{sql, intent, explanation} | {error}`; numeric literal N bounded 1–50.
4. `tools.ts runSql`: pre-check → backend → `{query, query_id, ...compact(result), chart}`.
5. `prompt.ts`: rules (cite "truy vấn #n", descriptive label, max 2 rewrites after 403/408).
6. `route.ts`: after the LLM stream finishes, run the number guard on the final text against all tool outputs + query literals; append warning part when needed; `offline()` branch uses `planOfflineSql` when the message looks like a data question.
7. `chat-messages.tsx`: runSql card open by default with CodeBlock + table + chart + link; badge "đã kiểm số" / "⚠ số chưa kiểm chứng".
8. `sql/page.tsx`: `?q=` pre-fill (Suspense boundary per Next 16 `useSearchParams` rules).

## Files to touch
`web/src/lib/analyst/sql-chart.ts` (new) + `.test.ts`, `web/src/lib/analyst/sql-guard.ts` (new) + `.test.ts`, `web/src/lib/analyst/nl2sql-offline.ts` (new) + `.test.ts`,
`web/src/lib/analyst/tools.ts`, `web/src/lib/analyst/prompt.ts`, `web/src/app/api/chat/route.ts`, `web/src/components/chat-messages.tsx`, `web/src/app/(dashboard)/sql/page.tsx`, `web/src/lib/api/types.ts`,
`tests/test_security.py` (regression cases for queries the LLM is likely to produce: `read_parquet`, `COPY … TO`, `PRAGMA`, `INSTALL httpfs`).

## Open-source reuse
Vercel AI SDK (Apache-2.0), Recharts via shadcn chart (MIT), zod (MIT). Considered and rejected: Vanna (MIT; Python, needs vector store/training — too heavy for 2-CPU and duplicates our tool loop), `node-sql-parser` (Apache-2.0; DuckDB dialect gaps — server guard already authoritative).

## Security considerations (OWASP Top 10 2021 / OWASP LLM Top 10 2025)
- **LLM01 Prompt injection / A03 Injection**: model-generated SQL treated as untrusted; DuckDB read-only connection with external access off; denylist; single statement; tests in `tests/test_security.py`.
- **LLM02 Sensitive information disclosure**: tool cannot read files/env (`getenv`, `read_*` blocked); warehouse holds only ingested public data; PII guidance in SECURITY.md.
- **LLM05 Improper output handling**: SQL text rendered in `<pre>`/CodeBlock as text; chart values numbers only; no HTML from model.
- **LLM06 Excessive agency**: tools are read-only; max 8 steps, ≤ 2 SQL rewrites.
- **LLM09 Misinformation**: number guard + citation requirement + "descriptive, untested" label.
- **LLM10 Unbounded consumption**: `limit ≤ 200` in tool, 20 s timeout, 20/min chat rate limit, 60/min SQL rate limit.
- **A04 Insecure design**: offline templates never interpolate raw user text into SQL — only allowlisted identifiers and bounded integers.
