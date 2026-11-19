"use client"

import * as React from "react"
import { Bar, BarChart as RechartsBarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { formatNumber } from "@/lib/monitor/format"

import { useChartAnimation } from "./use-chart-motion"

export interface BarRankRow {
  id: string
  label: string
  value: number
  highlight?: boolean
}

export interface BarRankProps {
  rows: BarRankRow[]
  unit?: string
  period?: string
  height?: number
  /** Defaults to the first `highlight` row. */
  highlightId?: string
  sourceName?: string
  ariaLabel: string
}

interface TooltipRow {
  payload?: BarRankRow
  value?: number | string
}

function RankTooltip({
  active,
  payload,
  unit,
  period,
  sourceName,
}: {
  active?: boolean
  payload?: TooltipRow[]
  unit?: string
  period?: string
  sourceName?: string
}) {
  const row = payload?.[0]?.payload
  if (!active || !row) return null
  return (
    <div className="flex flex-col gap-1 rounded-md border border-border bg-background px-2 py-1.5 text-xs">
      <p className="font-medium">{row.label}</p>
      <p className="tabular-nums">
        {formatNumber(row.value)}
        {unit ? ` ${unit}` : ""}
      </p>
      {period || sourceName ? (
        <p className="text-muted-foreground">
          {period ?? ""}
          {period && sourceName ? " · " : ""}
          {sourceName ?? ""}
        </p>
      ) : null}
    </div>
  )
}

/** Horizontal ranking bars, sorted high to low, one row in ink (§3.1). */
export function BarRank({
  rows,
  unit,
  period,
  height = 280,
  highlightId,
  sourceName,
  ariaLabel,
}: BarRankProps) {
  const animation = useChartAnimation()
  const sorted = React.useMemo(() => [...rows].sort((a, b) => b.value - a.value), [rows])
  if (!sorted.length) return null

  const highlight = highlightId ?? sorted.find((row) => row.highlight)?.id ?? sorted[0].id

  return (
    <div className="flex flex-col gap-1">
      {unit ? <p className="text-xs text-muted-foreground">Đơn vị: {unit}</p> : null}
      <div style={{ height }} role="img" aria-label={ariaLabel}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsBarChart layout="vertical" data={sorted} margin={{ top: 4, right: 56, bottom: 4, left: 0 }}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="label"
              width={104}
              tickLine={false}
              axisLine={false}
              interval={0}
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            />
            <Tooltip
              content={<RankTooltip unit={unit} period={period} sourceName={sourceName} />}
              animationDuration={80}
              cursor={{ fill: "var(--muted)" }}
            />
            <Bar
              dataKey="value"
              barSize={14}
              isAnimationActive={animation.isAnimationActive}
              animationDuration={animation.animationDuration}
              animationEasing={animation.animationEasing}
            >
              {sorted.map((row) => (
                <Cell key={row.id} fill={row.id === highlight ? "var(--foreground)" : "var(--chart-2)"} />
              ))}
              <LabelList
                dataKey="value"
                position="right"
                fill="var(--muted-foreground)"
                fontSize={11}
                formatter={(value) => formatNumber(Number(value))}
              />
            </Bar>
          </RechartsBarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
