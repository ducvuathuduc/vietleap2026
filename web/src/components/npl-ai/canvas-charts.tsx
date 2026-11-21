import { Area, Bar, BarChart, CartesianGrid, ComposedChart, ErrorBar, Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts"

import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { type BankSeriesPoint, type Lang } from "@/lib/npl/view"

import { comparisonHistory, forecastRows, formatValue, type CompareResult, type ForecastResult } from "./canvas-data"

const frame = "aspect-auto h-56 w-full min-w-0 px-2 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-inset has-[:focus-visible]:ring-ring sm:h-64 [&_.recharts-surface]:outline-none [&_*:focus]:outline-none"
const dimensions = { width: 320, height: 224 }
const margin = { top: 12, right: 14, left: 0, bottom: 4 }
const axisProps = { tickLine: false, axisLine: false, tick: { fontSize: 12 } }
const quarterAxis = { ...axisProps, interval: "preserveStartEnd", minTickGap: 22, padding: { left: 8, right: 8 } } as const
const palette = [
  { light: "var(--chart-2)", dark: "var(--chart-2)" },
  { light: "var(--chart-5)", dark: "var(--chart-1)" },
  { light: "var(--chart-2)", dark: "var(--chart-2)" },
  { light: "var(--chart-3)", dark: "var(--muted-foreground)" },
  { light: "var(--chart-4)", dark: "var(--foreground)" },
] as const

function canvasTooltip(lang: Lang, suffix: string, dayLabel?: string) {
  return (
    <ChartTooltipContent
      labelFormatter={dayLabel ? (_label, payload) => `${dayLabel} ${payload[0]?.payload?.day}` : undefined}
      formatter={(value, name) => (
        <>
          <span className="grow text-muted-foreground">{name}</span>
          <span className="font-medium tabular-nums">
            {typeof value === "number"
              ? formatValue(value, lang, suffix)
              : Array.isArray(value) ? value.map((item) => formatValue(Number(item), lang, suffix)).join(" – ") : value}
          </span>
        </>
      )}
    />
  )
}

function ChartUnits({ children }: { children: string }) {
  return <p className="px-3 pt-3 text-xs font-medium text-muted-foreground">{children}</p>
}

function niceDomain(values: number[]): { domain: [number, number]; ticks: number[] } {
  const lo = Math.min(0, ...values)
  const hi = Math.max(0, ...values)
  const span = hi - lo || 1
  const raw = span / 4
  const power = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((m) => m >= raw) ?? raw
  const start = Math.floor(lo / step) * step
  const end = Math.ceil(hi / step) * step
  const ticks: number[] = []
  for (let t = start; t <= end + step / 2; t += step) ticks.push(Number(t.toFixed(10)) || 0)
  return { domain: [start, end], ticks }
}

type MetricPoint = { label: string; value: number | null; interval?: [number, number] }
export function MetricBarsChart({ rows, metric, unit, lang, zeroLabel }: {
  rows: MetricPoint[]
  metric: string
  unit: string
  lang: Lang
  zeroLabel?: string
}) {
  const config = { value: { label: metric, theme: palette[0] } } satisfies ChartConfig
  const data = rows.map(({ interval, ...row }) => ({
    ...row,
    error: interval && row.value != null ? [row.value - interval[0], interval[1] - row.value] : undefined,
  }))
  const scale = niceDomain(rows.flatMap((row) => (row.value == null ? [] : [row.value, ...(row.interval ?? [])])))
  const decimals = scale.ticks.some((t) => !Number.isInteger(t)) ? Math.min(2, Math.max(1, -Math.floor(Math.log10(Math.abs(scale.ticks[1] - scale.ticks[0]) || 1)))) : 0
  return (
    <>
      <ChartUnits>{metric + " (" + unit.trim() + ")"}</ChartUnits>
      <ChartContainer config={config} className={frame} initialDimension={dimensions}>
        <BarChart data={data} margin={margin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="label" interval={0} {...axisProps} />
          <YAxis width={54} domain={scale.domain} ticks={scale.ticks}
            tickFormatter={(value: number) => formatValue(value, lang, "", decimals)} {...axisProps} />
          <ReferenceLine y={0} stroke="var(--muted-foreground)"
            label={zeroLabel ? { value: zeroLabel, position: "insideTopRight", fontSize: 11, fill: "var(--foreground)" } : undefined} />
          <ChartTooltip cursor={{ fill: "var(--muted)", opacity: 0.35 }} content={canvasTooltip(lang, unit)} />
          <Bar dataKey="value" name={metric} fill="var(--color-value)" radius={3} maxBarSize={48} isAnimationActive={false}>
            <ErrorBar dataKey="error" width={6} stroke="var(--muted-foreground)" />
          </Bar>
        </BarChart>
      </ChartContainer>
    </>
  )
}

export function BankCanvasChart({ rows, lang }: { rows: BankSeriesPoint[]; lang: Lang }) {
  const vi = lang === "vi"
  const npl = vi ? "Nợ xấu, trục trái" : "NPL, left axis"
  const coverage = vi ? "Bao phủ, trục phải" : "Coverage, right axis"
  const config = {
    npl_pct: { label: npl, theme: palette[0] },
    coverage_pct: { label: coverage, theme: palette[1] },
  } satisfies ChartConfig
  const tick = (value: number) => formatValue(value, lang, "%", 1)
  return (
    <ChartContainer config={config} className={frame} initialDimension={dimensions}>
      <LineChart data={rows} margin={margin}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="period" {...quarterAxis} />
        <YAxis yAxisId="npl" width={48} domain={["auto", "auto"]} tickFormatter={tick} {...axisProps} />
        <YAxis yAxisId="coverage" orientation="right" width={52} domain={["auto", "auto"]} tickFormatter={(value: number) => formatValue(value, lang, "%", 0)} {...axisProps} />
        <ChartTooltip content={canvasTooltip(lang, "%")} />
        <ChartLegend content={<ChartLegendContent nameKey="dataKey" className="flex-wrap" />} />
        <Line yAxisId="npl" dataKey="npl_pct" name={npl} stroke="var(--color-npl_pct)" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line yAxisId="coverage" dataKey="coverage_pct" name={coverage} stroke="var(--color-coverage_pct)" strokeWidth={2} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
      </LineChart>
    </ChartContainer>
  )
}

export function CompareCanvasChart({ rows, lang }: { rows: CompareResult["rows"]; lang: Lang }) {
  const banks = rows.filter((row) => row.history?.some((point) => point.npl_pct != null))
  const config: ChartConfig = Object.fromEntries(banks.map(({ code }, index) => [code, { label: code, theme: palette[index] }]))
  return (
    <>
      <ChartUnits>{lang === "vi" ? "Tỷ lệ nợ xấu (%)" : "NPL ratio (%)"}</ChartUnits>
      <ChartContainer config={config} className={frame} initialDimension={dimensions}>
        <LineChart data={comparisonHistory(banks)} margin={margin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" {...quarterAxis} />
          <YAxis width={54} tickFormatter={(value: number) => formatValue(value, lang, "%", 1)} {...axisProps} />
          <ChartTooltip content={canvasTooltip(lang, "%")} />
          <ChartLegend content={<ChartLegendContent nameKey="dataKey" className="flex-wrap" />} />
          {banks.map(({ code }, index) => (
            <Line key={code} dataKey={code} name={code} stroke={`var(--color-${code})`} strokeWidth={2} dot={false}
              strokeDasharray={[undefined, "5 3", "2 3", "7 3 2 3"][index]} isAnimationActive={false} />
          ))}
        </LineChart>
      </ChartContainer>
    </>
  )
}

export function QuarterNplChart({ rows, lang }: { rows: { period: string; value: number | null }[]; lang: Lang }) {
  const label = lang === "vi" ? "Tỷ lệ nợ xấu" : "NPL ratio"
  const config = { value: { label, theme: palette[0] } } satisfies ChartConfig
  return (
    <>
      <ChartUnits>{label + " (%)"}</ChartUnits>
      <ChartContainer config={config} className={frame} initialDimension={dimensions}>
        <LineChart data={rows} margin={margin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" {...quarterAxis} />
          <YAxis width={54} domain={["auto", "auto"]} tickFormatter={(value: number) => formatValue(value, lang, "%", 1)} {...axisProps} />
          <ChartTooltip content={canvasTooltip(lang, "%")} />
          <Line dataKey="value" name={label} stroke="var(--color-value)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        </LineChart>
      </ChartContainer>
    </>
  )
}

export function ForecastCanvasChart({ output, lang }: { output: ForecastResult; lang: Lang }) {
  const observed = lang === "vi" ? "Quan sát" : "Observed"
  const estimate = lang === "vi" ? "Dự báo" : "Forecast"
  const band = lang === "vi" ? "Khoảng dự báo 80%" : "80% prediction interval"
  const config = {
    observed: { label: observed, theme: palette[0] },
    estimate: { label: estimate, theme: palette[1] },
    band: { label: band, theme: palette[1] },
  } satisfies ChartConfig
  return (
    <>
      <ChartUnits>{lang === "vi" ? "Tỷ lệ nợ xấu (%)" : "NPL ratio (%)"}</ChartUnits>
      <ChartContainer config={config} className={frame} initialDimension={dimensions}>
        <ComposedChart data={forecastRows(output)} margin={margin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" {...quarterAxis} />
          <YAxis width={54} tickFormatter={(value: number) => formatValue(value, lang, "%", 1)} {...axisProps} />
          <ChartTooltip content={canvasTooltip(lang, "%")} />
          <ChartLegend content={<ChartLegendContent nameKey="dataKey" className="flex-wrap" />} />
          <Area dataKey="band" name={band} stroke="none" fill="var(--color-band)" fillOpacity={0.2} isAnimationActive={false} />
          <Line dataKey="observed" name={observed} stroke="var(--color-observed)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line dataKey="estimate" name={estimate} stroke="var(--color-estimate)" strokeDasharray="5 3" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false}>
            <ErrorBar dataKey="error" width={5} stroke="var(--color-estimate)" />
          </Line>
        </ComposedChart>
      </ChartContainer>
    </>
  )
}

export function MarketCanvasChart({ rows, lang }: {
  rows: { day: number; mean_car_pct: number | null; ci95: (number | null)[] | null }[]
  lang: Lang
}) {
  const vi = lang === "vi"
  const metric = vi ? "Lợi suất bất thường tích lũy" : "Cumulative abnormal return"
  const confidence = vi ? "Khoảng tin cậy 95%" : "95% confidence interval"
  const config = { value: { label: metric, theme: palette[0] }, band: { label: confidence, theme: palette[1] } } satisfies ChartConfig
  const data = rows.map(({ day, mean_car_pct, ci95 }) => ({
    day, value: mean_car_pct, band: ci95?.[0] != null && ci95?.[1] != null ? [ci95[0], ci95[1]] : undefined,
  }))
  return (
    <>
      <ChartUnits>{metric + " (%)"}</ChartUnits>
      <ChartContainer config={config} className={frame} initialDimension={dimensions}>
        <ComposedChart data={data} margin={margin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="day" label={{ value: vi ? "Ngày quanh công bố" : "Days around disclosure", position: "insideBottom", fontSize: 12 }}
            height={44} {...axisProps} />
          <YAxis width={54} tickFormatter={(value: number) => formatValue(value, lang, "%", 1)} {...axisProps} />
          <ReferenceLine y={0} stroke="var(--muted-foreground)" />
          <ChartTooltip content={canvasTooltip(lang, "%", vi ? "Ngày" : "Day")} />
          <ChartLegend content={<ChartLegendContent nameKey="dataKey" className="flex-wrap" />} />
          <Area dataKey="band" name={confidence} stroke="none" fill="var(--color-band)" fillOpacity={0.22} isAnimationActive={false} />
          <Line dataKey="value" name={metric} stroke="var(--color-value)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ChartContainer>
    </>
  )
}




