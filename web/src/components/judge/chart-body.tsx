import type { ChartBodyModel } from "@/app/(dashboard)/_lib/chart-block"

import { BarRank } from "./bar-rank"
import { Heatmap } from "./heatmap"
import { LineChart } from "./line-chart"
import { RangeChart } from "./range-chart"

/**
 * Server-side switch from a mapped chart body to the right island. Only the three
 * interactive chart families are client components; the heatmap and range chart are
 * plain SVG/HTML so they stay in the server payload.
 */
export function ChartBody({ body, label }: { body: ChartBodyModel | null; label: string }) {
  if (!body) return null
  if (body.kind === "line") {
    return <LineChart series={body.series} unit={body.unit} sourceName={body.sourceName} ariaLabel={label} />
  }
  if (body.kind === "bar") {
    return (
      <BarRank
        rows={body.rows}
        unit={body.unit}
        period={body.period}
        sourceName={body.sourceName}
        ariaLabel={label}
      />
    )
  }
  if (body.kind === "range") {
    return (
      <RangeChart
        items={body.items}
        unit={body.unit}
        reference={body.reference}
        referenceLabel={body.referenceLabel}
        highlightId={body.items[0]?.id}
        ariaLabel={label}
      />
    )
  }
  return <Heatmap rows={body.rows} unit={body.unit} ariaLabel={label} />
}
