import assert from "node:assert/strict"
import { test } from "node:test"

import { GET } from "./route.ts"

test("GET /api/health returns ok and the published snapshot id", async () => {
  const res = await GET()
  assert.equal(res.status, 200)
  const body = (await res.json()) as { ok: boolean; snapshot_id: string }
  assert.equal(body.ok, true)
  assert.equal(typeof body.snapshot_id, "string")
  assert.ok(body.snapshot_id.length > 0)
})
