# Implementation Plan: Real-key LLM test & YOLO real run

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 3 h LLM (+ 2 h YOLO, optional) · **Owner role**: LEAD/DE (AN writes the questions)

## Technical context
- Web route handlers `web/src/app/api/chat/route.ts` (`GET` → `{mode, model}`, `POST` UI message stream), `web/src/app/api/story/route.ts`; model selection `web/src/lib/analyst/model.ts`; guards `web/src/lib/analyst/story.ts`, `explain.ts`; rate limit `web/src/lib/rate-limit.ts`.
- Python agent `api/agent/{runner,llm,verify}.py`, settings `api/settings.py`, routes `api/routes/agent.py`.
- CV `scenarios/cv_counting/count.py`, connector `cv` in `engine/vlkit/de/connectors.py`.

## Constitution check
| Principle | Compliance |
|---|---|
| I | the run measures ungrounded numbers; any > 0 becomes a fix task |
| V | LLM providers optional; ultralytics AGPL stays optional and documented |
| VI | keys only in `web/.env.local` / shell env; gitleaks after the session; injection probe; logs exclude keys |
| VII | offline fallback verified with an invalid key |
| VIII | smoke script has a `--dry-run` unit test; results committed only as summaries |

## Design
- `tools/llm_smoke.py`: reads `specs/011-real-key-validation/checklists/questions.yaml` (dataset, question, expected tools); POSTs to `http://127.0.0.1:3000/api/chat` with `{messages:[{role:"user", parts:[{type:"text", text}]}], datasetId}`; parses the SSE/UI stream (`data:` JSON lines) collecting `tool-input-available`, `tool-output-available`, text deltas; checks numbers in the final text appear in tool outputs (Python port of `numbersIn`/`numberCandidates` VI/EN formats with a parity test against fixtures from `story.test.ts`); times each call; writes JSON + markdown table.
- YOLO: documented manual procedure (checklist), no code changes unless a bug is found.

## Files to touch
`tools/llm_smoke.py` (new), `specs/011-real-key-validation/checklists/{llm-run.md,yolo-run.md,questions.yaml}`, `tests/test_tools_scripts.py` (dry-run), `docs/MASTER_PLAN.md`, `specs/001-vietleap-insight-kit/plan.md`, `scenarios/cv_counting/README.md`.

## Open-source reuse
httpx (BSD-3) for streaming; Groq API (free tier, proprietary service — optional); Ollama (MIT) as local OpenAI-compatible option; ultralytics (AGPL-3.0, optional) + supervision (MIT).

## Security considerations (OWASP LLM Top 10 2025)
- **LLM01 Prompt injection**: explicit probe row; expected refusal + no tool write possible.
- **LLM02 Sensitive info disclosure**: probe asks for system prompt / env; must not leak keys (tools cannot read env: `getenv` blocked in SQL; no env tool).
- **LLM06 Excessive agency**: confirm max steps 8 and read-only tools during the run.
- **LLM10 Unbounded consumption**: rate-limit row; ≤ 60 requests per session.
- **A02/A07 Secrets**: key typed into `.env.local` by the owner only; `gitleaks detect` after the session; never paste keys into chat transcripts saved to `out/`.
