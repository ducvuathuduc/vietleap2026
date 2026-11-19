import { NextResponse } from "next/server"
import { guardApi } from "@/lib/api-guard"
import { getTableColumns } from "@/lib/engine/sql"
import { getAllDatasets } from "@/lib/engine/store"

export async function GET(req: Request, context: { params: Promise<{ fq: string }> }) {
  const denied = guardApi(req)
  if (denied) return denied
  const { fq } = await context.params
  return NextResponse.json(getTableColumns(getAllDatasets(), decodeURIComponent(fq)))
}
