"use client"

import * as React from "react"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { SendIcon, SquareIcon } from "lucide-react"

import { ChatMessages } from "@/components/chat-messages"
import { ErrorState } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import type { InsightContext } from "@/lib/insight-target"

const KIND_LABEL: Record<InsightContext["kind"], string> = {
  kpi: "Chỉ số KPI",
  chart: "Biểu đồ",
  insight: "Insight",
  "table-row": "Dòng bảng",
  segment: "Phân khúc",
  driver: "Yếu tố tác động",
  whatif: "Kịch bản what-if",
  "pipeline-stage": "Giai đoạn pipeline",
  quality: "Chất lượng dữ liệu",
  model: "Mô hình dữ liệu",
  decision: "Khuyến nghị",
}

/** One analyst conversation about one inspected element; remounted (fresh chat) per element. */
function InsightChat({ target, datasetId }: { target: InsightContext; datasetId: string | null }) {
  const [transport] = React.useState(() => new DefaultChatTransport({ api: "/api/chat" }))
  const { messages, sendMessage, status, error, stop } = useChat({ transport })
  const [input, setInput] = React.useState("")
  const busy = status === "submitted" || status === "streaming"
  const ask = React.useCallback(
    (text: string) => void sendMessage({ text }, { body: { datasetId, context: target } }),
    [sendMessage, datasetId, target]
  )
  const started = React.useRef(false)
  React.useEffect(() => {
    if (started.current) return
    started.current = true
    ask(`Giải thích “${target.label}” cho tôi: con số này nói gì, có ý nghĩa thống kê không, và hàm ý quyết định là gì?`)
  }, [ask, target.label])

  return (
    <>
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4">
        <ChatMessages messages={messages} />
        {status === "submitted" && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Spinner /> Đang phân tích…</p>}
        {error && <ErrorState error={error} title="AI Analyst gặp lỗi" />}
      </div>
      <SheetFooter>
        <form
          className="flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            const t = input.trim()
            if (!t || busy) return
            ask(t)
            setInput("")
          }}
        >
          <Textarea value={input} onChange={(e) => setInput(e.target.value.slice(0, 2000))} placeholder="Hỏi tiếp về phần tử này…" aria-label="Câu hỏi tiếp theo" />
          {busy ? (
            <Button type="button" variant="outline" onClick={() => void stop()}><SquareIcon /> Dừng</Button>
          ) : (
            <Button type="submit" disabled={!input.trim()}><SendIcon /> Gửi</Button>
          )}
        </form>
      </SheetFooter>
    </>
  )
}

export function InsightSheet({
  target,
  datasetId,
  requestKey,
  onClose,
}: {
  target: InsightContext | null
  datasetId: string | null
  requestKey: number
  onClose: () => void
}) {
  return (
    <Sheet open={target !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="flex w-full flex-col gap-0 sm:max-w-xl">
        {target && (
          <>
            <SheetHeader>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{KIND_LABEL[target.kind] ?? target.kind}</Badge>
                {datasetId && <Badge variant="secondary">{datasetId}</Badge>}
              </div>
              <SheetTitle>Hỏi AI: {target.label}</SheetTitle>
              <SheetDescription>Số liệu trong câu trả lời đều lấy từ tool (FastAPI/DuckDB) — xem các thẻ tool bên dưới.</SheetDescription>
            </SheetHeader>
            <InsightChat key={requestKey} target={target} datasetId={datasetId} />
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
