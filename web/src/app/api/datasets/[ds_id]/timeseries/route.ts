import { NextResponse } from "next/server"
import { computeTimeSeries } from "@/lib/engine/analyzer"
import { jsonError } from "@/lib/engine/http"
import { getDataset } from "@/lib/engine/store"

export async function GET(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    const ds = getDataset(ds_id)
    const { searchParams } = new URL(req.url)
    const metric = searchParams.get("metric") ?? ds.detail.meta.target
    const agg = (searchParams.get("agg") as "median" | "mean" | "sum" | "count" | null) ?? "median"
    const freq = searchParams.get("freq")
    const group = searchParams.get("group")
    return NextResponse.json(computeTimeSeries(ds.silverRows, ds.detail.meta.time_col, metric, agg, freq, group))
  } catch (e) {
    return jsonError(e)
  }
}
