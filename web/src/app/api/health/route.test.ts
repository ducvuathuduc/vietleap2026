import assert from "node:assert/strict"
import { test } from "node:test"

import seed from "../../../../seed/npl/snapshot.json" with { type: "json" }
import { GET } from "./route.ts"

test("GET /api/health returns ok and the published snapshot id", async () => {
  const res = await GET()
  assert.equal(res.status, 200)
  assert.deepEqual(await res.json(), { ok: true, snapshot_id: seed.meta.snapshot_id, product: "npl" })
})
