import { NextResponse } from "next/server"
import { loadPacks } from "@/lib/engine/brief"

export function GET() {
  return NextResponse.json(
    loadPacks().map((p) => ({
      id: p.id,
      title: p.title,
      sponsor: p.sponsor,
      domain: p.domain,
      kpis: p.kpis,
      decision_template: p.decision_template,
    }))
  )
}
