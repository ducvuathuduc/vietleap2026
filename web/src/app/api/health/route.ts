import { readFileSync } from "node:fs"
import path from "node:path"

import ratewatchFixture from "../../../../seed/ratewatch/snapshot.fixture.json" with { type: "json" }

// The NPL snapshot is written by the pipeline (python -m vlkit.npl.snapshot)
// next to the bundled ratewatch fixture; read it from disk when present.
function nplSnapshotId(): string | null {
  try {
    const raw = JSON.parse(readFileSync(path.join(process.cwd(), "seed/npl/snapshot.json"), "utf8")) as { meta?: { snapshot_id?: string } }
    return raw.meta?.snapshot_id ?? null
  } catch {
    return null
  }
}

// Liveness for the container HEALTHCHECK: ok plus the snapshot the site is
// serving (NPL study; the ratewatch fixture id is the fallback when the NPL
// snapshot has not been generated yet).
export function GET() {
  const npl = nplSnapshotId()
  return Response.json({ ok: true, snapshot_id: npl ?? ratewatchFixture.meta.snapshot_id, product: npl ? "npl" : "ratewatch" })
}
