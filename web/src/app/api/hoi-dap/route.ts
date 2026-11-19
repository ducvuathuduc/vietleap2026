import {
  convertToModelMessages,
  createUIMessageStream,
  createUIMessageStreamResponse,
  isStepCount,
  streamText,
  tool,
  toUIMessageStream,
  type UIMessage,
} from "ai"
import { z } from "zod"

import { analystModel } from "@/lib/analyst/model"
import { rateLimited } from "@/lib/rate-limit"
import { loadMonitor } from "@/lib/monitor/load"
import {
  answerOffline,
  flaggedNumbers,
  getIndicator,
  getProvince,
  getRecommendations,
  getRules,
  getSector,
  listIndicators,
  monitorChatGate,
  qaSystemPrompt,
} from "@/lib/monitor/qa"
import type { Monitor } from "@/lib/monitor/types"

export const maxDuration = 120

const Body = z.object({
  messages: z.array(z.custom<UIMessage>((m) => typeof m === "object" && m !== null && "role" in m && "parts" in m)).min(1).max(40),
})

function lastUserText(messages: UIMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message.role === "user") {
      return message.parts
        .filter((part): part is { type: "text"; text: string } => part.type === "text" && typeof part.text === "string")
        .map((part) => part.text)
        .join(" ")
        .trim()
    }
  }
  return ""
}

function textChunks(text: string) {
  const id = crypto.randomUUID()
  return [
    { type: "text-start" as const, id },
    { type: "text-delta" as const, id, delta: text },
    { type: "text-end" as const, id },
  ]
}

function offlineResponse(text: string) {
  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      writer.write({ type: "start" })
      textChunks(text).forEach((chunk) => writer.write(chunk))
      writer.write({ type: "finish" })
    },
  })
  return createUIMessageStreamResponse({ stream })
}

function monitorTools(monitor: Monitor) {
  return {
    listIndicators: tool({
      description: "Liệt kê chỉ số đã xuất bản: tên, đơn vị, kỳ, giá trị mới nhất và nguồn.",
      inputSchema: z.object({}),
      execute: async () => ({ indicators: listIndicators(monitor) }),
    }),
    getIndicator: tool({
      description: "Một chỉ số theo id từ listIndicators: giá trị mới nhất, sparkline, định nghĩa và nguồn.",
      inputSchema: z.object({ id: z.string().min(1).max(120) }),
      execute: async ({ id }) => getIndicator(monitor, id) ?? { error: "Không có chỉ số này trong bản đã xuất bản." },
    }),
    getSector: tool({
      description: "Một ngành theo key public_finance, fdi, banking, capital_market hoặc real_estate: các thẻ số và tóm tắt bảng.",
      inputSchema: z.object({ key: z.string().min(1).max(40) }),
      execute: async ({ key }) => getSector(monitor, key) ?? { error: "Không có ngành này trong bản đã xuất bản." },
    }),
    getProvince: tool({
      description: "Một tỉnh theo code hoặc tên, hoặc bảng xếp hạng tỉnh theo metric (id chỉ số). Trích nguồn bằng sources[].publisher.",
      inputSchema: z.object({
        code: z.string().min(1).max(80).optional(),
        metric: z.string().min(1).max(120).optional(),
      }),
      execute: async ({ code, metric }) => getProvince(monitor, { code, metric }) ?? { error: "Không có tỉnh hoặc chỉ số này trong bản đã xuất bản." },
    }),
    getRecommendations: tool({
      description: "Khuyến nghị đã xuất bản: bằng chứng, hàm ý, hành động, cơ quan và hạn.",
      inputSchema: z.object({}),
      execute: async () => ({ recommendations: getRecommendations(monitor) }),
    }),
    getRules: tool({
      description: "Quy tắc nghiệp vụ đã xuất bản: công thức, ngưỡng và trạng thái kích hoạt.",
      inputSchema: z.object({}),
      execute: async () => ({ rules: getRules(monitor) }),
    }),
  }
}

function guarded(stream: ReadableStream<unknown>) {
  const toolOutputs: unknown[] = []
  let assistantText = ""
  let guardEmitted = false
  return stream.pipeThrough(
    new TransformStream({
      transform(chunk, controller) {
        const part = chunk as Record<string, unknown>
        if (part.type === "text-delta" && typeof part.delta === "string") assistantText += part.delta
        else if (part.type === "tool-output-available") toolOutputs.push(part.output)
        else if (part.type === "finish" && !guardEmitted) {
          guardEmitted = true
          const bad = flaggedNumbers(assistantText, toolOutputs)
          if (bad.length > 0) {
            const id = crypto.randomUUID()
            controller.enqueue({ type: "text-start", id } as never)
            controller.enqueue({ type: "text-delta", id, delta: `\n\nSố chưa kiểm chứng: ${bad.join(", ")}` } as never)
            controller.enqueue({ type: "text-end", id } as never)
          }
        }
        controller.enqueue(chunk)
      },
    })
  )
}

export async function POST(req: Request) {
  const denied = monitorChatGate()
  if (denied) return denied
  const limited = rateLimited(req)
  if (limited) return limited

  let body: z.infer<typeof Body>
  try {
    body = Body.parse(await req.json())
  } catch (error) {
    const msg = error instanceof z.ZodError ? error.issues.map((issue) => `${issue.path.join(".") || "body"}: ${issue.message}`).join("; ") : (error as Error).message
    return Response.json({ detail: `Yêu cầu không hợp lệ: ${msg}` }, { status: 400 })
  }

  let monitor: Monitor | null
  try {
    monitor = loadMonitor()
  } catch {
    return Response.json({ detail: "Không tải được bản số liệu." }, { status: 500 })
  }

  const userText = lastUserText(body.messages)
  if (!monitor) return offlineResponse("Chưa có bản số liệu đã xuất bản.")
  const llm = analystModel()
  if (!llm) return offlineResponse(answerOffline(monitor, userText))

  let modelMessages: Awaited<ReturnType<typeof convertToModelMessages>>
  try {
    modelMessages = await convertToModelMessages(body.messages)
  } catch (error) {
    return Response.json({ detail: `Yêu cầu không hợp lệ: ${(error as Error).message}` }, { status: 400 })
  }

  const result = streamText({
    model: llm.model,
    system: qaSystemPrompt(),
    messages: modelMessages,
    tools: monitorTools(monitor),
    stopWhen: isStepCount(6),
    temperature: 0.2,
  })
  return createUIMessageStreamResponse({ stream: guarded(toUIMessageStream({ stream: result.stream })) })
}
