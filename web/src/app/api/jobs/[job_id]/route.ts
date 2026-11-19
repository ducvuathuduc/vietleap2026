import { NextResponse } from "next/server"
import { guardApi } from "@/lib/api-guard"
import { jsonError } from "@/lib/engine/http"
import { getJob } from "@/lib/engine/store"

export async function GET(req: Request, context: { params: Promise<{ job_id: string }> }) {
  const denied = guardApi(req)
  if (denied) return denied
  try {
    const { job_id } = await context.params
    return NextResponse.json(getJob(job_id))
  } catch (e) {
    return jsonError(e)
  }
}
