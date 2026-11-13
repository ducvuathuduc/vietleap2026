"use client"

import { CircleCheckIcon, InfoIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { EmptyState, PageShell, datasetGate } from "@/components/state"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import { fmtP } from "@/lib/format"

const CONFIDENCE = { high: "Tin cậy cao", medium: "Tin cậy trung bình" } as const

export default function DecisionPage() {
  const { datasetId, detail, loading: dsLoading, error: dsError } = useDataset()
  const r = useAsync(() => (datasetId ? api.insights(datasetId) : null), [datasetId])
  const gate = datasetGate({ datasetId, datasetsLoading: dsLoading, datasetsError: dsError, loading: r.loading, error: r.error, hasData: !!r.data })
  if (gate || !r.data) return <PageShell>{gate}</PageShell>
  const byId = Object.fromEntries(r.data.insights.map((i) => [i.id, i]))
  const recs = r.data.recommendations

  return (
    <PageShell>
      <div className="px-4 lg:px-6">
        <Alert>
          <InfoIcon />
          <AlertTitle>Từ dữ liệu đến quyết định</AlertTitle>
          <AlertDescription>
            Mỗi khuyến nghị sinh từ một insight đã kiểm định thống kê. Dữ liệu quan sát cho thấy quan hệ liên đới, không chứng minh nhân quả —
            đề xuất thí điểm và đo bằng KPI trước khi nhân rộng.
          </AlertDescription>
        </Alert>
      </div>
      {recs.length === 0 ? (
        <EmptyState title="Chưa có khuyến nghị" description="Engine chưa tìm thấy insight đủ mạnh để chuyển thành khuyến nghị cho dataset này." />
      ) : (
        <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
          {recs.map((rec, idx) => {
            const ins = byId[rec.from_insight]
            return (
              <Card key={`${rec.from_insight}-${idx}`} className="@container/card">
                <CardHeader>
                  <CardDescription>Khuyến nghị {idx + 1}{ins ? ` · từ insight #${ins.rank}` : ""}</CardDescription>
                  <CardTitle className="text-lg">{ins?.title_vi ?? rec.type}</CardTitle>
                  <CardAction>
                    <Badge variant={rec.confidence === "high" ? "default" : "outline"}>
                      {rec.confidence === "high" && <CircleCheckIcon />}
                      {CONFIDENCE[rec.confidence] ?? rec.confidence}
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardContent className="flex flex-col gap-3 text-sm leading-relaxed">
                  <div><span className="font-medium">Vấn đề (so what): </span>{rec.so_what_vi}</div>
                  <div><span className="font-medium">Hành động (now what): </span>{rec.now_what_vi}</div>
                  <div><span className="font-medium">Tác động ước tính: </span>{rec.impact_vi}</div>
                </CardContent>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  {ins && (
                    <div className="text-muted-foreground">
                      Bằng chứng: {ins.test}
                      {ins.p_value !== null ? ` · ${fmtP(ins.p_value)}` : ""}
                      {ins.effect !== null ? ` · effect size ${ins.effect.toFixed(2)}` : ""}
                    </div>
                  )}
                  {ins?.caveat && <div className="text-xs text-muted-foreground">Lưu ý: {ins.caveat}</div>}
                </CardFooter>
              </Card>
            )
          })}
        </div>
      )}
      {detail && detail.caveats.length > 0 && (
        <div className="px-4 lg:px-6">
          <Card>
            <CardHeader>
              <CardTitle>Hạn chế của dữ liệu</CardTitle>
              <CardDescription>Nói rõ với giám khảo trước khi trình bày quyết định.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {detail.caveats.map((c) => <li key={c}>{c}</li>)}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </PageShell>
  )
}
