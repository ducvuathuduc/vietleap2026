import assert from "node:assert/strict"
import { test } from "node:test"

import nextConfig from "../../next.config.ts"
import { FORBIDDEN_TEXT } from "../../e2e/helpers.ts"

async function headerMap(nodeEnv: string) {
  const prev = process.env.NODE_ENV
  process.env.NODE_ENV = nodeEnv
  try {
    const groups = await nextConfig.headers!()
    const headers = groups[0]?.headers ?? []
    return Object.fromEntries(headers.map((item) => [item.key, item.value]))
  } finally {
    if (prev === undefined) delete process.env.NODE_ENV
    else process.env.NODE_ENV = prev
  }
}

test("production CSP blocks framing, drops AI Studio, and has no unsafe-eval", async () => {
  const headers = await headerMap("production")
  const csp = headers["Content-Security-Policy"]
  assert.equal(csp.includes("unsafe-eval"), false)
  assert.match(csp, /frame-ancestors 'none'/)
  assert.equal(/aistudio|googleusercontent|googleapis|google\.com/.test(csp), false)
  assert.match(csp, /script-src 'self' 'unsafe-inline'/)
  assert.match(csp, /style-src 'self' 'unsafe-inline'/)
  assert.match(csp, /img-src 'self' data: blob:/)
  assert.equal(headers["X-Content-Type-Options"], "nosniff")
  assert.equal(headers["Referrer-Policy"], "strict-origin-when-cross-origin")
  assert.match(headers["Permissions-Policy"], /camera=\(\)/)
})

test("development CSP keeps unsafe-eval and the Next dev socket", async () => {
  const csp = (await headerMap("development"))["Content-Security-Policy"]
  assert.match(csp, /script-src 'self' 'unsafe-inline' 'unsafe-eval'/)
  assert.match(csp, /connect-src 'self' ws: wss:/)
  assert.match(csp, /frame-ancestors 'none'/)
})

test("production disables legacy aliases unless the lab is enabled", async () => {
  const original = process.env
  try {
    process.env = { ...original, NODE_ENV: "production", ENABLE_LAB: "0" }
    assert.deepEqual(await nextConfig.redirects!(), [])
    process.env.ENABLE_LAB = "1"
    const redirects = await nextConfig.redirects!()
    assert.ok(redirects.some(({ source, destination }) => source === "/analyst" && destination === "/lab/analyst"))
  } finally {
    process.env = original
  }
})

test("QA detects debug tokens in rendered text without flagging ordinary words", () => {
  assert.doesNotMatch("Consolidated financial statements and fixtureless datasets.", FORBIDDEN_TEXT)
  for (const token of ["get_ratios", "fixture", "run_id", "undefined", "NaN", "Error:", "stack", "console"]) {
    assert.match(`Value: (${token}).`, FORBIDDEN_TEXT)
  }
})
