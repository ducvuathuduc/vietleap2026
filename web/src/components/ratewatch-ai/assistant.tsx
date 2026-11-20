"use client"

// RateWatch AI assistant panel (client). The model only fills typed tool
// inputs; every chart/table is our own component fed by the tool output, and
// the "Nguồn & phép tính" drawer lists each tool call with its citations.
import * as React from "react"
import { useSearchParams } from "next/navigation"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport, type UIMessage } from "ai"
import { BookOpenIcon, SendIcon, SparklesIcon, SquareIcon } from "lucide-react"

import { CurveChart, type CurveSeries } from "@/components/ratewatch/curve-chart"
import { RateList } from "@/components/ratewatch/rate-list"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import type { Citation } from "@/lib/ratewatch/agent/tools"
import { gradeBadge, type Lang, type TableRow } from "@/lib/ratewatch/view"

const QUICK_PROMPTS = [
  "1,2 tỷ, cần sau 5 tháng",
  "So sánh OCB, ACB, MB kỳ 6 tháng",
  "Ngân hàng nào ở Cần Thơ trả lãi tại quầy cao nhất?",
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

function citationsOf(part: ToolPart): Citation[] {
  const output = part.output as { citations?: Citation[] } | undefined
  return Array.isArray(output?.citations) ? output.citations : []
}

function citationLine(c: Citation, lang: Lang): string {
  const vi = lang === "vi"
  const term = c.term_months != null ? `${c.term_months} ${vi ? "tháng" : "m"}` : ""
  const channel = c.channel ? ` · ${c.channel === "counter" ? (vi ? "quầy" : "counter") : "online"}` : ""
  const grade = c.grade ? ` · ${c.grade}` : ""
  const date = c.sheet_date ? ` · ${vi ? "biểu" : "sheet"} ${c.sheet_date}` : ""
  return `${c.bank}${term ? ` · ${term}` : ""}${channel}${grade}${date}`
}

function ToolCard({ part, lang }: { part: ToolPart; lang: Lang }) {
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

function ToolOutput({ name, output, lang }: { name: string; output: Record<string, unknown>; lang: Lang }) {
  const vi = lang === "vi"
  if (output.found === false) {
    return <p className="text-sm text-muted-foreground">{vi ? "Không có trong snapshot — không suy đoán." : "Not in the snapshot — nothing is invented."}</p>
  }
  if (name === "get_curve") {
    const points = (output.points as { term_months: number; rate_pct: number; grade: string }[]) ?? []
    const code = String(output.bank_code ?? "")
    const series: CurveSeries[] = [
      {
        code,
        name: String(output.bank_name ?? code),
        sheetDate: String(output.sheet_date ?? ""),
        sourceUrl: String(output.sheet_url ?? ""),
        points: points.map((p) => ({ term: p.term_months, rate: p.rate_pct, grade: p.grade as never, mark: p.term_months === 6 || p.term_months === 12 })),
      },
    ]
    const rows = points.map((p) => ({ term: p.term_months, [code]: p.rate_pct }))
    return <CurveChart rows={rows} series={series} ceiling={4.75} horizon={0} lang={lang} />
  }
  if (name === "compare_banks") {
    const rows = (output.rows as { bank_code: string; bank_name: string; channel: string; rate_pct: number; grade: string; sheet_date: string | null }[]) ?? []
    const tableRows: TableRow[] = rows.map((r) => {
      const badge = gradeBadge(r.grade as never, "", lang)
      return {
        bankCode: r.bank_code,
        bankName: r.bank_name,
        term: Number(output.term_months),
        channel: r.channel,
        tier: "",
        grade: r.grade as never,
        gradeLabel: badge.label,
        gradeDetail: badge.detail,
        rateText: `${r.rate_pct.toLocaleString(vi ? "vi-VN" : "en-US", { minimumFractionDigits: 2 })}%`,
        sheetDate: r.sheet_date ?? "",
        sourceUrl: "",
      }
    })
    return <RateList rows={tableRows} lang={lang} />
  }
  if (name === "plan_deposit") {
    const plans = (output.plans as { kind: string; interest_vnd: number; value_at_horizon: number; insured_share: number; rows: { bank_code: string; term_months: number; channel: string; rate_pct: number }[] }[]) ?? []
    return (
      <ul className="flex flex-col gap-1 text-sm">
        {plans.map((plan, index) => (
          <li key={index} className="rounded-xl bg-card p-3 ring-1 ring-foreground/10">
            <p className="font-medium">{plan.kind === "split" ? (vi ? "Chia nhiều ngân hàng" : "Split across banks") : plan.kind === "ladder_6_renewal" ? (vi ? "6 tháng rồi gửi tiếp" : "6-month renewal") : vi ? "Một kỳ hạn" : "Single term"}</p>
            <p>
              {vi ? "Lãi" : "Interest"}: {Math.round(plan.interest_vnd).toLocaleString(vi ? "vi-VN" : "en-US")} đ · {vi ? "giá trị cuối kỳ" : "value"}: {Math.round(plan.value_at_horizon).toLocaleString(vi ? "vi-VN" : "en-US")} đ
            </p>
            {plan.rows.map((row, rowIndex) => (
              <p key={rowIndex} className="text-muted-foreground">
                {row.bank_code} · {row.term_months} {vi ? "tháng" : "m"} · {row.channel} · {row.rate_pct.toLocaleString(vi ? "vi-VN" : "en-US", { minimumFractionDigits: 2 })}%
              </p>
            ))}
          </li>
        ))}
      </ul>
    )
  }
  if (name === "break_even") {
    return (
      <div className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
        <p className="font-medium">
          {String(output.bank_code)} · {vi ? "quầy" : "counter"}/{vi ? "online" : "online"}: {String(output.short_m)} {vi ? "tháng" : "m"} → {String(output.long_m)} {vi ? "tháng" : "m"}
        </p>
        <p>
          {vi ? "Hoà vốn khi gửi tiếp" : "Break-even renewal"}: {Number(output.break_even_pct).toLocaleString(vi ? "vi-VN" : "en-US", { minimumFractionDigits: 2 })}%/năm
        </p>
        <p className="text-muted-foreground">{String(output.note_vi ?? "")}</p>
      </div>
    )
  }
  if (name === "insured_split") {
    const allocations = (output.allocations as { bank_code: string; amount: number; term_months: number; rate_pct: number; interest_vnd: number }[]) ?? []
    return (
      <ul className="flex flex-col gap-1 text-sm">
        {allocations.map((a, index) => (
          <li key={index} className="rounded-xl bg-card p-3 ring-1 ring-foreground/10">
            {a.bank_code}: {Math.round(a.amount).toLocaleString(vi ? "vi-VN" : "en-US")} đ · {a.term_months} {vi ? "tháng" : "m"} · {a.rate_pct.toLocaleString(vi ? "vi-VN" : "en-US", { minimumFractionDigits: 2 })}% · {vi ? "lãi" : "interest"} {Math.round(a.interest_vnd).toLocaleString(vi ? "vi-VN" : "en-US")} đ
          </li>
        ))}
        <li className="text-muted-foreground">
          {vi ? "Còn lại" : "Remainder"}: {Math.round(Number(output.remainder_vnd ?? 0)).toLocaleString(vi ? "vi-VN" : "en-US")} đ · {vi ? "hạn mức" : "cap"} {Number(output.cap_vnd ?? 0).toLocaleString(vi ? "vi-VN" : "en-US")} đ
        </li>
      </ul>
    )
  }
  if (name === "policy") {
    return <p className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">{JSON.stringify(output.values)}</p>
  }
  if (name === "bank_profile") {
    return <p className="text-sm text-muted-foreground">{String(output.message_vi ?? "")}</p>
  }
  if (name === "banks_in_province") {
    const province = output.province as { name_vi?: string; branches_by_bank?: Record<string, number> } | undefined
    const branches = Object.entries(province?.branches_by_bank ?? {})
    return (
      <div className="text-sm">
        <p className="font-medium">{province?.name_vi}</p>
        {branches.length ? (
          branches.map(([code, count]) => (
            <p key={code} className="text-muted-foreground">
              {code}: {count}
            </p>
          ))
        ) : (
          <p className="text-muted-foreground">{String(output.note_vi ?? "")}</p>
        )}
      </div>
    )
  }
  if (name === "explain") {
    return <p className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">{String(output.text_vi ?? "")}</p>
  }
  return <pre className="overflow-x-auto rounded-xl bg-card p-3 text-xs ring-1 ring-foreground/10">{JSON.stringify(output, null, 2)}</pre>
}

function SourcesDrawer({ parts, lang }: { parts: ToolPart[]; lang: Lang }) {
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
                  <li key={index}>
                    {citationLine(c, lang)}
                    {c.source_url ? (
                      <>
                        {" · "}
                        <a href={c.source_url} className="underline underline-offset-4" rel="noreferrer">
                          {vi ? "nguồn" : "source"}
                        </a>
                      </>
                    ) : null}
                    {c.observed_at ? ` · ${vi ? "đọc" : "read"} ${c.observed_at}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}

export function RatewatchAssistant() {
  const params = useSearchParams()
  const lang: Lang = params.get("lang") === "en" ? "en" : "vi"
  const vi = lang === "vi"
  const [sessionId] = React.useState(() => crypto.randomUUID())
  const [transport] = React.useState(() => new DefaultChatTransport({ api: "/api/ratewatch/chat" }))
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

  const toolParts = messages.flatMap((message: UIMessage) => (message.role === "assistant" ? message.parts.filter(isToolPart) : []))

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="flex items-center gap-2 text-sm font-medium">
            <SparklesIcon className="size-4" /> {vi ? "Trợ lý lãi suất" : "Rate assistant"}
          </p>
          <SourcesDrawer parts={toolParts} lang={lang} />
        </div>
        <p className="text-xs text-muted-foreground">
          {vi
            ? "Trợ lý chỉ trả lời bằng số từ snapshot đã xuất bản, kèm nguồn. Thông tin tham khảo — phép tính trên biểu niêm yết, không phải tư vấn đầu tư."
            : "The assistant answers only with numbers from the published snapshot, each with its source. Reference information — calculations on posted sheets, not investment advice."}
        </p>
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {QUICK_PROMPTS.map((prompt) => (
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
            placeholder={vi ? "Vd. 500 triệu gửi 6 tháng ở đâu lãi cao nhất?" : "e.g. where is the best 6-month rate for 500 million?"}
            aria-label={vi ? "Câu hỏi cho trợ lý lãi suất" : "Question for the rate assistant"}
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

export default RatewatchAssistant
