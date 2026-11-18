"use client"

import * as React from "react"
import { useSearchParams } from "next/navigation"

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
  return <React.Suspense fallback={<LoadingState />}><DriversQuery /></React.Suspense>
}

function DriversQuery() {
  const params = useSearchParams()
  const initialFeature = params.get("feature")
  const value = Number(params.get("pct") ?? 10)
  const initialPct = Number.isFinite(value) ? Math.max(-30, Math.min(30, value)) : 10
  return <DriversContent key={`${initialFeature}:${initialPct}`} initialFeature={initialFeature} initialPct={initialPct} />
}

function DriversContent({ initialFeature, initialPct }: { initialFeature: string | null; initialPct: number }) {
  const { datasetId } = useDataset()
  const { data, error, loading } = useAsync(() => (datasetId ? api.drivers(datasetId) : null), [datasetId])
  const [picked, setPicked] = React.useState<{ ds: string | null; feature: string } | null>(null)
  const [pct, setPct] = React.useState(initialPct)
  const [result, setResult] = React.useState<WhatIfResult | null>(null)
  const [wiErr, setWiErr] = React.useState<string | null>(null)
  const defaultFeature = React.useMemo(() => {
    if (!data) return null
    if (data.whatif_features.some((feature) => feature.name === initialFeature)) return initialFeature
    const stable = data.drivers?.coefficients.find((c) => c.stable && data.whatif_features.some((f) => f.name === c.feature))
    return stable?.feature ?? data.whatif_features[0]?.name ?? null
  }, [data, initialFeature])
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
  if (!d) return <PageShell><ErrorState error="Chưa ước lượng được mô hình drivers cho dataset này (cần thêm dòng hoặc biến số)." /></PageShell>
  const imp = d.importance.slice(0, 10)
  const feats = data.whatif_features.map((f) => ({ label: f.name, value: f.name }))
  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
        {[
          { label: "CV R² (Gradient Boosting)", value: d.cv_r2.gb_mean.toFixed(3), foot: `± ${d.cv_r2.gb_std.toFixed(3)} qua 5-fold` },
          { label: "CV R² (Ridge chuẩn hoá)", value: d.cv_r2.ridge_mean.toFixed(3), foot: `± ${d.cv_r2.ridge_std.toFixed(3)} qua 5-fold` },
          { label: "Số dòng huấn luyện", value: d.n.toLocaleString("vi-VN"), foot: `${d.features.length} biến${d.log_target ? " · log target" : ""}` },
          { label: "Bộ lọc rò rỉ (Leakage guard)", value: String(d.leakage_excluded.length), foot: d.leakage_excluded.join(", ") || "Không có biến trùng cận mục tiêu" },
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
            <CardTitle>Yếu tố tác động tới {data.target}</CardTitle>
            <CardDescription>Độ quan trọng hoán vị (permutation importance) trên 25% mẫu kiểm định (mức giảm R² khi xáo trộn biến)</CardDescription>
          </CardHeader>
          <CardContent>
            <InsightChart spec={{ kind: "hbar", x: imp.map((i) => i.feature), series: [{ name: "importance", data: imp.map((i) => i.importance) }] }} height={320} />
          </CardContent>
          <CardFooter className="text-xs text-muted-foreground">{d.note}</CardFooter>
        </Card>
        <Card {...insightTarget("whatif", feature ?? "none", `What-if: ${feature ?? ""} ${pct > 0 ? "+" : ""}${pct}%`, { feature, pct_change: pct, result })}>
          <CardHeader>
            <CardTitle>Kịch bản What-if đơn biến</CardTitle>
            <CardDescription>Thay đổi một yếu tố cho toàn bộ bản ghi; Ridge bootstrap (200 lượt) cho khoảng tin cậy 90% (confidence interval)</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <div className="grid gap-2">
              <Label>Yếu tố (Driver)</Label>
              <Select value={feature ?? ""} onValueChange={(v) => v && setFeature(v)} items={feats}>
                <SelectTrigger className="w-full"><SelectValue placeholder="Chọn một biến số" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {feats.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <Label>Mức thay đổi của {feature ?? "biến"}</Label>
                <span className="font-mono text-sm tabular-nums">{pct > 0 ? "+" : ""}{pct}%</span>
              </div>
              <Slider min={-30} max={30} step={1} value={[pct]} onValueChange={(v) => setPct(Array.isArray(v) ? v[0] : v)} />
            </div>
            <div className="rounded-lg border p-4">
              {wiErr ? (
                <div className="text-sm text-destructive">{wiErr}</div>
              ) : result ? (
                <>
                  <div className="text-sm text-muted-foreground">Thay đổi kỳ vọng của {result.target}</div>
                  <div className="text-3xl font-semibold tabular-nums">{fmtPct(result.target_change_pct)}</div>
                  <div className="text-sm text-muted-foreground">
                    Khoảng tin cậy 90%: {fmtPct(result.ci90_pct[0])} đến {fmtPct(result.ci90_pct[1])} · ≈ {fmtNum(result.target_change_abs)} trên trung bình nền {fmtNum(result.baseline_target_mean)}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">{result.interpretation}</div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">Kéo thanh trượt để mô phỏng…</div>
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
            <CardTitle>Hệ số Ridge chuẩn hoá (Standardised coefficients)</CardTitle>
            <CardDescription>Ứng với +1 độ lệch chuẩn (SD) của biến, giữ các biến khác cố định; “ổn định” nghĩa là KTC 90% không chứa 0</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Biến (Feature)</TableHead>
                  <TableHead className="text-right">Hệ số</TableHead>
                  <TableHead className="text-right">KTC 90%</TableHead>
                  <TableHead>Chiều tác động</TableHead>
                  <TableHead>Độ ổn định</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.coefficients.slice(0, 15).map((c) => (
                  <TableRow key={c.feature} {...insightTarget("driver", c.feature, `Yếu tố ${c.feature}`, c)}>
                    <TableCell className="max-w-72 truncate font-medium">{c.feature}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums">{c.coef_std.toFixed(4)}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums">[{c.ci90[0].toFixed(3)}, {c.ci90[1].toFixed(3)}]</TableCell>
                    <TableCell>{c.direction === "+" ? "cùng chiều (+)" : "ngược chiều (-)"}</TableCell>
                    <TableCell><Badge variant={c.stable ? "secondary" : "outline"}>{c.stable ? "ổn định" : "chưa chắc chắn"}</Badge></TableCell>
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
