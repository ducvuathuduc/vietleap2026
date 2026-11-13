"use client"

import * as React from "react"
import { AlertTriangleIcon, WandSparklesIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { CodeBlock } from "@/components/result-table"
import { EmptyState, ErrorState, PageShell } from "@/components/state"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { Brief } from "@/lib/api/types"

const MIN = 10
const MAX = 20_000
const UNIT_VI: Record<string, string> = {
  province: "tỉnh", district: "quận/huyện", region: "vùng", year: "năm", quarter: "quý", month: "tháng",
  firm: "doanh nghiệp", sector: "ngành", country: "quốc gia", household: "hộ gia đình",
}

function Chips({ items, empty = "–" }: { items: string[]; empty?: string }) {
  if (items.length === 0) return <span className="text-muted-foreground">{empty}</span>
  return <div className="flex flex-wrap gap-1">{items.map((x) => <Badge key={x} variant="outline">{x}</Badge>)}</div>
}

export default function BriefPage() {
  const { datasetId } = useDataset()
  const samples = useAsync(() => api.briefSamples(), [])
  const [text, setText] = React.useState("")
  const [useDs, setUseDs] = React.useState(true)
  const [brief, setBrief] = React.useState<Brief | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)
  const invalid = text.trim().length < MIN ? `Dán đề bài (tối thiểu ${MIN} ký tự).` : text.length > MAX ? `Tối đa ${MAX.toLocaleString("vi-VN")} ký tự.` : null

  const run = async () => {
    if (invalid || busy) return
    setBusy(true)
    setError(null)
    try {
      setBrief(await api.brief(text, useDs ? datasetId : null))
    } catch (e) {
      setBrief(null)
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const sampleItems = (samples.data ?? []).map((s) => ({ label: s.name, value: s.name }))
  const cfg = brief?.run_config
  const cli = cfg ? `python run.py <file>${cfg.target ? ` --target "${cfg.target}"` : ""}${cfg.domain !== "auto" ? ` --domain ${cfg.domain}` : ""}` : ""

  return (
    <PageShell>
      <div className="px-4 lg:px-6">
        <Card>
          <CardHeader>
            <CardTitle>Dán đề bài → kế hoạch phân tích</CardTitle>
            <CardDescription>Phân tích bằng luật (offline): câu hỏi, biến mục tiêu, đơn vị, loại quyết định, gói kịch bản phù hợp.</CardDescription>
            <CardAction>
              {sampleItems.length > 0 && (
                <Select value="" onValueChange={(v) => { const s = samples.data?.find((x) => x.name === v); if (s) setText(s.text) }} items={sampleItems}>
                  <SelectTrigger size="sm" className="w-56" aria-label="Đề mẫu"><SelectValue placeholder="Chọn đề mẫu" /></SelectTrigger>
                  <SelectContent align="end">
                    <SelectGroup>{sampleItems.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}</SelectGroup>
                  </SelectContent>
                </Select>
              )}
            </CardAction>
          </CardHeader>
          <CardContent>
            <Textarea value={text} onChange={(e) => setText(e.target.value)} className="min-h-48" placeholder="Dán nguyên văn đề bài của BTC (tiếng Việt hoặc tiếng Anh)…" aria-label="Đề bài" aria-invalid={text !== "" && !!invalid} />
            {text !== "" && invalid && <p className="mt-2 text-sm text-destructive">{invalid}</p>}
          </CardContent>
          <CardFooter className="flex flex-wrap items-center gap-4">
            <Label className="flex items-center gap-2">
              <Checkbox checked={useDs && !!datasetId} disabled={!datasetId} onCheckedChange={(v) => setUseDs(v === true)} />
              Khớp với cột của dataset đang chọn{datasetId ? ` (${datasetId})` : " (chưa có dataset)"}
            </Label>
            <Button className="ml-auto" onClick={() => void run()} disabled={!!invalid || busy}>
              {busy ? <Spinner /> : <WandSparklesIcon />} Phân tích đề
            </Button>
          </CardFooter>
        </Card>
      </div>

      {error && <ErrorState error={error} title="Không phân tích được đề" />}
      {!brief && !error && <EmptyState title="Chưa có kế hoạch" description="Dán đề hoặc chọn một đề mẫu, rồi bấm Phân tích đề." />}

      {brief && (
        <>
          {brief.warnings.length > 0 && (
            <div className="px-4 lg:px-6">
              <Alert>
                <AlertTriangleIcon />
                <AlertTitle>Cần kiểm tra</AlertTitle>
                <AlertDescription>{brief.warnings.join(" ")}</AlertDescription>
              </Alert>
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-3">
            <Card>
              <CardHeader>
                <CardDescription>Biến mục tiêu</CardDescription>
                <CardTitle className="text-2xl">{brief.target?.label ?? "Chưa xác định"}</CardTitle>
                {brief.target?.column && <CardAction><Badge>{brief.target.column}</Badge></CardAction>}
              </CardHeader>
              <CardContent className="flex flex-col gap-2 text-sm">
                <div className="text-muted-foreground">{brief.target?.resolved}</div>
                {brief.alternatives.length > 0 && (
                  <div>Ứng viên khác: <Chips items={brief.alternatives.map((a) => `${a.label}${a.column ? ` → ${a.column}` : ""}`)} /></div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Phạm vi</CardDescription>
                <CardTitle>Đơn vị · phân khúc · thời gian</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2 text-sm">
                <div>Đơn vị: <Chips items={brief.units.map((u) => UNIT_VI[u] ?? u)} /></div>
                <div>Phân khúc: <Chips items={brief.segments} empty="engine tự chọn" /></div>
                <div>Thời gian: {brief.time.range ? `${brief.time.range[0]}–${brief.time.range[1]}` : "không nêu"}</div>
                <div>Ngôn ngữ đề: {brief.language === "vi" ? "Tiếng Việt" : "English"}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Đầu ra</CardDescription>
                <CardTitle>Quyết định & sản phẩm</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2 text-sm">
                <div>Loại quyết định: <Chips items={brief.decision_types.map((d) => d.label)} /></div>
                <div>Sản phẩm BTC yêu cầu: <Chips items={brief.deliverables} /></div>
                <div>Nguồn dữ liệu được nhắc: <Chips items={brief.data_sources_mentioned} /></div>
              </CardContent>
            </Card>
          </div>
          <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Kế hoạch phân tích</CardTitle>
                <CardDescription>Chạy engine với cấu hình dưới đây.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm">
                <ol className="list-decimal space-y-1 pl-5">{brief.plan.map((p) => <li key={p}>{p}</li>)}</ol>
                <CodeBlock code={cli} label="Lệnh chạy engine" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Câu hỏi trích từ đề</CardTitle>
                <CardDescription>{brief.questions.length} câu</CardDescription>
              </CardHeader>
              <CardContent>
                {brief.questions.length === 0 ? <p className="text-sm text-muted-foreground">Không tìm thấy câu hỏi rõ ràng.</p> : (
                  <ul className="list-disc space-y-1 pl-5 text-sm">{brief.questions.map((q) => <li key={q}>{q}</li>)}</ul>
                )}
              </CardContent>
            </Card>
          </div>
          {brief.pack && (
            <div className="px-4 lg:px-6">
              <Card>
                <CardHeader>
                  <CardDescription>Gói kịch bản phù hợp nhất · {brief.pack.sponsor}</CardDescription>
                  <CardTitle>{brief.pack.title}</CardTitle>
                  <CardAction><Badge variant="outline">{brief.pack.id}</Badge></CardAction>
                </CardHeader>
                <CardContent className="grid grid-cols-1 gap-4 text-sm @3xl/main:grid-cols-3">
                  <div>
                    <div className="mb-1 font-medium">KPI gợi ý</div>
                    <ul className="list-disc space-y-1 pl-5">{brief.pack.kpis.map((k) => <li key={k}>{k}</li>)}</ul>
                    <div className="mt-3 mb-1 font-medium">Cột kỳ vọng</div>
                    <ul className="list-disc space-y-1 pl-5">{brief.pack.expected_columns.map((k) => <li key={k}>{k}</li>)}</ul>
                  </div>
                  <div>
                    <div className="mb-1 font-medium">Mẫu khuyến nghị</div>
                    <dl className="space-y-1">
                      <div><dt className="inline font-medium">Ai: </dt><dd className="inline">{brief.pack.decision_template.who}</dd></div>
                      <div><dt className="inline font-medium">Làm gì: </dt><dd className="inline">{brief.pack.decision_template.what}</dd></div>
                      <div><dt className="inline font-medium">Ở đâu: </dt><dd className="inline">{brief.pack.decision_template.where}</dd></div>
                      <div><dt className="inline font-medium">Đo bằng: </dt><dd className="inline">{brief.pack.decision_template.kpi}</dd></div>
                      <div className="text-muted-foreground">Lưu ý: {brief.pack.decision_template.caveat}</div>
                    </dl>
                  </div>
                  <div>
                    <div className="mb-1 font-medium">Mạch slide pitch</div>
                    <ol className="list-decimal space-y-1 pl-5">{brief.pack.deck_storyline.map((k) => <li key={k}>{k}</li>)}</ol>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}
    </PageShell>
  )
}
