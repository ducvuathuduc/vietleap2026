import { NextResponse } from "next/server"
import { computeSegments } from "@/lib/engine/analyzer"
import { jsonError } from "@/lib/engine/http"
import { getDataset } from "@/lib/engine/store"

export async function GET(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    const ds = getDataset(ds_id)
    const { searchParams } = new URL(req.url)
    return NextResponse.json(computeSegments(ds, searchParams.get("by"), searchParams.get("metric")))
  } catch (e) {
    return jsonError(e)
  }
}
