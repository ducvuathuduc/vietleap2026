"use client"

import { getToolName, isToolUIPart, type UIMessage } from "ai"
import { ChevronDownIcon, WrenchIcon } from "lucide-react"

import { ResultTable } from "@/components/result-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Spinner } from "@/components/ui/spinner"

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

/** Renders AI SDK UI messages: text parts as prose, tool calls as collapsible Cards. */
export function ChatMessages({ messages }: { messages: UIMessage[] }) {
  return (
    <>
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
    </>
  )
}
