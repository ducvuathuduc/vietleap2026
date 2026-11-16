# LLM real-key run — results (fill from tools/llm_smoke.py output; no keys, no raw transcripts)

**Date**: ____ (Asia/Saigon) · **Commit**: ____ · **Provider/model** (from `GET /api/chat`): ____ · **Dataset**: wdi_fiscal

| Id | Tools called | Expected tool hit? | Answer in VI with diacritics? | Ungrounded numbers | Latency (s) | Pass? | Notes |
|---|---|---|---|---|---|---|---|
| q1-insight | | | | | | | |
| q2-segment | | | | | | | |
| q3-whatif | | | | | | | |
| q4-sql | | | | | | | |
| q5-pipeline | | | | | | | |
| p1-injection | | n/a | | n/a | | | system prompt leaked? write executed? |
| p2-offline (invalid key) | | n/a | | | | | |
| rate limit (25 req / 60 s) | n/a | n/a | n/a | n/a | | | first 429 at request # |
| story (Câu chuyện) | | n/a | | steps fallen back to engine: | | | |
| python agent SSE | | | | | | | events seen |

After the run: `gitleaks detect --no-banner` → result: ____ . Summary copied to `docs/MASTER_PLAN.md` §0: ☐
