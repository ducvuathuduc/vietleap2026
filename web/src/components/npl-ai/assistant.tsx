"use client"

import * as React from "react"
import { usePathname, useSearchParams } from "next/navigation"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport, getToolName, isToolUIPart, type UIMessage } from "ai"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import type { Lang } from "@/lib/npl/view"

import { AskCanvas, type CanvasCard, type ListedTool } from "./canvas"
import { promptsFor, questionLang, refusalFor, visibleText } from "./question-lang"

const MAX_INPUT = 500

type Refusal = { id: string; after: number; question: string; answer: string }

type ThreadPiece =
  | { kind: "message"; message: UIMessage; lang: Lang }
  | { kind: "refusal"; id: string; question: string; answer: string }

export function NplAskDock(): React.JSX.Element {
  const params = useSearchParams()
  const pathname = usePathname()
  const pageLang: Lang = params.get("lang") === "en" ? "en" : "vi"
  const pageVi = pageLang === "vi"
  const side = useSheetSide()
  const [open, setOpen] = React.useState(false)
  const [sessionId] = React.useState(() => crypto.randomUUID())
  const [transport] = React.useState(() => new DefaultChatTransport({ api: "/api/npl/chat" }))
  const { messages, sendMessage, status, error, stop, clearError } = useChat({ transport })
  const [input, setInput] = React.useState("")
  const [refusals, setRefusals] = React.useState<Refusal[]>([])
  const [pinned, setPinned] = React.useState<string[]>([])
  const threadRef = React.useRef<HTMLDivElement>(null)
  const busy = status === "submitted" || status === "streaming"
  const prompts = promptsFor(pathname ?? "/")
  const pieces = threadPieces(messages, refusals, pageLang)
  const { cards, tools } = canvasModel(messages, pinned, pageLang)
  const answerLang = latestQuestionLang(messages, pageLang)
  const waiting = busy && !assistantHasText(messages)
  const follow = React.useRef(true)

  React.useEffect(() => {
    const node = threadRef.current
    if (!node || !follow.current) return
    node.scrollTop = node.scrollHeight
  }, [messages, refusals, waiting, open])

  const send = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || busy || trimmed.length > MAX_INPUT) return
    follow.current = true
    const refusal = refusalFor(trimmed)
    if (refusal) {
      setRefusals((current) => [...current, { id: crypto.randomUUID(), after: messages.length, question: trimmed, answer: refusal }])
      setInput("")
      return
    }
    clearError()
    void sendMessage({ text: trimmed }, { body: { sessionId } })
    setInput("")
  }

  const togglePin = (id: string) => {
    setPinned((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button type="button" variant="outline" size="sm">
            {pageVi ? "Hỏi về dữ liệu" : "Ask the data"}
          </Button>
        }
      />
      <SheetContent
        side={side}
        className="gap-0 overflow-hidden p-0 data-[side=bottom]:h-[85vh]! data-[side=bottom]:max-h-[85vh]! data-[side=right]:w-[min(100vw,72rem)]! data-[side=right]:max-w-none! data-[side=right]:sm:max-w-none!"
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false)
        }}
      >
        <SheetHeader className="shrink-0 pr-12">
          <SheetTitle>{pageVi ? "Hỏi về dữ liệu" : "Ask the data"}</SheetTitle>
        </SheetHeader>
        <div className="grid min-h-0 flex-1 grid-cols-1 grid-rows-2 gap-4 overflow-hidden px-4 pb-4 sm:grid-cols-2 sm:grid-rows-1">
          <section className="flex min-h-0 min-w-0 flex-col gap-3" aria-label={pageVi ? "Hội thoại" : "Conversation"}>
            <div
              ref={threadRef}
              className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto"
              onScroll={() => {
                const node = threadRef.current
                if (!node) return
                follow.current = node.scrollHeight - node.scrollTop - node.clientHeight < 64
              }}
            >
              <div className="flex flex-col gap-2">
                <Button type="button" variant="outline" size="sm" className="h-auto whitespace-normal text-left" disabled={busy} onClick={() => send(prompts.vi)}>
                  {prompts.vi}
                </Button>
                <Button type="button" variant="outline" size="sm" className="h-auto whitespace-normal text-left" disabled={busy} onClick={() => send(prompts.en)}>
                  {prompts.en}
                </Button>
              </div>
              {pieces.map((piece) =>
                piece.kind === "refusal" ? (
                  <div key={piece.id} className="flex flex-col gap-2">
                    <p className="self-end rounded-lg bg-muted px-3 py-2 text-sm whitespace-pre-wrap">{piece.question}</p>
                    <p className="text-sm">{piece.answer}</p>
                  </div>
                ) : (
                  <MessageView key={piece.message.id} message={piece.message} lang={piece.lang} />
                ),
              )}
              {waiting ? (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Spinner className="size-3" /> {answerLang === "vi" ? "Đang trả lời" : "Answering"}
                </p>
              ) : null}
              {error ? (
                <p className="text-sm text-destructive">
                  {answerLang === "vi" ? "Không nhận được câu trả lời. Thử lại." : "No answer came back. Try again."}
                </p>
              ) : null}
            </div>
            <form
              onSubmit={(event) => {
                event.preventDefault()
                send(input)
              }}
              className="flex shrink-0 flex-col gap-2"
            >
              <Textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault()
                    send(input)
                  }
                  if (event.key === "Escape") {
                    event.preventDefault()
                    setOpen(false)
                  }
                }}
                placeholder={pageVi ? "Hỏi về một số trong snapshot" : "Ask about a figure in the snapshot"}
                aria-label={pageVi ? "Câu hỏi về dữ liệu" : "Question about the data"}
                aria-invalid={input.length > MAX_INPUT}
              />
              <div className="flex items-center justify-between gap-2">
                <p className={input.length > MAX_INPUT ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
                  {input.length}/{MAX_INPUT}
                </p>
                {busy ? (
                  <Button type="button" variant="outline" size="sm" onClick={() => void stop()}>
                    {pageVi ? "Dừng" : "Stop"}
                  </Button>
                ) : (
                  <Button type="submit" size="sm" disabled={!input.trim() || input.length > MAX_INPUT}>
                    {pageVi ? "Gửi" : "Send"}
                  </Button>
                )}
              </div>
            </form>
          </section>
          <AskCanvas cards={cards} pinned={new Set(pinned)} onTogglePin={togglePin} tools={tools} lang={pageLang} />
        </div>
      </SheetContent>
    </Sheet>
  )
}

export default NplAskDock

function useSheetSide(): "right" | "bottom" {
  const [side, setSide] = React.useState<"right" | "bottom">("right")
  React.useEffect(() => {
    const media = window.matchMedia("(max-width: 639px)")
    const apply = () => setSide(media.matches ? "bottom" : "right")
    apply()
    media.addEventListener("change", apply)
    return () => media.removeEventListener("change", apply)
  }, [])
  return side
}

function threadPieces(messages: UIMessage[], refusals: Refusal[], pageLang: Lang): ThreadPiece[] {
  const langs = messageLangs(messages, pageLang)
  const pieces: ThreadPiece[] = []
  let messageIndex = 0
  let refusalIndex = 0
  while (messageIndex < messages.length || refusalIndex < refusals.length) {
    const refusal = refusals[refusalIndex]
    if (refusal && refusal.after === messageIndex) {
      pieces.push({ kind: "refusal", id: refusal.id, question: refusal.question, answer: refusal.answer })
      refusalIndex += 1
      continue
    }
    const message = messages[messageIndex]
    if (!message) break
    pieces.push({ kind: "message", message, lang: langs[messageIndex] ?? pageLang })
    messageIndex += 1
  }
  return pieces
}

function latestQuestionLang(messages: UIMessage[], pageLang: Lang): Lang {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message?.role === "user") return questionLang(messageText(message))
  }
  return pageLang
}

function messageLangs(messages: UIMessage[], pageLang: Lang): Lang[] {
  const langs: Lang[] = []
  let current = pageLang
  for (const message of messages) {
    if (message.role === "user") current = questionLang(messageText(message))
    langs.push(current)
  }
  return langs
}

function canvasModel(messages: UIMessage[], pinned: string[], pageLang: Lang): { cards: CanvasCard[]; tools: ListedTool[] } {
  let lang = pageLang
  let latestId: string | null = null
  const finished: (CanvasCard & { messageId: string })[] = []
  const tools: ListedTool[] = []
  for (const message of messages) {
    if (message.role === "user") {
      lang = questionLang(messageText(message))
      continue
    }
    if (message.role !== "assistant") continue
    latestId = message.id
    for (const part of message.parts) {
      if (!isToolUIPart(part) || part.state === "input-streaming") continue
      const name = getToolName(part)
      tools.push({ id: part.toolCallId, name, input: part.input })
      if (part.state === "output-available" && part.preliminary !== true) {
        finished.push({ id: part.toolCallId, messageId: message.id, name, lang, input: part.input, output: part.output })
      }
    }
  }
  const byId = new Map(finished.map((card) => [card.id, card]))
  const pinnedCards = pinned.flatMap((id) => {
    const card = byId.get(id)
    return card ? [card] : []
  })
  const pinnedSet = new Set(pinned)
  const current = finished.filter((card) => card.messageId === latestId && !pinnedSet.has(card.id))
  return { cards: [...pinnedCards, ...current], tools }
}

function assistantHasText(messages: UIMessage[]): boolean {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message?.role !== "assistant") continue
    return message.parts.some((part) => part.type === "text" && part.text.trim().length > 0)
  }
  return false
}

function MessageView({ message, lang }: { message: UIMessage; lang: Lang }) {
  if (message.role === "user") {
    return <p className="self-end rounded-lg bg-muted px-3 py-2 text-sm whitespace-pre-wrap">{messageText(message)}</p>
  }
  const parts = message.parts.filter((part) => part.type === "text" || part.type === "data-guard")
  if (parts.length === 0) return null
  return (
    <div className="flex flex-col gap-2">
      {parts.map((part, index) => {
        if (part.type === "text") {
          return (
            <p key={index} className="text-sm whitespace-pre-wrap">
              {visibleText(part.text)}
            </p>
          )
        }
        return (
          <Badge key={index} variant="secondary">
            {lang === "vi" ? "Số chưa kiểm chứng đã được thay." : "Ungrounded numbers were replaced."}
          </Badge>
        )
      })}
    </div>
  )
}

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text)
    .join(" ")
}
