import seed from "../../../../seed/npl/snapshot.json" with { type: "json" }

// Keep container liveness independent of the upstream S3 connection.
export function GET() {
  return Response.json({ ok: true, snapshot_id: seed.meta.snapshot_id, product: "npl" })
}
