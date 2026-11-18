import { NextResponse } from "next/server"
import { listWarehouseTables } from "@/lib/engine/sql"
import { getAllDatasets } from "@/lib/engine/store"

export function GET() {
  return NextResponse.json(listWarehouseTables(getAllDatasets()))
}
