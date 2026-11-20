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
