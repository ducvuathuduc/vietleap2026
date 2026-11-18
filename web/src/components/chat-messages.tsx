"use client"

import Link from "next/link"
import { getToolName, isToolUIPart, type UIMessage } from "ai"
import { ChevronDownIcon, ExternalLinkIcon, WrenchIcon } from "lucide-react"

import { InsightChart } from "@/components/insight-chart"
import { CodeBlock, ResultTable } from "@/components/result-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Spinner } from "@/components/ui/spinner"
import type { ChartSpec } from "@/lib/api/types"

type ToolPart = Extract<UIMessage["parts"][number], { toolCallId: string }>

const STATE_LABEL: Record<string, string> = {
  "input-streaming": "đang gọi",
  "input-available": "đang chạy",
  "output-available": "xong",
  "output-error": "lỗi",
}

const MAX_CHAT_COLS = 20

function isSqlResult(
  v: unknown
): v is {
  columns: string[]
  rows: (string | number | boolean | null)[][]
  row_count?: number
  query?: string
  query_id?: number
  chart?: ChartSpec | null
} {
  return (
    typeof v === "object" &&
    v !== null &&
    Array.isArray((v as { columns?: unknown }).columns) &&
    Array.isArray((v as { rows?: unknown }).rows)
  )
}

function ToolCard({ part }: { part: ToolPart }) {
  const name = getToolName(part)
  const output = part.state === "output-available" ? part.output : undefined
  const isRunSql = name === "runSql"
  const sqlResult = isSqlResult(output) ? output : null
  const inputQuery =
    typeof (part.input as { query?: unknown } | undefined)?.query === "string"
      ? (part.input as { query: string }).query
      : sqlResult?.query ?? ""

  const shownCols = sqlResult ? sqlResult.columns.slice(0, MAX_CHAT_COLS) : []
  const shownRows = sqlResult ? sqlResult.rows.map((r) => r.slice(0, MAX_CHAT_COLS)) : []
  const truncatedCols = sqlResult ? sqlResult.columns.length > MAX_CHAT_COLS : false

  return (
    <Card size="sm">
      <Collapsible defaultOpen={isRunSql}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <WrenchIcon className="size-4" />{" "}
            {isRunSql && sqlResult?.query_id ? `Truy vấn #${sqlResult.query_id}` : name}
          </CardTitle>
          <CardDescription className="truncate font-mono text-xs">
            {isRunSql && inputQuery ? inputQuery.replace(/\s+/g, " ") : JSON.stringify(part.input ?? {})}
          </CardDescription>
          <CardAction className="flex items-center gap-1">
            {isRunSql && sqlResult ? (
              <Badge variant="secondary">{(sqlResult.row_count ?? sqlResult.rows.length).toLocaleString("vi-VN")} dòng</Badge>
            ) : null}
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
          <CardContent className="flex flex-col gap-3 pt-2">
            {part.state === "output-error" ? (
              <p className="text-sm text-destructive">{part.errorText}</p>
            ) : sqlResult ? (
              <>
                {inputQuery ? <CodeBlock code={inputQuery} label="Truy vấn đã chạy" /> : null}
                {sqlResult.chart ? (
                  <div className="rounded-lg border p-2">
                    <InsightChart spec={sqlResult.chart} height={220} />
                  </div>
                ) : null}
                <ResultTable columns={shownCols} rows={shownRows} maxHeight="16rem" />
                {truncatedCols ? (
                  <p className="text-xs text-muted-foreground">
                    Hiển thị {MAX_CHAT_COLS}/{sqlResult.columns.length} cột — xem đủ trong SQL Explorer.
                  </p>
                ) : null}
                {inputQuery ? (
                  <div className="flex justify-end">
                    <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/sql?q=${encodeURIComponent(inputQuery)}`} />}>
                      <ExternalLinkIcon className="size-3.5" /> Mở trong SQL Explorer
                    </Button>
                  </div>
                ) : null}
              </>
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

/** Renders AI SDK UI messages: text parts as prose, tool calls as collapsible Cards. */
export function ChatMessages({ messages }: { messages: UIMessage[] }) {
  return (
    <>
      {messages.map((m) => {
        const joinedText =
          m.role === "assistant"
            ? m.parts
                .filter((p): p is { type: "text"; text: string } => p.type === "text")
                .map((p) => p.text)
                .join("\n")
            : ""
        const hasWarning = joinedText.includes("⚠ Số chưa kiểm chứng:")
        const hasNumbers = /\d/.test(joinedText)
        const hasTool = m.role === "assistant" && m.parts.some((p) => isToolUIPart(p) && p.state === "output-available")

        return (
          <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex flex-col gap-2"}>
            {m.role === "user" ? (
              <div className="max-w-[80%] rounded-lg bg-muted px-3 py-2 text-sm whitespace-pre-wrap">
                {m.parts.map((p, i) => (p.type === "text" ? <span key={i}>{p.text}</span> : null))}
              </div>
            ) : (
              <>
                {m.parts.map((p, i) => {
                  if (p.type === "text") return <div key={i} className="text-sm leading-relaxed whitespace-pre-wrap">{p.text}</div>
                  if (isToolUIPart(p)) return <ToolCard key={p.toolCallId} part={p} />
                  return null
                })}
                {joinedText && (hasWarning || (hasNumbers && hasTool)) ? (
                  <div className="flex items-center gap-2">
                    {hasWarning ? (
                      <Badge variant="destructive" className="text-xs">⚠ số chưa kiểm chứng</Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs">đã kiểm số</Badge>
                    )}
                  </div>
                ) : null}
              </>
            )}
          </div>
        )
      })}
    </>
  )
}

