# V-TECH — Technical research for the build: AI SDK v7 + Bedrock + Langfuse, ECS Express Mode, chart patterns

Written: 20/11/2026, all web fetches 19:32–19:52 Asia/Saigon (UTC+7). Method: official docs only, fetched live via web tools; AI SDK v7 claims read from the installed package docs (`web/node_modules/ai/docs`, ai 7.0.173 — version verified from `ai/package.json`). Every claim marked [verified] (fetched this session) or [inferred] (reasoned, not directly fetched). Negative claims state the exact URL and what came back.

---

## 1. Vercel AI SDK v7 (installed: ai 7.0.173)

Source: installed official docs `web/node_modules/ai/docs/` (shipped by Vercel in the npm package; public mirror ai-sdk.dev). [verified]

- **Tool calling with `streamText`**: `tools` parameter of `generateText`/`streamText` is an object keyed by tool name, values built with the `tool()` helper. Tools with an `execute` function run automatically as the model calls them; manual approval via `toolApproval` on `generateText`/`streamText`/`ToolLoopAgent` (manual approval completes the call and returns `tool-approval-request` parts — two-call flow). [verified — `03-ai-sdk-core/15-tools-and-tool-calling.mdx` lines 21, 161, 246; public: https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling]
- **Multi-step**: `stopWhen: isStepCount(5)` — when set and the model generates a tool call, the SDK re-generates with the tool result until no further tool calls or the condition is met. Stop conditions are only evaluated when the last step contains tool calls. (`maxSteps` is gone in v7; the doc title itself is "Multi-Step Calls (using stopWhen)".) [verified — same file lines 42, 399–412, 453]
- **Agents**: `ToolLoopAgent` class from `'ai'` is the recommended agent primitive: `new ToolLoopAgent({ model, tools, stopWhen, ... })`; it handles the loop, context management and stopping conditions. Use core `generateText`/`streamText` only when you need explicit per-step control. [verified — `03-agents/01-overview.mdx` lines 33–92; public: https://ai-sdk.dev/docs/agents/overview]
- **Structured output**: v7 uses `generateText`/`streamText` with `output: Output.object({ schema })` (zod schema validates the result); result destructured as `{ output }`. Also `Output.text()`, `Output.array()`, `Output.choice()`, `Output.json()`. **`generateObject`/`streamObject` no longer appear in the v7 structured-data doc** — grep for them in `03-ai-sdk-core/10-generating-structured-data.mdx` returns nothing. [verified — same file lines 30–50, 41–279; public: https://ai-sdk.dev/docs/ai-sdk-core/generating-structured-data]
- **Telemetry**: v7 moved to a registered OpenTelemetry integration: install `@ai-sdk/otel`, then once at startup:
  ```ts
  import { registerTelemetry } from 'ai';
  import { OpenTelemetry } from '@ai-sdk/otel';
  registerTelemetry(new OpenTelemetry());
  ```
  `experimental_telemetry` does **not** appear in the v7 telemetry doc (grep returns nothing); Langfuse confirms `experimental_telemetry: { isEnabled: true }` is the AI SDK ≤6 legacy path. [verified — `03-ai-sdk-core/60-telemetry.mdx` lines 8–29; https://ai-sdk.dev/docs/ai-sdk-core/telemetry; legacy note: https://www.npmjs.com/package/@langfuse/vercel-ai-sdk, accessed 19:32]
- Repo already has `ai@7.0.173`, `@ai-sdk/react@4.0.177`, `@ai-sdk/groq@4.0.84`, `@ai-sdk/openai-compatible@3.0.92` (web/package.json). Bedrock/Langfuse packages are **not** installed yet. [verified — repo]

## 2. Langfuse with AI SDK v7 in Next.js 16 on Node

Sources: https://langfuse.com/integrations/frameworks/vercel-ai-sdk (accessed 19:32–19:33), https://www.npmjs.com/package/@langfuse/vercel-ai-sdk (19:32), https://langfuse.com/changelog/2026-06-26-vercel-ai-sdk-7 (19:32), https://ai-sdk.dev/providers/observability/langfuse (19:32).

- **Packages**: `@langfuse/vercel-ai-sdk` (targets AI SDK 7, **requires Node.js ≥ 22**; stable as of 5.9.0 per changelog), `@langfuse/otel` (exports `LangfuseSpanProcessor`), `@langfuse/client` (prompt management, datasets/evals/scores), `@langfuse/tracing`, plus `@opentelemetry/sdk-node`. [verified]
- **OTel setup in Next.js** — create `instrumentation.ts` in project root (runs at app startup):
  ```ts
  import { registerTelemetry } from 'ai';
  import { LangfuseSpanProcessor } from '@langfuse/otel';
  import { LangfuseVercelAiSdkIntegration } from '@langfuse/vercel-ai-sdk';
  import { NodeSDK } from '@opentelemetry/sdk-node';
  const sdk = new NodeSDK({ spanProcessors: [new LangfuseSpanProcessor()] });
  sdk.start();
  registerTelemetry(new LangfuseVercelAiSdkIntegration());
  ```
  Env: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` (canonical spelling). [verified — integration page + npm README]
- **Trace/observation model + tagging + sessions**: wrap any AI call with
  `propagateAttributes({ traceName, userId, sessionId, tags, metadata, version }, () => streamText(...))` — `sessionId` groups related traces into a session; `tags` is a string array (e.g. `["production","chat"]`); spans can be updated (`span.update({ output })`). [verified — integration page, "propagateAttributes" examples]
- **Citations/sources**: no first-class "citation" object found on the integration page; the pattern shown is `metadata` (free-form object, e.g. `{ source: "api" }`) and `tags`. [verified for what the page shows; a dedicated citations API was **not found** on this page — negative claim]
- **PII masking**: masking functions redact sensitive information from trace/observation inputs, outputs and metadata **before data leaves the application**, and transform OpenTelemetry span attributes before export. Python SDK hooks: `mask_otel_spans` (recommended, runs at export stage) and legacy `mask`. [verified — https://langfuse.com/docs/observability/features/masking, accessed 19:44; the JS/TS-specific hook section was not in the fetched text — JS specifics unverified]
- **Public trace sharing**: each trace has a unique URL; trace header "⋯" → "Make Public" → toast "Trace shared publicly" + copied link. [verified — https://langfuse.com/docs/observability/features/url, accessed 19:38]
- **Cloud regions**: EU, US, Japan, and a separate HIPAA-compliant US region; select via `LANGFUSE_BASE_URL` / `baseUrl` (EU: `https://cloud.langfuse.com`, US: `https://us.cloud.langfuse.com`). [verified — https://langfuse.com/faq/all/where-is-my-project + https://langfuse.com/security/data-regions, accessed 19:46]
- **Free tier**: Hobby plan free, no credit card: 50k units/month, 30 days data access, 2 users. Core $29/mo: 100k units included, $8 per extra 100k, 90 days retention. [verified — https://langfuse.com/pricing, accessed 19:33]
- **Self-host**: open source, Docker Compose (local/testing) or Kubernetes/Helm (production); "some add-on features require a license key"; runs the same infrastructure as Langfuse Cloud. Software cost 0; infra cost = your VM/cluster [inferred: a 2–4 GB VM roughly $5–15/month on typical clouds — not fetched]. [verified — https://langfuse.com/self-hosting, accessed 19:35]

## 3. Amazon Bedrock from the AI SDK

Source: https://ai-sdk.dev/providers/ai-sdk-providers/amazon-bedrock (accessed 19:33).

- **Provider**: `@ai-sdk/amazon-bedrock`, `createAmazonBedrock({ region, ... })`; default instance `amazonBedrock`; model call `bedrock('anthropic.claude-...-v1:0')`. Uses the Bedrock Converse API. [verified]
- **Auth with an IAM role (ECS task role)**: the provider supports SigV4 via the AWS SDK credentials chain —
  ```ts
  import { createAmazonBedrock } from '@ai-sdk/amazon-bedrock';
  import { fromNodeProviderChain } from '@aws-sdk/credential-providers';
  const amazonBedrock = createAmazonBedrock({ region: 'ap-southeast-1', credentialProvider: fromNodeProviderChain() });
  ```
  `fromNodeProviderChain()` resolves credentials in the standard AWS order, which on ECS includes the **task role**. Alternative: Bedrock API key via `AWS_BEARER_TOKEN_BEDROCK` (takes precedence over SigV4 when set). [verified — provider page, "Using IAM Access Key"/credentialProvider sections; that the chain includes the ECS task role is standard AWS behavior, marked here as the documented purpose of `fromNodeProviderChain`]
- **Inference profiles**: direct provider supports account-specific **application inference profiles**; for Anthropic application-inference-profile ARNs prefer `bedrockAnthropic` from `@ai-sdk/amazon-bedrock/anthropic` (native InvokeModel, accepts profile ARNs). Cross-region CRIS prefixes (`us.`, `eu.`, `apac.`) route within a geography; `apac` routes to any supported Asia Pacific region. [verified — provider page + https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html, accessed 19:49]
- **Tool use**: provider supports tool calling; structured-output modes `providerOptions.bedrock.structuredOutput`: `"jsonTool"` | `"auto"` (default) — in `"auto"`, supported **Claude 5 models use native structured output** for compatible schemas. [verified — provider page]
- **Models in ap-southeast-1 (Singapore)**: AWS official blog: "Claude Opus 5 and Claude Sonnet 5 with in-region inference in Seoul, and **Claude Sonnet 5 in Singapore**... there is no routing layer... requests stay within [the region]" [verified — https://aws.amazon.com/blogs/machine-learning/introducing-anthropic-models-on-amazon-bedrock-for-in-region-inference-in-seoul-and-singapore/, accessed 19:32]. The models-region-compatibility page lists an `ap-southeast-1` (Singapore) row, but the per-model availability cells did not survive text extraction (empty markdown cells), so per-model Nova availability in Singapore is **not verified**: the extracted Nova 2 Sonic / Nova 2.5 Sonic tables show `us-east-1` rows only [negative claim — https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html, accessed 19:49, len 32793 served chars].
- **Pricing per 1M tokens**: Anthropic official list (docs.claude.com): **Claude Sonnet 5.5 $2 input / $10 output per MTok**; Opus 5.5 $4/$20; Haiku 5.5 $0.10/$0.50 (≤100k-token prompts); Sonnet 4.6/4.5/4 $3/$15. [verified — https://docs.claude.com/en/docs/about-claude/pricing, accessed 19:49]. AWS Bedrock pricing page served HTML: Anthropic section header present but Claude price rows were **beyond the served text**; visible CRIS rows were Kimi 3 Global CRIS $3.00/$15.00 and Kimi K3.1 Pro $4.00/$20.00 (per 1M, Standard tier) [negative claim — https://aws.amazon.com/bedrock/pricing/, accessed 19:44, 32793 served chars]. **Bedrock-specific on-demand price for Claude in ap-southeast-1: not verified**; budget with the Anthropic list price as an upper bound [inferred].

## 4. ECS Express Mode

Sources: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html (19:41), .../express-service-create-full.html (19:35), .../express-service-work.html (19:38), AWS blog https://aws.amazon.com/blogs/aws/build-production-ready-applications-without-infrastructure-complexity-using-amazon-ecs-express-mode/ (19:35).

- **What it is/creates**: "a Fargate-based ECS service with a unique accessible URL, load balancer with SSL/TLS, auto scaling policies, monitoring, and networking components" — you provide only a container image + task execution role. You pay for Fargate compute, Application Load Balancer, CloudWatch logs and metrics, data transfer. Available in all Regions where ECS + Fargate are supported (includes ap-southeast-1). [verified — overview page]
- **From ECR**: image in Amazon ECR (or private registry via a Secrets Manager secret). Optional customizations: ECS cluster, container port + **health check path**, **environment variables and secrets**, custom commands, **task role** ("allows your application code (on the container) to use other AWS services"), CPU/memory allocation. [verified — create-full page]
- **Under the hood**: auto-configured IAM roles (`ecsServiceRoleForECS`, `AWSServiceRoleForElasticLoadBalancing`), `enableECSManagedTags: true`, `healthCheckGracePeriodSeconds: 300`; deployment strategy cannot be updated on Express Mode services. AWS blog: creates ALB, HTTPS listener, listener rules, target groups, security groups, ACM certificate, Auto Scaling configs, log groups, alarms. [verified — express-service-work page + blog]
- **HTTPS URL**: the service gets "a unique accessible URL" with SSL/TLS on the load balancer (ACM cert per blog). [verified — overview + blog]
- **Scheduled daily pipeline**: Express Mode itself targets stateless HTTP apps; a daily scrape→warehouse job fits **EventBridge Scheduler** — "a serverless scheduler... create schedules using cron and rate expressions... or one-time invocations", targeting ECS tasks among others. Architecture (separate Fargate task triggered by Scheduler, not part of the Express service) is [inferred] from the two docs; the AWS containers blog "Extending Amazon ECS Express Mode..." shows extending Express services beyond defaults. [verified — https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html, accessed 19:35]
- **Rough daily cost, 0.5 vCPU / 1 GB, always-on**: Fargate Linux/X86 us-east-1 rates: CPU $0.000011244 per vCPU-second, memory $0.000001235 per GB-second [verified — https://aws.amazon.com/fargate/pricing/, accessed 19:50]. Compute: 0.5×0.000011244×86400 + 1×0.000001235×86400 ≈ **$0.59/day** (≈$18/month). Plus ALB (~$0.0225/h ≈ $0.54/day) and CloudWatch logs [inferred — ALB rate not fetched]. Singapore-region Fargate rates are not listed on the pricing page (only the us-east-1 example) [negative claim — same URL]; expect ap-southeast-1 slightly higher [inferred]. A cheaper alternative for a once-daily job: run the pipeline as a scheduled Fargate task (minutes/day) instead of an always-on service — cost then pennies/day [inferred].

## 5. Chart patterns from well-known finance dashboards

References fetched this session:
- **US Treasury daily par yield curve** — official page is a table of tenors 1 Mo…30 Yr with CSV/XML download; the canonical visual is the curve (line, x=tenor, y=yield). [verified — https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2026, accessed 19:44]
- **CME FedWatch** — "probabilities of FOMC rate moves" per upcoming meeting; visual: per-meeting probability bars/dots over meeting dates. [verified — https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html, accessed 19:44]
- **FRED** — series pages show a single clean line chart with latest observation highlighted (DGS10: 5.07% on 2026-11-18, daily). [verified — https://fred.stlouisfed.org/series/DGS10, accessed 19:46]
- **IMF DataMapper** — JS SPA: served HTML contains only template placeholders (`{ indicator.label }`); API probe `https://www.imf.org/external/datamapper/api/v1/PCPSCH/VNM` returned `{"error":"Blob not found"}` (endpoint live, that indicator code invalid). [verified negative — accessed 19:46]
- **Bloomberg WIRP** — terminal-only, no public URL to cite [inferred — well-known, not publicly verifiable]. **FT/OWID style** — small-multiple slope/line charts with direct end-labels instead of legends [inferred — style knowledge, page not fetched].

Mapping to our product (deposit decision tool) and to what `web/` can render today:

| View | Visual form (source of pattern) | Component in web/ |
|---|---|---|
| Deposit yield curve by bank | Multi-line chart, x=term (1–13 m), y=APR, one line per bank, direct labels — Treasury/FRED multi-series style | `LineChart` via `ui/chart.tsx` (`ChartContainer`, `ChartTooltip`, `ChartConfig`); already used in `insight-chart.tsx` |
| Implied rate path (forward: lock 12 m now vs 6 m twice) | Line/step chart of implied future rate vs date, per-meeting/path markers — FedWatch probability-path style | `LineChart` + `ReferenceLine`/dots (Recharts 3.10.1) |
| Ceiling kink (4.75% for 1–<6 m) | Curve with horizontal `ReferenceLine` at 4.75% and shaded band where posted rates pin to the ceiling; annotate the kink at 6 m | `ComposedChart` (already in `chart-area-interactive.tsx`) |
| Insured vs uninsured (cap 350 m VND/bank) | Grouped/stacked bar per bank: insured portion vs uninsured exposure | `BarChart` (in `insight-chart.tsx`) |
| Rate vs risk | Scatter: x = bank risk proxy (e.g. equity/assets), y = posted max rate; label outliers | `ScatterChart` (in `insight-chart.tsx`) |

[verified — repo: `web/src/components/ui/chart.tsx` exports `ChartConfig` + chart primitives; `insight-chart.tsx` imports `Bar, BarChart, Line, LineChart, Scatter, ScatterChart` from recharts; `chart-area-interactive.tsx` uses `ComposedChart`; recharts ^3.10.1 in web/package.json]

## Build recommendation (short)

- AI Q&A add-on: keep `@ai-sdk/groq` (works today, key on machine) as primary; Bedrock is optional — it needs an AWS account with model access enabled ("Access to Amazon Bedrock foundation models isn't granted by default" [verified — provider page]) and adds cost; Langfuse Hobby (free 50k units) is enough for the demo and gives public trace links judges can open — but AI is explicitly "only a quick add-on" per the owner.
- Deploy: Express Mode fits the Next.js container (HTTPS URL, no VPC config) on a weak laptop-free workflow; the daily pipeline should be a scheduled Fargate task, not an always-on service.
- Node version: `@langfuse/vercel-ai-sdk` requires Node ≥ 22 — check the deploy container base image before adding [inferred — not checked locally].

## Gaps / not verified

1. Bedrock on-demand Claude pricing for ap-southeast-1 (AWS pricing page served text truncated before Claude rows).
2. Per-model Nova availability in ap-southeast-1 (region-compatibility table cells not extractable).
3. Langfuse JS/TS masking hook name (fetched masking doc covered Python hooks; JS section not in served text).
4. ALB hourly price (not fetched).
