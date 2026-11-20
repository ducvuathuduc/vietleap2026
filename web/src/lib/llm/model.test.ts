// Run: node --test src/lib/llm/model.test.ts
import assert from "node:assert/strict"
import { test } from "node:test"

import { gatewayHeaders, providerName, createAssistantModel, PROVIDER_ENV_KEYS } from "./model.ts"

function withEnv<T>(env: Record<string, string | undefined>, fn: () => T): T {
  const saved: Record<string, string | undefined> = {}
  for (const key of PROVIDER_ENV_KEYS) {
    saved[key] = process.env[key]
    delete process.env[key]
  }
  for (const [key, value] of Object.entries(env)) {
    if (value !== undefined) process.env[key] = value
  }
  try {
    return fn()
  } finally {
    for (const key of PROVIDER_ENV_KEYS) {
      if (saved[key] === undefined) delete process.env[key]
      else process.env[key] = saved[key]
    }
  }
}

test("provider switch: gateway wins when its host and key are set", () => {
  withEnv({ LANGFUSE_GATEWAY_HOST: "https://gateway.jp.cloud.langfuse.com", LANGFUSE_GATEWAY_KEY: "gk", OPENAI_API_KEY: "ok", GROQ_API_KEY: "gr" }, () => {
    assert.equal(providerName(), "gateway")
  })
})

test("provider switch: openai when only its key is set, groq next, offline last", () => {
  withEnv({ OPENAI_API_KEY: "ok", GROQ_API_KEY: "gr" }, () => assert.equal(providerName(), "openai"))
  withEnv({ GROQ_API_KEY: "gr" }, () => assert.equal(providerName(), "groq"))
  withEnv({}, () => assert.equal(providerName(), "offline"))
})

test("provider switch: LLM_PROVIDER forces a provider", () => {
  withEnv({ LANGFUSE_GATEWAY_HOST: "https://x", LANGFUSE_GATEWAY_KEY: "k", LLM_PROVIDER: "groq" }, () => {
    assert.equal(providerName(), "groq")
  })
  withEnv({ LLM_PROVIDER: "offline" }, () => assert.equal(providerName(), "offline"))
})

test("createAssistantModel returns null in offline mode", () => {
  withEnv({}, () => assert.equal(createAssistantModel(), null))
})

test("createAssistantModel builds a model for each provider with the expected label", () => {
  withEnv({ LANGFUSE_GATEWAY_HOST: "https://gateway.jp.cloud.langfuse.com", LANGFUSE_GATEWAY_KEY: "gk" }, () => {
    const m = createAssistantModel()!
    assert.equal(m.provider, "gateway")
    assert.ok(m.label.includes("gpt-6-luna"))
  })
  withEnv({ OPENAI_API_KEY: "ok", OPENAI_MODEL: "gpt-6-luna" }, () => {
    const m = createAssistantModel()!
    assert.equal(m.provider, "openai")
    assert.ok(m.label.includes("gpt-6-luna"))
  })
  withEnv({ GROQ_API_KEY: "gr" }, () => {
    const m = createAssistantModel()!
    assert.equal(m.provider, "groq")
    assert.ok(m.label.includes("openai/gpt-oss-120b"))
  })
})

test("gateway base URL points at the Langfuse gateway OpenAI surface", () => {
  withEnv({ LANGFUSE_GATEWAY_HOST: "https://gateway.jp.cloud.langfuse.com/", LANGFUSE_GATEWAY_KEY: "gk" }, () => {
    const m = createAssistantModel()!
    assert.ok(m.gatewayBaseUrl === "https://gateway.jp.cloud.langfuse.com/openai/v1")
  })
})

test("gateway headers carry the session id so gateway calls and tool spans share one session", () => {
  assert.deepEqual(gatewayHeaders("abc-123"), { "langfuse-session-id": "abc-123" })
  assert.equal(gatewayHeaders(), undefined)
  assert.equal(gatewayHeaders("  "), undefined)
})
