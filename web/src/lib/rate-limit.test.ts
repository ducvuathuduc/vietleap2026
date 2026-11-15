import assert from "node:assert/strict"
import { test } from "node:test"

import { clientKey, createRateLimiter } from "./rate-limit.ts"

test("allows up to N requests per window then blocks with Retry-After", () => {
  const allow = createRateLimiter(3)
  const t0 = 1_000_000
  assert.deepEqual([0, 1, 2].map((i) => allow("a", t0 + i).ok), [true, true, true])
  const blocked = allow("a", t0 + 10)
  assert.equal(blocked.ok, false)
  assert.ok(blocked.retryAfterS >= 1 && blocked.retryAfterS <= 60)
  assert.equal(allow("b", t0 + 10).ok, true) // other clients unaffected
  assert.equal(allow("a", t0 + 60_001).ok, true) // window slides
})

test("0 disables the limit", () => {
  const allow = createRateLimiter(0)
  for (let i = 0; i < 100; i++) assert.equal(allow("x").ok, true)
})

test("client key from proxy headers", () => {
  assert.equal(clientKey(new Request("http://x", { headers: { "x-forwarded-for": "1.2.3.4, 10.0.0.1" } })), "1.2.3.4")
  assert.equal(clientKey(new Request("http://x")), "local")
})
