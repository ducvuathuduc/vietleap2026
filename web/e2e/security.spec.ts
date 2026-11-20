import { expect, test, type APIResponse } from "@playwright/test"

import { isProductionTarget, RATEWATCH_BANK_CODES, RATEWATCH_ROUTES } from "./helpers"

const SECURITY_HEADERS = [
  ["content-security-policy", /default-src 'self'/],
  ["content-security-policy", /frame-ancestors 'none'/],
  ["x-content-type-options", /^nosniff$/],
  ["referrer-policy", /^strict-origin-when-cross-origin$/],
  ["permissions-policy", /camera=\(\)/],
  ["strict-transport-security", /max-age=\d+/],
] as const

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const JSON_HEADERS = { "content-type": "application/json" }

function expectSecurityHeaders(response: APIResponse) {
  const headers = response.headers()
  for (const [name, pattern] of SECURITY_HEADERS) {
    expect(headers[name] ?? "", `${name} on ${response.url()}`).toMatch(pattern)
  }
}

test("security headers are present on /", async ({ request }) => {
  const response = await request.get("/")
  expect(response.status()).toBe(200)
  expectSecurityHeaders(response)
})

for (const [name, data] of [["malformed JSON", Buffer.from("not-json")], ["invalid chat payload", { messages: {} }]] as const) {
  test(`/api/npl/chat rejects ${name} with security headers, a generic message and a request id`, async ({ request }) => {
    const response = await request.post("/api/npl/chat", { data, headers: JSON_HEADERS })
    expect(response.status()).toBe(400)
    expectSecurityHeaders(response)
    const body = await response.json()
    expect(body).toEqual({ detail: "Yêu cầu không hợp lệ. / Invalid request.", request_id: expect.stringMatching(UUID) })
  })
}

test.describe("internal routes @production", () => {
  test.skip(({ baseURL }) => !isProductionTarget(baseURL), "production-only checks require a production BASE_URL or E2E_PROD=1 for a local production server")

  const hiddenPaths = [
    "/lab", "/lab/analyst", "/analyst", "/print", "/api/ratewatch", "/api/ratewatch/chat",
    "/api/brief/packs", "/api/datasets", "/api/sources/kinds", "/api/warehouse/tables",
  ]
  for (const path of hiddenPaths) {
    test(`GET ${path} returns a direct 404`, async ({ request }) => {
      const response = await request.get(path, { maxRedirects: 0 })
      expect(response.status()).toBe(404)
    })
  }

  const legacyRatewatch = [...RATEWATCH_ROUTES, ...RATEWATCH_BANK_CODES.map((code) => `/lai-suat/ngan-hang/${code}`), "/tai-lieu/lai-suat"]
  for (const path of legacyRatewatch) {
    test(`GET ${path} returns a direct 404`, { tag: "@legacy" }, async ({ request }) => {
      const response = await request.get(path, { maxRedirects: 0 })
      expect(response.status()).toBe(404)
    })
  }

  test("POST /api/ratewatch/chat returns a direct 404", async ({ request }) => {
    const response = await request.post("/api/ratewatch/chat", { data: {}, maxRedirects: 0 })
    expect(response.status()).toBe(404)
  })
})
