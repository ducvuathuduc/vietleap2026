import {
  convertToModelMessages,
  createUIMessageStream,
  createUIMessageStreamResponse,
  isStepCount,
  streamText,
  toUIMessageStream,
  type UIMessage,
} from "ai"
import { z } from "zod"

import type { Insight, Recommendation } from "@/lib/api/types"
import { backend, dsPath } from "@/lib/analyst/backend"
import { analystModel } from "@/lib/analyst/model"
import { systemPrompt } from "@/lib/analyst/prompt"
import { makeTools, topInsights } from "@/lib/analyst/tools"

export const maxDuration = 120

const Body = z.object({
  messages: z.array(z.custom<UIMessage>((m) => typeof m === "object" && m !== null && "role" in m && "parts" in m)).min(1).max(100),
  datasetId: z.string().regex(/^[\w.-]{1,80}$/).nullish(),
})

/** Mode probe for the analyst page (no secrets returned). */
export function GET() {
  const m = analystModel()
  return Response.json({ mode: m ? "llm" : "offline", model: m?.label ?? null })
}

export async function POST(req: Request) {
  let body: z.infer<typeof Body>
  try {
    body = Body.parse(await req.json())
  } catch (e) {
    return Response.json({ detail: `Yêu cầu không hợp lệ: ${(e as Error).message}` }, { status: 400 })
  }
  const datasetId = body.datasetId ?? null
  const llm = analystModel()
  if (!llm) return offline(datasetId)

  const result = streamText({
    model: llm.model,
    system: systemPrompt(datasetId),
    messages: await convertToModelMessages(body.messages),
    tools: makeTools(datasetId),
    stopWhen: isStepCount(8),
    temperature: 0.2,
  })
  return createUIMessageStreamResponse({ stream: toUIMessageStream({ stream: result.stream }) })
}

/** No LLM key: answer with the top-ranked insights straight from the API, shown as a getInsights tool call. Never errors. */
function offline(datasetId: string | null) {
  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      writer.write({ type: "start" })
      const say = (text: string) => {
        const id = crypto.randomUUID()
        writer.write({ type: "text-start", id })
        writer.write({ type: "text-delta", id, delta: text })
        writer.write({ type: "text-end", id })
      }
      if (!datasetId) {
        say("Chế độ offline (chưa cấu hình GROQ_API_KEY hoặc OPENAI_COMPATIBLE_*). Hãy chọn một dataset ở thanh trên cùng để xem insight hàng đầu.")
        writer.write({ type: "finish" })
        return
      }
      const toolCallId = crypto.randomUUID()
      writer.write({ type: "tool-input-available", toolCallId, toolName: "getInsights", input: { top: 3 } })
      try {
        const r = await backend<{ insights: Insight[]; recommendations: Recommendation[] }>(`${dsPath(datasetId)}/insights`)
        const top = topInsights(r.insights, 3)
        writer.write({ type: "tool-output-available", toolCallId, output: { insights: top } })
        if (top.length === 0) {
          say("Chế độ offline: engine chưa tìm thấy insight có ý nghĩa thống kê cho dataset này.")
        } else {
          const lines = top.map((i) => `${i.rank}. **${i.title}** — ${i.finding}${i.caveat ? `\n   Lưu ý: ${i.caveat}` : ""}`)
          const rec = r.recommendations[0]
          say(
            [
              "Chế độ offline (chưa có khoá LLM) — đây là các insight xếp hạng cao nhất do engine tính:",
              "",
              ...lines,
              ...(rec ? ["", `Khuyến nghị hàng đầu: ${rec.now_what_vi}`] : []),
              "",
              "Nguồn: getInsights (results.json của engine). Đây là quan hệ liên đới, không phải nhân quả.",
            ].join("\n")
          )
        }
      } catch (e) {
        writer.write({ type: "tool-output-error", toolCallId, errorText: (e as Error).message })
        say(`Chế độ offline: chưa lấy được insight (${(e as Error).message}).`)
      }
      writer.write({ type: "finish" })
    },
  })
  return createUIMessageStreamResponse({ stream })
}
