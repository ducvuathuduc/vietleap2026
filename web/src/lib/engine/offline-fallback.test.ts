import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { discoverStaticOutputs, FallbackBackendError, fetchBackendOrFallback } from "./offline-fallback.ts"

test("fetchBackendOrFallback falls back when EXTERNAL_API_URL refuses connection", async () => {
  const failingFetch = (async () => {
    throw new TypeError("fetch failed")
  }) as unknown as typeof fetch

  const result = await fetchBackendOrFallback(
    "http://127.0.0.1:8000",
    "/api/datasets",
    undefined,
    async (p) => ({ ok: true, path: p }),
    failingFetch
  )
  assert.deepEqual(result, { ok: true, path: "/api/datasets" })
})

test("fetchBackendOrFallback falls back on 502/503/504 gateway errors", async () => {
  const gatewayFetch = (async () => new Response("Bad Gateway", { status: 502 })) as unknown as typeof fetch
  const result = await fetchBackendOrFallback(
    "http://127.0.0.1:8000",
    "/api/datasets/demo/geo",
    undefined,
    async (p) => ({ fallback: true, path: p }),
    gatewayFetch
  )
  assert.deepEqual(result, { fallback: true, path: "/api/datasets/demo/geo" })
})

test("fetchBackendOrFallback preserves genuine 4xx HTTP errors", async () => {
  const notFoundFetch = (async () =>
    new Response(JSON.stringify({ detail: "not found" }), { status: 404 })) as unknown as typeof fetch

  await assert.rejects(
    () =>
      fetchBackendOrFallback(
        "http://127.0.0.1:8000",
        "/api/datasets/missing",
        undefined,
        async () => ({ ok: false }),
        notFoundFetch
      ),
    (err: FallbackBackendError) => err.status === 404 && err.message === "not found"
  )
})

test("discoverStaticOutputs reads precomputed out/<ds>/ clean_sample, results, and brief", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vlkit-out-"))
  try {
    const dsDir = path.join(tmp, "demo_offline")
    fs.mkdirSync(dsDir, { recursive: true })
    fs.writeFileSync(path.join(dsDir, "clean_sample.csv"), "province,val\nHà Nội,10\n", "utf-8")
    fs.writeFileSync(
      path.join(dsDir, "results.json"),
      JSON.stringify({ meta: { target: "val", domain: "property" } }),
      "utf-8"
    )
    fs.writeFileSync(path.join(dsDir, "brief.json"), JSON.stringify({ target: { column: "val" } }), "utf-8")

    const found = discoverStaticOutputs(tmp)
    assert.equal(found.length, 1)
    assert.equal(found[0].id, "demo_offline")
    assert.equal(found[0].target, "val")
    assert.equal(found[0].domain, "property")
    assert.ok(found[0].sampleCsvPath?.endsWith("clean_sample.csv"))
    assert.deepEqual(found[0].briefRaw, { target: { column: "val" } })
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true })
  }
})
