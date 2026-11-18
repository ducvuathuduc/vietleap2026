import { NextResponse } from "next/server"
import { computeWhatIfCurve } from "@/lib/engine/analyzer"
import { jsonError } from "@/lib/engine/http"
import { getDataset } from "@/lib/engine/store"

export async function GET(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    const { searchParams } = new URL(req.url)
    const feature = searchParams.get("feature") ?? ""
    const ds = getDataset(ds_id)
    return NextResponse.json(computeWhatIfCurve(ds, feature))
  } catch (e) {
    return jsonError(e, 422)
  }
}
