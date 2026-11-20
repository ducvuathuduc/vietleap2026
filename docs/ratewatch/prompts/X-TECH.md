# X-TECH Technical spike notes for the AI layer: providers, Langfuse (Japan region), live charts in chat, on-device OCR
Repo (read only): C:\Users\dieut\Desktop\Money\vietleap
## Context
- Read ..\CONTEST.md, ..\BA.md and your ..\V-TECH\TECH.md. New facts: Bedrock is NOT usable on this AWS account today (Claude Sonnet 5
  AccessDenied "not available for this account", applied token quotas are 0). The owner wants Claude Sonnet 5; available today is Groq
  (openai/gpt-oss-120b, key in .env.local). The owner has a Langfuse Pro organisation on https://jp.cloud.langfuse.com (Japan region).
- Judge rule: keep private data out of the prompt and off public pages.
## Do (write XTECH.md; official docs only, URL + access time for every claim; exact code snippets for AI SDK 7.0.173 from
   web/node_modules/ai/docs and the installed @ai-sdk/* packages)
1. Providers: how to call Claude Sonnet 5 from AI SDK v7 without Bedrock (@ai-sdk/anthropic with an Anthropic API key; OpenRouter;
   Langfuse AI Gateway if it can proxy), model ids, tool-calling support; a provider switch by env var with Groq as fallback. Does
   gpt-oss-120b on Groq support parallel tool calls and structured output in AI SDK v7?
2. Langfuse in Next.js 16 (Node >= 22) with AI SDK v7: packages, instrumentation.ts, base URL for the Japan region, tagging a trace
   with session id and source ids, masking function to drop or hash fields, making a trace public via API (not only the UI button),
   and linking from the UI to a public trace.
3. Live charts in chat ("generative UI"): with AI SDK v7 useChat, how tool results are streamed as typed parts and rendered by our own
   React chart components (no model-written code). Exact part type names and a minimal example from the installed docs.
4. On-device OCR of a printed Vietnamese savings book / deposit certificate: Tesseract.js with the "vie" language in the browser (size
   of traineddata, speed on a mid phone, accuracy notes), alternatives (PaddleOCR in WASM/ONNX), and a field-extraction approach
   (regex for amount, rate, term, dates, bank name) that never sends the image off the device. Licence of each option.
5. Recommendation in 10 lines.
## Rules
- No repo edits, no git writes, no installs into the repo, do not kill processes you did not start, never print secrets.
- Timebox: 35 minutes. Write XTECH.md and REPORT.md (max 15 lines) in THIS folder.