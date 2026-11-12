"use client"

import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { DataTable } from "@/components/data-table"
import { useDataset } from "@/components/dataset-provider"
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
      <SectionCards kpis={detail?.kpis} />
      <div className="px-4 lg:px-6">
        <ChartAreaInteractive
          points={ts.data?.points}
          title={meta ? `${ts.data?.agg ?? "median"} ${meta.target} over time` : "Trend"}
          subtitle={meta?.time_col ? `${meta.time_col} · ${ts.data?.freq ?? ""} periods · ${meta.source_file}` : "No time column"}
          metricLabel={meta?.target ?? "value"}
        />
      </div>
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
