import { NextResponse } from "next/server"
import { executeReadOnlySql } from "@/lib/engine/sql"
import { getAllDatasets } from "@/lib/engine/store"

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { query?: string; limit?: number }
    const query = String(body.query ?? "")
    const limit = Math.min(5000, Math.max(1, Number(body.limit ?? 500)))
    return NextResponse.json(executeReadOnlySql(getAllDatasets(), query, limit))
  } catch (e) {
    const msg = (e as Error).message
    const status = msg.includes("chỉ đọc") ? 403 : 400
    return NextResponse.json({ detail: msg }, { status })
  }
}
