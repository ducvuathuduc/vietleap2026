"use client"

import { Line, LineChart, ReferenceArea, ReferenceLine, XAxis, YAxis } from "recharts"

import { useCurveDraw } from "@/components/ratewatch/count-up"
import { Badge } from "@/components/ui/badge"
import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart"
import { formatPct } from "@/lib/ratewatch/format"
import { gradeBadge, type Grade, type Lang } from "@/lib/ratewatch/view"
import type { ChartRow } from "@/lib/ratewatch/decide"

export interface CurveSeries {
  code: string
  name: string
  sheetDate: string
  sourceUrl: string
  points: { term: number; rate: number; grade: Grade; mark: boolean }[]
}

function hostName(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return ""
  }
}

function CurveTip({
  active,
  payload,
  series,
  lang,
}: {
  active?: boolean
  payload?: { dataKey?: unknown; value?: unknown; payload?: { term?: number } }[]
  series: CurveSeries[]
  lang: Lang
}) {
  if (!active || !payload?.length) return null
  const term = payload[0]?.payload?.term
  if (typeof term !== "number") return null
  const vi = lang === "vi"
  return (
    <div className="grid min-w-40 gap-2 rounded-lg border border-border bg-background px-2.5 py-2 text-xs">
      <p className="font-medium">{term} {vi ? "tháng" : "months"}</p>
      {payload.map((item) => {
        const code = String(item.dataKey ?? "")
        const meta = series.find((entry) => entry.code === code)
        const point = meta?.points.find((entry) => entry.term === term)
        if (!meta || !point || typeof item.value !== "number") return null
        const badge = gradeBadge(point.grade, "", lang)
        const host = hostName(meta.sourceUrl)
        return (
          <div key={code} className="grid gap-0.5">
            <p>{meta.name}: {formatPct(item.value, 2, lang)}%</p>
            <p><Badge variant="outline">{badge.label}</Badge></p>
            <p>{vi ? "Ngày biểu" : "Sheet date"} {meta.sheetDate}</p>
            {host ? <p>{host}</p> : null}
          </div>
        )
      })}
    </div>
  )
}

export function CurveChart({
  rows,
  series,
  ceiling,
  horizon,
  bandLabel,
  ceilingLabel,
  lang,
}: {
  rows: ChartRow[]
  series: CurveSeries[]
  ceiling: number
  horizon: number
  bandLabel: string
  ceilingLabel: string
  lang: Lang
}) {
  const draw = useCurveDraw()
  const config: ChartConfig = {}
  for (const [index, item] of series.entries()) {
    config[item.code] = { label: item.name, color: `var(--chart-${(index % 5) + 1})` }
  }
  const data = rows.map((row) => ({ ...row, label: String(row.term) }))
  const marker = Math.min(36, Math.max(1, horizon || 1))
  if (!data.some((row) => row.term === marker)) {
    data.push({ term: marker, label: String(marker) })
    data.sort((left, right) => left.term - right.term)
  }
  const labels = new Set(data.map((row) => row.label))
  return (
    <ChartContainer config={config} className="aspect-auto h-[260px] w-full min-w-0" initialDimension={{ width: 640, height: 260 }}>
      <LineChart data={data} margin={{ top: 18, right: 8, left: 0, bottom: 0 }}>
        <XAxis dataKey="label" type="category" tickLine={false} axisLine={false} />
        <YAxis width={36} tickLine={false} axisLine={false} domain={["auto", "auto"]} />
        <ChartTooltip content={<CurveTip series={series} lang={lang} />} />
        {labels.has("1") && labels.has("5") ? (
          <ReferenceArea x1="1" x2="5" fill="var(--chart-1)" fillOpacity={0.45} label={{ value: bandLabel, position: "insideTop", fill: "var(--foreground)", fontSize: 11 }} />
        ) : null}
        <ReferenceLine y={ceiling} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={{ value: ceilingLabel, position: "insideTopRight", fill: "var(--foreground)", fontSize: 11 }} />
        <ReferenceLine x={String(marker)} stroke="var(--foreground)" />
        {series.map((item) => (
          <Line
            key={item.code}
            type="monotone"
            dataKey={item.code}
            stroke={`var(--color-${item.code})`}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
            isAnimationActive={draw}
            animationDuration={1200}
            animationEasing="ease-out"
          />
        ))}
      </LineChart>
    </ChartContainer>
  )
}
