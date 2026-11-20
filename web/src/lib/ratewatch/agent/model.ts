// Provider switch for the RateWatch assistant.
// LLM_PROVIDER=openai|gateway|groq forces a provider; otherwise the first
// configured one wins: Langfuse AI Gateway (default per brief), then OpenAI
// direct, then Groq, and with no key at all the offline deterministic mode
// (ratewatchModel() returns null and the route answers without an LLM).
// When the gateway is used, model calls are recorded by the gateway itself —
// instrumentation.ts must not also trace them (double recording).
import { createGroq } from "@ai-sdk/groq"
import { createOpenAI } from "@ai-sdk/openai"
import type { LanguageModel } from "ai"

export type ProviderName = "gateway" | "openai" | "groq" | "offline"

export const PROVIDER_ENV_KEYS = [
  "LLM_PROVIDER",
  "LANGFUSE_GATEWAY_HOST",
  "LANGFUSE_GATEWAY_KEY",
  "OPENAI_API_KEY",
  "OPENAI_MODEL",
  "GROQ_API_KEY",
  "GROQ_MODEL",
] as const

export const DEFAULT_OPENAI_MODEL = "gpt-6-luna"
export const DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

export function providerName(env: NodeJS.ProcessEnv = process.env): ProviderName {
  const forced = env.LLM_PROVIDER?.trim()
  if (forced === "gateway" || forced === "openai" || forced === "groq" || forced === "offline") return forced
  if (env.LANGFUSE_GATEWAY_HOST?.trim() && env.LANGFUSE_GATEWAY_KEY?.trim()) return "gateway"
  if (env.OPENAI_API_KEY?.trim()) return "openai"
  if (env.GROQ_API_KEY?.trim()) return "groq"
  return "offline"
}

export interface RatewatchModel {
  model: LanguageModel
  provider: ProviderName
  label: string
  /** Set for the gateway: the OpenAI surface the calls go through. */
  gatewayBaseUrl?: string
}

/** The gateway tags each call with the chat session id so gateway model calls
 * and our tool spans land in one Langfuse session (brief update 14:50). */
export function gatewayHeaders(sessionId?: string | null): Record<string, string> | undefined {
  const sid = sessionId?.trim()
  return sid ? { "langfuse-session-id": sid } : undefined
}

export function ratewatchModel(env: NodeJS.ProcessEnv = process.env, sessionId?: string | null): RatewatchModel | null {
  const provider = providerName(env)
  if (provider === "offline") return null
  if (provider === "gateway") {
    const host = env.LANGFUSE_GATEWAY_HOST!.trim().replace(/\/+$/, "")
    const gatewayBaseUrl = `${host}/openai/v1`
    const id = env.OPENAI_MODEL?.trim() || DEFAULT_OPENAI_MODEL
    const openai = createOpenAI({
      baseURL: gatewayBaseUrl,
      apiKey: env.LANGFUSE_GATEWAY_KEY!.trim(),
      headers: gatewayHeaders(sessionId),
    })
    return { model: openai(id), provider, label: `langfuse-gateway · ${id}`, gatewayBaseUrl }
  }
  if (provider === "openai") {
    const id = env.OPENAI_MODEL?.trim() || DEFAULT_OPENAI_MODEL
    const openai = createOpenAI({ apiKey: env.OPENAI_API_KEY!.trim() })
    return { model: openai(id), provider, label: `openai · ${id}` }
  }
  const id = env.GROQ_MODEL?.trim() || DEFAULT_GROQ_MODEL
  const groq = createGroq({ apiKey: env.GROQ_API_KEY!.trim() })
  return { model: groq(id), provider, label: `groq · ${id}` }
}
