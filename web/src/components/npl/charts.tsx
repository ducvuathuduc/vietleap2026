"use client"

import { Area, Bar, BarChart, CartesianGrid, ComposedChart, ErrorBar, Line, ReferenceDot, ReferenceLine, XAxis, YAxis } from "recharts"

import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart"
import { HowToRead } from "@/components/npl/how-to-read"
import { formatNumber, type Lang } from "@/lib/npl/view"
import type { SeasonalRow } from "@/lib/npl/research-types"

type TipItem = { name?: string; value?: number | string; color?: string; dataKey?: string | number }

export function AdjustedNplChart({ rows, lang }: { rows: SeasonalRow[]; lang: Lang }) {
  const vi = lang === "vi"
  const reported = vi ? "Công bố" : "Reported"
  const adjusted = vi ? "Đã điều chỉnh mùa vụ" : "Seasonally adjusted"
  const config = {
    reported_npl_pct: { label: reported, color: "var(--chart-5)" },
    adjusted_npl_pct: { label: adjusted, color: "var(--chart-2)" },
  } satisfies ChartConfig
  return (
    <div className="min-w-0 rounded-xl border border-border px-2 pt-2 pb-3 sm:px-3">
      <ChartContainer config={config} className="aspect-auto h-56 w-full min-w-0" initialDimension={{ width: 640, height: 224 }}>
        <ComposedChart data={rows} margin={{ top: 12, right: 18, left: 4, bottom: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={24} tick={{ fontSize: 11 }} />
          <YAxis width={45} tickLine={false} axisLine={false} tick={{ fontSize: 11 }}
            tickFormatter={(value: number) => `${formatNumber(value, lang, 1)}%`} />
          <ChartTooltip content={<Tip digits={2} lang={lang} />} />
          <Line dataKey="reported_npl_pct" name={reported} stroke="var(--color-reported_npl_pct)" dot={false} strokeWidth={2} isAnimationActive={false} />
          <Line dataKey="adjusted_npl_pct" name={adjusted} stroke="var(--color-adjusted_npl_pct)" dot={false} strokeWidth={2}
            strokeDasharray="5 3" isAnimationActive={false} />
        </ComposedChart>
      </ChartContainer>
      <ul className="flex flex-wrap gap-4 px-2 text-xs text-muted-foreground">
        <li className="flex items-center gap-1.5"><span className="w-5 border-b-2 border-chart-5" aria-hidden="true" />{reported}</li>
        <li className="flex items-center gap-1.5"><span className="w-5 border-b-2 border-dashed border-chart-2" aria-hidden="true" />{adjusted}</li>
      </ul>
    </div>
  )
}

function axisTick(lang: Lang) {
  return (value: number | string) => formatNumber(Number(value), lang, 2)
}

function Tip({ active, payload, label, digits = 3, lang = "vi" }: { active?: boolean; payload?: TipItem[]; label?: string | number; digits?: number; lang?: Lang }) {
  if (!active || !payload?.length) return null
  const rows = payload.filter((item) => typeof item.value === "number" && item.dataKey !== "base" && item.dataKey !== "band" && item.dataKey !== "allBase" && item.dataKey !== "allBand" && item.dataKey !== "q4Base" && item.dataKey !== "q4Band")
  if (!rows.length) return null
  return (
    <div className="grid min-w-32 gap-1 rounded-lg border border-border bg-background px-2 py-1.5 text-xs">
      <p className="font-medium">{label}</p>
      {rows.map((item) => (
        <p key={String(item.dataKey)}>{item.name}: {formatNumber(Number(item.value), lang, digits)}</p>
      ))}
    </div>
  )
}

const medianConfig = {
  median: { label: "Trung vị", color: "var(--foreground)" },
  band: { label: "25–75% ngân hàng", color: "var(--chart-1)" },
  q4: { label: "Quý 4", color: "var(--foreground)" },
} satisfies ChartConfig

function MedianTip({ active, payload, label, lang }: { active?: boolean; payload?: { payload?: { median?: number | null; p25?: number | null; p75?: number | null; nBanks?: number | null } }[]; label?: string | number; lang: Lang }) {
  const row = payload?.[0]?.payload
  if (!active || row?.median == null) return null
  const pct = (value: number | null | undefined) => value == null ? "—" : `${formatNumber(value, lang, 2)}%`
  return (
    <div className="grid min-w-32 gap-1 rounded-lg border border-border bg-background px-2 py-1.5 text-xs">
      <p className="font-medium">{label}</p>
      <p>{lang === "vi" ? "Trung vị" : "Median"}: {pct(row.median)}</p>
      <p>25%: {pct(row.p25)}</p>
      <p>75%: {pct(row.p75)}</p>
      <p>{lang === "vi" ? "Số ngân hàng" : "Banks"}: {row.nBanks ?? "—"}</p>
    </div>
  )
}

export function MedianChart({
  rows,
  lang,
  mark,
}: {
  rows: { period: string; median: number | null; p25: number | null; p75: number | null; nBanks?: number; q4: boolean }[]
  lang: Lang
  mark?: { period: string; label: string } | null
}) {
  const data = rows.map((row) => ({
    period: row.period,
    median: row.median,
    p25: row.p25,
    p75: row.p75,
    nBanks: row.nBanks ?? null,
    base: row.p25,
    band: row.p25 != null && row.p75 != null ? row.p75 - row.p25 : null,
    q4: row.q4,
  }))
  const vi = lang === "vi"
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <ChartContainer config={medianConfig} className="aspect-auto h-56 w-full min-w-0" initialDimension={{ width: 640, height: 224 }}>
        <ComposedChart data={data} margin={{ top: 16, right: 8, left: 12, bottom: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" tickLine={false} axisLine={false} interval="preserveStartEnd" tick={{ fontSize: 11 }} />
          <YAxis width={52} tickLine={false} axisLine={false} tick={{ fontSize: 11 }} tickFormatter={axisTick(lang)} label={{ value: vi ? "% dư nợ" : "% of loans", angle: -90, position: "insideLeft", style: { fill: "var(--muted-foreground)", fontSize: 11 } }} />
          <ChartTooltip content={<MedianTip lang={lang} />} />
          <Area dataKey="base" stackId="iqr" stroke="none" fill="transparent" name="P25" isAnimationActive={false} />
          <Area dataKey="band" stackId="iqr" stroke="none" fill="var(--color-band)" fillOpacity={0.15} name={vi ? "25–75% ngân hàng" : "25–75% of banks"} isAnimationActive={false} />
          <Line dataKey="median" name={vi ? "Trung vị" : "Median"} stroke="var(--foreground)" strokeWidth={2.5} dot={false} animationDuration={800} />
          {data.filter((row) => row.q4 && row.median != null).map((row) => (
            <ReferenceDot
              key={row.period}
              x={row.period}
              y={row.median ?? 0}
              r={4}
              fill="var(--foreground)"
              stroke="var(--background)"
              label={row.period === mark?.period ? { value: mark.label, position: "top", fontSize: 11, fill: "var(--foreground)" } : undefined}
            />
          ))}
        </ComposedChart>
      </ChartContainer>
      <ul className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        <li className="flex items-center gap-1"><span className="inline-block h-0.5 w-6 bg-foreground" />{vi ? "Trung vị" : "Median"}</li>
        <li className="flex items-center gap-1"><span className="inline-block size-3 bg-chart-1/15" />{vi ? "25–75% ngân hàng" : "25–75% of banks"}</li>
        <li className="flex items-center gap-1"><span className="inline-block size-2 rounded-full bg-foreground" />{vi ? "Quý 4" : "Q4"}</li>
      </ul>
    </div>
  )
}

const quarterConfig = {
  coef: { label: "Hệ số", color: "var(--chart-1)" },
} satisfies ChartConfig

export function QuarterChart({
  bars,
  lang,
}: {
  bars: { quarter: number; coef: number; lo: number | null; hi: number | null }[]
  lang: Lang
}) {
  const data = bars.map((bar) => ({
    quarter: `Q${bar.quarter}`,
    coef: bar.coef,
    error: bar.lo != null && bar.hi != null ? [bar.coef - bar.lo, bar.hi - bar.coef] : undefined,
  }))
  return (
    <ChartContainer config={quarterConfig} className="aspect-auto h-52 w-full min-w-0" initialDimension={{ width: 640, height: 208 }}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="quarter" tickLine={false} axisLine={false} />
        <YAxis width={52} tickLine={false} axisLine={false} tickFormatter={axisTick(lang)} />
        <ReferenceLine y={0} stroke="var(--muted-foreground)" label={{ value: lang === "vi" ? "Quý 1 = 0" : "Q1 = 0", position: "insideTopRight", fontSize: 11, fill: "var(--foreground)" }} />
        <ChartTooltip content={<Tip lang={lang} />} />
        <Bar dataKey="coef" name={lang === "vi" ? "Hệ số" : "Coefficient"} fill="var(--color-coef)" radius={4}>
          <ErrorBar dataKey="error" width={6} stroke="var(--foreground)" />
        </Bar>
      </BarChart>
    </ChartContainer>
  )
}

const drillConfig = {
  q4: { label: "Q4", color: "var(--chart-1)" },
  q1: { label: "Q1", color: "var(--chart-2)" },
} satisfies ChartConfig

export function DrillChart({
  rows,
  lang,
  onPick,
}: {
  rows: { code: string; q4: number | null; q1: number | null }[]
  lang: Lang
  onPick: (code: string) => void
}) {
  return (
    <ChartContainer config={drillConfig} className="aspect-auto h-[34rem] w-full min-w-0" initialDimension={{ width: 640, height: 544 }}>
      <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid horizontal={false} />
        <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={axisTick(lang)} />
        <YAxis type="category" dataKey="code" width={44} tickLine={false} axisLine={false} />
        <ReferenceLine x={0} stroke="var(--muted-foreground)" />
        <ChartTooltip content={<Tip lang={lang} />} />
        <Bar dataKey="q4" name={lang === "vi" ? "Trung vị quý 4" : "Median Q4"} fill="var(--color-q4)" onClick={(row) => onPick(String(row?.payload?.code ?? ""))} />
        <Bar dataKey="q1" name={lang === "vi" ? "Trung vị quý 1" : "Median Q1"} fill="var(--color-q1)" onClick={(row) => onPick(String(row?.payload?.code ?? ""))} />
      </BarChart>
    </ChartContainer>
  )
}

const compareConfig = {
  bank: { label: "Ngân hàng", color: "var(--chart-1)" },
  panel: { label: "Cả nhóm", color: "var(--chart-3)" },
} satisfies ChartConfig

export function BankCompareChart({
  rows,
  lang,
}: {
  rows: { quarter: number; bank: number | null; panel: number | null }[]
  lang: Lang
}) {
  const data = rows.map((row) => ({ quarter: `Q${row.quarter}`, bank: row.bank, panel: row.panel }))
  return (
    <ChartContainer config={compareConfig} className="aspect-auto h-56 w-full min-w-0" initialDimension={{ width: 640, height: 224 }}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="quarter" tickLine={false} axisLine={false} />
        <YAxis width={52} tickLine={false} axisLine={false} tickFormatter={axisTick(lang)} />
        <ReferenceLine y={0} stroke="var(--muted-foreground)" />
        <ChartTooltip content={<Tip lang={lang} />} />
        <Bar dataKey="bank" name={lang === "vi" ? "Trung bình của ngân hàng này" : "This bank's mean"} fill="var(--color-bank)" radius={4} />
        {data.map((row) => row.panel == null ? null : (
          <ReferenceDot key={row.quarter} x={row.quarter} y={row.panel} r={5} fill="var(--color-panel)" stroke="var(--background)" />
        ))}
      </ComposedChart>
    </ChartContainer>
  )
}

const ratioConfig = {
  npl: { label: "NPL", color: "var(--chart-1)" },
  nim: { label: "NIM", color: "var(--chart-2)" },
} satisfies ChartConfig

const balanceConfig = {
  coverage: { label: "Bao phủ", color: "var(--chart-3)" },
  ldr: { label: "LDR", color: "var(--chart-4)" },
} satisfies ChartConfig

const growthConfig = {
  loanGrowth: { label: "Tăng trưởng dư nợ", color: "var(--chart-5)" },
} satisfies ChartConfig

type BankLineRow = { period: string; npl: number | null; coverage: number | null; nim: number | null; ldr: number | null; loanGrowth: number | null }

export function BankLines({ rows, lang }: { rows: BankLineRow[]; lang: Lang }) {
  const growthLabel = lang === "vi" ? "Tăng trưởng dư nợ" : "Loan growth"
  const coverageLabel = lang === "vi" ? "Bao phủ" : "Coverage"
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm font-medium">NPL, NIM</p>
      <ChartContainer config={ratioConfig} className="aspect-auto h-48 w-full min-w-0" initialDimension={{ width: 640, height: 192 }}>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" tickLine={false} axisLine={false} interval="preserveStartEnd" tick={{ fontSize: 11 }} />
          <YAxis width={44} tickLine={false} axisLine={false} tickFormatter={axisTick(lang)} />
          <ChartTooltip content={<Tip lang={lang} digits={2} />} />
          <Line dataKey="npl" name="NPL" stroke="var(--color-npl)" dot={false} strokeWidth={2} connectNulls={false} />
          <Line dataKey="nim" name="NIM" stroke="var(--color-nim)" dot={false} strokeWidth={2} connectNulls={false} />
        </ComposedChart>
      </ChartContainer>
      <HowToRead
        label={lang === "vi" ? "Cách đọc" : "How to read"}
        sentences={lang === "vi"
          ? ["Một đường là tỷ lệ nợ xấu, đường kia là NIM.", "Hai đường cùng thang phần trăm. Chỗ đứt là quý chưa có số."]
          : ["One line is the NPL ratio and the other is NIM.", "Both use the percent scale. A break is a quarter without a figure."]}
      />
      <p className="text-sm font-medium">{lang === "vi" ? "Bao phủ, LDR" : "Coverage, LDR"}</p>
      <ChartContainer config={balanceConfig} className="aspect-auto h-48 w-full min-w-0" initialDimension={{ width: 640, height: 192 }}>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" tickLine={false} axisLine={false} interval="preserveStartEnd" tick={{ fontSize: 11 }} />
          <YAxis width={52} tickLine={false} axisLine={false} tickFormatter={axisTick(lang)} />
          <ChartTooltip content={<Tip lang={lang} digits={2} />} />
          <Line dataKey="coverage" name={coverageLabel} stroke="var(--color-coverage)" dot={false} strokeWidth={2} connectNulls={false} />
          <Line dataKey="ldr" name="LDR" stroke="var(--color-ldr)" dot={false} strokeWidth={2} connectNulls={false} />
        </ComposedChart>
      </ChartContainer>
      <HowToRead
        label={lang === "vi" ? "Cách đọc" : "How to read"}
        sentences={lang === "vi"
          ? ["Một đường là tỷ lệ bao phủ, đường kia là LDR.", "Cùng thang phần trăm. Bao phủ trên 100% nghĩa là dự phòng lớn hơn nợ xấu."]
          : ["One line is coverage and the other is LDR.", "They share the percent scale. Coverage above 100% means provisions exceed bad debt."]}
      />
      <p className="text-sm font-medium">{growthLabel}</p>
      <ChartContainer config={growthConfig} className="aspect-auto h-48 w-full min-w-0" initialDimension={{ width: 640, height: 192 }}>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" tickLine={false} axisLine={false} interval="preserveStartEnd" tick={{ fontSize: 11 }} />
          <YAxis width={52} tickLine={false} axisLine={false} tickFormatter={axisTick(lang)} />
          <ReferenceLine y={0} stroke="var(--muted-foreground)" />
          <ChartTooltip content={<Tip lang={lang} digits={2} />} />
          <Line dataKey="loanGrowth" name={growthLabel} stroke="var(--color-loanGrowth)" dot={false} strokeWidth={2} connectNulls={false} />
        </ComposedChart>
      </ChartContainer>
      <HowToRead
        label={lang === "vi" ? "Cách đọc" : "How to read"}
        sentences={lang === "vi"
          ? ["Đường là tăng trưởng dư nợ so với cùng kỳ.", "Vạch 0 là dư nợ không đổi."]
          : ["The line is loan growth versus a year earlier.", "The zero line is unchanged loans."]}
      />
    </div>
  )
}

const marketConfig = {
  all: { label: "Tất cả", color: "var(--chart-1)" },
  q4: { label: "Q4", color: "var(--chart-4)" },
  allBand: { label: "Khoảng tất cả", color: "var(--chart-1)" },
  q4Band: { label: "Khoảng Q4", color: "var(--chart-4)" },
} satisfies ChartConfig

export function MarketChart({
  rows,
  lang,
}: {
  rows: { day: number; all: number | null; allLo: number | null; allHi: number | null; q4: number | null; q4Lo: number | null; q4Hi: number | null }[]
  lang: Lang
}) {
  const data = rows.map((row) => ({
    day: row.day,
    all: row.all,
    q4: row.q4,
    allBase: row.allLo,
    allBand: row.allLo != null && row.allHi != null ? row.allHi - row.allLo : null,
    q4Base: row.q4Lo,
    q4Band: row.q4Lo != null && row.q4Hi != null ? row.q4Hi - row.q4Lo : null,
  }))
  return (
    <ChartContainer config={marketConfig} className="aspect-auto h-64 w-full min-w-0" initialDimension={{ width: 640, height: 256 }}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="day" tickLine={false} axisLine={false} />
        <YAxis width={52} tickLine={false} axisLine={false} tickFormatter={axisTick(lang)} />
        <ReferenceLine y={0} stroke="var(--muted-foreground)" />
        <ChartTooltip content={<Tip lang={lang} />} />
        <Area dataKey="allBase" stackId="all" stroke="none" fill="transparent" />
        <Area dataKey="allBand" stackId="all" stroke="none" fill="var(--color-allBand)" fillOpacity={0.2} name={lang === "vi" ? "Khoảng tất cả" : "All interval"} />
        <Area dataKey="q4Base" stackId="q4" stroke="none" fill="transparent" />
        <Area dataKey="q4Band" stackId="q4" stroke="none" fill="var(--color-q4Band)" fillOpacity={0.18} name={lang === "vi" ? "Khoảng quý 4" : "Q4 interval"} />
        <Line dataKey="all" name={lang === "vi" ? "Tất cả" : "All"} stroke="var(--color-all)" strokeWidth={2} dot={false} />
        <Line dataKey="q4" name="Q4" stroke="var(--color-q4)" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ChartContainer>
  )
}

const forecastConfig = {
  npl: { label: "NPL", color: "var(--chart-1)" },
} satisfies ChartConfig

export function ForecastBand({
  point,
  lang,
}: {
  point: { period: string; npl: number; lo: number; hi: number }
  lang: Lang
}) {
  const data = [{ period: point.period, npl: point.npl, error: [point.npl - point.lo, point.hi - point.npl] }]
  return (
    <ChartContainer config={forecastConfig} className="aspect-auto h-40 w-full min-w-0" initialDimension={{ width: 320, height: 160 }}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="period" tickLine={false} axisLine={false} />
        <YAxis width={44} tickLine={false} axisLine={false} tickFormatter={axisTick(lang)} />
        <ChartTooltip content={<Tip lang={lang} digits={2} />} />
        <Bar dataKey="npl" name="NPL" fill="var(--color-npl)" radius={4}>
          <ErrorBar dataKey="error" width={6} stroke="var(--foreground)" />
        </Bar>
      </BarChart>
    </ChartContainer>
  )
}
