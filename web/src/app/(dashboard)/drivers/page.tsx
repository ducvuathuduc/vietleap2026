"use client"

import * as React from "react"

import { useDataset } from "@/components/dataset-provider"
import { InsightChart } from "@/components/insight-chart"
import { ErrorState, LoadingState, PageShell } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { WhatIfResult } from "@/lib/api/types"
import { fmtNum, fmtPct } from "@/lib/format"
import { insightTarget } from "@/lib/insight-target"

export default function DriversPage() {
  const { datasetId } = useDataset()
  const { data, error, loading } = useAsync(() => (datasetId ? api.drivers(datasetId) : null), [datasetId])
  const [picked, setPicked] = React.useState<{ ds: string | null; feature: string } | null>(null)
  const [pct, setPct] = React.useState(10)
  const [result, setResult] = React.useState<WhatIfResult | null>(null)
  const [wiErr, setWiErr] = React.useState<string | null>(null)
  const defaultFeature = React.useMemo(() => {
    if (!data) return null
    const stable = data.drivers?.coefficients.find((c) => c.stable && data.whatif_features.some((f) => f.name === c.feature))
    return stable?.feature ?? data.whatif_features[0]?.name ?? null
  }, [data])
  const feature = picked && picked.ds === datasetId ? picked.feature : defaultFeature
  const setFeature = (f: string) => setPicked({ ds: datasetId, feature: f })
  const curve = useAsync(() => (datasetId && feature ? api.whatIfCurve(datasetId, feature) : null), [datasetId, feature])
  React.useEffect(() => {
    if (!datasetId || !feature) return
    const t = setTimeout(() => {
      api.whatIf(datasetId, feature, pct).then(
        (r) => (setResult(r), setWiErr(null)),
        (e: Error) => setWiErr(e.message)
      )
    }, 150)
    return () => clearTimeout(t)
  }, [datasetId, feature, pct])

  if (error) return <PageShell><ErrorState error={error} /></PageShell>
  if (loading || !data) return <PageShell><LoadingState /></PageShell>
  const d = data.drivers
  if (!d) return <PageShell><ErrorState error="No driver model could be fitted for this dataset (too few rows or no numeric features)." /></PageShell>
  const imp = d.importance.slice(0, 10)
  const feats = data.whatif_features.map((f) => ({ label: f.name, value: f.name }))
  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
        {[
          { label: "Gradient boosting CV R²", value: d.cv_r2.gb_mean.toFixed(3), foot: `± ${d.cv_r2.gb_std.toFixed(3)} across 5 folds` },
          { label: "Ridge CV R²", value: d.cv_r2.ridge_mean.toFixed(3), foot: `± ${d.cv_r2.ridge_std.toFixed(3)} across 5 folds` },
          { label: "Rows used", value: d.n.toLocaleString(), foot: `${d.features.length} features${d.log_target ? " · log target" : ""}` },
          { label: "Leakage guard", value: String(d.leakage_excluded.length), foot: d.leakage_excluded.join(", ") || "no near-duplicates of the target" },
        ].map((k) => (
          <Card key={k.label}>
            <CardHeader>
              <CardDescription>{k.label}</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums">{k.value}</CardTitle>
            </CardHeader>
            <CardFooter className="text-sm text-muted-foreground"><span className="line-clamp-1">{k.foot}</span></CardFooter>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Drivers of {data.target}</CardTitle>
            <CardDescription>Permutation importance on a held-out 25% (drop in R² when the feature is shuffled)</CardDescription>
          </CardHeader>
          <CardContent>
            <InsightChart spec={{ kind: "hbar", x: imp.map((i) => i.feature), series: [{ name: "importance", data: imp.map((i) => i.importance) }] }} height={320} />
          </CardContent>
          <CardFooter className="text-xs text-muted-foreground">{d.note}</CardFooter>
        </Card>
        <Card {...insightTarget("whatif", feature ?? "none", `What-if: ${feature ?? ""} ${pct > 0 ? "+" : ""}${pct}%`, { feature, pct_change: pct, result })}>
          <CardHeader>
            <CardTitle>What-if scenario</CardTitle>
            <CardDescription>Change one driver for every record; bootstrapped ridge (200 resamples) gives the 90% interval</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <div className="grid gap-2">
              <Label>Driver</Label>
              <Select value={feature ?? ""} onValueChange={(v) => v && setFeature(v)} items={feats}>
                <SelectTrigger className="w-full"><SelectValue placeholder="Choose a numeric driver" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {feats.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <Label>Change in {feature ?? "driver"}</Label>
                <span className="font-mono text-sm tabular-nums">{pct > 0 ? "+" : ""}{pct}%</span>
              </div>
              <Slider min={-30} max={30} step={1} value={[pct]} onValueChange={(v) => setPct(Array.isArray(v) ? v[0] : v)} />
            </div>
            <div className="rounded-lg border p-4">
              {wiErr ? (
                <div className="text-sm text-destructive">{wiErr}</div>
              ) : result ? (
                <>
                  <div className="text-sm text-muted-foreground">Expected change in {result.target}</div>
                  <div className="text-3xl font-semibold tabular-nums">{fmtPct(result.target_change_pct)}</div>
                  <div className="text-sm text-muted-foreground">
                    90% interval {fmtPct(result.ci90_pct[0])} to {fmtPct(result.ci90_pct[1])} · ≈ {fmtNum(result.target_change_abs)} on a mean of {fmtNum(result.baseline_target_mean)}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">{result.interpretation}</div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">Move the slider…</div>
              )}
            </div>
            {curve.data && (
              <InsightChart
                spec={{
                  kind: "line",
                  x: curve.data.points.map((p) => `${p.pct > 0 ? "+" : ""}${p.pct}%`),
                  series: [
                    { name: `Δ ${data.target} %`, data: curve.data.points.map((p) => p.change) },
                    { name: "low 90%", data: curve.data.points.map((p) => p.low) },
                    { name: "high 90%", data: curve.data.points.map((p) => p.high) },
                  ],
                }}
                height={180}
              />
            )}
          </CardContent>
        </Card>
      </div>
      <div className="px-4 lg:px-6">
        <Card>
          <CardHeader>
            <CardTitle>Standardised ridge coefficients</CardTitle>
            <CardDescription>Per 1 SD of the feature, holding the others fixed; “stable” = bootstrap 90% interval excludes zero</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Feature</TableHead>
                  <TableHead className="text-right">Coefficient</TableHead>
                  <TableHead className="text-right">90% interval</TableHead>
                  <TableHead>Direction</TableHead>
                  <TableHead>Stability</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.coefficients.slice(0, 15).map((c) => (
                  <TableRow key={c.feature} {...insightTarget("driver", c.feature, `Yếu tố ${c.feature}`, c)}>
                    <TableCell className="max-w-72 truncate font-medium">{c.feature}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums">{c.coef_std.toFixed(4)}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums">[{c.ci90[0].toFixed(3)}, {c.ci90[1].toFixed(3)}]</TableCell>
                    <TableCell>{c.direction === "+" ? "positive" : "negative"}</TableCell>
                    <TableCell><Badge variant={c.stable ? "secondary" : "outline"}>{c.stable ? "stable" : "uncertain"}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </PageShell>
  )
}
