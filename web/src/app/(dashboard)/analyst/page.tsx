"use client"

import * as React from "react"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { SendIcon, SparklesIcon, SquareIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { ChatMessages } from "@/components/chat-messages"
import { EmptyState, ErrorState, PageShell } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
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
        <ChatMessages messages={messages} />
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
