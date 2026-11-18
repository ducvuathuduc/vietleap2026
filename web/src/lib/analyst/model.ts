// Pick the LLM from environment variables; null means offline mode (no key configured).
import { createGroq } from "@ai-sdk/groq"
import { createOpenAICompatible } from "@ai-sdk/openai-compatible"
import type { LanguageModel } from "ai"

export interface AnalystModel {
  model: LanguageModel
  label: string
}

export function analystModel(): AnalystModel | null {
  const groqKey = process.env.GROQ_API_KEY?.trim()
  if (groqKey) {
    const id = process.env.GROQ_MODEL?.trim() || "llama-3.3-70b-versatile"
    return { model: createGroq({ apiKey: groqKey })(id), label: `Groq · ${id}` }
  }
  const baseURL = process.env.OPENAI_COMPATIBLE_BASE_URL?.trim()
  const id = process.env.OPENAI_COMPATIBLE_MODEL?.trim()
  if (baseURL && id) {
    const apiKey = process.env.OPENAI_COMPATIBLE_API_KEY?.trim() || undefined
    const provider = createOpenAICompatible({ name: "openai-compatible", baseURL, apiKey })
    return { model: provider(id), label: `${new URL(baseURL).host} · ${id}` }
  }
  return null
}
