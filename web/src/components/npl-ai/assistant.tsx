"use client"

import * as React from "react"
import { usePathname, useSearchParams } from "next/navigation"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport, getToolName, isToolUIPart, type UIMessage } from "ai"

import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { detectLang, type Lang } from "@/lib/npl/agent/lang"

import { AnswerSources, AskCanvas, type CanvasCard, type ListedTool } from "./canvas"
import { promptsFor, visibleText } from "./question-lang"

const MAX_INPUT = 500
const PINNED_STORAGE_KEY = "npl-assistant-pinned"

export function NplAskDock(): React.JSX.Element {
  const params = useSearchParams()
  const pathname = usePathname()
  const pageLang: Lang = params.get("lang") === "en" ? "en" : "vi"
  const pageVi = pageLang === "vi"
  const side = useSheetSide()
  const [open, setOpen] = React.useState(false)
  const [sessionId] = React.useState(() => crypto.randomUUID())
  const [transport] = React.useState(() => new DefaultChatTransport({
    api: "/api/npl/chat",
    prepareSendMessagesRequest: ({ body, messages }) => ({
      body: {
        ...body,
        // Tool data stays in the canvas. Send only recent dialogue back to the agent.
        messages: messages.slice(-11).flatMap(({ id, role, parts }) => {
          const textParts = parts.filter((part) => part.type === "text")
          return textParts.length ? [{ id, role, parts: textParts }] : []
        }),
      },
    }),
  }))
  const { messages, sendMessage, status, error, stop, clearError } = useChat({ transport })
  const [input, setInput] = React.useState("")
  const [pinned, setPinned] = React.useState<CanvasCard[]>([])
  const triggerRef = React.useRef<HTMLButtonElement>(null)
  const threadRef = React.useRef<HTMLDivElement>(null)
  const busy = status === "submitted" || status === "streaming"
  const prompts = promptsFor(pathname ?? "/")
  const langs = messageLangs(messages, pageLang)
  const pinnedIds = new Set(pinned.map((card) => card.id))
  const currentCards = canvasModel(messages, langs)
  const cards = [...pinned, ...currentCards.filter((card) => !pinnedIds.has(card.id))]
  const answerLang = latestQuestionLang(messages, pageLang)
  const waiting = busy && !assistantHasText(messages)
  const follow = React.useRef(true)

  React.useEffect(() => {
    const node = threadRef.current
    if (!node || !follow.current) return
    node.scrollTop = node.scrollHeight
  }, [messages, waiting, open])

  const send = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || busy || trimmed.length > MAX_INPUT) return
    follow.current = true
    clearError()
    void sendMessage({ text: trimmed }, { body: { sessionId } })
    setInput("")
  }

  const togglePin = (id: string) => {
    const card = cards.find((item) => item.id === id)
    if (!card) return
    const next = pinnedIds.has(id) ? pinned.filter((item) => item.id !== id) : [...pinned, card]
    setPinned(next)
    try {
      sessionStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Keep the in-memory pins when tab storage is unavailable.
    }
  }

  return (
    <Sheet open={open} onOpenChange={(next) => {
      if (next && pinned.length === 0) setPinned(readPins())
      setOpen(next)
    }}>
      <SheetTrigger
        render={
          <Button ref={triggerRef} type="button" variant="outline" size="sm" className="min-h-11 shrink-0 px-2.5" aria-label={pageVi ? "Hỏi về dữ liệu" : "Ask the data"}>
            <span className="md:hidden">{pageVi ? "Hỏi" : "Ask"}</span>
            <span className="hidden md:inline">{pageVi ? "Hỏi về dữ liệu" : "Ask the data"}</span>
          </Button>
        }
      />
      <SheetContent
        side={side}
        finalFocus={triggerRef}
        className="gap-0 overflow-hidden p-0 data-[side=bottom]:h-[92dvh]! data-[side=right]:w-[min(100vw,72rem)]! data-[side=right]:max-w-none!"
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
              <details className="shrink-0" key={pathname}>
                <summary className="w-fit cursor-pointer text-sm text-muted-foreground">
                  {pageVi ? "Câu hỏi gợi ý" : "Suggested questions"}
                </summary>
                <div className="mt-2 grid gap-2 lg:grid-cols-2">
                  {([pageLang, pageVi ? "en" : "vi"] as const).map((lang) => (
                    <div key={lang} lang={lang} className="grid content-start gap-2">
                      {prompts[lang].map((prompt) => (
                        <Button key={prompt} type="button" variant="outline" size="sm" className="h-auto justify-start whitespace-normal px-2 py-1.5 text-left" disabled={busy} onClick={() => send(prompt)}>
                          {prompt}
                        </Button>
                      ))}
                    </div>
                  ))}
                </div>
              </details>
              {messages.map((message, index) => (
                <MessageView key={message.id} message={message} lang={langs[index] ?? pageLang} />
              ))}
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
              className="grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-end gap-2 sm:flex sm:flex-col sm:items-stretch"
            >
              <Textarea
                className="max-sm:min-h-12!"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault()
                    send(input)
                  }
                }}
                placeholder={pageVi ? "Hỏi về số liệu trên trang" : "Ask about the numbers on this page"}
                aria-label={pageVi ? "Câu hỏi về dữ liệu" : "Question about the data"}
                aria-invalid={input.length > MAX_INPUT}
              />
              <div className="flex items-center justify-between gap-2">
                <p className={input.length > MAX_INPUT ? "text-xs text-destructive" : "hidden text-xs text-muted-foreground sm:block"}>
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
          <AskCanvas cards={cards} pinned={pinnedIds} onTogglePin={togglePin} onOpenPage={() => setOpen(false)} lang={pageLang} />
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

function latestQuestionLang(messages: UIMessage[], pageLang: Lang): Lang {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message?.role === "user") return detectLang(messageText(message))
  }
  return pageLang
}

function messageLangs(messages: UIMessage[], pageLang: Lang): Lang[] {
  const langs: Lang[] = []
  let current = pageLang
  for (const message of messages) {
    if (message.role === "user") current = detectLang(messageText(message))
    langs.push(current)
  }
  return langs
}

function canvasModel(messages: UIMessage[], langs: Lang[]): CanvasCard[] {
  const index = messages.findLastIndex((message) => message.role === "assistant")
  const message = messages[index]
  return message ? completedTools(message).map((tool) => ({ ...tool, lang: langs[index] ?? "vi" })) : []
}

function readPins(): CanvasCard[] {
  try {
    const stored: unknown = JSON.parse(sessionStorage.getItem(PINNED_STORAGE_KEY) ?? "[]")
    return Array.isArray(stored) ? stored : []
  } catch {
    return []
  }
}

function completedTools(message: UIMessage): ListedTool[] {
  return message.parts.flatMap((part) => {
    if (!isToolUIPart(part) || part.state !== "output-available" || part.preliminary) return []
    return [{ id: part.toolCallId, name: getToolName(part), input: part.input, output: part.output }]
  })
}

function assistantHasText(messages: UIMessage[]): boolean {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message?.role === "user") return false
    if (message?.role === "assistant") return Boolean(messageText(message).trim())
  }
  return false
}

function MessageView({ message, lang }: { message: UIMessage; lang: Lang }) {
  if (message.role === "user") {
    return <p lang={lang} className="self-end rounded-lg bg-muted px-3 py-2 text-sm whitespace-pre-wrap">{messageText(message)}</p>
  }
  const text = visibleText(messageText(message))
  if (!text.trim()) return null
  return (
    <div lang={lang} className="flex flex-col gap-2">
      <p className="text-sm whitespace-pre-wrap">{text}</p>
      <AnswerSources tools={completedTools(message)} lang={lang} />
    </div>
  )
}

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text)
    .join(" ")
}
