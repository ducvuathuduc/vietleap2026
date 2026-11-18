import { NextResponse } from "next/server"
import { jsonError } from "@/lib/engine/http"
import { getDatasetRows } from "@/lib/engine/store"

export async function GET(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    const { searchParams } = new URL(req.url)
    return NextResponse.json(
      getDatasetRows(ds_id, {
        page: Number(searchParams.get("page") ?? 1),
        page_size: Number(searchParams.get("page_size") ?? 25),
        sort: searchParams.get("sort"),
        desc: searchParams.get("desc") === "true",
        q: searchParams.get("q"),
        filter_col: searchParams.get("filter_col"),
        filter_val: searchParams.get("filter_val"),
      })
    )
  } catch (e) {
    return jsonError(e)
  }
}
