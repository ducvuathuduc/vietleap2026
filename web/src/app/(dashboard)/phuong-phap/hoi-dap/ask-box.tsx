"use client"

import * as React from "react"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport, type UIMessage } from "ai"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"

const MAX = 1000

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part): part is { type: "text"; text: string } => part.type === "text" && "text" in part && typeof part.text === "string")
    .map((part) => part.text)
    .join("")
}

export function AskBox({ questions }: { questions: string[] }) {
  const [transport] = React.useState(() => new DefaultChatTransport({ api: "/api/hoi-dap" }))
  const { messages, sendMessage, status, error, stop, clearError } = useChat({ transport })
  const [input, setInput] = React.useState("")
  const last = React.useRef("")
  const busy = status === "submitted" || status === "streaming"
  const waiting = busy && !messages.some((message) => message.role === "assistant" && messageText(message))

  const send = (value: string) => {
    const text = value.trim()
    if (!text || busy || text.length > MAX) return
    last.current = text
    clearError()
    void sendMessage({ text })
    setInput("")
  }

  return (
    <div className="flex flex-col gap-4">
      {questions.length ? (
        <section className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">Câu hỏi gợi ý</h2>
          <ul className="flex list-disc flex-col gap-2 pl-5 text-sm">
            {questions.map((question) => (
              <li key={question}>
                <button
                  type="button"
                  className="bg-transparent p-0 text-left underline underline-offset-4 hover:text-foreground disabled:opacity-50"
                  disabled={busy}
                  onClick={() => send(question)}
                >
                  {question}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <form
        onSubmit={(event) => {
          event.preventDefault()
          send(input)
        }}
        className="flex flex-col gap-2 sm:flex-row sm:items-center"
      >
        <Input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Hỏi về một chỉ số đã xuất bản"
          aria-label="Câu hỏi về số liệu"
          maxLength={MAX}
          disabled={busy}
          className="sm:flex-1"
        />
        {busy ? (
          <Button type="button" variant="outline" onClick={() => void stop()}>
            Dừng
          </Button>
        ) : (
          <Button type="submit" variant="outline" disabled={!input.trim()}>
            Gửi câu hỏi
          </Button>
        )}
      </form>
      <div aria-live="polite" aria-busy={busy} className="flex flex-col gap-3">
        {waiting ? <Skeleton className="h-4 w-2/3" /> : null}
        {messages.map((message) => {
          const text = messageText(message)
          if (!text) return null
          return (
            <p key={message.id} className={message.role === "user" ? "text-sm text-muted-foreground" : "text-sm whitespace-pre-wrap"}>
              {text}
            </p>
          )
        })}
        {error ? (
          <p className="text-sm">
            Không tải được câu trả lời.{" "}
            <button type="button" className="bg-transparent p-0 underline underline-offset-4" onClick={() => send(last.current)}>
              Thử lại
            </button>
          </p>
        ) : null}
      </div>
    </div>
  )
}
