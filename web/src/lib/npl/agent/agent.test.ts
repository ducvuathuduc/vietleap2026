// Run: node --test src/lib/npl/agent/agent.test.ts
import assert from "node:assert/strict"
import { test } from "node:test"

import { makeNplAgent, nplSystemPrompt, detectLang } from "./index.ts"

test("system prompt: tools only, association note, no causation claims", () => {
  const prompt = nplSystemPrompt("vi")
  assert.match(prompt, /tool/)
  assert.match(prompt, /liên hệ, không phải nhân quả/)
  assert.match(prompt, /phép tính, không phải lời hứa/)
})

test("system prompt follows the requested language", () => {
  assert.match(nplSystemPrompt("vi"), /tiếng Việt/)
  assert.match(nplSystemPrompt("en"), /English/)
})

test("agent exposes the ten NPL tools", () => {
  const agent = makeNplAgent({ env: { LANGFUSE_GATEWAY_HOST: "https://x", LANGFUSE_GATEWAY_KEY: "k" } })
  assert.ok(agent)
  const names = Object.keys(agent.tools).sort()
  assert.deepEqual(names, [
    "adjusted_change",
    "bank_profile",
    "compare_banks",
    "forecast",
    "glossary",
    "limitations",
    "market_reaction",
    "method",
    "overview",
    "quarter_effects",
  ])
})

test("agent is null in offline mode", () => {
  assert.equal(makeNplAgent({ env: {} }), null)
  assert.equal(makeNplAgent({ model: null }), null)
})

test("detectLang: diacritics, unaccented words, English default", () => {
  assert.equal(detectLang("Ngân hàng nào có nợ xấu thấp nhất?"), "vi")
  assert.equal(detectLang("ngan hang nao co no xau thap nhat"), "vi")
  assert.equal(detectLang("Which bank has the lowest NPL?"), "en")
})
