"use client"

import * as React from "react"
import {
  CartesianGrid,
  Label,
  Line,
  LineChart as RechartsLineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { formatNumber, formatPeriod } from "@/lib/monitor/format"

import { useChartAnimation } from "./use-chart-motion"

export interface LineSeries {
  id: string
  name: string
  points: { period: string; value: number | null }[]
  /** Context series stay grey; the first non-context series is the focus. */
  context?: boolean
}

export interface LineChartThreshold {
  value: number
  label: string
  /** `--destructive` only when the rule is actually breached (§2.4). */
  breached?: boolean
}

export interface LineChartProps {
  series: LineSeries[]
  unit?: string
  height?: number
  threshold?: LineChartThreshold | null
  sourceName?: string
  ariaLabel: string
  /** Lines may clip the y-axis; the note below says so (§3.3). */
  zeroBased?: boolean
}

const CONTEXT_COLORS = ["var(--chart-2)", "var(--chart-3)"]
const MAX_SERIES = 3

type Row = { period: string } & Record<string, number | null | string>

interface TooltipRow {
  name?: string | number
  value?: number | string
  color?: string
  dataKey?: string | number
}

function lastPoint(points: LineSeries["points"]): { period: string; value: number } | null {
  for (let index = points.length - 1; index >= 0; index -= 1) {
    const point = points[index]
    if (point && typeof point.value === "number" && Number.isFinite(point.value)) {
      return { period: point.period, value: point.value }
    }
  }
  return null
}

function LineTooltip({
  active,
  payload,
  label,
  unit,
  sourceName,
}: {
  active?: boolean
  payload?: TooltipRow[]
  label?: string | number
  unit?: string
  sourceName?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="flex flex-col gap-1 rounded-md border border-border bg-background px-2 py-1.5 text-xs">
      <p className="font-medium">{formatPeriod(String(label ?? ""))}</p>
      {payload.map((row, index) => (
        <p key={`${row.dataKey ?? index}`} className="flex items-baseline gap-1.5 tabular-nums">
          <span className="inline-block size-1.5 rounded-full" style={{ backgroundColor: row.color }} aria-hidden="true" />
          <span className="text-muted-foreground">{row.name}</span>
          <span>
            {typeof row.value === "number" ? formatNumber(row.value) : row.value}
            {unit ? ` ${unit}` : ""}
          </span>
        </p>
      ))}
      {sourceName ? <p className="text-muted-foreground">{sourceName}</p> : null}
    </div>
  )
}

/** ≤3 series: one focus line in `--foreground`, ≤2 grey context lines, labelled last point. */
export function LineChart({ series, unit, height = 240, threshold, sourceName, ariaLabel, zeroBased }: LineChartProps) {
  const animation = useChartAnimation()

  const plot = React.useMemo(() => {
    const capped = series.slice(0, MAX_SERIES)
    const focusIndex = Math.max(
      0,
      capped.findIndex((item) => !item.context)
    )
    let contextSlot = 0
    const lines = capped.map((item, index) => ({
      key: `s${index}`,
      name: item.name,
      points: item.points,
      color: index === focusIndex ? "var(--foreground)" : CONTEXT_COLORS[contextSlot++ % CONTEXT_COLORS.length],
      focus: index === focusIndex,
    }))

    const byPeriod = new Map<string, Row>()
    for (const line of lines) {
      for (const point of line.points) {
        const row: Row = byPeriod.get(point.period) ?? { period: point.period }
        row[line.key] = point.value
        byPeriod.set(point.period, row)
      }
    }
    const rows = [...byPeriod.values()].sort((a, b) => String(a.period).localeCompare(String(b.period)))
    const values = lines.flatMap((line) =>
      line.points.map((point) => point.value).filter((value): value is number => typeof value === "number")
    )
    return { lines, rows, min: values.length ? Math.min(...values) : null }
  }, [series])

  if (!plot.rows.length) return null
  const clipped = !zeroBased && plot.min !== null && plot.min > 0

  return (
    <div className="flex flex-col gap-1">
      {unit ? <p className="text-xs text-muted-foreground">Đơn vị: {unit}</p> : null}
      <div style={{ height }} role="img" aria-label={ariaLabel}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsLineChart data={plot.rows} margin={{ top: 18, right: 28, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="2 4" />
            <XAxis
              dataKey="period"
              tickFormatter={(value: string) => formatPeriod(value)}
              tickLine={false}
              axisLine={false}
              minTickGap={16}
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            />
            <YAxis
              tickFormatter={(value: number) => formatNumber(value)}
              tickLine={false}
              axisLine={false}
              tickCount={4}
              width={54}
              domain={zeroBased ? [0, "auto"] : ["auto", "auto"]}
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            />
            <Tooltip
              content={<LineTooltip unit={unit} sourceName={sourceName} />}
              animationDuration={80}
              cursor={{ stroke: "var(--border)" }}
            />
            {threshold ? (
              <ReferenceLine
                y={threshold.value}
                stroke={threshold.breached ? "var(--destructive)" : "var(--border)"}
                strokeDasharray="4 4"
                label={{
                  value: threshold.label,
                  position: "insideTopRight",
                  fontSize: 11,
                  fill: threshold.breached ? "var(--destructive)" : "var(--muted-foreground)",
                }}
              />
            ) : null}
            {plot.lines.map((line) => (
              <Line
                key={line.key}
                dataKey={line.key}
                name={line.name}
                stroke={line.color}
                strokeWidth={line.focus ? 2 : 1.5}
                dot={false}
                activeDot={{ r: 3 }}
                connectNulls={false}
                isAnimationActive={animation.isAnimationActive}
                animationDuration={animation.animationDuration}
                animationEasing={animation.animationEasing}
              />
            ))}
            {plot.lines.map((line) => {
              const last = lastPoint(line.points)
              if (!last) return null
              return (
                <ReferenceDot
                  key={`${line.key}-last`}
                  x={last.period}
                  y={last.value}
                  r={2.5}
                  fill={line.color}
                  stroke="none"
                  ifOverflow="extendDomain"
                >
                  <Label
                    value={unit === "%" ? `${formatNumber(last.value)}%` : unit ? `${formatNumber(last.value)} ${unit}` : formatNumber(last.value)}
                    position="top"
                    fontSize={11}
                    fill={line.focus ? "var(--foreground)" : "var(--muted-foreground)"}
                  />
                </ReferenceDot>
              )
            })}
          </RechartsLineChart>
        </ResponsiveContainer>
      </div>
      {clipped ? <p className="text-xs text-muted-foreground">Trục tung không từ 0.</p> : null}
    </div>
  )
}
