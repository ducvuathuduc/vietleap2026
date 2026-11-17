"use client"

import { useAsync } from "@/hooks/use-async"
import { SectionCards } from "@/components/section-cards"
import { ErrorState, LoadingState } from "@/components/state"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ApiError, api } from "@/lib/api/client"

async function loadPrintData() {
  const id = new URLSearchParams(window.location.search).get("dataset")
  if (!id) throw new Error("Chọn dataset để in báo cáo.")
  const [detail, evidence, pipeline] = await Promise.all([
    api.dataset(id), api.insights(id), api.pipeline(id).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 404) return null
      throw error
    }),
  ])
  const brief = detail.has_brief ? await api.datasetBrief(id) : null
  return { id, detail, evidence, pipeline, brief }
}

export default function PrintPage() {
  const { data, error } = useAsync(loadPrintData, [])
  if (error) return <ErrorState error={error} />
  if (!data) return <LoadingState />
  const { id, detail, evidence, pipeline, brief } = data
  const question = brief?.questions.find((item) => item.trim()) ?? brief?.pack?.decision_template.question ?? brief?.title
  const recommendation = evidence.recommendations.find((rec) => evidence.insights.some((item) =>
    item.id === rec.from_insight && !item.weak && (item.p_value === null || item.p_value < 0.05)))
  return (
    <main data-print-ready={id} className="@container/main mx-auto flex w-full max-w-6xl flex-col gap-4 p-4">
      <h1 className="text-2xl font-semibold">Tổng quan · {detail.meta.name}</h1>
      {question && <p>{question}</p>}
      <SectionCards kpis={detail.kpis} />
      <Card className="break-inside-avoid">
        <CardHeader><CardTitle>Pipeline</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {pipeline ? <>
            <p>Mã lượt chạy {pipeline.run_id}</p>
            <p>Bronze · {pipeline.bronze.join(", ")}</p>
            <p>Silver · {pipeline.silver.join(", ")}</p>
            <p>Gold · {pipeline.gold.join(", ")}</p>
          </> : <p>Dataset này chưa có kết quả pipeline.</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Bằng chứng</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {evidence.insights.map((insight) => <article key={insight.id} className="break-inside-avoid">
            <h2 className="font-medium">{insight.title_vi}</h2>
            <p>{insight.sentence_vi}</p>
            <p className="text-sm text-muted-foreground">{insight.test}{insight.p_value !== null ? ` · p ${insight.p_value}` : ""}</p>
          </article>)}
        </CardContent>
      </Card>
      <Card className="break-inside-avoid">
        <CardHeader><CardTitle>Quyết định và hạn chế</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          <p>{recommendation?.now_what_vi ?? "Cần thêm bằng chứng để chốt hành động."}</p>
          <ul className="list-inside list-disc">{detail.caveats.map((item) => <li key={item}>{item}</li>)}</ul>
        </CardContent>
      </Card>
    </main>
  )
}
