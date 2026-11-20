import { connection } from "next/server"
import { readSnapshotSelection } from "../../../lib/npl/snapshot-source.ts"

export async function GET() {
  await connection()
  const { snapshot, source } = await readSnapshotSelection()
  return Response.json({
    ok: true,
    snapshot_id: snapshot.meta.snapshot_id,
    generated_at: snapshot.meta.generated_at,
    source,
    product: "npl",
  }, { headers: { "Cache-Control": "no-store" } })
}
