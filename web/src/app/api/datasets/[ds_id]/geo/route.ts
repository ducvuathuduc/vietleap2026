import { NextRequest } from "next/server"
import { computeGeo } from "@/lib/engine/analyzer"
import { getDataset } from "@/lib/engine/store"

const VALID_AGG = new Set(["median", "mean", "sum", "count"])

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ ds_id: string }> }
) {
  try {
    const { ds_id } = await context.params
    const ds = getDataset(decodeURIComponent(ds_id))
    const metric = req.nextUrl.searchParams.get("metric")
    const aggParam = req.nextUrl.searchParams.get("agg") || "median"
    if (!VALID_AGG.has(aggParam)) {
      return Response.json(
        { detail: "agg phải là một trong median|mean|sum|count." },
        { status: 422 }
      )
    }
    return Response.json(
      computeGeo(ds, metric, aggParam as "median" | "mean" | "sum" | "count")
    )
  } catch (e) {
    const err = e as Error & { status?: number }
    return Response.json({ detail: err.message }, { status: err.status ?? 500 })
  }
}
