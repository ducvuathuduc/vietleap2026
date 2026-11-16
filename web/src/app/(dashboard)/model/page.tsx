"use client"

import { useDataset } from "@/components/dataset-provider"
import { JoinCoverageCard, KEY_LABEL } from "@/components/join-coverage"
import { MermaidDiagram } from "@/components/mermaid-diagram"
import { CodeBlock, ResultTable } from "@/components/result-table"
import { EmptyState, PageShell, datasetGate } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { ModelKind, ModelsResponse } from "@/lib/api/types"
import { insightTarget } from "@/lib/insight-target"

const ORDER: { key: ModelKind; label: string; role: string }[] = [
  { key: "obt", label: "OBT", role: "One Big Table — phục vụ dashboard/ML" },
  { key: "star", label: "Star", role: "Kimball fact + dim — mô hình ngữ nghĩa" },
  { key: "snowflake", label: "Snowflake", role: "Dim chuẩn hoá nhiều tầng" },
  { key: "data_vault", label: "Data Vault", role: "Hub / Link / Satellite — truy vết lịch sử" },
  { key: "conformed", label: "Conformed", role: "Dim chung nhiều nguồn (bus matrix) + OBT tích hợp" },
]

function ConformedDetails({ datasetId, keys }: { datasetId: string; keys: NonNullable<ModelsResponse["keys"]> }) {
  const r = useAsync(() => api.conformed(datasetId), [datasetId])
  const detected = Object.entries(keys.detected ?? {}).flatMap(([src, cols]) => Object.entries(cols).map(([k, col]) => [src, KEY_LABEL[k] ?? k, col]))
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Khoá chung & dimension dùng chung</CardTitle>
          <CardDescription>Khoá {keys.shared.map((k) => KEY_LABEL[k] ?? k).join(", ") || "–"} được nhận diện tự động ở từng nguồn.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <ResultTable columns={["Khoá", "Dimension chung"]} rows={Object.entries(keys.dims).map(([k, d]) => [KEY_LABEL[k] ?? k, d])} />
          {detected.length > 0 && <ResultTable columns={["Nguồn", "Khoá", "Cột nhận diện"]} rows={detected} />}
        </CardContent>
      </Card>
      {r.data ? (
        <JoinCoverageCard c={r.data} />
      ) : r.error ? (
        <p className="text-sm text-muted-foreground">Không đọc được conformed.json: {r.error.message}</p>
      ) : null}
    </>
  )
}

export default function ModelPage() {
  const { datasetId, loading: dsLoading, error: dsError } = useDataset()
  const r = useAsync(() => (datasetId ? api.models(datasetId) : null), [datasetId])
  const gate = datasetGate({ datasetId, datasetsLoading: dsLoading, datasetsError: dsError, loading: r.loading, error: r.error, hasData: !!r.data })
  if (gate || !r.data) return <PageShell>{gate}</PageShell>
  const m = r.data
  const available = ORDER.filter((o) => m.models[o.key])
  if (available.length === 0)
    return (
      <PageShell>
        <EmptyState title="Chưa có mô hình dữ liệu" description="Pipeline chưa sinh bảng gold cho dataset này." />
      </PageShell>
    )
  const recBadges = (k: ModelKind) => [
    m.recommended.serving === k ? "Khuyến nghị cho dashboard" : null,
    m.recommended.semantic === k ? "Khuyến nghị để trình bày mô hình" : null,
  ].filter((x): x is string => !!x)
  const plan = m.column_plan

  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
        <Card data-tour="model-choice">
          <CardHeader>
            <CardTitle>Chọn mô hình theo quy mô hackathon</CardTitle>
            <CardDescription>Cả 4 mô hình được sinh tự động từ cùng bảng silver (thêm Conformed khi ≥2 nguồn chung khoá); số bảng lấy từ warehouse.</CardDescription>
          </CardHeader>
          <CardContent>
            <ResultTable
              columns={["Mô hình", "Vai trò", "Số bảng gold", "Khuyến nghị"]}
              rows={available.map((o) => [o.label, o.role, m.models[o.key]?.tables.length ?? 0, recBadges(o.key).join(" · ") || "–"])}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Phân vai cột (column plan)</CardTitle>
            <CardDescription>Engine tự nhận diện vai trò cột để dựng dim và fact.</CardDescription>
          </CardHeader>
          <CardContent>
            <ResultTable
              columns={["Vai trò", "Cột"]}
              rows={[
                ["Thời gian", plan.time ?? "–"],
                ["Địa lý (tỉnh)", plan.province ?? "–"],
                ["Phân loại → dim", plan.cats.join(", ") || "–"],
                ["Số đo → fact", plan.measures.join(", ") || "–"],
                ["Khoá nghiệp vụ", plan.ids.join(", ") || "–"],
              ]}
            />
          </CardContent>
        </Card>
      </div>
      <div className="px-4 lg:px-6">
        <Tabs defaultValue={available[0].key}>
          <TabsList>
            {available.map((o) => (
              <TabsTrigger key={o.key} value={o.key}>{o.label}</TabsTrigger>
            ))}
          </TabsList>
          {available.map((o) => {
            const info = m.models[o.key]!
            const sql = m.sql[o.key]
            return (
              <TabsContent key={o.key} value={o.key} className="flex flex-col gap-4">
                <Card {...insightTarget("model", o.key, `Mô hình ${o.label}`, { tables: info.tables, rationale: m.rationale[o.key], recommended: recBadges(o.key) })}>
                  <CardHeader>
                    <CardTitle>{o.label}</CardTitle>
                    <CardDescription>{m.rationale[o.key] ?? o.role}</CardDescription>
                    <CardAction className="flex flex-wrap gap-1">
                      {recBadges(o.key).map((b) => <Badge key={b}>{b}</Badge>)}
                    </CardAction>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-1">
                    {info.tables.map((t) => <Badge key={t} variant="outline">{t}</Badge>)}
                  </CardContent>
                </Card>
                {o.key === "conformed" && m.keys && datasetId ? <ConformedDetails datasetId={datasetId} keys={m.keys} /> : null}
                <Card>
                  <CardHeader>
                    <CardTitle>ERD</CardTitle>
                    <CardDescription>Sơ đồ quan hệ thực thể (Mermaid) sinh từ schema thật.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <MermaidDiagram code={info.erd} label={`ERD mô hình ${o.label}`} />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>SQL DuckDB</CardTitle>
                    <CardDescription>Câu lệnh đã chạy để dựng mô hình ({`out/<dataset>/models/${o.key}.sql`}).</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {sql ? <CodeBlock code={sql} label={`SQL mô hình ${o.label}`} /> : <p className="text-sm text-muted-foreground">Không có file SQL.</p>}
                  </CardContent>
                </Card>
              </TabsContent>
            )
          })}
        </Tabs>
      </div>
    </PageShell>
  )
}
