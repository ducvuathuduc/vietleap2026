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

import { guardApi } from "@/lib/api-guard"
import { rateLimited } from "@/lib/rate-limit"

import type { Insight, ModelsResponse, PipelineSummary, QualityResponse, Recommendation, SqlResult } from "@/lib/api/types"
import { backend, compact, dsPath, post } from "@/lib/analyst/backend"
import { explainOffline, sourcesFor, type OfflineSources } from "@/lib/analyst/explain"
import { analystModel } from "@/lib/analyst/model"
import { isSqlLikeQuestion, planOfflineSql } from "@/lib/analyst/nl2sql-offline"
import { systemPrompt } from "@/lib/analyst/prompt"
import { chartFromResult } from "@/lib/analyst/sql-chart"
import { sqlTruthNumbers, ungroundedNumbers } from "@/lib/analyst/story"
import { makeTools, topInsights } from "@/lib/analyst/tools"
import type { InsightContext } from "@/lib/insight-target"

export const maxDuration = 120

const Body = z.object({
  messages: z.array(z.custom<UIMessage>((m) => typeof m === "object" && m !== null && "role" in m && "parts" in m)).min(1).max(100),
  datasetId: z.string().regex(/^[\w.-]{1,80}$/).nullish(),
  // element inspected in "Hỏi AI" mode (data-insight-target)
  context: z
    .object({
      kind: z.enum(["kpi", "chart", "insight", "table-row", "segment", "driver", "whatif", "pipeline-stage", "quality", "model", "decision", "join"]),
      id: z.string().min(1).max(200),
      label: z.string().max(300),
      data: z.unknown().optional().refine((d) => d === undefined || JSON.stringify(d).length <= 8000, "context.data quá lớn (> 8000 ký tự)"),
    })
    .nullish(),
})

/** Mode probe for the analyst page (no secrets returned). */
export function GET(req: Request) {
  const denied = guardApi(req)
  if (denied) return denied
  const m = analystModel()
  return Response.json({ mode: m ? "llm" : "offline", model: m?.label ?? null })
}

function lastUserText(messages: UIMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]
    if (m.role === "user") {
      return m.parts
        .filter((p): p is { type: "text"; text: string } => p.type === "text" && typeof p.text === "string")
        .map((p) => p.text)
        .join(" ")
        .trim()
    }
  }
  return ""
}

export async function POST(req: Request) {
  const denied = guardApi(req)
  if (denied) return denied
  const limited = rateLimited(req)
  if (limited) return limited
  let body: z.infer<typeof Body>
  try {
    body = Body.parse(await req.json())
  } catch (e) {
    const msg = e instanceof z.ZodError ? e.issues.map((i) => `${i.path.join(".") || "body"}: ${i.message}`).join("; ") : (e as Error).message
    return Response.json({ detail: `Yêu cầu không hợp lệ: ${msg}` }, { status: 400 })
  }
  const datasetId = body.datasetId ?? null
  const context = (body.context ?? null) as InsightContext | null
  const llm = analystModel()
  const userText = lastUserText(body.messages)
  if (!llm) return context && datasetId ? offlineExplain(datasetId, context) : offline(datasetId, userText)

  const result = streamText({
    model: llm.model,
    system: systemPrompt(datasetId, context),
    messages: await convertToModelMessages(body.messages),
    tools: makeTools(datasetId),
    stopWhen: isStepCount(8),
    temperature: 0.2,
  })

  const rawStream = toUIMessageStream({ stream: result.stream })
  const toolOutputs: unknown[] = []
  const sqlQueries: string[] = []
  let assistantText = ""
  let guardEmitted = false

  const checkedStream = rawStream.pipeThrough(
    new TransformStream({
      transform(chunk, controller) {
        const c = chunk as Record<string, unknown>
        if (c.type === "text-delta" && typeof c.delta === "string") {
          assistantText += c.delta
        } else if (c.type === "tool-input-available" && c.toolName === "runSql") {
          const inp = c.input as { query?: unknown } | undefined
          if (typeof inp?.query === "string") sqlQueries.push(inp.query)
        } else if (c.type === "tool-output-available") {
          toolOutputs.push(c.output)
        } else if (c.type === "finish" && !guardEmitted) {
          guardEmitted = true
          const bad = ungroundedNumbers(assistantText, sqlTruthNumbers(toolOutputs, sqlQueries))
          if (bad.length > 0) {
            const gid = crypto.randomUUID()
            controller.enqueue({ type: "text-start", id: gid } as never)
            controller.enqueue({ type: "text-delta", id: gid, delta: `\n\n⚠ Số chưa kiểm chứng: ${bad.join(", ")}` } as never)
            controller.enqueue({ type: "text-end", id: gid } as never)
          }
        }
        controller.enqueue(chunk)
      },
    })
  )

  return createUIMessageStreamResponse({ stream: checkedStream })
}

function textChunks(text: string) {
  const id = crypto.randomUUID()
  return [
    { type: "text-start" as const, id },
    { type: "text-delta" as const, id, delta: text },
    { type: "text-end" as const, id },
  ]
}

/** No LLM key + an inspected element: deterministic explanation from the engine resources that element needs. */
function offlineExplain(datasetId: string, context: InsightContext) {
  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      writer.write({ type: "start" })
      const need = sourcesFor(context.kind)
      const toolCallId = crypto.randomUUID()
      writer.write({ type: "tool-input-available", toolCallId, toolName: `get${need[0][0].toUpperCase()}${need[0].slice(1)}`, input: { target: `${context.kind}:${context.id}` } })
      try {
        const src: OfflineSources = {}
        const base = dsPath(datasetId)
        if (need.includes("insights")) src.insights = await backend<{ insights: Insight[]; recommendations: Recommendation[] }>(`${base}/insights`)
        if (need.includes("pipeline")) src.pipeline = await backend<PipelineSummary>(`${base}/pipeline`)
        if (need.includes("quality")) src.quality = await backend<QualityResponse>(`${base}/quality`)
        if (need.includes("models")) src.models = await backend<ModelsResponse>(`${base}/models`)
        const out = explainOffline(context, src)
        writer.write({ type: "tool-output-available", toolCallId, output: out.output })
        textChunks(out.text).forEach((c) => writer.write(c))
      } catch (e) {
        writer.write({ type: "tool-output-error", toolCallId, errorText: (e as Error).message })
        textChunks(`Chế độ offline: chưa lấy được dữ liệu để giải thích (${(e as Error).message}).`).forEach((c) => writer.write(c))
      }
      writer.write({ type: "finish" })
    },
  })
  return createUIMessageStreamResponse({ stream })
}

/** No LLM key: try offline NL->SQL templates when question asks for rankings/trends/comparisons, else top insights. */
function offline(datasetId: string | null, userText = "") {
  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      writer.write({ type: "start" })
      const say = (text: string) => textChunks(text).forEach((c) => writer.write(c))
      if (!datasetId) {
        say("Chế độ offline (chưa cấu hình GROQ_API_KEY hoặc OPENAI_COMPATIBLE_*). Hãy chọn một dataset ở thanh trên cùng để xem insight hàng đầu.")
        writer.write({ type: "finish" })
        return
      }

      if (userText && isSqlLikeQuestion(userText)) {
        try {
          const models = await backend<ModelsResponse>(`${dsPath(datasetId)}/models`)
          const obtTable = models.models.obt?.tables?.[0] ?? `gold.obt_${datasetId}`
          const planned = planOfflineSql(userText, models.column_plan, obtTable)
          if (planned) {
            const sqlCallId = crypto.randomUUID()
            writer.write({ type: "tool-input-available", toolCallId: sqlCallId, toolName: "runSql", input: { query: planned.sql } })
            try {
              const res = await backend<SqlResult>("/api/sql", post({ query: planned.sql, limit: 200 }))
              const chart = chartFromResult(res.columns, res.rows)
              const output = compact({
                query_id: 1,
                query: planned.sql,
                columns: res.columns,
                rows: res.rows,
                row_count: res.row_count,
                chart,
                offline_template: true,
              })
              writer.write({ type: "tool-output-available", toolCallId: sqlCallId, output })
              if (res.row_count === 0) {
                say(`${planned.explanation}\n\nKết quả không có dòng nào (Nguồn: truy vấn #1 · chế độ offline).`)
              } else {
                const topLines = res.rows.slice(0, 5).map((row, idx) => `${idx + 1}. ${row.map((v) => (v === null ? "–" : String(v))).join(" · ")}`)
                say(
                  [
                    `${planned.explanation} (mô tả, chưa kiểm định — Nguồn: truy vấn #1 · chế độ offline):`,
                    "",
                    ...topLines,
                  ].join("\n")
                )
              }
              writer.write({ type: "finish" })
              return
            } catch (sqlErr) {
              writer.write({ type: "tool-output-error", toolCallId: sqlCallId, errorText: (sqlErr as Error).message })
              say(`Truy vấn mẫu offline gặp lỗi (${(sqlErr as Error).message}) — hãy mở SQL Explorer để chỉnh sửa.`)
              writer.write({ type: "finish" })
              return
            }
          } else {
            say("Không khớp cột nào — hãy dùng SQL Explorer để viết truy vấn tuỳ chỉnh trên các bảng bronze/silver/gold.")
            writer.write({ type: "finish" })
            return
          }
        } catch {
          /* fall through to top insights */
        }
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
