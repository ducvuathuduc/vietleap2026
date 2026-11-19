"use client"

import { BriefQuestionCard } from "@/components/brief-question-card"
import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { DataTable } from "@/components/data-table"
import { useDataset } from "@/components/dataset-provider"
import { ProvinceRankingCard } from "@/components/province-ranking-card"
import { SectionCards } from "@/components/section-cards"
import { ErrorState, LoadingState, PageShell } from "@/components/state"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"

export default function OverviewPage() {
  const { datasetId, detail, error } = useDataset()
  const ts = useAsync(() => (datasetId ? api.timeseries(datasetId) : null), [datasetId])
  const ins = useAsync(() => (datasetId ? api.insights(datasetId) : null), [datasetId])
  const prof = useAsync(() => (datasetId ? api.profile(datasetId) : null), [datasetId])
  if (error) return <PageShell><ErrorState error={error} /></PageShell>
  const meta = detail?.meta
  return (
    <PageShell>
      {datasetId && detail && (
        <div className="px-4 lg:px-6">
          <BriefQuestionCard datasetId={datasetId} hasBrief={detail.has_brief} />
        </div>
      )}
      <SectionCards kpis={detail?.kpis} />
      <div className="px-4 lg:px-6">
        <ChartAreaInteractive
          points={ts.data?.points}
          title={meta ? `Diễn biến ${meta.target} theo thời gian` : "Xu hướng theo thời gian"}
          subtitle={meta?.time_col ? `${meta.time_col} · ${ts.data?.freq ?? ""} · ${meta.source_file}` : "Chưa xác định cột thời gian"}
          metricLabel={meta?.target ?? "value"}
          gaps={ts.data?.gaps}
        />
      </div>
      {datasetId && (
        <div className="px-4 lg:px-6">
          <ProvinceRankingCard datasetId={datasetId} silentOnMissing />
        </div>
      )}
      {ins.error ? (
        <ErrorState error={ins.error} />
      ) : ins.data && datasetId && prof.data ? (
        <DataTable
          insights={ins.data.insights}
          recommendations={ins.data.recommendations}
          cleaningLog={prof.data.cleaning_log}
          datasetId={datasetId}
        />
      ) : (
        <LoadingState rows={1} />
      )}
    </PageShell>
  )
}
