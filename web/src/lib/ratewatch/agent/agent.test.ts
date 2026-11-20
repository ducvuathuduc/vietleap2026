// Run: node --test src/lib/ratewatch/agent/agent.test.ts
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

import { MockLanguageModelV3 } from "ai/test"

import type { Snapshot } from "../types.ts"
import { makeRatewatchAgent, ratewatchSystemPrompt, TOOL_NAMES } from "./agent.ts"

// The fixture is read directly (load.ts uses a bundler-only JSON import).
const snapshot = JSON.parse(
  readFileSync(new URL("../../../../seed/ratewatch/snapshot.fixture.json", import.meta.url), "utf8"),
) as Snapshot

test("system prompt: tools only, sheet dates, not-a-forecast, no advice, no PII", () => {
  const prompt = ratewatchSystemPrompt()
  assert.match(prompt, /tool/)
  assert.match(prompt, /phép tính, không phải dự báo/)
  assert.match(prompt, /calculation, not a forecast/)
  assert.match(prompt, /tư vấn đầu tư/)
  assert.match(prompt, /CCCD|CMND|điện thoại|tài khoản/)
})

test("agent exposes the nine tools", () => {
  const agent = makeRatewatchAgent({ snapshot, env: { LANGFUSE_GATEWAY_HOST: "https://x", LANGFUSE_GATEWAY_KEY: "k" } })
  assert.ok(agent)
  assert.deepEqual(Object.keys(agent.tools).sort(), [...TOOL_NAMES].sort())
})

test("agent is null in offline mode", () => {
  assert.equal(makeRatewatchAgent({ snapshot, env: {} }), null)
  assert.equal(makeRatewatchAgent({ snapshot, model: null }), null)
})

test("agent loop: a mocked model calls get_curve then answers with the tool number", async () => {
  const usage = { inputTokens: { total: 5, noCache: 5, cacheRead: 0, cacheWrite: 0 }, outputTokens: { total: 5, noCache: 5, reasoning: 0 }, totalTokens: 10 }
  const model = new MockLanguageModelV3({
    doGenerate: [
      {
        content: [{ type: "tool-call", toolCallId: "c1", toolName: "get_curve", input: '{"bank": "OCB", "channel": "online"}' }],
        finishReason: { unified: "tool-calls", raw: "tool-calls" },
        usage,
      },
      {
        content: [{ type: "text", text: "OCB online kỳ 6 tháng là 6,00%/năm, biểu đề ngày 06/11/2026." }],
        finishReason: { unified: "stop", raw: "stop" },
        usage,
      },
    ],
  })
  const agent = makeRatewatchAgent({ snapshot, model })
  assert.ok(agent)
  const result = await agent.generate({ prompt: "OCB online kỳ 6 tháng bao nhiêu?" })
  assert.equal(result.steps.length, 2)
  assert.match(result.text, /6,00%/)
  // the tool actually executed against the fixture snapshot
  const toolResult = result.steps[0]!.content.find((part) => part.type === "tool-result")
  assert.ok(toolResult)
  const output = (toolResult as { output?: { points?: { term_months: number; rate_pct: number }[] } }).output
  assert.ok(output?.points?.some((p) => p.term_months === 6 && p.rate_pct === 6.0))
})
