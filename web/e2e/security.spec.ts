import { expect, test } from "@playwright/test"

const SECURITY_HEADERS: Array<[string, RegExp]> = [
  ["content-security-policy", /default-src 'self'/],
  ["x-content-type-options", /^nosniff$/],
  ["referrer-policy", /^strict-origin-when-cross-origin$/],
  ["permissions-policy", /camera=\(\)/],
  ["strict-transport-security", /max-age=\d+/],
]

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

test("security headers present on /", async ({ request }) => {
  const res = await request.get("/")
  expect(res.status()).toBe(200)
  const headers = res.headers()
  for (const [name, pattern] of SECURITY_HEADERS) {
    expect(headers[name], `${name} on /`).toMatch(pattern)
  }
})

test("security headers present on /api/npl/chat", async ({ request }) => {
  // Malformed body keeps the test offline (400 before any LLM call); the
  // security headers must still be on the error response.
  const res = await request.post("/api/npl/chat", { data: "not-json", headers: { "content-type": "application/json" } })
  expect(res.status()).toBe(400)
  const headers = res.headers()
  for (const [name, pattern] of SECURITY_HEADERS) {
    expect(headers[name], `${name} on /api/npl/chat`).toMatch(pattern)
  }
})

test("malformed chat request returns a generic message with a request id", async ({ request }) => {
  const res = await request.post("/api/npl/chat", { data: "not-json", headers: { "content-type": "application/json" } })
  expect(res.status()).toBe(400)
  const body = await res.json()
  expect(body.request_id, "request id must be a UUID").toMatch(UUID)
  expect(typeof body.detail).toBe("string")
  expect(body.detail.length, "detail must be a short generic message").toBeLessThan(300)
  expect(body.detail, "detail must not leak a stack").not.toMatch(/at\s+\S+\s+\(|stack|Error:/i)
})

test.describe("forbidden in production", () => {
  test.skip(!process.env.E2E_PROD, "production-only checks: run with E2E_PROD=1 against the production URL")

  test("/lab returns 404", async ({ request }) => {
    const res = await request.get("/lab")
    expect(res.status()).toBe(404)
  })

  test("/lab/analyst returns 404", async ({ request }) => {
    const res = await request.get("/lab/analyst")
    expect(res.status()).toBe(404)
  })

  test("/api/ratewatch/chat returns 404", async ({ request }) => {
    const res = await request.post("/api/ratewatch/chat", { data: {}, headers: { "content-type": "application/json" } })
    expect(res.status()).toBe(404)
  })
})
