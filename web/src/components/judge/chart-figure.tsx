import type { ReactNode } from "react"
import { cn } from "cn"

import { EmptyState } from "./empty-state"
import { canRenderChart, emptyPeriodText, figureLabel, loadErrorText, partialPeriodText } from "./labels"
import { enterClass } from "./motion"
import { TrustLine, type TrustLineProps } from "./trust-line"

export interface ChartFigureProps {
  /** `charts[].number`; when present the figcaption is numbered. */
  number?: number | null
  /** `charts[].title_vi` — a conclusion sentence, not the indicator name. */
  title: string
  ariaLabel: string
  /** The chart island (or a server-rendered SVG/table). */
  children: ReactNode
  trust: TrustLineProps
  note?: string | null
  /** `charts[].source_ids`; no source means the figure is not rendered at all. */
  sourceIds: string[]
  pointCount: number
  frequency?: string | null
  /** Whole months covered when the period is not complete yet (§3.5). */
  partialMonths?: number | null
  /** Block name when loading failed, e.g. "biểu đồ tín dụng". */
  error?: string | null
  id?: string
}

/** §3.2 figure wrapper: numbered figcaption, aria-label, empty/partial states, TrustLine. */
export function ChartFigure({
  number,
  title,
  ariaLabel,
  children,
  trust,
  note,
  sourceIds,
  pointCount,
  frequency,
  partialMonths,
  error,
  id,
}: ChartFigureProps) {
  // Fail closed: a number without a source is not shown (§1.3).
  if (!sourceIds.length) return null

  const hasData = canRenderChart({ sourceIds, pointCount })
  const sourceHref = trust.links?.data

  return (
    <figure
      id={id}
      aria-label={ariaLabel}
      className={cn("flex scroll-mt-20 flex-col gap-3 rounded-xl border border-border bg-card p-4", enterClass())}
    >
      <figcaption className="text-sm font-medium">{figureLabel(number, title)}</figcaption>
      {error ? (
        <EmptyState title="Không tải được số liệu" message={loadErrorText(error)} />
      ) : hasData ? (
        children
      ) : (
        <EmptyState
          message={emptyPeriodText(frequency)}
          link={sourceHref ? { label: "Xem nguồn", href: sourceHref } : undefined}
        />
      )}
      {hasData && partialMonths ? (
        <p className="text-xs text-muted-foreground">{partialPeriodText(partialMonths)}</p>
      ) : null}
      {note ? <p className="text-xs text-muted-foreground">{note}</p> : null}
      <TrustLine {...trust} />
    </figure>
  )
}
