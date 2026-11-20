import assert from "node:assert/strict"
import { registerHooks } from "node:module"
import { test } from "node:test"

const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    const resolved = specifier.startsWith("@/")
      ? new URL(`../../../../${specifier.slice(2)}.ts`, import.meta.url).href
      : specifier
    return nextResolve(resolved, context)
  },
})
const { POST } = await import("./route.ts").finally(() => hooks.deregister())

for (const [name, body] of [["malformed JSON", "{"], ["schema-invalid JSON", JSON.stringify({ messages: {} })]]) {
  test(`NPL chat returns only a generic bilingual error and request ID for ${name}`, async () => {
    const response = await POST(new Request("http://localhost/api/npl/chat", { method: "POST", body }))
    assert.equal(response.status, 400)
    const result = await response.json()
    assert.deepEqual(Object.keys(result).sort(), ["detail", "request_id"])
    assert.equal(result.detail, "Yêu cầu không hợp lệ. / Invalid request.")
    assert.match(result.request_id, /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i)
  })
}

test("the chat route refuses buy and sell advice in the question language, with a decoder offer", async (t) => {
  const previous = process.env.LLM_PROVIDER
  process.env.LLM_PROVIDER = "offline"
  t.after(() => {
    if (previous === undefined) delete process.env.LLM_PROVIDER
    else process.env.LLM_PROVIDER = previous
  })
  const cases = [
    ["Should I buy VCB stock?", /investment advice/i, /decoder check/i],
    ["Có nên bán cổ phiếu MBB không?", /khuyến nghị đầu tư/i, /giải mã/i],
  ] as const
  for (const [question, refusal, alternative] of cases) {
    const body = JSON.stringify({ messages: [{ id: "a", role: "user", parts: [{ type: "text", text: question }] }] })
    const response = await POST(new Request("http://localhost/api/npl/chat", { method: "POST", body }))
    assert.equal(response.status, 200)
    const stream = await response.text()
    assert.match(stream, refusal)
    assert.match(stream, alternative)
  }
})

test("the chat route streams one grounded comparison for the 2025Q4 Group 2 question", async () => {
  const body = JSON.stringify({ messages: [{ id: "s1", role: "user", parts: [{
    type: "text", text: "Ngân hàng nào có NPL giảm quý 4/2025 nhưng nợ nhóm 2 tăng?",
  }] }] })
  const response = await POST(new Request("http://localhost/api/npl/chat", { method: "POST", body }))
  assert.equal(response.status, 200)
  const stream = await response.text()
  const chunks = stream.split(/\r?\n/).filter((line) => line.startsWith("data: ") && line !== "data: [DONE]")
    .map((line) => JSON.parse(line.slice(6)))
  const evidence = chunks.filter((part) => part.type === "tool-output-available")
  assert.equal(evidence.length, 1)
  assert.equal(evidence[0].output.rows.length, 6)
  assert.match(chunks.find((part) => part.type === "text-delta").delta, /BVB, LPB, NAB, NVB, SGB, SHB/)
  assert.ok(!chunks.some((part) => part.type === "data-guard"))
})
