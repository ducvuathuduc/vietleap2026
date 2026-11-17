# LLM real-key run — results (fill from tools/llm_smoke.py output; no keys, no raw transcripts)

**Date** 18/11/2026 (Asia/Saigon) · **Dataset** `wdi_asean` · **Mode** offline (`GET /api/chat`)

- Analyst Q1 used `getInsights` and returned a Vietnamese answer in 0.04 s, with 0 unmatched number tokens and 0 stream errors.
- Story returned 5 engine steps, the brief question and 3 limitations.
- The Python offline agent emitted two tool calls, two tool results, `verification` and `done`. The Vietnamese title regression has a test.
- The local route rate-limited at request 21 of 25 with the default 20/minute limit. Probe requests were validation-only and made no model calls.
- Real-key web and Python runs skipped because the processes had no model credentials. The provider-error and invalid-key checks remain open.

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

Local `gitleaks git --config .gitleaks.toml --redact --no-banner --exit-code 1 .` reported no leaks. Local and CI checks are recorded in `docs/MASTER_PLAN.md` §0.
