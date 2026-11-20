import { Area, Bar, BarChart, CartesianGrid, ComposedChart, ErrorBar, Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts"

import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { type BankSeriesPoint, type Lang } from "@/lib/npl/view"

import { forecastRows, formatValue, type CompareResult, type ForecastResult } from "./canvas-data"

const frame = "aspect-auto h-44 w-full min-w-0 sm:h-52"
const dimensions = { width: 320, height: 208 }
const margin = { top: 8, right: 12, left: 4, bottom: 0 }
const axisProps = { tickLine: false, axisLine: false }

function CanvasTip({ lang, suffix }: { lang: Lang; suffix: string }) {
  return (
    <ChartTooltipContent
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

export function BankCanvasChart({ rows, lang }: { rows: BankSeriesPoint[]; lang: Lang }) {
  const npl = lang === "vi" ? "Nợ xấu · trái" : "NPL · left"
  const coverage = lang === "vi" ? "Bao phủ · phải" : "Coverage · right"
  const config = {
    npl_pct: { label: npl, color: "var(--chart-1)" },
    coverage_pct: { label: coverage, color: "var(--chart-3)" },
  } satisfies ChartConfig
  const tick = (value: number) => formatValue(value, lang, "%", 1)
  return (
    <ChartContainer config={config} className={frame} initialDimension={dimensions}>
      <LineChart data={rows} margin={margin}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="period" interval="preserveStartEnd" minTickGap={22} {...axisProps} />
        <YAxis yAxisId="npl" width={48} domain={["auto", "auto"]} tickFormatter={tick} {...axisProps} />
        <YAxis yAxisId="coverage" orientation="right" width={48} domain={["auto", "auto"]} tickFormatter={(value: number) => formatValue(value, lang, "%", 0)} {...axisProps} />
        <ChartTooltip content={<CanvasTip lang={lang} suffix="%" />} />
        <ChartLegend content={<ChartLegendContent nameKey="dataKey" className="flex-wrap" />} />
        <Line yAxisId="npl" dataKey="npl_pct" name={npl} stroke="var(--color-npl_pct)" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line yAxisId="coverage" dataKey="coverage_pct" name={coverage} stroke="var(--color-coverage_pct)" strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ChartContainer>
  )
}

export function CompareCanvasChart({ rows, lang }: { rows: CompareResult["rows"]; lang: Lang }) {
  const raw = lang === "vi" ? "Biến động gốc" : "Raw change"
  const adjusted = lang === "vi" ? "Đã điều chỉnh mùa vụ" : "Seasonally adjusted"
  const config = {
    d_npl_pp: { label: raw, color: "var(--chart-1)" },
    adjusted_change_pp: { label: adjusted, color: "var(--chart-3)" },
  } satisfies ChartConfig
  return (
    <ChartContainer config={config} className={frame} initialDimension={dimensions}>
      <BarChart data={rows} margin={margin}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="code" {...axisProps} />
        <YAxis width={42} tickFormatter={(value: number) => formatValue(value, lang, "", 2)} {...axisProps} />
        <ReferenceLine y={0} stroke="var(--muted-foreground)" />
        <ChartTooltip content={<CanvasTip lang={lang} suffix={lang === "vi" ? " điểm %" : " pp"} />} />
        <ChartLegend content={<ChartLegendContent nameKey="dataKey" className="flex-wrap" />} />
        <Bar dataKey="d_npl_pp" name={raw} fill="var(--color-d_npl_pp)" maxBarSize={40} isAnimationActive={false} />
        <Bar dataKey="adjusted_change_pp" name={adjusted} fill="var(--color-adjusted_change_pp)" maxBarSize={40} isAnimationActive={false} />
      </BarChart>
    </ChartContainer>
  )
}

export function ForecastCanvasChart({ output, lang }: { output: ForecastResult; lang: Lang }) {
  const observed = lang === "vi" ? "Quan sát" : "Observed"
  const estimate = lang === "vi" ? "Dự báo" : "Forecast"
  const band = lang === "vi" ? "Khoảng dự báo 80%" : "80% prediction interval"
  const config = {
    observed: { label: observed, color: "var(--chart-1)" },
    estimate: { label: estimate, color: "var(--chart-3)" },
    band: { label: band, color: "var(--chart-3)" },
  } satisfies ChartConfig
  return (
    <ChartContainer config={config} className={frame} initialDimension={dimensions}>
      <ComposedChart data={forecastRows(output)} margin={margin}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="period" interval="preserveStartEnd" minTickGap={22} {...axisProps} />
        <YAxis width={50} tickFormatter={(value: number) => formatValue(value, lang, "%", 1)} {...axisProps} />
        <ChartTooltip content={<CanvasTip lang={lang} suffix="%" />} />
        <ChartLegend content={<ChartLegendContent nameKey="dataKey" className="flex-wrap" />} />
        <Area dataKey="band" name={band} stroke="none" fill="var(--color-band)" fillOpacity={0.2} isAnimationActive={false} />
        <Line dataKey="observed" name={observed} stroke="var(--color-observed)" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line dataKey="estimate" name={estimate} stroke="var(--color-estimate)" strokeDasharray="5 3" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false}>
          <ErrorBar dataKey="error" width={5} stroke="var(--color-estimate)" />
        </Line>
      </ComposedChart>
    </ChartContainer>
  )
}
