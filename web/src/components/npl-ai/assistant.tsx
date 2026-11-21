"use client"

import * as React from "react"
import { usePathname } from "next/navigation"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport, getToolName, isToolUIPart, type UIMessage } from "ai"
import { XIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { detectLang, type Lang } from "@/lib/npl/agent/lang"

import { AnswerEvidence, hasAnswerCanvas, type ListedTool } from "./canvas"
import { promptsFor, visibleText } from "./question-lang"

const MAX_INPUT = 500
const NARROW_WIDTH = 400
const CANVAS_WIDTH = 760
const MIN_WIDTH = 360
const RESIZE_STEP = 24
const WIDTH_KEY = "npl-assistant-width"
const subscribeToHydration = () => () => {}

type ManualWidth = { answerId?: string; width: number }

function subscribeToViewport(notify: () => void) {
  window.addEventListener("resize", notify)
  return () => window.removeEventListener("resize", notify)
}

function loadWidth(): ManualWidth | null {
  if (typeof window === "undefined") return null
  const width = Number(window.sessionStorage.getItem(WIDTH_KEY))
  return Number.isFinite(width) && width >= MIN_WIDTH ? { width } : null
}

export function NplAskDock({ lang: pageLang }: { lang: Lang }): React.JSX.Element {
  const pathname = usePathname()
  const pageVi = pageLang === "vi"
  const interactive = React.useSyncExternalStore(subscribeToHydration, () => true, () => false)
  const viewport = React.useSyncExternalStore(subscribeToViewport, () => window.innerWidth, () => 0)
  const mobile = viewport > 0 && viewport < 768
  const [open, setOpen] = React.useState(false)
  const [manualWidth, setManualWidth] = React.useState(loadWidth)
  const [collapsedAnswer, setCollapsedAnswer] = React.useState<string>()
  const [dragging, setDragging] = React.useState(false)
  const drag = React.useRef<{ pointerId: number; x: number; startWidth: number; width?: number } | null>(null)
  const resizeRef = React.useRef<HTMLDivElement>(null)
  const panelRef = React.useRef<HTMLDivElement>(null)
  const panelId = React.useId()
  const [sessionId] = React.useState(() => crypto.randomUUID())
  const [transport] = React.useState(() => new DefaultChatTransport({
    api: "/api/npl/chat",
    prepareSendMessagesRequest: ({ body, messages }) => ({
      body: {
        ...body,
        messages: messages.slice(-11).flatMap(({ id, role, parts }) => {
          const textParts = parts.filter((part) => part.type === "text")
          return textParts.length ? [{ id, role, parts: textParts }] : []
        }),
      },
    }),
  }))
  const { messages, sendMessage, status, error, stop, clearError } = useChat({ transport })
  const [input, setInput] = React.useState("")
  const triggerRef = React.useRef<HTMLButtonElement>(null)
  const threadRef = React.useRef<HTMLDivElement>(null)
  const busy = status === "submitted" || status === "streaming"
  const prompts = promptsFor(pathname ?? "/")[pageLang]
  const langs = messageLangs(messages, pageLang)
  const answerLang = langs.at(-1) ?? pageLang
  const last = messages.at(-1)
  const waiting = busy && (last?.role !== "assistant" || !messageText(last).trim())
  const latestAnswer = messages.findLast((message) => message.role === "assistant" && visibleText(messageText(message)).trim())
  const answerId = latestAnswer?.id
  const expanded = latestAnswer && collapsedAnswer !== answerId && hasAnswerCanvas(completedTools(latestAnswer))
  const maxWidth = Math.max(MIN_WIDTH, Math.floor(viewport * .75))
  const width = manualWidth && manualWidth.answerId === answerId
    ? Math.min(manualWidth.width, maxWidth)
    : expanded ? Math.min(CANVAS_WIDTH, Math.floor(viewport * .6)) : NARROW_WIDTH
  const follow = React.useRef(true)
  const title = pageVi ? "Hỏi về dữ liệu" : "Ask the data"

  React.useEffect(() => {
    const node = threadRef.current
    if (node && follow.current) node.scrollTop = node.scrollHeight
  }, [messages, waiting, open, width])

  function resizeTo(next: number) {
    const fitted = Math.min(maxWidth, Math.max(MIN_WIDTH, Math.round(next)))
    setManualWidth({ answerId, width: fitted })
    return fitted
  }

  function endResize() {
    if (!drag.current) return
    if (drag.current.width !== undefined) {
      window.sessionStorage.setItem(WIDTH_KEY, String(drag.current.width))
    }
    drag.current = null
    setDragging(false)
  }

  function resizeWithKey(event: React.KeyboardEvent<HTMLDivElement>) {
    let next: number
    switch (event.key) {
      case "ArrowLeft":
        next = width + RESIZE_STEP
        break
      case "ArrowRight":
        next = width - RESIZE_STEP
        break
      case "Home":
        next = MIN_WIDTH
        break
      case "End":
        next = maxWidth
        break
      default: return
    }
    event.preventDefault()
    window.sessionStorage.setItem(WIDTH_KEY, String(resizeTo(next)))
  }

  const send = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || busy || trimmed.length > MAX_INPUT) return
    follow.current = true
    clearError()
    void sendMessage({ text: trimmed }, { body: { sessionId } })
    setInput("")
  }

  return (
    <Sheet open={open} onOpenChange={(next) => {
      if (!next) endResize()
      setOpen(next)
    }} modal={mobile ? true : "trap-focus"} disablePointerDismissal>
      <SheetTrigger render={
        <Button ref={triggerRef} type="button" variant="outline" size="sm"
          className={`min-h-11 shrink-0 px-2.5${interactive ? "" : " invisible"}`} aria-label={title}>
          <span className="md:hidden">{pageVi ? "Hỏi" : "Ask"}</span>
          <span className="hidden md:inline">{title}</span>
        </Button>
      } />
      <SheetContent ref={panelRef} side="right" showOverlay={false} showCloseButton={false} finalFocus={triggerRef}
        style={{ "--assistant-width": `${width}px` } as React.CSSProperties}
        className={`gap-0 overflow-hidden p-0 data-[side=right]:h-dvh! data-[side=right]:w-full! data-[side=right]:max-w-none! md:data-[side=right]:w-(--assistant-width)! motion-reduce:transition-none ${dragging ? "transition-none" : "transition-[width,opacity,translate]"}`}>
        <SheetHeader className="flex-row items-center justify-between gap-3 border-b border-border py-3">
          <SheetTitle>{title}</SheetTitle>
          <div className="flex items-center gap-1">
            {!mobile && expanded && (
              <Button variant="ghost" size="sm" type="button" onClick={() => {
                setCollapsedAnswer(answerId)
                setManualWidth(null)
                window.sessionStorage.removeItem(WIDTH_KEY)
                resizeRef.current?.focus()
              }}>
                {pageVi ? "Thu gọn" : "Collapse panel"}
              </Button>
            )}
            <SheetClose render={
              <Button variant="ghost" size="icon-sm" type="button" aria-label={pageVi ? "Đóng" : "Close"}>
                <XIcon aria-hidden="true" />
              </Button>
            } />
          </div>
        </SheetHeader>
        <section id={panelId} className="flex min-h-0 min-w-0 flex-1 flex-col" aria-label={pageVi ? "Hội thoại" : "Conversation"}>
          <div ref={threadRef} className="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4"
            onScroll={() => {
              const node = threadRef.current
              if (node) follow.current = node.scrollHeight - node.scrollTop - node.clientHeight < 64
            }}>
            {messages.length === 0 && (
              <div className="grid gap-2">
                <p className="text-xs text-muted-foreground">{pageVi ? "Câu hỏi gợi ý" : "Suggested questions"}</p>
                {prompts.map((prompt) => (
                  <Button key={prompt} type="button" variant="outline" size="sm"
                    className="h-auto min-w-0 justify-start whitespace-normal px-2.5 py-2 text-left"
                    disabled={busy} onClick={() => send(prompt)}>
                    {prompt}
                  </Button>
                ))}
              </div>
            )}
            {messages.map((message, index) => (
              <MessageView key={message.id} message={message} lang={langs[index] ?? pageLang} />
            ))}
            {waiting && (
              <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner className="size-3 motion-reduce:animate-none" /> {answerLang === "vi" ? "Đang trả lời" : "Answering"}
              </p>
            )}
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {answerLang === "vi" ? "Không nhận được câu trả lời. Thử lại." : "No answer came back. Try again."}
              </p>
            )}
          </div>
          <form onSubmit={(event) => { event.preventDefault(); send(input) }}
            className="grid w-full shrink-0 gap-2 border-t border-border bg-popover px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            <Textarea className="min-h-14 w-full resize-none text-base md:text-sm" rows={2}
              value={input} onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault()
                  send(input)
                }
              }}
              placeholder={pageVi ? "Hỏi về số liệu trên trang" : "Ask about the numbers on this page"}
              aria-label={pageVi ? "Câu hỏi về dữ liệu" : "Question about the data"}
              aria-invalid={input.length > MAX_INPUT} />
            <div className="flex items-center justify-between gap-2">
              <p className={input.length > MAX_INPUT ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
                {input.length}/{MAX_INPUT}
              </p>
              {busy
                ? <Button type="button" variant="outline" size="sm" onClick={() => void stop()}>{pageVi ? "Dừng" : "Stop"}</Button>
                : <Button type="submit" size="sm" disabled={!input.trim() || input.length > MAX_INPUT}>{pageVi ? "Gửi" : "Send"}</Button>}
            </div>
          </form>
        </section>
        {!mobile && (
          <div ref={resizeRef} role="separator" tabIndex={0} aria-orientation="vertical" aria-controls={panelId}
            aria-label={pageVi ? "Đổi kích thước khung hỏi đáp" : "Resize assistant panel"}
            aria-valuemin={MIN_WIDTH} aria-valuemax={maxWidth} aria-valuenow={width}
            aria-valuetext={pageVi ? `${width} điểm ảnh` : `${width} pixels`}
            className="group absolute inset-y-0 left-0 z-10 hidden w-3 touch-none cursor-ew-resize items-center justify-center outline-none select-none hover:bg-muted/60 focus-visible:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset md:flex"
            onPointerDown={(event) => {
              if (!event.isPrimary || event.button !== 0 || drag.current) return
              const startWidth = panelRef.current?.getBoundingClientRect().width ?? width
              drag.current = { pointerId: event.pointerId, x: event.clientX, startWidth }
              event.currentTarget.setPointerCapture(event.pointerId)
              setDragging(true)
            }}
            onPointerMove={(event) => {
              const active = drag.current
              if (active?.pointerId === event.pointerId && (active.width !== undefined || event.clientX !== active.x)) {
                active.width = resizeTo(active.startWidth + active.x - event.clientX)
              }
            }}
            onLostPointerCapture={(event) => {
              if (drag.current?.pointerId === event.pointerId) endResize()
            }}
            onKeyDown={resizeWithKey}>
            <span aria-hidden="true" className="h-8 w-0.5 rounded-full bg-border group-hover:bg-ring group-focus-visible:bg-ring" />
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

export default NplAskDock

function messageLangs(messages: UIMessage[], pageLang: Lang): Lang[] {
  let current = pageLang
  return messages.map((message) => {
    if (message.role === "user") current = detectLang(messageText(message))
    return current
  })
}

function completedTools(message: UIMessage): ListedTool[] {
  return message.parts.flatMap((part) => {
    if (!isToolUIPart(part) || part.state !== "output-available" || part.preliminary) return []
    return [{ id: part.toolCallId, name: getToolName(part), input: part.input, output: part.output }]
  })
}

function MessageView({ message, lang }: { message: UIMessage; lang: Lang }) {
  if (message.role === "user") {
    return <p lang={lang} className="max-w-[90%] self-end rounded-lg bg-muted px-3 py-2 text-sm whitespace-pre-wrap [overflow-wrap:anywhere]">{messageText(message)}</p>
  }
  const text = visibleText(messageText(message))
  if (!text.trim()) return null
  return (
    <article lang={lang} className="grid min-w-0 gap-2">
      <p className="text-sm leading-relaxed whitespace-pre-wrap [overflow-wrap:anywhere]">{text}</p>
      <AnswerEvidence tools={completedTools(message)} lang={lang} />
    </article>
  )
}

function messageText(message: UIMessage): string {
  return message.parts.filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text).join(" ")
}
