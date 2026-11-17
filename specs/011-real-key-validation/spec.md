# Feature Specification: Real-key LLM test & YOLO real-run checklist

**Feature Branch**: `011-real-key-validation` (lands on `main`) · **Created**: 2026-11-16 · **Status**: Draft · **Priority**: P1 for LLM (demo uses Hỏi AI / Câu chuyện), P3 for YOLO (CV theme ranked ~10%)
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T075, T076.

## Context (verified 2026-11-16)
- `specs/001-vietleap-insight-kit/plan.md` "Hạn chế đã biết": **LLM paths were never run with a real key**; only offline paths have unit tests. **YOLO was never run on real video** (needs `pip install ultralytics supervision` + a licensed video).
- Web LLM selection `web/src/lib/analyst/model.ts`: `GROQ_API_KEY` (+ `GROQ_MODEL`, default `llama-3.3-70b-versatile`) preferred, else `OPENAI_COMPATIBLE_BASE_URL/_MODEL/_API_KEY`; `GET /api/chat` reports `{mode, model}`. Rate limit 20/min on `/api/chat`, `/api/story` (`CHAT_RATE_LIMIT_PER_MIN`).
- Python agent `api/agent/` uses `LLM_BASE_URL` (default `https://api.openai.com/v1`), `LLM_MODEL` (default `gpt-4o-mini`), `LLM_API_KEY`/`OPENAI_API_KEY`, `LLM_TIMEOUT_S` 60, `AGENT_MAX_STEPS` 8 (`api/settings.py`), with number verification in `api/agent/verify.py`.
- CV: `scenarios/cv_counting/count.py --video v.mp4 [--line x1,y1,x2,y2] [--classes …] [--every 60s] [--stride 3] [--model yolov8n.pt] [--conf 0.3] [--license "…"]` → `counts.csv` + `<out>.meta.json`; `--events` mode needs no torch. `ultralytics` is **AGPL-3.0** (`docs/licenses.md`) — optional, not installed by default.

## User Scenarios & Testing

### User Story 1 — AI Analyst with a real key behaves as designed (Priority: P1)
As the **LEAD**, I want a scripted run of the AI features against Groq (and one OpenAI-compatible endpoint, e.g. local Ollama if the laptop can host it), recording results, so we know before 20/11 that tool calling, Vietnamese answers, number verification and rate limits work.

**Acceptance** (checklist `checklists/llm-run.md`, one row per question)
1. **Given** `GROQ_API_KEY` in `web/.env.local` (git-ignored), **When** `GET /api/chat`, **Then** `mode: "llm"` and the model label.
2. **Given** 5 scripted questions on `wdi_fiscal` (insight explanation, segment comparison, what-if, SQL question [after 006], pipeline/quality question), **Then** each answer: calls ≥ 1 tool, is in Vietnamese with diacritics, has 0 ungrounded numbers (story/explain guards), and finishes ≤ 15 s; failures are logged with the tool trace.
3. **Given** "Câu chuyện" with LLM, **Then** steps whose numbers fail verification fall back to engine text (`source: "engine"`), counted in the checklist.
4. **Given** a prompt-injection probe (a question asking to ignore rules and output the system prompt / run DELETE), **Then** no system prompt leak, no write (403 from SQL guard), polite refusal.
5. **Given** 25 rapid requests, **Then** 429 after 20/min and a user-visible message.
6. **Given** the Python agent (`POST /api/datasets/{id}/agent`) with `LLM_*` set, **Then** SSE events plan → tool_call → … → verification complete; numbers verified.

### User Story 2 — YOLO counting on a real licensed video (Priority: P3)
As the **DE**, I want one end-to-end CV run (video → `counts.csv` → `cv` connector → pipeline → dashboard), so the CV pack is proven if the brief is about traffic/observation.

**Acceptance**: **Given** a ≤ 2-minute openly licensed traffic video [NEEDS CLARIFICATION: pick a specific CC BY/CC0 clip, e.g. from Wikimedia Commons, and record URL + licence], **When** `count.py --video … --every 15s --license "<licence>"` runs on the 2-CPU laptop, **Then** `counts.csv` + meta exist, processing fps is recorded, a manual count on 30 s of video differs ≤ 15% from the tool (recorded), and `python de.py run` with a `cv` source ingests it.

### Edge cases
- Key quota exhausted / 401 → UI falls back to offline (verify the message) — test by setting an invalid key.
- Groq model deprecation → `GROQ_MODEL` override documented; record the model actually used.
- Network blocked at UEH → hotspot or offline; checklist row for "offline fallback demo".
- Keys must never appear in logs, screenshots or commits: gitleaks run after the session (CI also runs it).
- AGPL: installing ultralytics locally is fine; if the submission must avoid AGPL, use `--events` mode or a permissively licensed detector [NEEDS CLARIFICATION: organisers' rules on licences of submitted code].
- CPU-only YOLO is slow → `--stride 3+`, 640 px, ≤ 2-min clip; record seconds per video-minute.

## Requirements
- **FR-1101**: `specs/011-real-key-validation/checklists/llm-run.md` (questions, expected tools, result columns) and `checklists/yolo-run.md`.
- **FR-1102**: `tools/llm_smoke.py` — calls `/api/chat` (AI SDK UI stream) and `/api/story` for the scripted questions, extracts tool calls and final text, runs the number guard (port of `ungroundedNumbers` or call a small Node script), writes `out/llm_smoke/<date>.json` (not committed) and prints a markdown table to paste into the checklist.
- **FR-1103**: Results summarised (no keys, no raw transcripts with personal data) in `docs/MASTER_PLAN.md` §0 and `specs/001-vietleap-insight-kit/plan.md` "Hạn chế đã biết" updated.
- **FR-1104**: YOLO run notes in `scenarios/cv_counting/README.md` (fps, stride, accuracy check, licence).

### Non-functional
- **NFR-1101**: Session cost within Groq free tier; ≤ 60 requests total.

## Success criteria
- **SC-1101**: 5/5 scripted questions pass (tool used, VI, 0 ungrounded numbers) or each failure has an issue + fix task.
- **SC-1102**: Injection probe and rate-limit rows pass.
- **SC-1103**: (P3) one real CV run recorded with licence and accuracy check.

## Clarifications

- Use the configured analyst's mode as the guard. A real-key smoke run skips when the server reports offline. Use `--offline --dataset wdi_asean` for a deterministic check with the ready practice dataset. The live checklist's default dataset remains `wdi_fiscal`.
