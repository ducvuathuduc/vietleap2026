"use client"

import * as React from "react"
import { PlayIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { ResultTable } from "@/components/result-table"
import { EmptyState, ErrorState, LoadingState, PageShell } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { ModelsResponse, SqlResult, WarehouseTable } from "@/lib/api/types"

const MAX_LEN = 10_000
const READONLY = /^\s*(select|with|describe|summarize|show)\b/i

/** Example queries built only from tables that exist (star schema keys are date_key / geo_key by convention). */
function examples(tables: WarehouseTable[], models: ModelsResponse | undefined): { label: string; sql: string }[] {
  const out: { label: string; sql: string }[] = []
  const star = models?.models.star?.tables ?? []
  const fact = star.find((t) => t.startsWith("gold.fact_"))
  const geo = star.find((t) => t.endsWith("__dim_geo"))
  const date = star.find((t) => t.endsWith("__dim_date"))
  const q = (fq: string) => fq.replace(/^(\w+)\.(.+)$/, '$1."$2"')
  if (fact && geo)
    out.push({ label: "Fact × dim_geo theo vùng", sql: `SELECT g.region, g.province_2025, COUNT(*) AS so_dong\nFROM ${q(fact)} f\nJOIN ${q(geo)} g USING (geo_key)\nGROUP BY 1, 2\nORDER BY so_dong DESC` })
  if (fact && date)
    out.push({ label: "Fact × dim_date theo năm–quý", sql: `SELECT d.year, d.quarter, COUNT(*) AS so_dong\nFROM ${q(fact)} f\nJOIN ${q(date)} d USING (date_key)\nGROUP BY 1, 2\nORDER BY 1, 2` })
  out.push({ label: "Bảng trong warehouse", sql: "SELECT layer, name, rows, cols FROM (\n  SELECT schema_name AS layer, table_name AS name, estimated_size AS rows, column_count AS cols\n  FROM duckdb_tables()\n) ORDER BY layer, name" })
  const firstGold = tables.find((t) => t.layer === "gold")
  if (firstGold) out.push({ label: `Xem ${firstGold.name}`, sql: `SELECT * FROM gold."${firstGold.name}" LIMIT 50` })
  return out
}

export default function SqlPage() {
  const { datasetId } = useDataset()
  const tables = useAsync(() => api.tables(), [])
  const models = useAsync(() => (datasetId ? api.models(datasetId).catch(() => undefined) : null), [datasetId])
  const [query, setQuery] = React.useState("")
  const [result, setResult] = React.useState<SqlResult | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [running, setRunning] = React.useState(false)

  const ex = React.useMemo(() => examples(tables.data ?? [], models.data), [tables.data, models.data])
  const validation =
    query.trim() === "" ? "Nhập một câu SQL." :
    query.length > MAX_LEN ? `Câu SQL dài quá ${MAX_LEN.toLocaleString("vi-VN")} ký tự.` :
    !READONLY.test(query) ? "Chỉ cho phép truy vấn đọc: SELECT / WITH / DESCRIBE / SUMMARIZE." : null

  const run = async () => {
    if (validation || running) return
    setRunning(true)
    setError(null)
    try {
      setResult(await api.sql(query, 500))
    } catch (e) {
      setResult(null)
      setError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-3">
        <Card className="@5xl/main:col-span-2">
          <CardHeader>
            <CardTitle>SQL Explorer (DuckDB, chỉ đọc)</CardTitle>
            <CardDescription>Truy vấn trực tiếp bronze / silver / gold. DDL/DML, COPY, read_csv bị chặn ở API; tối đa 500 dòng.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void run()
              }}
              placeholder="SELECT ... FROM gold.&quot;...&quot; LIMIT 50"
              className="min-h-40 font-mono text-sm"
              aria-label="Câu SQL"
              aria-invalid={query !== "" && !!validation}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={() => void run()} disabled={!!validation || running}>
                {running ? <Spinner /> : <PlayIcon />} Chạy (Ctrl+Enter)
              </Button>
              {query !== "" && validation && <span className="text-sm text-destructive">{validation}</span>}
            </div>
            {ex.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {ex.map((e) => (
                  <Button key={e.label} variant="outline" size="sm" onClick={() => setQuery(e.sql)}>{e.label}</Button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Bảng trong warehouse</CardTitle>
            <CardDescription>Bấm để tạo câu SELECT mẫu.</CardDescription>
          </CardHeader>
          <CardContent>
            {tables.error ? (
              <ErrorState error={tables.error} />
            ) : tables.loading ? (
              <LoadingState rows={2} />
            ) : (tables.data ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Warehouse trống — hãy chạy pipeline trước.</p>
            ) : (
              <div className="flex max-h-80 flex-col gap-1 overflow-auto">
                {tables.data!.map((t) => (
                  <Button key={`${t.layer}.${t.name}`} variant="ghost" size="sm" className="justify-start" onClick={() => setQuery(`SELECT * FROM ${t.layer}."${t.name}" LIMIT 50`)}>
                    <Badge variant="outline">{t.layer}</Badge>
                    <span className="truncate">{t.name}</span>
                    <span className="ml-auto text-muted-foreground tabular-nums">{t.rows.toLocaleString("vi-VN")}</span>
                  </Button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <div className="px-4 lg:px-6">
        {error ? (
          <ErrorState error={error} title="Truy vấn lỗi" />
        ) : result ? (
          <Card>
            <CardHeader>
              <CardTitle>Kết quả</CardTitle>
              <CardAction className="text-sm text-muted-foreground">{result.row_count.toLocaleString("vi-VN")} dòng</CardAction>
            </CardHeader>
            <CardContent>
              <ResultTable columns={result.columns} rows={result.rows} />
            </CardContent>
          </Card>
        ) : (
          <EmptyState title="Chưa có kết quả" description="Viết câu SQL hoặc chọn một ví dụ rồi bấm Chạy." />
        )}
      </div>
    </PageShell>
  )
}
