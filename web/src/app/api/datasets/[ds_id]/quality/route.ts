import { NextResponse } from "next/server"
import { jsonError } from "@/lib/engine/http"
import { getDataset } from "@/lib/engine/store"

export async function GET(_req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    return NextResponse.json(getDataset(ds_id).quality)
  } catch (e) {
    return jsonError(e)
  }
}
