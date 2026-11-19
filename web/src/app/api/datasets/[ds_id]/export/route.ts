import { NextResponse } from "next/server"
import { guardApi } from "@/lib/api-guard"
import { jsonError } from "@/lib/engine/http"
import { startExportJob } from "@/lib/engine/store"

export async function POST(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  const denied = guardApi(req)
  if (denied) return denied
  try {
    const { ds_id } = await context.params
    return NextResponse.json(startExportJob(ds_id), { status: 202 })
  } catch (e) {
    return jsonError(e)
  }
}
