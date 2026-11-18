import { NextResponse } from "next/server"
import { z } from "zod"

import { computeWhatIfMulti } from "@/lib/engine/analyzer"
import { jsonError } from "@/lib/engine/http"
import { getDataset } from "@/lib/engine/store"
import { clientKey, createRateLimiter } from "@/lib/rate-limit"

const scenarioLimiter = createRateLimiter(60)

const ChangeSchema = z
  .object({
    feature: z.string().min(1).max(200),
    pct_change: z.number().min(-30).max(30),
  })
  .strict()

const ScenarioReqSchema = z
  .object({
    changes: z
      .array(ChangeSchema)
      .min(1)
      .max(5)
      .refine((arr) => new Set(arr.map((c) => c.feature)).size === arr.length, "Các biến trong kịch bản phải duy nhất"),
    target: z.string().nullish(),
  })
  .strict()

export async function POST(req: Request, context: { params: Promise<{ ds_id: string }> }) {
  const rl = scenarioLimiter(clientKey(req))
  if (!rl.ok) {
    return NextResponse.json(
      { detail: "Quá giới hạn yêu cầu what-if — vui lòng đợi giây lát." },
      { status: 429, headers: { "Retry-After": String(rl.retryAfterS) } }
    )
  }
  try {
    const { ds_id } = await context.params
    const parsed = ScenarioReqSchema.safeParse(await req.json())
    if (!parsed.success) {
      return NextResponse.json(
        { detail: parsed.error.issues.map((i) => `${i.path.join(".") || "body"}: ${i.message}`).join("; ") },
        { status: 422 }
      )
    }
    const ds = getDataset(ds_id)
    return NextResponse.json(computeWhatIfMulti(ds, parsed.data.changes, parsed.data.target ?? null))
  } catch (e) {
    return jsonError(e, 422)
  }
}
