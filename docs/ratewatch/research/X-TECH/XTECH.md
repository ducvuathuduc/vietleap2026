# X-TECH — AI layer spike for "Lãi Suất Hôm Nay" (20/11/2026, 13:10–13:16 Asia/Saigon)

Scope: call Claude Sonnet 5 from AI SDK v7 without Bedrock; Langfuse Japan tracing; live charts in chat; on-device OCR of a savings book. Every claim carries its source URL + access time (UTC). "Installed docs" = `web/node_modules/ai/docs` (ai 7.0.173) and `web/node_modules/@ai-sdk/groq/docs/09-groq.mdx` (groq 4.0.84), read from the repo.

---

## 1. Providers: Claude Sonnet 5 without Bedrock

- **Direct provider**: `@ai-sdk/anthropic` (NOT installed yet — repo has only `@ai-sdk/groq`, `@ai-sdk/openai-compatible`, `@ai-sdk/react`, `@ai-sdk/gateway`, `@ai-sdk/provider`, `@ai-sdk/mcp`). Install: `npm i @ai-sdk/anthropic`. Auth via `ANTHROPIC_API_KEY` env var; `createAnthropic()` for custom settings. [https://ai-sdk.dev/providers/ai-sdk-providers/anthropic, 06:11]
- **Model id**: dateless major format — `claude-sonnet-5` (docs.claude.com model-naming page, quoted in search results 06:11: "Major-version releases such as Claude Sonnet 5 and Claude Opus 5 omit the minor segment. For example: claude-sonnet-4-6, claude-sonnet-5, claude-opus-4-6…"). The ai-sdk.dev Anthropic page's own examples use `claude-haiku-5-5` / gateway string `anthropic/claude-sonnet-5.5`. [https://ai-sdk.dev/providers/ai-sdk-providers/anthropic, 06:11]
- **Tool calling**: provider-agnostic in v7 — `tool()` helper + `stopWhen: isStepCount(n)` multi-step loop; Anthropic models "support structured data generation with `Output`" per the provider page. [installed docs 03-ai-sdk-core/15-tools-and-tool-calling.mdx; 04-generative-user-interfaces.mdx]
- **Provider switch by env var with Groq fallback** (drop-in, no other changes):
  ```ts
  // ai/provider.ts
  import { createGroq } from '@ai-sdk/groq';
  import { createAnthropic } from '@ai-sdk/anthropic';
  const groq = createGroq(); const anthropic = createAnthropic();
  export const model = process.env.AI_PROVIDER === 'anthropic'
    ? anthropic('claude-sonnet-5')
    : groq(process.env.GROQ_MODEL ?? 'openai/gpt-oss-120b');
  ```
  Groq fallback works today: `GROQ_API_KEY` + `GROQ_MODEL=openai/gpt-oss-120b` already in `web/.env.local`; gpt-oss-120b capabilities per GroqDocs model page: Tool Use, JSON Object Mode, JSON Schema Mode, Reasoning, ~500 tps, 131,072 ctx, $0.15/$0.60 per MTok. [https://console.groq.com/docs/model/openai/gpt-oss-120b, 06:12]
- **Langfuse AI Gateway as proxy**: exists and is in **public beta** — "Authorize user with gateway key… Map model name and URL to valid model provider request"; every call becomes a full Langfuse trace. Provider fallbacks are on its **roadmap**, not shipped. [https://langfuse.com/docs/gateway, 06:11] → For the demo, call providers directly; use the gateway only if we want enforced spend governance.

## 2. Langfuse in Next.js 16 (Node ≥ 22), Japan region

- **Packages** (one-time install): `npm i @langfuse/vercel-ai-sdk @langfuse/otel @langfuse/tracing @langfuse/client @opentelemetry/sdk-node`. `@langfuse/vercel-ai-sdk` targets AI SDK 7 and **requires Node.js ≥ 22**. [https://langfuse.com/integrations/frameworks/vercel-ai-sdk, 06:11]
- **instrumentation.ts** (project root, runs at startup) — exact pattern from the integration page:
  ```ts
  import { registerTelemetry } from 'ai';
  import { LangfuseSpanProcessor } from '@langfuse/otel';
  import { LangfuseVercelAiSdkIntegration } from '@langfuse/vercel-ai-sdk';
  import { NodeSDK } from '@opentelemetry/sdk-node';
  const sdk = new NodeSDK({ spanProcessors: [new LangfuseSpanProcessor()] });
  sdk.start();
  registerTelemetry(new LangfuseVercelAiSdkIntegration());
  ```
- **Env**: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL=https://jp.cloud.langfuse.com` (Japan is a first-class cloud region; region visible in the URL bar per Langfuse FAQ). [https://langfuse.com/faq/all/where-is-my-project, 06:11]
- **Session id + source ids**: wrap the call with `propagateAttributes({ sessionId, userId, tags, metadata }, () => streamText(...))` from `@langfuse/tracing` — `sessionId` groups traces into a session; `metadata` carries our source ids (e.g. `{ sourceIds: [...], snapshotDate }`). [integration page, 06:11]
- **Masking** (judge rule: private data off public pages): `new LangfuseSpanProcessor({ mask })` — `MaskFunction = (params: { data: any }) => any`, applied to observation input/output and each metadata value **before export**; returning `null`/`undefined` drops the key. Trace metadata propagated via `propagateAttributes` is NOT masked (source: `packages/otel/src/span-processor.ts`, read 06:13). → Keep amounts out of `metadata`, or hash them in `mask`.
- **Public trace**: UI "Make Public" in the trace header ⋯ menu, or programmatically `startObservation('...').setTraceAsPublic()` (JS) / `span.set_trace_as_public()` (Python). URL format `{baseUrl}/project/{projectId}/traces/{traceId}` — from `LangfuseClient.getTraceUrl()` source. [https://langfuse.com/docs/observability/features/url, 06:13]

## 3. Live charts in chat (generative UI, no model-written code)

- Server: `streamText({ model, tools, stopWhen: isStepCount(5), messages: await convertToModelMessages(messages) })`, return `createUIMessageStreamResponse({ stream: toUIMessageStream({ stream: result.stream }) })`. [installed docs 04-ai-sdk-ui/04-generative-user-interfaces.mdx]
- Client: `useChat()`; assistant `message.parts` contains **typed tool parts named `tool-${toolName}`** (static tools) or generic `dynamic-tool` (compile-time-unknown tools), with states `input-streaming` → `input-available` → `output-available` / `output-error`; approval states `approval-requested`/`approval-responded`/`output-denied` exist but are optional. [installed docs 03-chatbot-tool-usage.mdx, 04-generative-user-interfaces.mdx]
- Minimal pattern: model calls our zod-schema tool (e.g. `getDepositCurve`); the tool's `execute` runs server-side (DuckDB query); `part.state === 'output-available'` → render `part.output` with our own Recharts component (`ChartContainer` from `ui/chart.tsx`). The model never writes code — it only fills the typed tool input; the chart is our React component. [installed docs + repo `insight-chart.tsx`]
- Groq model for this: `openai/gpt-oss-120b` (verified capabilities above); `@ai-sdk/groq` options `parallelToolCalls` (default `true`), `structuredOutputs` (default `true`, json_schema), `strictJsonSchema` (default `true`), `reasoningEffort: 'low'|'medium'|'high'`, `serviceTier: 'on_demand'|'performance'|'flex'|'auto'`. [installed @ai-sdk/groq docs/09-groq.mdx, 06:10]

## 4. On-device OCR of a printed savings book / deposit certificate

- **Tesseract.js** — pure JS OCR in the browser, 100+ languages, Apache-2.0. [https://github.com/naptha/tesseract.js, 06:12] Vietnamese `vie.traineddata`: **519 KB** (tessdata_fast integerized LSTM model) or **7.4 MB** (tessdata best). [https://github.com/tesseract-ocr/tessdata_fast/blob/main/vie.traineddata, 06:12; https://github.com/tesseract-ocr/tessdata/blob/main/vie.traineddata, 06:12] Loads from a CDN at runtime; runs in a web worker; nothing leaves the device. Speed on a mid phone: no official number published — budget seconds, not ms; use `tessdata_fast` for the demo.
- **PaddleOCR in-browser**: no first-party WASM port; community route is ONNX Runtime Web with converted PaddleOCR det/rec models (e.g. `monkt/paddleocr-onnx` on HuggingFace; npm `client-side-ocr`, MIT, wraps onnxruntime-web + tesseract.js). PaddleOCR itself is Apache-2.0. [https://huggingface.co/monkt/paddleocr-onnx; https://libraries.io/npm/client-side-ocr, 06:12] Higher accuracy than Tesseract on printed VN text, but bigger download and more integration work — treat as the upgrade path, not the demo.
- **Field extraction without sending the image anywhere**: run OCR fully in-browser, then regex the text — amount: `/(\d{1,3}([.,]\d{3})+)\s*(VND|đ|d)/i`; rate: `/(\d{1,2}[.,]\d+)\s*%/`; term: `/(\d+)\s*(tháng|month)/i`; dates: `/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})/`; bank name: match against our `dim_bank` list. Confidence per field from Tesseract word confidences; low-confidence fields fall back to manual input in the UI.

## 5. Recommendation (10 lines)

1. Ship the AI planner on Groq `openai/gpt-oss-120b` today — key on machine, tool calling + JSON-schema structured output verified, ~500 tps.
2. Keep `claude-sonnet-5` behind the `AI_PROVIDER` env switch; add `@ai-sdk/anthropic` only when an Anthropic key exists (Bedrock stays dead: AccessDenied, 0 token quota).
3. Add Langfuse Japan (`LANGFUSE_BASE_URL=https://jp.cloud.langfuse.com`) via `@langfuse/vercel-ai-sdk` + `@langfuse/otel` — ~5 lines in `instrumentation.ts`.
4. Mask first: amounts and any personal data never enter `metadata`; the `mask` function is the last line of defense before export.
5. "Xem dấu vết" = `getTraceUrl(traceId)` link to the Japan-region trace; make only demo traces public via `setTraceAsPublic()`.
6. Charts: typed tool parts (`tool-getDepositCurve` etc.) rendered by our own Recharts components — no model-written code, judge-safe.
7. OCR demo: Tesseract.js + `vie` fast model (519 KB) for the savings book; regex extraction with per-field confidence; PaddleOCR-ONNX only if accuracy disappoints.
8. All four pieces are open-source (Apache-2.0/MIT) — no license risk in the submission.
9. Node ≥ 22 required by `@langfuse/vercel-ai-sdk` — pin the deploy container before wiring instrumentation.
10. Total new dependencies: 5 Langfuse/OTel packages + 1 provider; everything else already in the repo.

---

### Gaps / not verified this session
- REST `PATCH /api/public/traces/{traceId}`: the served openapi.yml text was truncated before the traces paths; the verified programmatic path is the SDK's `setTraceAsPublic()`. Classic-API PATCH is [inferred], not fetched.
- Per-model Bedrock pricing/availability in ap-southeast-1: not re-checked (Bedrock ruled out by AccessDenied anyway).
- Tesseract.js phone speed: no official benchmark exists; treat any ms figure as an estimate until we test on a real device.
