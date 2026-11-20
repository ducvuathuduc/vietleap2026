// NPL assistant chat route: streaming UI messages from the ToolLoopAgent.
// Protections: per-IP rate limit, request size limit, PII filter on the prompt
// (private data never reaches the model, a log or a trace), output number
// guard, structured log line without prompt text, generic VI/EN error with a
// request id — never a stack trace.
import { createAgentUIStream, createUIMessageStream, createUIMessageStreamResponse, type UIMessageChunk } from "ai"
import { propagateAttributes } from "@langfuse/tracing"
import { z } from "zod"

import { makeNplAgent } from "@/lib/npl/agent/agent"
import { guardNplStream, investmentAdviceNotice, messagesForNplModel, nplMessageText } from "@/lib/npl/agent/answer-policy"
import { detectLang, type Lang } from "@/lib/npl/agent/lang"
import { loadNplSnapshot } from "@/lib/npl/agent/snapshot"
import { answerSnapshot, type SnapshotAnswer } from "@/lib/npl/agent/snapshot-answers"
import { filterInput } from "@/lib/llm/guards"
import { createAssistantModel } from "@/lib/llm/model"
import { rateLimited } from "@/lib/rate-limit"

export const maxDuration = 120

const MAX_BODY_BYTES = 20_000
const MAX_MESSAGES = 30

const Body = z.object({
  // UIMessage shape: createAgentUIStream validates id/role/parts strictly.
  messages: z
    .array(
      z.object({
        id: z.string().min(1),
        role: z.enum(["user", "assistant"]),
        parts: z.array(z.custom<unknown>((p) => typeof p === "object" && p !== null && "type" in p)),
      }),
    )
    .min(1)
    .max(MAX_MESSAGES),
  // client-generated session id (uuid) for Langfuse session grouping — never a name or phone
  sessionId: z.string().uuid().nullish(),
})

function noticeStream(notice: string, evidence?: SnapshotAnswer, lang: Lang = "vi"): Response {
  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      writer.write({ type: "start" })
      const id = crypto.randomUUID()
      if (evidence) {
        writer.write({ type: "tool-input-available", toolCallId: id, toolName: evidence.name, input: evidence.input })
        writer.write({ type: "tool-output-available", toolCallId: id, output: evidence.output })
      }
      writer.write({ type: "text-start", id })
      writer.write({ type: "text-delta", id, delta: notice })
      writer.write({ type: "text-end", id })
      writer.write({ type: "finish" })
    },
  })
  return createUIMessageStreamResponse({ stream: evidence ? stream.pipeThrough(guardNplStream(lang)) : stream })
}

/** One structured line per request. No prompt text, no personal data, no keys. */
function logRequest(entry: LogEntry): void {
  if (process.env.NODE_ENV === "production") return
  console.log(JSON.stringify({ route: "/api/npl/chat", ...entry }))
}

interface LogEntry {
  status: number
  provider: string
  model: string | null
  session: string | null
  tools: string[]
  flagged: number
  ms: number
  rejected: string | null
}

export async function POST(req: Request) {
  const requestId = crypto.randomUUID()
  try {
    const limited = rateLimited(req)
    if (limited) return limited

    const declared = Number(req.headers.get("content-length") ?? "0")
    if (Number.isFinite(declared) && declared > MAX_BODY_BYTES) {
      return Response.json({ detail: "Yêu cầu quá lớn.", request_id: requestId }, { status: 413 })
    }
    const raw = await req.text()
    if (raw.length > MAX_BODY_BYTES) {
      return Response.json({ detail: "Yêu cầu quá lớn.", request_id: requestId }, { status: 413 })
    }

    let body: z.infer<typeof Body>
    try {
      body = Body.parse(JSON.parse(raw))
    } catch {
      return Response.json({ detail: "Yêu cầu không hợp lệ. / Invalid request.", request_id: requestId }, { status: 400 })
    }

    const log: LogEntry = { status: 200, provider: "none", model: null, session: body.sessionId?.slice(0, 8) ?? null, tools: [], flagged: 0, ms: 0, rejected: null }

    const question = nplMessageText(body.messages.findLast((message) => message.role === "user")?.parts ?? [])
    const lang = detectLang(question)
    // Private data never reaches the model, a log or a trace.
    const pii = filterInput(question)
    if (!pii.ok) {
      log.rejected = "pii"
      logRequest(log)
      return noticeStream(lang === "vi"
        ? "Bạn vui lòng xoá thông tin cá nhân rồi hỏi lại. Trợ lý chỉ cần câu hỏi về số liệu nghiên cứu."
        : "Please remove the personal information and ask again. The assistant only needs your question about the study data.")
    }

    const refusal = investmentAdviceNotice(question, lang)
    if (refusal) {
      log.rejected = "investment_advice"
      logRequest(log)
      return noticeStream(refusal)
    }

    const snapshot = await loadNplSnapshot()
    const known = answerSnapshot(snapshot, question, lang)
    if (known) {
      log.tools.push(known.name)
      logRequest(log)
      return noticeStream(known.text, known, lang)
    }
    const unavailable = lang === "vi" ? "Trợ lý hiện chưa khả dụng. Bạn có thể xem số liệu trực tiếp trên các trang nghiên cứu." : "The assistant is temporarily unavailable. You can find the data on the study pages."
    const llm = createAssistantModel(process.env, body.sessionId)
    if (!llm) {
      log.rejected = "offline"
      logRequest(log)
      return noticeStream(unavailable)
    }

    const agent = makeNplAgent({ snapshot, model: llm.model, sessionId: body.sessionId, lang })
    if (!agent) {
      log.rejected = "offline"
      logRequest(log)
      return noticeStream(unavailable)
    }

    const started = Date.now()
    const stream = await propagateAttributes(
      {
        sessionId: body.sessionId ?? undefined,
        tags: ["npl", "assistant"],
        metadata: { snapshot_id: snapshot.meta.snapshot_id, provider: llm.provider, request_id: requestId },
      },
      () =>
        createAgentUIStream({
          agent,
          uiMessages: messagesForNplModel(body.messages),
          abortSignal: req.signal,
          // Mid-stream failures (model or tool) surface as this generic text, never a stack.
          onError: () => lang === "vi"
            ? "Trợ lý gặp lỗi tạm thời. Bạn vui lòng thử lại."
            : "The assistant hit a temporary error. Please try again.",
        }),
    )

    const guarded = stream
      .pipeThrough(
        new TransformStream<UIMessageChunk, UIMessageChunk>({
          transform(chunk, controller) {
            if (chunk.type === "tool-input-available" && typeof chunk.toolName === "string") log.tools.push(chunk.toolName)
            controller.enqueue(chunk)
          },
        }),
      )
      .pipeThrough(guardNplStream(lang))
      .pipeThrough(
        new TransformStream<UIMessageChunk, UIMessageChunk>({
          transform(chunk, controller) {
            if (chunk.type === "data-guard") {
              const flagged = (chunk.data as { flagged?: string[] } | undefined)?.flagged ?? []
              log.flagged = flagged.length
            }
            controller.enqueue(chunk)
          },
          flush() {
            log.ms = Date.now() - started
            logRequest(log)
          },
        }),
      )

    return createUIMessageStreamResponse({ stream: guarded })
  } catch (e) {
    // Pre-stream failure: generic VI/EN message with the request id, no stack.
    console.error(`npl chat ${requestId.slice(0, 8)} failed:`, e instanceof Error ? e.name : "unknown")
    return Response.json(
      {
        detail: `Trợ lý gặp lỗi tạm thời — vui lòng thử lại. / The assistant hit a temporary error — please try again. (mã ${requestId.slice(0, 8)})`,
        request_id: requestId,
      },
      { status: 500 },
    )
  }
}
