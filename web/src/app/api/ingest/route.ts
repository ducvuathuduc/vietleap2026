import { NextResponse } from "next/server"
import type { IngestRequest } from "@/lib/api/types"
import { jsonError } from "@/lib/engine/http"
import { createIngestJob } from "@/lib/engine/store"

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as IngestRequest
    if (!body.dataset?.trim() || !Array.isArray(body.sources) || body.sources.length === 0) {
      return NextResponse.json({ detail: "dataset and at least one source are required" }, { status: 422 })
    }
    return NextResponse.json(createIngestJob(body), { status: 202 })
  } catch (e) {
    return jsonError(e, 422)
  }
}
