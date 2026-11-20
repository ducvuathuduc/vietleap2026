// RateWatch AI chat route: streaming UI messages from the ToolLoopAgent.
// Protections: per-IP rate limit, request size limit, PII filter on the prompt
// (private data never reaches the model or a trace), output number guard
// (every number in the answer comes from a tool result), structured server log
// line per request without prompt text, no stack traces to the client.
import {
  createAgentUIStream,
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
  type UIMessageChunk,
} from "ai"
import { propagateAttributes } from "@langfuse/tracing"
import { z } from "zod"

import { rateLimited } from "@/lib/rate-limit"
import { loadSnapshot } from "@/lib/ratewatch/load"

import { makeRatewatchAgent } from "@/lib/ratewatch/agent/agent"
import { loadRepoEnv } from "@/lib/ratewatch/agent/env"
import { filterInput, guardTextStream } from "@/lib/ratewatch/agent/guards"
import { ratewatchModel } from "@/lib/ratewatch/agent/model"

export const maxDuration = 120

const MAX_BODY_BYTES = 20_000
const MAX_MESSAGES = 30

const Body = z.object({
  // UIMessage shape: createAgentUIStream validates id/role/parts strictly.
  messages: z
    .array(
      z.object({
        id: z.string().min(1),
        role: z.string(),
        parts: z.array(z.custom<unknown>((p) => typeof p === "object" && p !== null && "type" in p)),
      }),
    )
    .min(1)
    .max(MAX_MESSAGES),
  // client-generated session id (uuid) for Langfuse session grouping — never a name or phone
  sessionId: z.string().uuid().nullish(),
})

let envLoaded = false

/** Mode probe for the assistant panel (no secrets returned). */
export function GET(req: Request) {
  void req
  if (!envLoaded) {
    loadRepoEnv()
    envLoaded = true
  }
  const m = ratewatchModel()
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

function noticeStream(notice: string): Response {
  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      writer.write({ type: "start" })
      const id = crypto.randomUUID()
      writer.write({ type: "text-start", id })
      writer.write({ type: "text-delta", id, delta: notice })
      writer.write({ type: "text-end", id })
      writer.write({ type: "finish" })
    },
  })
  return createUIMessageStreamResponse({ stream })
}

/** One structured line per request. No prompt text, no personal data, no keys. */
function logRequest(entry: LogEntry): void {
  console.log(JSON.stringify({ route: "/api/ratewatch/chat", ...entry }))
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
  if (!envLoaded) {
    loadRepoEnv()
    envLoaded = true
  }
  const limited = rateLimited(req)
  if (limited) return limited

  const declared = Number(req.headers.get("content-length") ?? "0")
  if (Number.isFinite(declared) && declared > MAX_BODY_BYTES) {
    return Response.json({ detail: "Yêu cầu quá lớn." }, { status: 413 })
  }
  const raw = await req.text()
  if (raw.length > MAX_BODY_BYTES) {
    return Response.json({ detail: "Yêu cầu quá lớn." }, { status: 413 })
  }

  let body: z.infer<typeof Body>
  try {
    body = Body.parse(JSON.parse(raw))
  } catch (e) {
    const msg = e instanceof z.ZodError ? e.issues.map((i) => `${i.path.join(".") || "body"}: ${i.message}`).join("; ") : "JSON không hợp lệ"
    return Response.json({ detail: `Yêu cầu không hợp lệ: ${msg}` }, { status: 400 })
  }

  const log: LogEntry = { status: 200, provider: "none", model: null, session: body.sessionId?.slice(0, 8) ?? null, tools: [], flagged: 0, ms: 0, rejected: null }

  // Private data never reaches the model, a log or a trace.
  const pii = filterInput(lastUserText(body.messages))
  if (!pii.ok) {
    log.rejected = "pii"
    logRequest(log)
    return noticeStream(`${pii.notice_vi}\n\n${pii.notice_en}`)
  }

  const llm = ratewatchModel(process.env, body.sessionId)
  if (!llm) {
    log.rejected = "offline"
    logRequest(log)
    return noticeStream(
      "Chế độ offline: chưa cấu hình khoá LLM nên trợ lý trả lời không được bật. Hãy dùng máy tính kế hoạch và biểu lãi suất trên trang chính — mọi số đều có nguồn.",
    )
  }
  log.provider = llm.provider
  log.model = llm.label

  const snapshot = loadSnapshot()
  const agent = makeRatewatchAgent({ snapshot, model: llm.model })
  if (!agent) {
    log.rejected = "offline"
    logRequest(log)
    return noticeStream("Chế độ offline: trợ lý chưa khả dụng.")
  }

  const started = Date.now()
  const stream = await propagateAttributes(
    {
      sessionId: body.sessionId ?? undefined,
      tags: ["ratewatch", "assistant"],
      metadata: { snapshot_id: snapshot.meta.snapshot_id, provider: llm.provider },
    },
    () => createAgentUIStream({ agent, uiMessages: body.messages as unknown as UIMessage[], abortSignal: req.signal }),
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
    .pipeThrough(guardTextStream() as unknown as TransformStream<UIMessageChunk, UIMessageChunk>)
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
}
