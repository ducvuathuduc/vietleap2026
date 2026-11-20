# V-TECH Technical research for the build: AI SDK v7 + Bedrock + Langfuse, ECS Express Mode, chart patterns
Repo (read only): C:\Users\dieut\Desktop\Money\vietleap
## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (rubric, judges, owner rules). Area is fixed: banking/finance in Vietnam,
  household deposits. Prior findings (read only what you need): ..\B-RATES\RATES.md (21-bank panel, 268/289 rows from one aggregator),
  ..\B-POLICY\POLICY.md (deposit-insurance cap 350 million from Thông tư 05/2026 in force 13/7/2026; ceiling 4.75% for 1 to <6 months
  under QĐ 2411/QĐ-NHNN), ..\B-HOUSE\HOUSE.md (DIV page still shows 125 million; SBV stats pages; household deposits 11,434,266 tỷ 8/2026),
  ..\B-BANKDATA\BANKDATA.md (FiinQuant 28 banks, ratios 614/644 quarters).
- Working product idea (test it, do not defend it): a deposit decision tool for households that reads every bank's posted curve daily,
  shows where the 4.75% short-term ceiling bends the curve, derives the market-implied future rate from the curve (forward rates) to
  answer "lock 12 months now or 6 months twice", checks the insured cap per bank, and shows each bank's risk profile.
## Do (write TECH.md; official docs only, URL for every claim)
1. Vercel AI SDK v7 (installed: ai 7.0.173, see web/node_modules/ai/docs): tool calling with streamText, multi-step agents, structured
   output, telemetry (experimental_telemetry / OpenTelemetry). Exact current API names from the installed docs.
2. Langfuse with AI SDK v7 in Next.js 16 on Node: package names, OTel setup (instrumentation.ts), trace/observation model, tagging
   sources/citations, sessions, public trace sharing links, PII masking, Langfuse Cloud regions and free-tier limits; self-host cost.
3. Amazon Bedrock from the AI SDK (@ai-sdk/amazon-bedrock): auth with an IAM role (ECS task role), which Claude / Nova models and
   inference profiles are available in ap-southeast-1, tool-use support, pricing per 1M tokens.
4. ECS Express Mode: what it creates, how to deploy a container from ECR, HTTPS URL, health checks, env vars/secrets, task role,
   scheduled tasks for a daily pipeline (EventBridge Scheduler), rough daily cost for 0.5 vCPU / 1 GB.
5. Chart patterns from well-known finance dashboards (US Treasury yield curve, CME FedWatch, Bloomberg WIRP, FRED, FT, OWID, IMF
   DataMapper): which visual forms fit "deposit yield curve by bank", "implied rate path", "ceiling kink", "insured vs uninsured",
   "rate vs risk"; and which shadcn/Recharts components in web/ can render them (check web/package.json and web/src/components).
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. Negative claims need the
  exact URL and response. Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets.
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.
- Timebox: 30 minutes. Write the named findings file and REPORT.md (max 15 lines) in THIS folder.