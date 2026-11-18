import { NextResponse } from "next/server"
import { listDatasets } from "@/lib/engine/store"

export function GET() {
  return NextResponse.json({ status: "ok", datasets: listDatasets().length })
}
