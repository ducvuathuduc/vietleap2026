import { NextResponse } from "next/server"
import { guardApi } from "@/lib/api-guard"
import { jsonError } from "@/lib/engine/http"
import { analyzeBrief } from "@/lib/engine/store"

export async function POST(req: Request) {
  const denied = guardApi(req)
  if (denied) return denied
  try {
    const body = (await req.json()) as { text?: string; dataset?: string | null }
    return NextResponse.json(analyzeBrief(String(body.text ?? ""), body.dataset ?? null))
  } catch (e) {
    return jsonError(e, 422)
  }
}
