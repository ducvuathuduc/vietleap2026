import { NextResponse } from "next/server"
import { jsonError } from "@/lib/engine/http"
import { getDatasetBrief } from "@/lib/engine/store"

export async function GET(_req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    return NextResponse.json(getDatasetBrief(ds_id))
  } catch (e) {
    return jsonError(e)
  }
}
