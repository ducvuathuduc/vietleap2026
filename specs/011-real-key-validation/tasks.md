# Tasks: 011 Real-key LLM test & YOLO real run

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — LLM (target 17/11)
- [ ] T1101 AN: finalise `checklists/questions.yaml` (5 questions on `wdi_fiscal` + 1 injection probe + 1 offline check).
- [x] T1102 `0b9d869` Added smoke runner, test-first dry run and number verification fixture. See the [run checklist](checklists/llm-run.md).
- [ ] T1103 Owner puts `GROQ_API_KEY` in `web/.env.local`; `make api` + `make web`; run `python tools/llm_smoke.py`; fill `checklists/llm-run.md` (model, latency, tools, ungrounded numbers, pass/fail). Then invalid-key run (offline fallback) and rate-limit row → T1102.
- [ ] T1104 Python agent run (`LLM_BASE_URL/LLM_MODEL/LLM_API_KEY` → Groq OpenAI-compatible endpoint `https://api.groq.com/openai/v1` [verify]) — SSE events + verification row.
- [x] T1105 `0b9d869` Local gitleaks history scan found no leaks. Updated master plan and run checklist with offline results and pending real-key checks.
- [ ] T1106 Commit + push "test(llm): T1101–T1105 real-key run results"; open fix tasks for any failure (append below).

## Phase B — YOLO (optional, after 004/009)
- [ ] T1107 RQ: choose a ≤ 2-min CC BY/CC0 traffic clip; record URL/licence in `checklists/yolo-run.md` and `docs/licenses.md`.
- [ ] T1108 `pip install ultralytics supervision` in `.venv` (not in `requirements.txt`); run `count.py`; manual 30-s count; record fps/accuracy → T1107.
- [ ] T1109 Ingest `counts.csv` via a `cv` source in a temporary `sources.yaml`; dashboard check; notes in `scenarios/cv_counting/README.md`.
- [ ] T1110 Commit + push "test(cv): T1107–T1109 real YOLO run notes".

## Dependencies
T1101→T1102→T1103→T1105→T1106; T1104 ∥ T1103; T1107→T1108→T1109→T1110. Question 4 (SQL) is meaningful after 006 lands; until then it checks `runSql` table output only.
