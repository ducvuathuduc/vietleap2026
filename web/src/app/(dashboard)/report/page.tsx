"use client"

import { ArchiveIcon, DownloadIcon, FileSpreadsheetIcon, FileTextIcon, GlobeIcon, PresentationIcon, type LucideIcon } from "lucide-react"
import { useCallback } from "react"

import { useDataset } from "@/components/dataset-provider"
import { ExportDialog } from "@/components/export-dialog"
import { ErrorState, LoadingState, NoDatasetState, PageShell } from "@/components/state"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { api } from "@/lib/api/client"
import type { ExportKind } from "@/lib/api/types"

const DOWNLOADS: [ExportKind, string, string, LucideIcon][] = [
  ["bundle", "bundle", "Gói báo cáo", ArchiveIcon],
  ["dashboard_pdf", "dashboard_pdf", "Bản in dashboard", FileTextIcon],
  ["dashboard", "dashboard_html", "Dashboard tương tác", GlobeIcon],
  ["deck_vi", "deck_vi", "Bài trình bày tiếng Việt", PresentationIcon],
  ["deck", "deck", "Bài trình bày tiếng Anh", PresentationIcon],
  ["pitch_md", "pitch_md", "Kịch bản thuyết trình tiếng Việt", FileTextIcon],
  ["pitch_en", "pitch_en", "Kịch bản thuyết trình tiếng Anh", FileTextIcon],
  ["summary_pdf", "summary_pdf", "Tóm tắt điều hành", FileTextIcon],
  ["dictionary_csv", "dictionary_csv", "Từ điển dữ liệu", FileSpreadsheetIcon],
  ["dictionary_md", "dictionary_md", "Từ điển dữ liệu", FileTextIcon],
  ["eda_md", "eda_md", "Phân tích khám phá", FileTextIcon],
]

export default function ReportPage() {
  const { datasetId, detail, loading, error, refresh } = useDataset()
  const onDone = useCallback(() => { void refresh() }, [refresh])
  if (error) return <ErrorState error={error} />
  if (loading) return <LoadingState />
  if (!datasetId) return <NoDatasetState />
  if (!detail) return <LoadingState />
  const files = DOWNLOADS.flatMap(([kind, key, label, Icon]) => {
    const filename = detail.files[key]
    return typeof filename === "string" && filename
      ? [{ kind, label, Icon, format: filename.split(".").pop()?.toUpperCase() }]
      : []
  })
  return (
    <PageShell>
      <Card className="mx-4 lg:mx-6">
        <CardHeader>
          <CardTitle className="font-mono text-base font-semibold">{detail.meta.name}</CardTitle>
          <CardDescription>{detail.meta.rows.toLocaleString("vi-VN")} dòng · {files.length} tệp</CardDescription>
          <CardAction><ExportDialog key={datasetId} datasetId={datasetId} onDone={onDone} /></CardAction>
        </CardHeader>
        <CardContent>
          <Table aria-label="Tệp kết quả">
            <TableHeader><TableRow>
              <TableHead>Tài liệu</TableHead>
              <TableHead>Định dạng</TableHead>
              <TableHead className="text-right">Tải về</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {files.map(({ kind, format, label, Icon }) => (
                <TableRow key={kind}>
                  <TableCell className="whitespace-normal font-medium">
                    <span className="flex items-center gap-2">
                      <Icon className="size-4 shrink-0 text-muted-foreground" />
                      {label}
                    </span>
                  </TableCell>
                  <TableCell><Badge variant="secondary" className="font-mono text-[11px]">{format}</Badge></TableCell>
                  <TableCell className="text-right">
                    <Button nativeButton={false} variant="ghost" size="icon-sm" aria-label={`Tải ${label} (${format})`}
                      render={<a href={api.fileUrl(datasetId, kind)} download />}><DownloadIcon /></Button>
                  </TableCell>
                </TableRow>
              ))}
              {files.length === 0 && <TableRow><TableCell colSpan={3}>Chưa có tệp kết quả.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </PageShell>
  )
}
