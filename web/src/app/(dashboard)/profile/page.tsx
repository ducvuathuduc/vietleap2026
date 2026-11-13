"use client"

import * as React from "react"

import { useDataset } from "@/components/dataset-provider"
import { InsightChart } from "@/components/insight-chart"
import { ErrorState, LoadingState, PageShell } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { ColumnProfile } from "@/lib/api/types"
import { fmtNum } from "@/lib/format"

const SEV: Record<string, "destructive" | "secondary" | "outline"> = { high: "destructive", medium: "secondary", low: "outline" }

export default function ProfilePage() {
  const { datasetId } = useDataset()
  const { data, error, loading } = useAsync(() => (datasetId ? api.profile(datasetId) : null), [datasetId])
  const [picked, setCol] = React.useState<ColumnProfile | null>(null)
  const cols = data?.profile.column_profiles
  const col = picked && cols?.includes(picked) ? picked : (cols?.find((c) => c.hist) ?? null)
  if (error) return <PageShell><ErrorState error={error} /></PageShell>
  if (loading || !data) return <PageShell><LoadingState /></PageShell>
  const p = data.profile
  const stats = [
    { label: "Rows (clean)", value: p.rows.toLocaleString() },
    { label: "Columns", value: String(p.columns) },
    { label: "Missing cells", value: `${p.missing_overall_pct.toFixed(1)}%` },
    { label: "Rows with extreme values", value: `${p.outlier_rows_pct.toFixed(1)}%` },
  ]
  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardHeader>
              <CardDescription>{s.label}</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums">{s.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 px-4 lg:px-6 @5xl/main:grid-cols-3">
        <Card className="@5xl/main:col-span-2">
          <CardHeader>
            <CardTitle>Columns</CardTitle>
            <CardDescription>Inferred role, completeness and distribution. Click a numeric column to see its histogram.</CardDescription>
          </CardHeader>
          <CardContent className="overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Column</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="text-right">Missing</TableHead>
                  <TableHead className="text-right">Unique</TableHead>
                  <TableHead className="text-right">Median</TableHead>
                  <TableHead className="text-right">Min</TableHead>
                  <TableHead className="text-right">Max</TableHead>
                  <TableHead className="text-right">Outliers</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {p.column_profiles.map((c) => (
                  <TableRow key={c.name} data-state={col?.name === c.name ? "selected" : undefined} className="cursor-pointer" onClick={() => c.hist && setCol(c)}>
                    <TableCell className="max-w-48 truncate font-medium">{c.name}</TableCell>
                    <TableCell><Badge variant="outline" className="text-muted-foreground">{c.role}</Badge></TableCell>
                    <TableCell className="text-right tabular-nums">{c.missing_pct.toFixed(1)}%</TableCell>
                    <TableCell className="text-right tabular-nums">{c.unique.toLocaleString()}</TableCell>
                    <TableCell className="text-right tabular-nums">{typeof c.median === "number" ? fmtNum(c.median) : "–"}</TableCell>
                    <TableCell className="text-right tabular-nums">{typeof c.min === "number" ? fmtNum(c.min) : c.min ?? "–"}</TableCell>
                    <TableCell className="text-right tabular-nums">{typeof c.max === "number" ? fmtNum(c.max) : c.max ?? "–"}</TableCell>
                    <TableCell className="text-right tabular-nums">{c.outliers ?? "–"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>{col ? `Distribution of ${col.name}` : "Distribution"}</CardTitle>
              <CardDescription>1st–99th percentile, 20 bins</CardDescription>
            </CardHeader>
            <CardContent>
              {col?.hist ? (
                <InsightChart
                  spec={{ kind: "bar", x: col.hist.edges.slice(0, -1).map((e) => fmtNum(e)), series: [{ name: "count", data: col.hist.counts }] }}
                  height={200}
                />
              ) : (
                <div className="text-sm text-muted-foreground">No numeric column selected.</div>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Data-quality flags</CardTitle>
              <CardDescription>{p.issues.length} issue(s)</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              {p.issues.map((i, k) => (
                <div key={k} className="flex items-start gap-2">
                  <Badge variant={SEV[i.severity]}>{i.severity}</Badge>
                  <span><span className="font-medium">{i.column}</span>: {i.issue}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
      <div className="grid gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Cleaning log</CardTitle>
            <CardDescription>Every transformation, nothing deleted silently</CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="list-decimal space-y-1.5 pl-5 font-mono text-xs text-muted-foreground">
              {data.cleaning_log.map((l, i) => <li key={i}>{l}</li>)}
            </ol>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Caveats & limitations</CardTitle>
            <CardDescription>Say these before the judges do</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">
              {data.caveats.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </CardContent>
        </Card>
      </div>
    </PageShell>
  )
}
