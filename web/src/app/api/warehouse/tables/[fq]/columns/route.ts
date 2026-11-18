import { NextResponse } from "next/server"
import { getTableColumns } from "@/lib/engine/sql"
import { getAllDatasets } from "@/lib/engine/store"

export async function GET(_req: Request, context: { params: Promise<{ fq: string }> }) {
  const { fq } = await context.params
  return NextResponse.json(getTableColumns(getAllDatasets(), decodeURIComponent(fq)))
}
