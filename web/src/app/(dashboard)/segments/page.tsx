"use client"

import * as React from "react"

import { useDataset } from "@/components/dataset-provider"
import { InsightChart } from "@/components/insight-chart"
import { ErrorState, LoadingState, PageShell } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import { fmtNum, fmtP } from "@/lib/format"

export default function SegmentsPage() {
  const { datasetId } = useDataset()
  const [picked, setPicked] = React.useState<{ ds: string | null; by: string } | null>(null)
  const by = picked && picked.ds === datasetId ? picked.by : undefined
  const setBy = (v: string) => setPicked({ ds: datasetId, by: v })
  const { data, error, loading } = useAsync(() => (datasetId ? api.segments(datasetId, { by }) : null), [datasetId, by])
  if (error) return <PageShell><ErrorState error={error} /></PageShell>
  if (loading && !data) return <PageShell><LoadingState /></PageShell>
  if (!data) return null
  const t = data.test
  const opts = data.options.map((o) => ({ label: o, value: o }))
  return (
    <PageShell>
      <div className="grid gap-4 px-4 lg:px-6 @5xl/main:grid-cols-3">
        <Card className="@5xl/main:col-span-2">
          <CardHeader>
            <CardTitle>Median {data.metric} by {data.by}</CardTitle>
            <CardDescription>Top {data.groups.length} of {data.groups_total} groups</CardDescription>
            <CardAction>
              <Select value={data.by} onValueChange={(v) => v && setBy(v)} items={opts}>
                <SelectTrigger size="sm" className="w-48"><SelectValue /></SelectTrigger>
                <SelectContent align="end">
                  <SelectGroup>
                    {opts.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </CardAction>
          </CardHeader>
          <CardContent>
            <InsightChart spec={{ kind: "bar", x: data.groups.map((g) => String(g[data.by])), series: [{ name: `median ${data.metric}`, data: data.groups.map((g) => g.median) }] }} height={300} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Is the gap real?</CardTitle>
            <CardDescription>Kruskal–Wallis across groups, Mann–Whitney top vs bottom</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            {t.kruskal && t.top && t.bottom && t.top_vs_bottom ? (
              <>
                <div><span className="text-muted-foreground">Kruskal–Wallis</span> H={t.kruskal.H}, {fmtP(t.kruskal.p)}, ε²={t.kruskal.epsilon2}</div>
                <div><span className="text-muted-foreground">Highest</span> {t.top.group}: {fmtNum(t.top.median)} (n={t.top.n})</div>
                <div><span className="text-muted-foreground">Lowest</span> {t.bottom.group}: {fmtNum(t.bottom.median)} (n={t.bottom.n})</div>
                <div><span className="text-muted-foreground">Ratio</span> {t.top_vs_bottom.median_ratio}× · {fmtP(t.top_vs_bottom.p)} · rank-biserial {t.top_vs_bottom.rank_biserial}</div>
                <Badge variant={t.kruskal.p < 0.05 ? "secondary" : "outline"} className="w-fit">{t.kruskal.p < 0.05 ? "significant at 5%" : "not significant"}</Badge>
              </>
            ) : (
              <div className="text-muted-foreground">{String(t.error ?? "Not enough data per group for a test.")}</div>
            )}
          </CardContent>
        </Card>
      </div>
      <div className="px-4 lg:px-6">
        <Card>
          <CardHeader>
            <CardTitle>Natural segments (k-means)</CardTitle>
            <CardDescription>
              {data.clusters ? `k=${data.clusters.k} chosen by silhouette (${data.clusters.silhouette}); features: ${data.clusters.features.join(", ")}` : "No segmentation available"}
            </CardDescription>
          </CardHeader>
          {data.clusters && (
            <CardContent className="overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Segment</TableHead>
                    <TableHead className="text-right">Size</TableHead>
                    <TableHead className="text-right">Share</TableHead>
                    <TableHead>What makes it different</TableHead>
                    {data.clusters.features.slice(0, 4).map((f) => <TableHead key={f} className="text-right">{f}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.clusters.profiles.map((p) => (
                    <TableRow key={p.cluster}>
                      <TableCell className="font-medium">C{p.cluster}</TableCell>
                      <TableCell className="text-right tabular-nums">{p.size.toLocaleString()}</TableCell>
                      <TableCell className="text-right tabular-nums">{(p.share * 100).toFixed(0)}%</TableCell>
                      <TableCell className="text-muted-foreground">{p.distinctive.map((d) => `${d.feature} ${d.z > 0 ? "↑" : "↓"}`).join(", ")}</TableCell>
                      {data.clusters!.features.slice(0, 4).map((f) => <TableCell key={f} className="text-right tabular-nums">{fmtNum(p.medians[f])}</TableCell>)}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          )}
        </Card>
      </div>
    </PageShell>
  )
}
