# VietLeap Insight Kit — Constitution

<!-- Spec Kit (github/spec-kit, MIT) layout. Every spec, plan and task in specs/ must pass the gates below. -->

**Version**: 1.0.0 · **Ratified**: 2026-11-15 · **Last amended**: 2026-11-15

## Core Principles

### I. Real numbers only (NON-NEGOTIABLE)
Every number shown in the UI, the deck, the pitch, the executive summary or an AI answer MUST come from the engine
(pandas/scipy/statsmodels/scikit-learn) or a DuckDB query over the warehouse. No placeholder, mock, sample or
"illustrative" figure may ship. LLM output is verified against tool/engine output: a sentence containing a number not
found in the source is replaced by the engine's own sentence (`web/src/lib/analyst/story.ts`, `api/agent/verify.py`).
Missing data is shown as missing ("—", empty state), never filled in.

### II. Statistically tested insights
An insight is published only with its test name, p-value (and correction where several tests run: Bonferroni),
effect size and n. Weak or non-significant results are labelled as such, not dropped silently and not overstated.
Forecasts carry an interval and a holdout error; what-if results carry a bootstrap 90% interval.

### III. No causal claims from observational data
Drivers, correlations and what-if simulations are conditional associations. Wording MUST be "is associated with",
never "causes/drives/leads to", unless the design is experimental or quasi-experimental and stated. Every deck and AI
answer carries the most important caveat.

### IV. Reuse open-source UI as-is
The web UI is the shadcn/ui `dashboard-01` block (style base-nova) plus official shadcn components/blocks added with
`npx shadcn@latest add`. No custom theme, colours, fonts or spacing; no hand-rolled replacement for a component shadcn
provides. Charts use shadcn chart (Recharts). Vietnamese text with diacritics; times in Asia/Saigon.

### V. Open-source only
Runtime, libraries, data and assets MUST be open-source / openly licensed, with the licence recorded
(`requirements.txt`, `web/package.json`, `docs/licenses.md`, provenance `license_note`). LLM providers are optional,
pluggable via OpenAI-compatible endpoints (local Ollama works), never required.

### VI. Security by default
Read-only SQL for every user/AI surface; inputs validated at the API edge (pydantic/zod); uploads size- and
type-limited; connectors refuse private-network targets from the API (SSRF) and local paths outside allowed
directories; secrets only via environment / `.env*` files that are never committed; AI tools are read-only and tool
output is treated as data, not instructions. See `SECURITY.md`, `docs/security/threat-model.md`.

### VII. Offline-first fallback
Every AI feature has a deterministic offline path (engine text) so the demo works without a key or network.
Online connectors cache responses (`data/cache/`) so re-runs during the contest cost no quota.

### VIII. Tests before push, push after every feature
A feature is done only when `pytest -q tests`, `cd web && npm test && npm run lint && npm run build` pass (run
sequentially — 2-CPU machine). Each feature is its own commit and is pushed to `origin main` immediately; finished
work is never left unpushed. Specs/docs (`specs/001-*/tasks.md`, `docs/MASTER_PLAN.md` §0) are updated in the same push.

## Constraints

- Target machine: 2 CPU, 7 GB RAM, no GPU (DuckDB `threads=2`; never build web concurrently with pytest/engine).
- Contest timeline: brief published 20/11/2026 09:00, submission 21/11/2026 13:00, pitch 13:15 (Asia/Saigon).
- Never commit `node_modules/ .venv/ .tools/ out/ data/raw/ data/warehouse.duckdb data/lake/ data/cache/ .env*`, files > 20 MB.
- Scraping respects robots.txt, uses delays, never bypasses captchas or logins.

## Governance

This constitution supersedes conflicting guidance in other docs. Amendments: edit this file, bump the version
(MAJOR = principle removed/redefined, MINOR = principle added, PATCH = wording), note it in the commit message, and
re-run the Constitution Check in `specs/*/plan.md`. Reviewers (human or agent) reject changes that violate a
NON-NEGOTIABLE principle regardless of deadline pressure.
