import { NextResponse } from "next/server"
import { jsonError } from "@/lib/engine/http"
import { getIngestJob } from "@/lib/engine/store"

export async function GET(_req: Request, context: { params: Promise<{ job_id: string }> }) {
  try {
    const { job_id } = await context.params
    return NextResponse.json(getIngestJob(job_id))
  } catch (e) {
    return jsonError(e)
  }
}
