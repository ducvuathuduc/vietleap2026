import { NextResponse } from "next/server"
import { loadBriefSamples } from "@/lib/engine/brief"

export function GET() {
  return NextResponse.json(loadBriefSamples())
}
