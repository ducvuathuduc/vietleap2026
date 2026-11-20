import assert from "node:assert/strict"
import { registerHooks } from "node:module"
import { test, type TestContext } from "node:test"
import { S3Client } from "@aws-sdk/client-s3"

import seed from "../../../../seed/npl/snapshot.json" with { type: "json" }
import { readSnapshot } from "../../../lib/npl/snapshot-source.ts"

const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    // The Next request boundary is already established in the deployed handler.
    if (specifier === "next/server") {
      return { url: "data:text/javascript,export%20async%20function%20connection()%7B%7D", shortCircuit: true }
    }
    return nextResolve(specifier, context)
  },
})
const { GET } = await import("./route.ts").finally(() => hooks.deregister())

function setSource(t: TestContext, uri?: string) {
  const previous = process.env.NPL_SNAPSHOT_S3_URI
  if (uri) process.env.NPL_SNAPSHOT_S3_URI = uri
  else delete process.env.NPL_SNAPSHOT_S3_URI
  t.after(() => {
    if (previous === undefined) delete process.env.NPL_SNAPSHOT_S3_URI
    else process.env.NPL_SNAPSHOT_S3_URI = previous
  })
}

test("health identifies the bundled snapshot with S3 unconfigured", async (t) => {
  setSource(t)
  const response = await GET()
  assert.equal(response.status, 200)
  assert.equal(response.headers.get("cache-control"), "no-store")
  assert.deepEqual(await response.json(), {
    ok: true, snapshot_id: seed.meta.snapshot_id, generated_at: seed.meta.generated_at, source: "seed", product: "npl",
  })
})

for (const [label, delta] of [["newer", 1_000], ["older", -1_000]] as const) {
  test(`health reports the same publication as the pages when S3 is ${label}`, async (t) => {
    setSource(t, `s3://vietleap-test/snapshots/health-${label}.json`)
    const cloud = { ...seed, meta: { ...seed.meta, snapshot_id: "cloud-publication",
      generated_at: new Date(Date.parse(seed.meta.generated_at) + delta).toISOString() } }
    const send = t.mock.method(S3Client.prototype, "send", async () => ({
      Body: { transformToString: async () => JSON.stringify(cloud) },
    }))
    const warn = t.mock.method(console, "warn", () => {})
    const [snapshot, response] = await Promise.all([readSnapshot(), GET()])
    const accepted = delta > 0
    const expected = accepted ? cloud : seed
    assert.equal(snapshot.meta.snapshot_id, expected.meta.snapshot_id)
    assert.deepEqual(await response.json(), {
      ok: true, snapshot_id: expected.meta.snapshot_id, generated_at: expected.meta.generated_at,
      source: accepted ? "s3" : "seed", product: "npl",
    })
    assert.equal(send.mock.callCount(), 1)
    assert.equal(warn.mock.callCount(), accepted ? 0 : 1)
  })
}
