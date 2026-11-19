import { formatNumber } from "@/lib/monitor/format"

export interface RangeItem {
  id: string
  label: string
  min: number
  median: number
  max: number
}

export interface RangeChartProps {
  items: RangeItem[]
  unit?: string
  /** The one row to ink in (§3.1 highlight). */
  highlightId?: string
  /** Optional vertical benchmark, e.g. the national median. */
  reference?: number | null
  referenceLabel?: string
  ariaLabel: string
}

const WIDTH = 640
const LABEL_WIDTH = 136
const RIGHT_PAD = 56
const ROW_HEIGHT = 28
const TICK_ROW = 20

/**
 * Min–median–max range chart, server-rendered as inline SVG (zero JS): one row per
 * unit, dots at min/median/max, dashed benchmark, no grid (§3.1, §3.2).
 */
export function RangeChart({ items, unit, highlightId, reference, referenceLabel, ariaLabel }: RangeChartProps) {
  if (!items.length) return null

  const values = items.flatMap((item) => [item.min, item.median, item.max])
  if (reference !== null && reference !== undefined) values.push(reference)
  const finite = values.filter((value) => Number.isFinite(value))
  if (!finite.length) return null

  const lo = Math.min(...finite)
  const hi = Math.max(...finite)
  const plotWidth = WIDTH - LABEL_WIDTH - RIGHT_PAD
  const scaleX = (value: number) => (hi === lo ? LABEL_WIDTH + plotWidth / 2 : LABEL_WIDTH + ((value - lo) / (hi - lo)) * plotWidth)
  const plotBottom = items.length * ROW_HEIGHT
  const height = plotBottom + TICK_ROW + 8
  const ticks = [lo, (lo + hi) / 2, hi]

  return (
    <div className="flex flex-col gap-1">
      {unit ? <p className="text-xs text-muted-foreground">Đơn vị: {unit}</p> : null}
      <svg viewBox={`0 0 ${WIDTH} ${height}`} width="100%" role="img" aria-label={ariaLabel} className="text-foreground">
        {reference !== null && reference !== undefined ? (
          <g>
            <line
              x1={scaleX(reference)}
              y1={0}
              x2={scaleX(reference)}
              y2={plotBottom}
              stroke="var(--border)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            {referenceLabel ? (
              <text x={scaleX(reference) + 4} y={10} fontSize={10} fill="var(--muted-foreground)">
                {referenceLabel}
              </text>
            ) : null}
          </g>
        ) : null}

        {items.map((item, index) => {
          const y = index * ROW_HEIGHT + ROW_HEIGHT / 2
          const isHighlight = item.id === highlightId
          return (
            <g key={item.id}>
              <title>
                {`${item.label}: ${formatNumber(item.min)} – ${formatNumber(item.max)}, trung vị ${formatNumber(item.median)}${unit ? ` ${unit}` : ""}`}
              </title>
              <text
                x={0}
                y={y + 4}
                fontSize={11}
                fontWeight={isHighlight ? 600 : 400}
                fill={isHighlight ? "var(--foreground)" : "var(--muted-foreground)"}
              >
                {item.label}
              </text>
              <line
                x1={scaleX(item.min)}
                y1={y}
                x2={scaleX(item.max)}
                y2={y}
                stroke={isHighlight ? "var(--chart-3)" : "var(--border)"}
                strokeWidth={isHighlight ? 2 : 1}
              />
              <circle cx={scaleX(item.min)} cy={y} r={2} fill="var(--chart-2)" />
              <circle cx={scaleX(item.max)} cy={y} r={2} fill="var(--chart-2)" />
              <circle
                cx={scaleX(item.median)}
                cy={y}
                r={isHighlight ? 4 : 3}
                fill={isHighlight ? "var(--foreground)" : "var(--chart-3)"}
              />
            </g>
          )
        })}

        {ticks.map((tick, index) => (
          <text
            key={tick}
            x={scaleX(tick)}
            y={plotBottom + 16}
            fontSize={11}
            fill="var(--muted-foreground)"
            textAnchor={index === 0 ? "start" : index === ticks.length - 1 ? "end" : "middle"}
          >
            {formatNumber(tick)}
          </text>
        ))}
      </svg>
    </div>
  )
}
