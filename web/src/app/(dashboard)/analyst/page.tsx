"use client"

import * as React from "react"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport, getToolName, isToolUIPart, type UIMessage } from "ai"
import { ChevronDownIcon, SendIcon, SparklesIcon, SquareIcon, WrenchIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { ResultTable } from "@/components/result-table"
import { EmptyState, ErrorState, PageShell } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { useAsync } from "@/hooks/use-async"

const SUGGESTIONS = [
  "Insight quan trọng nhất là gì?",
  "Yếu tố nào tác động mạnh nhất tới chỉ số mục tiêu?",
  "Chất lượng dữ liệu trước và sau làm sạch thế nào?",
  "Nên chọn mô hình dữ liệu nào cho dashboard, vì sao?",
]
const MAX_INPUT = 2000

type ToolPart = Extract<UIMessage["parts"][number], { toolCallId: string }>

const STATE_LABEL: Record<string, string> = {
  "input-streaming": "đang gọi",
  "input-available": "đang chạy",
  "output-available": "xong",
  "output-error": "lỗi",
}

function isSqlResult(v: unknown): v is { columns: string[]; rows: (string | number | null)[][] } {
  return typeof v === "object" && v !== null && Array.isArray((v as { columns?: unknown }).columns) && Array.isArray((v as { rows?: unknown }).rows)
}

function ToolCard({ part }: { part: ToolPart }) {
  const name = getToolName(part)
  const output = part.state === "output-available" ? part.output : undefined
  return (
    <Card size="sm">
      <Collapsible>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <WrenchIcon className="size-4" /> {name}
          </CardTitle>
          <CardDescription className="truncate font-mono text-xs">{JSON.stringify(part.input ?? {})}</CardDescription>
          <CardAction className="flex items-center gap-1">
            <Badge variant={part.state === "output-error" ? "destructive" : "outline"}>
              {part.state === "input-available" || part.state === "input-streaming" ? <Spinner /> : null}
              {STATE_LABEL[part.state] ?? part.state}
            </Badge>
            <CollapsibleTrigger render={<Button variant="ghost" size="icon-sm" aria-label="Xem kết quả tool" />}>
              <ChevronDownIcon />
            </CollapsibleTrigger>
          </CardAction>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="pt-2">
            {part.state === "output-error" ? (
              <p className="text-sm text-destructive">{part.errorText}</p>
            ) : isSqlResult(output) ? (
              <ResultTable columns={output.columns} rows={output.rows} maxHeight="16rem" />
            ) : output !== undefined ? (
              <pre className="max-h-64 overflow-auto rounded-lg border bg-muted/50 p-3 font-mono text-xs">{JSON.stringify(output, null, 2)}</pre>
            ) : (
              <p className="text-sm text-muted-foreground">Đang chờ kết quả…</p>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}

export default function AnalystPage() {
  const { datasetId } = useDataset()
  const config = useAsync(
    () => fetch("/api/chat", { cache: "no-store" }).then((r) => r.json() as Promise<{ mode: "llm" | "offline"; model: string | null }>),
    []
  )
  const [transport] = React.useState(() => new DefaultChatTransport({ api: "/api/chat" }))
  const { messages, sendMessage, status, error, stop, clearError } = useChat({ transport })
  const [input, setInput] = React.useState("")
  const busy = status === "submitted" || status === "streaming"

  const send = (text: string) => {
    const t = text.trim()
    if (!t || busy || t.length > MAX_INPUT) return
    clearError()
    void sendMessage({ text: t }, { body: { datasetId } })
    setInput("")
  }

  return (
    <PageShell>
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 lg:px-6">
        <p className="text-sm text-muted-foreground">
          Mọi con số trong câu trả lời đến từ tool gọi FastAPI/DuckDB (xem các thẻ tool). Tương quan không phải nhân quả.
        </p>
        {config.data && (
          <Badge variant="outline">{config.data.mode === "llm" ? `LLM: ${config.data.model}` : "Chế độ offline (không có khoá LLM)"}</Badge>
        )}
      </div>
      <div className="flex flex-col gap-4 px-4 lg:px-6">
        {messages.length === 0 && (
          <EmptyState icon={<SparklesIcon />} title="Hỏi AI Analyst về dữ liệu" description="Chọn một câu gợi ý hoặc tự đặt câu hỏi.">
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <Button key={s} variant="outline" size="sm" onClick={() => send(s)}>{s}</Button>
              ))}
            </div>
          </EmptyState>
        )}
        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex flex-col gap-2"}>
            {m.role === "user" ? (
              <div className="max-w-[80%] rounded-lg bg-muted px-3 py-2 text-sm whitespace-pre-wrap">
                {m.parts.map((p, i) => (p.type === "text" ? <span key={i}>{p.text}</span> : null))}
              </div>
            ) : (
              m.parts.map((p, i) => {
                if (p.type === "text") return <div key={i} className="text-sm leading-relaxed whitespace-pre-wrap">{p.text}</div>
                if (isToolUIPart(p)) return <ToolCard key={p.toolCallId} part={p} />
                return null
              })
            )}
          </div>
        ))}
        {status === "submitted" && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground"><Spinner /> Đang suy nghĩ…</p>
        )}
        {error && <ErrorState error={error} title="AI Analyst gặp lỗi" />}
      </div>
      <div className="px-4 lg:px-6">
        <Card>
          <CardContent>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                send(input)
              }}
              className="flex flex-col gap-2"
            >
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    send(input)
                  }
                }}
                placeholder="Vd. Tỉnh nào có giá/m² cao nhất? (Enter để gửi, Shift+Enter xuống dòng)"
                aria-label="Câu hỏi cho AI Analyst"
                aria-invalid={input.length > MAX_INPUT}
              />
              <CardFooter className="justify-between gap-2 px-0">
                <span className={input.length > MAX_INPUT ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
                  {input.length}/{MAX_INPUT}
                </span>
                {busy ? (
                  <Button type="button" variant="outline" onClick={() => void stop()}><SquareIcon /> Dừng</Button>
                ) : (
                  <Button type="submit" disabled={!input.trim() || input.length > MAX_INPUT}><SendIcon /> Gửi</Button>
                )}
              </CardFooter>
            </form>
          </CardContent>
        </Card>
      </div>
    </PageShell>
  )
}
