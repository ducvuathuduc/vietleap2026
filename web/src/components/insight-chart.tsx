"use client"

import { Bar, BarChart, CartesianGrid, Line, LineChart, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from "recharts"

import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import type { ChartSpec } from "@/lib/api/types"
import { fmtNum } from "@/lib/format"

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"]
const key = (i: number) => `s${i}`

/** Renders the engine's chart spec ({kind, x, series}) with shadcn charts (Recharts). */
export function InsightChart({ spec, height = 240 }: { spec: ChartSpec; height?: number }) {
  const config: ChartConfig = Object.fromEntries(
    spec.series.map((s, i) => [key(i), { label: s.name, color: i === 0 ? "var(--primary)" : COLORS[i % COLORS.length] }])
  )
  const style = { height }
  const tick = (v: unknown) => (typeof v === "number" ? fmtNum(v) : String(v ?? "").slice(0, 14))

  if (spec.kind === "scatter") {
    const data = spec.x
      .map((x, i) => ({ x: Number(x), y: spec.series[0]?.data[i] ?? null }))
      .filter((d): d is { x: number; y: number } => d.y !== null && Number.isFinite(d.x))
    const scale = data.length > 0 && data.every((d) => d.x > 0 && d.y > 0) ? "log" : "auto"
    return (
      <ChartContainer config={config} className="aspect-auto w-full" style={style}>
        <ScatterChart margin={{ left: 4, right: 8, top: 8 }}>
          <CartesianGrid />
          <XAxis dataKey="x" type="number" name={spec.x_label} tickFormatter={tick} tickLine={false} axisLine={false} scale={scale} domain={["auto", "auto"]} />
          <YAxis dataKey="y" type="number" name={spec.y_label} tickFormatter={tick} tickLine={false} axisLine={false} width={48} scale={scale} domain={["auto", "auto"]} />
          <ZAxis range={[14, 14]} />
          <ChartTooltip content={<ChartTooltipContent hideLabel />} />
          <Scatter data={data} fill="var(--color-s0)" fillOpacity={0.45} />
        </ScatterChart>
      </ChartContainer>
    )
  }

  const data = spec.x.map((x, i) => {
    const row: Record<string, string | number | null> = { x: String(x) }
    spec.series.forEach((s, j) => (row[key(j)] = s.data[i] ?? null))
    return row
  })

  if (spec.kind === "line") {
    return (
      <ChartContainer config={config} className="aspect-auto w-full" style={style}>
        <LineChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="x" tickLine={false} axisLine={false} tickMargin={8} minTickGap={24} />
          <YAxis tickFormatter={tick} tickLine={false} axisLine={false} width={48} domain={["auto", "auto"]} />
          <ChartTooltip content={<ChartTooltipContent indicator="line" />} />
          {spec.series.map((s, i) => (
            <Line
              key={s.name}
              dataKey={key(i)}
              type="monotone"
              stroke={`var(--color-${key(i)})`}
              strokeWidth={i === 0 ? 2 : 1.5}
              strokeDasharray={/low|high|lower|upper/.test(s.name) ? "4 4" : undefined}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ChartContainer>
    )
  }

  const horizontal = spec.kind === "hbar"
  return (
    <ChartContainer config={config} className="aspect-auto w-full" style={style}>
      <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ left: 4, right: 8, top: 8 }}>
        <CartesianGrid vertical={horizontal} horizontal={!horizontal} />
        {horizontal ? (
          <>
            <XAxis type="number" tickFormatter={tick} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="x" tickLine={false} axisLine={false} width={130} tickFormatter={(v) => String(v).slice(0, 20)} />
          </>
        ) : (
          <>
            <XAxis dataKey="x" tickLine={false} axisLine={false} tickMargin={8} interval={0} angle={data.length > 6 ? -30 : 0} textAnchor={data.length > 6 ? "end" : "middle"} height={data.length > 6 ? 60 : 30} tickFormatter={(v) => String(v).slice(0, 14)} />
            <YAxis tickFormatter={tick} tickLine={false} axisLine={false} width={48} />
          </>
        )}
        <ChartTooltip cursor={false} content={<ChartTooltipContent hideIndicator />} />
        {spec.series.map((s, i) => (
          <Bar key={s.name} dataKey={key(i)} fill={`var(--color-${key(i)})`} radius={4} />
        ))}
      </BarChart>
    </ChartContainer>
  )
}
