export interface SparklineProps {
  points: number[]
  width?: number
  height?: number
  ariaLabel?: string
}

/**
 * Inline SVG sparkline: zero JS, server rendered, no grid (§3.2). Fewer than two
 * finite points renders only the layout box, never a fake flat line.
 */
export function Sparkline({ points, width = 96, height = 24, ariaLabel = "Xu hướng gần nhất" }: SparklineProps) {
  const values = points.filter((value) => Number.isFinite(value))
  if (values.length < 2) return <span className="block h-6" aria-hidden="true" />

  const min = Math.min(...values)
  const max = Math.max(...values)
  const scaleX = (index: number) => (index / (values.length - 1)) * width
  const scaleY = (value: number) => (max === min ? height / 2 : height - ((value - min) / (max - min)) * height)

  const path = values
    .map((value, index) => `${index === 0 ? "M" : "L"}${scaleX(index).toFixed(1)},${scaleY(value).toFixed(1)}`)
    .join(" ")
  const lastValue = values[values.length - 1]

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      role="img"
      aria-label={ariaLabel}
      className="text-foreground"
    >
      <path d={path} fill="none" stroke="currentColor" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      <circle cx={scaleX(values.length - 1)} cy={scaleY(lastValue)} r={2} fill="currentColor" />
    </svg>
  )
}
