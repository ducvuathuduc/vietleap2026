"use client"

import { useDataset } from "@/components/dataset-provider"
import { MermaidDiagram } from "@/components/mermaid-diagram"
import { ResultTable } from "@/components/result-table"
import { StatCards } from "@/components/stat-cards"
import { PageShell, datasetGate } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { ModelKind } from "@/lib/api/types"
import { SOURCE_KINDS, fmtSeconds } from "@/lib/source-kinds"
import { insightTarget } from "@/lib/insight-target"

const MODEL_LABEL: Record<ModelKind, string> = { obt: "OBT", star: "Star", snowflake: "Snowflake", data_vault: "Data Vault", conformed: "Conformed" }

export default function PipelinePage() {
  const { datasetId, loading: dsLoading, error: dsError } = useDataset()
  const r = useAsync(
    () => (datasetId ? Promise.all([api.pipeline(datasetId), api.lineage(datasetId)]) : null),
    [datasetId]
  )
  const gate = datasetGate({ datasetId, datasetsLoading: dsLoading, datasetsError: dsError, loading: r.loading, error: r.error, hasData: !!r.data })
  if (gate || !r.data) return <PageShell>{gate}</PageShell>
  const [p, lineage] = r.data

  const scores = Object.values(p.quality)
  const avg = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN)
  const before = avg(scores.map((s) => s.score_before))
  const after = avg(scores.map((s) => s.score_after))
  const kinds = [...new Set(p.provenance.map((s) => s.kind))]
  const models = (Object.keys(p.models) as ModelKind[]).map((m) => MODEL_LABEL[m])

  return (
    <PageShell>
      <div className="px-4 lg:px-6">
        <p className="text-sm text-muted-foreground">
          Vòng đời dữ liệu end-to-end <span className="font-medium text-foreground">Ingestion → Storage → Transform → Serving</span> · dataset{" "}
          <span className="font-medium text-foreground">{p.dataset}</span> · lần chạy {p.run_id} · xong lúc {p.finished_at}
        </p>
      </div>
      <StatCards
        items={[
          {
            label: "1 · Ingestion — thu thập",
            value: `${p.provenance.length} nguồn`,
            badge: kinds.map((k) => SOURCE_KINDS[k]?.label ?? k).join(" · "),
            footer: `Thời gian ${fmtSeconds(p.timings.ingest)}`,
            hint: "DB/JDBC · Public API · File · Scraping · Social",
            target: insightTarget("pipeline-stage", "ingestion", "Ingestion — thu thập", { sources: p.provenance.map((s) => ({ source: s.source, kind: s.kind, fetched_at: s.fetched_at })), seconds: p.timings.ingest }),
          },
          {
            label: "2 · Storage — DuckDB + Parquet",
            value: `${p.bronze.length} bảng bronze`,
            badge: "medallion",
            footer: "Giữ dữ liệu thô + _src, _ingested_at, _row_hash",
            hint: "bronze → silver → gold, meta.lineage",
            target: insightTarget("pipeline-stage", "storage", "Storage — DuckDB + Parquet", { bronze: p.bronze }),
          },
          {
            label: "3 · Transform — làm sạch & mô hình",
            value: `${p.silver.length} bảng silver`,
            badge: Number.isFinite(before) ? `điểm TB ${before.toFixed(1)} → ${after.toFixed(1)}` : undefined,
            footer: `Làm sạch ${fmtSeconds(p.timings.clean)} · mô hình ${fmtSeconds(p.timings.model)}`,
            hint: "Missing · Duplicate · Outlier (gắn cờ, không xoá)",
            target: insightTarget("pipeline-stage", "transform", "Transform — làm sạch & mô hình", { quality: p.quality }),
          },
          {
            label: "4 · Serving — gold & dashboard",
            value: `${p.gold.length} bảng gold`,
            badge: models.join(" · "),
            footer: `Phục vụ ${fmtSeconds(p.timings.serve)}`,
            hint: `Dashboard dùng ${MODEL_LABEL[p.recommended.serving]}, ngữ nghĩa ${MODEL_LABEL[p.recommended.semantic]}`,
            target: insightTarget("pipeline-stage", "serving", "Serving — gold & dashboard", { gold: p.gold, recommended: p.recommended }),
          },
        ]}
      />

      <div className="px-4 lg:px-6">
        <Card data-tour="lineage">
          <CardHeader>
            <CardTitle>Sơ đồ lineage</CardTitle>
            <CardDescription>Nguồn → bronze → silver → gold, mỗi cạnh là một bước biến đổi đã chạy thật.</CardDescription>
          </CardHeader>
          <CardContent>
            {lineage.mermaid ? (
              <MermaidDiagram code={lineage.mermaid} label="Sơ đồ lineage dữ liệu" />
            ) : (
              <p className="text-sm text-muted-foreground">Chưa có file lineage.mmd cho dataset này.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Nguồn dữ liệu & provenance</CardTitle>
            <CardDescription>Nguồn, thời điểm tải (Asia/Saigon), giấy phép, số dòng — để truy vết mọi con số.</CardDescription>
          </CardHeader>
          <CardContent>
            <ResultTable
              columns={["Nguồn", "Loại", "Tải lúc", "Số dòng", "Giấy phép", "URI"]}
              rows={p.provenance.map((s) => [
                s.source,
                SOURCE_KINDS[s.kind]?.label ?? s.kind,
                s.fetched_at,
                Object.values(s.tables ?? {}).reduce((a, t) => a + t.rows, 0),
                s.license_note,
                s.uri,
              ])}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Các bước đã chạy</CardTitle>
            <CardDescription>Nhật ký lần chạy {p.run_id}.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-2">
              {p.steps.length === 0 && <p className="text-sm text-muted-foreground">Không có bước nào được ghi.</p>}
              {p.steps.map((s, i) => (
                <div key={`${s.step}-${i}`} className="flex flex-wrap items-center gap-2 rounded-lg border p-2 text-sm">
                  <Badge variant={s.status === "ok" ? "outline" : "destructive"}>{s.status === "ok" ? "thành công" : "lỗi"}</Badge>
                  <span className="font-medium">{s.step}</span>
                  {s.tables && <span className="text-muted-foreground">{s.tables.join(", ")}</span>}
                  {typeof s.error === "string" && <span className="text-destructive">{s.error}</span>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </PageShell>
  )
}
