"use client"

// NPL study AI assistant panel (client, export only — mounted by a page).
// The model only fills typed tool inputs; every card/table is our own
// component fed by the tool output, and the "Nguồn & phép tính" drawer lists
// each tool call with its citations (source, period, n, CI).
import * as React from "react"
import { useSearchParams } from "next/navigation"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport, type UIMessage } from "ai"
import { BookOpenIcon, SendIcon, SparklesIcon, SquareIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import type { NplCitation } from "@/lib/npl/agent/tools"

const QUICK_PROMPTS_VI = [
  "Mức nợ xấu trung vị mới nhất là bao nhiêu?",
  "Hiệu ứng quý 4 mạnh cỡ nào?",
  "So sánh VCB, MBB, VPB",
  "Dự báo NPL quý tới của VCB",
]
const QUICK_PROMPTS_EN = [
  "What is the latest median NPL?",
  "How strong is the Q4 effect?",
  "Compare VCB, MBB, VPB",
  "Forecast VCB's NPL for next quarter",
]
const MAX_INPUT = 500

type ToolPart = {
  type: string
  state: string
  toolCallId: string
  toolName?: string
  input?: unknown
  output?: unknown
  errorText?: string
}

function isToolPart(part: unknown): part is ToolPart {
  return typeof part === "object" && part !== null && "type" in part && String((part as { type: unknown }).type).startsWith("tool-")
}

function citationsOf(part: ToolPart): NplCitation[] {
  const output = part.output as { citations?: NplCitation[] } | undefined
  return Array.isArray(output?.citations) ? output.citations : []
}

function citationLine(c: NplCitation, lang: "vi" | "en"): string {
  const period = c.period ? ` · ${c.period}` : ""
  const n = c.n != null ? ` · n=${c.n}` : ""
  const ci = c.ci95 ? ` · CI [${c.ci95[0]}, ${c.ci95[1]}]` : ""
  return `${c.source}${period}${n}${ci}${lang === "vi" ? "" : ""}`
}

function fmt(value: number | null | undefined, digits = 2): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "—"
}

function ToolCard({ part, lang }: { part: ToolPart; lang: "vi" | "en" }) {
  const vi = lang === "vi"
  const name = part.toolName ?? part.type.replace(/^tool-/, "")
  if (part.state !== "output-available") {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner className="size-3" /> {vi ? "Đang tra snapshot" : "Reading the snapshot"} ({name})…
      </p>
    )
  }
  const output = part.output as Record<string, unknown>
  return <ToolOutput name={name} output={output} lang={lang} />
}

function ToolOutput({ name, output, lang }: { name: string; output: Record<string, unknown>; lang: "vi" | "en" }) {
  const vi = lang === "vi"
  if (output.found === false) {
    return <p className="text-sm text-muted-foreground">{vi ? "Không có trong snapshot — không suy đoán." : "Not in the snapshot — nothing is invented."}</p>
  }
  if (name === "overview") {
    const level = output.level as { npl_median_pct?: number; period?: string; n_banks?: number } | undefined
    const benchmark = output.benchmark as { coef_pp?: number; ci95?: [number, number]; n?: number } | undefined
    const headline = output.headline as { vi?: string; en?: string } | undefined
    return (
      <div className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
        <p className="font-medium">{String((vi ? headline?.vi : headline?.en) ?? "")}</p>
        <p className="text-muted-foreground">
          {vi ? "Trung vị NPL" : "Median NPL"}: {fmt(level?.npl_median_pct)}% ({level?.period}, n={level?.n_banks})
        </p>
        <p className="text-muted-foreground">
          {vi ? "Hệ số quý 4" : "Q4 coefficient"}: {fmt(benchmark?.coef_pp, 3)} pp
          {benchmark?.ci95 ? ` [${fmt(benchmark.ci95[0], 3)}, ${fmt(benchmark.ci95[1], 3)}]` : ""} (n={benchmark?.n})
        </p>
      </div>
    )
  }
  if (name === "quarter_effects") {
    const effects = (output.effects as { quarter: number; coef_pp: number; ci95: [number, number]; n: number }[]) ?? []
    return (
      <ul className="flex flex-col gap-1 text-sm">
        {effects.map((e) => (
          <li key={e.quarter} className="rounded-xl bg-card p-2 ring-1 ring-foreground/10">
            Q{e.quarter}: {fmt(e.coef_pp, 3)} pp [{fmt(e.ci95?.[0], 3)}, {fmt(e.ci95?.[1], 3)}] (n={e.n})
          </li>
        ))}
      </ul>
    )
  }
  if (name === "bank_profile") {
    const bank = output.bank as { code?: string; name_vi?: string; ownership?: string; q4_change_median_pp?: number | null; q1_rebound_median_pp?: number | null; latest?: { period?: string; adjusted_change_pp?: number | null } | null } | undefined
    return (
      <div className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
        <p className="font-medium">
          {bank?.code} · {bank?.ownership === "state" ? (vi ? "nhà nước" : "state") : vi ? "tư nhân" : "private"}
        </p>
        <p className="text-muted-foreground">
          {vi ? "Thay đổi trung vị quý 4" : "Median Q4 change"}: {fmt(bank?.q4_change_median_pp, 2)} pp · {vi ? "quay lại quý 1" : "Q1 rebound"}: {fmt(bank?.q1_rebound_median_pp, 2)} pp
        </p>
        <p className="text-muted-foreground">
          {vi ? "Mới nhất" : "Latest"}: {bank?.latest?.period} — {vi ? "thay đổi đã điều chỉnh" : "adjusted change"} {fmt(bank?.latest?.adjusted_change_pp, 3)} pp
        </p>
      </div>
    )
  }
  if (name === "adjusted_change") {
    const row = output.row as { period?: string; d_npl_pp?: number | null; adjusted_change_pp?: number | null } | undefined
    return (
      <p className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
        {row?.period}: {vi ? "thô" : "raw"} {fmt(row?.d_npl_pp, 2)} pp → {vi ? "đã điều chỉnh" : "adjusted"} {fmt(row?.adjusted_change_pp, 3)} pp
      </p>
    )
  }
  if (name === "compare_banks") {
    const rows = (output.rows as { code: string; q4_change_median_pp: number | null; q1_rebound_median_pp: number | null; adjusted_change_pp: number | null }[]) ?? []
    return (
      <ul className="flex flex-col gap-1 text-sm">
        {rows.map((r) => (
          <li key={r.code} className="rounded-xl bg-card p-2 ring-1 ring-foreground/10">
            {r.code}: Q4 {fmt(r.q4_change_median_pp, 2)} pp · Q1 {fmt(r.q1_rebound_median_pp, 2)} pp · {vi ? "mới nhất" : "latest"} {fmt(r.adjusted_change_pp, 3)} pp
          </li>
        ))}
      </ul>
    )
  }
  if (name === "forecast") {
    const fc = output.forecast as { period?: string; npl_pct?: number; lo80?: number; hi80?: number } | undefined
    const mae = output.mae as { model?: number; seasonal_naive?: number } | undefined
    return (
      <div className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
        <p className="font-medium">
          {fc?.period}: {fmt(fc?.npl_pct)}% [{fmt(fc?.lo80)}, {fmt(fc?.hi80)}] (80%)
        </p>
        <p className="text-muted-foreground">
          MAE {fmt(mae?.model, 3)} · {vi ? "so sánh mùa vụ" : "seasonal naive"} {fmt(mae?.seasonal_naive, 3)}
        </p>
        <p className="text-muted-foreground">{vi ? "Đây là phép tính, không phải lời hứa." : "This is a calculation, not a promise."}</p>
      </div>
    )
  }
  if (name === "market_reaction") {
    return (
      <p className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">{String((vi ? output.reading_vi : output.reading_en) ?? "")}</p>
    )
  }
  if (name === "method") {
    const entry = output.entry as { id?: string; name_vi?: string; name_en?: string; reading_vi?: string; reading_en?: string; does_not_show_vi?: string; does_not_show_en?: string } | undefined
    return (
      <div className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
        <p className="font-medium">
          {entry?.id}: {vi ? entry?.name_vi : entry?.name_en}
        </p>
        <p className="text-muted-foreground">{vi ? entry?.reading_vi : entry?.reading_en}</p>
        <p className="text-muted-foreground">{vi ? "Không cho thấy" : "Does not show"}: {vi ? entry?.does_not_show_vi : entry?.does_not_show_en}</p>
      </div>
    )
  }
  if (name === "limitations") {
    const items = (output.items as { vi: string; en: string }[]) ?? []
    return (
      <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-muted-foreground">
        {items.map((item, index) => (
          <li key={index}>{vi ? item.vi : item.en}</li>
        ))}
      </ul>
    )
  }
  if (name === "glossary") {
    const entry = output.entry as { vi?: string; en?: string } | undefined
    return <p className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">{String((vi ? entry?.vi : entry?.en) ?? "")}</p>
  }
  return <pre className="overflow-x-auto rounded-xl bg-card p-3 text-xs ring-1 ring-foreground/10">{JSON.stringify(output, null, 2)}</pre>
}

function SourcesDrawer({ parts, lang }: { parts: ToolPart[]; lang: "vi" | "en" }) {
  const vi = lang === "vi"
  return (
    <Sheet>
      <SheetTrigger
        render={
          <Button variant="outline" size="sm">
            <BookOpenIcon /> {vi ? "Nguồn & phép tính" : "Sources & calculations"}
          </Button>
        }
      />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>{vi ? "Nguồn & phép tính" : "Sources & calculations"}</SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-4 overflow-y-auto p-4">
          {parts.length === 0 && <p className="text-sm text-muted-foreground">{vi ? "Chưa có lượt gọi tool nào." : "No tool calls yet."}</p>}
          {parts.map((part) => (
            <div key={part.toolCallId} className="flex flex-col gap-2 rounded-xl bg-card p-3 ring-1 ring-foreground/10">
              <p className="font-medium">{part.toolName ?? part.type.replace(/^tool-/, "")}</p>
              <pre className="overflow-x-auto text-xs text-muted-foreground">{JSON.stringify(part.input, null, 2)}</pre>
              <ul className="flex flex-col gap-1 text-xs">
                {citationsOf(part).map((c, index) => (
                  <li key={index}>{citationLine(c, lang)}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}

export function NplAssistant() {
  const params = useSearchParams()
  const lang: "vi" | "en" = params.get("lang") === "en" ? "en" : "vi"
  const vi = lang === "vi"
  const [sessionId] = React.useState(() => crypto.randomUUID())
  const [transport] = React.useState(() => new DefaultChatTransport({ api: "/api/npl/chat" }))
  const { messages, sendMessage, status, error, stop, clearError } = useChat({ transport })
  const [input, setInput] = React.useState("")
  const busy = status === "submitted" || status === "streaming"

  const send = (text: string) => {
    const t = text.trim()
    if (!t || busy || t.length > MAX_INPUT) return
    clearError()
    void sendMessage({ text: t }, { body: { sessionId } })
    setInput("")
  }

  const toolParts: ToolPart[] = []
  for (const message of messages) {
    if (message.role !== "assistant") continue
    for (const part of message.parts) if (isToolPart(part)) toolParts.push(part)
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="flex items-center gap-2 text-sm font-medium">
            <SparklesIcon className="size-4" /> {vi ? "Trợ lý nghiên cứu nợ xấu" : "NPL study assistant"}
          </p>
          <SourcesDrawer parts={toolParts} lang={lang} />
        </div>
        <p className="text-xs text-muted-foreground">
          {vi
            ? "Trợ lý chỉ trả lời bằng số từ snapshot đã xuất bản, kèm nguồn. M4–M6 là liên hệ, không phải nhân quả; dự báo là phép tính, không phải lời hứa."
            : "The assistant answers only with numbers from the published snapshot, each with its source. M4–M6 are association, not causation; forecasts are calculation, not a promise."}
        </p>
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {(vi ? QUICK_PROMPTS_VI : QUICK_PROMPTS_EN).map((prompt) => (
              <Button key={prompt} variant="outline" size="sm" onClick={() => send(prompt)}>
                {prompt}
              </Button>
            ))}
          </div>
        )}
        <div className="flex max-h-96 flex-col gap-3 overflow-y-auto">
          {messages.map((message: UIMessage) => (
            <div key={message.id} className={message.role === "user" ? "self-end rounded-xl bg-primary/10 px-3 py-2 text-sm" : "flex flex-col gap-2"}>
              {message.parts.map((part, index) => {
                if (part.type === "text") {
                  return (
                    <p key={index} className="whitespace-pre-wrap text-sm">
                      {part.text}
                    </p>
                  )
                }
                if (part.type === "data-guard") {
                  const flagged = (part.data as { flagged?: string[] } | undefined)?.flagged ?? []
                  return (
                    <Badge key={index} variant="destructive">
                      {vi ? "Số chưa kiểm chứng đã được thay" : "Ungrounded numbers replaced"}: {flagged.join(", ")}
                    </Badge>
                  )
                }
                if (isToolPart(part)) return <ToolCard key={index} part={part} lang={lang} />
                return null
              })}
            </div>
          ))}
          {status === "submitted" && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner className="size-3" /> {vi ? "Đang tra snapshot…" : "Reading the snapshot…"}
            </p>
          )}
          {error && (
            <p className="text-sm text-destructive">{vi ? "Trợ lý gặp lỗi — thử lại." : "The assistant hit an error — try again."}</p>
          )}
        </div>
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
            placeholder={vi ? "Vd. hiệu ứng quý 4 của nhóm ngân hàng nhà nước?" : "e.g. what is the Q4 effect for state banks?"}
            aria-label={vi ? "Câu hỏi cho trợ lý nghiên cứu" : "Question for the study assistant"}
            aria-invalid={input.length > MAX_INPUT}
          />
          <div className="flex items-center justify-between gap-2">
            <span className={input.length > MAX_INPUT ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
              {input.length}/{MAX_INPUT} · {vi ? "Không gửi thông tin cá nhân" : "Never send personal data"}
            </span>
            {busy ? (
              <Button type="button" variant="outline" size="sm" onClick={() => void stop()}>
                <SquareIcon /> {vi ? "Dừng" : "Stop"}
              </Button>
            ) : (
              <Button type="submit" size="sm" disabled={!input.trim() || input.length > MAX_INPUT}>
                <SendIcon /> {vi ? "Gửi" : "Send"}
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export default NplAssistant
