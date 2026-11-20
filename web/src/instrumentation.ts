// Next.js instrumentation: Langfuse OTel tracing for tool spans and session
// ids — only when the Langfuse project keys exist; until then this skips
// cleanly (the gateway records model calls on its own, so when the provider is
// the gateway the AI SDK integration is NOT registered: no double recording).
// Every exported span value goes through the PII mask first.
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return

  const { loadRepoEnv } = await import("./lib/ratewatch/agent/env")
  loadRepoEnv()

  const publicKey = process.env.LANGFUSE_PUBLIC_KEY?.trim()
  const secretKey = process.env.LANGFUSE_SECRET_KEY?.trim()
  if (!publicKey || !secretKey) return

  const { NodeSDK } = await import("@opentelemetry/sdk-node")
  const { LangfuseSpanProcessor } = await import("@langfuse/otel")
  const { redactPii } = await import("./lib/ratewatch/agent/guards")
  const { providerName } = await import("./lib/ratewatch/agent/model")

  const sdk = new NodeSDK({
    spanProcessors: [
      new LangfuseSpanProcessor({
        mask: async ({ data }) => redactPii(data),
      }),
    ],
  })
  sdk.start()

  if (providerName() !== "gateway") {
    const { registerTelemetry } = await import("ai")
    const { LangfuseVercelAiSdkIntegration } = await import("@langfuse/vercel-ai-sdk")
    registerTelemetry(new LangfuseVercelAiSdkIntegration())
  }
}
