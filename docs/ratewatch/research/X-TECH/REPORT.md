# X-TECH REPORT
Status: DONE

## Acceptance evidence
- All web claims fetched live this session (06:10–06:16 UTC, 20/11/2026) from official sources only: ai-sdk.dev provider pages, langfuse.com docs (integration/masking/trace-URLs/FAQ), console.groq.com model page, GitHub raw sources (tessdata sizes, licenses, span-processor source).
- Installed-docs claims read from `web/node_modules/ai/docs` (ai 7.0.173) and `web/node_modules/@ai-sdk/groq/docs/09-groq.mdx` (groq 4.0.84); versions confirmed from package.json files.
- No repo edits, no installs, no git writes, no secrets printed (env var NAMES only).

## Deliverable
- XTECH.md in this folder: providers (Sonnet 5 without Bedrock + env-var switch with Groq fallback), Langfuse Japan setup (instrumentation.ts, masking, public traces), generative-UI typed tool parts, on-device OCR with licenses.

## Not done / risks
- REST `PATCH /api/public/traces/{traceId}` not verifiable in served docs this session; SDK `setTraceAsPublic()` is the verified path (marked [inferred] in XTECH.md).
- Tesseract.js on-phone speed: no official benchmark; needs a real-device test before the pitch.
