import { NextResponse } from "next/server"
import { computeWhatIf } from "@/lib/engine/analyzer"
import { jsonError } from "@/lib/engine/http"
import { getDataset } from "@/lib/engine/store"

export async function POST(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    const body = (await req.json()) as { feature?: string; pct_change?: number }
    const ds = getDataset(ds_id)
    return NextResponse.json(computeWhatIf(ds, String(body.feature ?? ""), Number(body.pct_change ?? 0)))
  } catch (e) {
    return jsonError(e, 422)
  }
}
