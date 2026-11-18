import { NextResponse } from "next/server"
import { z } from "zod"

import { jsonError } from "@/lib/engine/http"
import { deleteScenario, listScenarios, saveScenario } from "@/lib/engine/store"

const ChangeSchema = z
  .object({
    feature: z.string().min(1).max(200),
    pct_change: z.number().min(-30).max(30),
  })
  .strict()

const SaveScenarioSchema = z
  .object({
    name: z.string().trim().min(1).max(60),
    request: z
      .object({
        changes: z
          .array(ChangeSchema)
          .min(1)
          .max(5)
          .refine((arr) => new Set(arr.map((c) => c.feature)).size === arr.length, "Các biến trong kịch bản phải duy nhất"),
        target: z.string().nullish(),
      })
      .strict(),
  })
  .strict()

export async function GET(_req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    return NextResponse.json(listScenarios(ds_id))
  } catch (e) {
    return jsonError(e, 404)
  }
}

export async function POST(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    const parsed = SaveScenarioSchema.safeParse(await req.json())
    if (!parsed.success) {
      return NextResponse.json(
        { detail: parsed.error.issues.map((i) => `${i.path.join(".") || "body"}: ${i.message}`).join("; ") },
        { status: 422 }
      )
    }
    return NextResponse.json(saveScenario(ds_id, parsed.data.name, parsed.data.request))
  } catch (e) {
    return jsonError(e, 422)
  }
}

export async function DELETE(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  try {
    const { ds_id } = await context.params
    const name = new URL(req.url).searchParams.get("name") ?? ""
    if (!name.trim()) {
      return NextResponse.json({ detail: "Thiếu tham số name" }, { status: 422 })
    }
    return NextResponse.json(deleteScenario(ds_id, name))
  } catch (e) {
    return jsonError(e, 404)
  }
}
