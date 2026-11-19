import assert from "node:assert/strict"
import { test } from "node:test"

import { guardApi } from "./api-guard.ts"

function call(path: string, method: string, env: { ENABLE_LAB?: string; ENABLE_CHAT?: string }) {
  const prev = { ENABLE_LAB: process.env.ENABLE_LAB, ENABLE_CHAT: process.env.ENABLE_CHAT }
  for (const key of ["ENABLE_LAB", "ENABLE_CHAT"] as const) {
    const value = env[key]
    if (value === undefined) delete process.env[key]
    else process.env[key] = value
  }
  try {
    return guardApi(new Request(`http://local${path}`, { method }))
  } finally {
    for (const key of ["ENABLE_LAB", "ENABLE_CHAT"] as const) {
      const value = prev[key]
      if (value === undefined) delete process.env[key]
      else process.env[key] = value
    }
  }
}

const off = {}

test("lab tools return 404 unless ENABLE_LAB is exactly 1", () => {
  for (const [path, method] of [
    ["/api/sql", "POST"],
    ["/api/ingest", "POST"],
    ["/api/ingest/job-1", "GET"],
    ["/api/sources/kinds", "GET"],
    ["/api/warehouse/tables", "GET"],
    ["/api/warehouse/tables/gold.obt/columns", "GET"],
    ["/api/jobs/job-1", "GET"],
    ["/api/export/job-1", "GET"],
    ["/api/datasets", "POST"],
    ["/api/datasets/demo/export", "POST"],
    ["/api/brief", "POST"],
    ["/api/story", "POST"],
  ] as const) {
    assert.equal(call(path, method, off)?.status, 404, `${method} ${path}`)
    assert.equal(call(path, method, { ENABLE_LAB: "true" })?.status, 404, `${method} ${path} true`)
    assert.equal(call(path, method, { ENABLE_LAB: "1" }), null, `${method} ${path} on`)
  }
})

test("chat uses ENABLE_CHAT and ignores ENABLE_LAB", () => {
  assert.equal(call("/api/chat", "GET", { ENABLE_LAB: "1" })?.status, 404)
  assert.equal(call("/api/chat", "POST", { ENABLE_LAB: "1" })?.status, 404)
  assert.equal(call("/api/chat", "POST", { ENABLE_CHAT: "1" }), null)
  assert.equal(call("/api/chat", "GET", { ENABLE_CHAT: "1", ENABLE_LAB: undefined }), null)
})

test("health and judge-unused reads stay open when the lab is off", () => {
  for (const [path, method] of [
    ["/api/health", "GET"],
    ["/api/datasets", "GET"],
    ["/api/datasets/demo", "GET"],
    ["/api/datasets/demo/insights", "GET"],
    ["/api/datasets/demo/brief", "GET"],
    ["/api/datasets/demo/files/results", "GET"],
    ["/api/datasets/demo/whatif", "POST"],
    ["/api/brief/samples", "GET"],
    ["/api/brief/packs", "GET"],
  ] as const) {
    assert.equal(call(path, method, off), null, `${method} ${path}`)
  }
})
