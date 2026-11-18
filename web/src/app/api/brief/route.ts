import { NextResponse } from "next/server"
import { jsonError } from "@/lib/engine/http"
import { analyzeBrief } from "@/lib/engine/store"

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { text?: string; dataset?: string | null }
    return NextResponse.json(analyzeBrief(String(body.text ?? ""), body.dataset ?? null))
  } catch (e) {
    return jsonError(e, 422)
  }
}
