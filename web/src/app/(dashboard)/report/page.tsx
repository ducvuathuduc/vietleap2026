"use client"

import { useCallback } from "react"

import { useDataset } from "@/components/dataset-provider"
import { ExportDialog } from "@/components/export-dialog"
import { ErrorState, LoadingState, NoDatasetState, PageShell } from "@/components/state"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api/client"
import type { ExportKind } from "@/lib/api/types"

const DOWNLOADS: [ExportKind, string, string][] = [
  ["bundle", "bundle", "Gói ZIP"],
  ["dashboard_pdf", "dashboard_pdf", "Dashboard (PDF)"],
  ["dashboard", "dashboard_html", "Dashboard (HTML)"],
  ["deck_vi", "deck_vi", "Deck tiếng Việt"],
  ["deck", "deck", "Deck tiếng Anh"],
  ["pitch_md", "pitch_md", "Pitch tiếng Việt"],
  ["pitch_en", "pitch_en", "Pitch tiếng Anh"],
  ["summary_pdf", "summary_pdf", "Tóm tắt điều hành (PDF)"],
  ["dictionary_csv", "dictionary_csv", "Từ điển dữ liệu (CSV)"],
  ["dictionary_md", "dictionary_md", "Từ điển dữ liệu (Markdown)"],
  ["eda_md", "eda_md", "Phân tích khám phá"],
]

export default function ReportPage() {
  const { datasetId, detail, loading, error, refresh } = useDataset()
  const onDone = useCallback(() => { void refresh() }, [refresh])
  if (error) return <ErrorState error={error} />
  if (loading) return <LoadingState />
  if (!datasetId) return <NoDatasetState />
  if (!detail || detail.meta.name !== datasetId) return <LoadingState />
  return (
    <PageShell>
      <Card className="mx-4 lg:mx-6">
        <CardHeader><CardTitle>Xuất báo cáo</CardTitle></CardHeader>
        <CardContent className="flex flex-col items-start gap-4">
          <p className="text-sm text-muted-foreground">{datasetId}</p>
          <ExportDialog key={datasetId} datasetId={datasetId} onDone={onDone} />
          <div className="flex flex-wrap gap-2">
            {DOWNLOADS.filter(([, key]) => detail.files[key]).map(([kind, , label]) => (
              <Button key={kind} variant="outline" size="sm" render={<a href={api.fileUrl(datasetId, kind)} />}>{label}</Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </PageShell>
  )
}
