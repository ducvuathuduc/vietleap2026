import { NextResponse } from "next/server"
import { guardApi } from "@/lib/api-guard"
import { listWarehouseTables } from "@/lib/engine/sql"
import { getAllDatasets } from "@/lib/engine/store"

export function GET(req: Request) {
  const denied = guardApi(req)
  if (denied) return denied
  return NextResponse.json(listWarehouseTables(getAllDatasets()))
}
