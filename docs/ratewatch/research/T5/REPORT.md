T5 — status: DONE
Acceptance (all run fresh, exit codes verified):
- cd web; npm run lint → exit 0
- cd web; npm test → exit 0 (250 tests: guards, PII filter, provider switch, 9 tools on fixture, agent, env loader)
- npm run eval:ai live, gateway gpt-6-luna → 20/20 PASS, 0 unguarded numbers (results: eval-gateway.json)
- npm run eval:ai live, LLM_PROVIDER=groq → 18/20, guard clean 20/20 (results: eval-groq.json); fails are model variance (empty banks:[], one no-tool reply)
- Dev server :3108 → POST /api/ratewatch/chat streamed plan_deposit tool parts + grounded answer (4,75%, 23.750.000, sheet 2026-11-06); PII prompt got VI/EN notice, no echo; structured log line has no prompt text; server stopped (only my PID)
Deps installed (web/package.json): @ai-sdk/openai@^4.0.121, @langfuse/vercel-ai-sdk@^6.1.1, @langfuse/otel@^6.1.1, @langfuse/tracing@^6.1.1, @langfuse/client@^6.1.1, @opentelemetry/sdk-node@0.223.2 (pinned: peer @opentelemetry/api<1.10)
Files: agent/{env,guards,model,tools,agent}.ts + tests, agent/eval/{cases.json,run-eval.ts}, api/ratewatch/chat/route.ts, components/ratewatch-ai/assistant.tsx, src/instrumentation.ts, package.json + lock
Cost of live runs: gateway 111,861 in / 11,997 out tokens (gpt-6-luna price unknown — tokens only); Groq completed runs 132,002 in / 8,083 out ≈ $0.0246 (0.15/0.60 per MTok)
Notes: instrumentation at web/src/instrumentation.ts (Next 16 requires src/ when src/ exists; brief said web/). Gateway model id = plain "gpt-6-luna" (Responses API default). Langfuse dataset created via api.datasets.create + items deduped by input.id; dataset runs recorded: gateway e76c85d71e767cd1, groq 1df686facf73e5f9. Gateway calls carry langfuse-session-id header = chat sessionId.
Guard fixes found by the live eval (TDD, tests added): NBSP/narrow-NBSP thousand groups ("332 068 311"), EN unit words million/billion/thousand.
Risks: a weak model sending invalid tool args (e.g. compare_banks banks>3) throws mid-stream → route 500s without stack trace (gpt-6-luna did not do this); eval script records dataset runs via client API — OTel traces only in the Next runtime; Groq free tier needs EVAL_CASE_DELAY_MS=20000 (8000 TPM).
