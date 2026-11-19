import { cn } from "cn"

import { Sparkline } from "./sparkline"
import { enterClass } from "./motion"

export interface KpiChange {
  /** Already formatted, e.g. "+1,2 điểm % so với T9/2026". */
  text: string
  direction?: "up" | "down" | "flat"
  severity?: "info" | "watch" | "alert"
}

export interface KpiTileProps {
  /** Eyebrow, 11px (§2.1). */
  name: string
  /** Formatted value from `@/lib/monitor/format`, e.g. "12,5". */
  value: string
  unit?: string
  /** Formatted period, e.g. "T10/2026". */
  period?: string
  change?: KpiChange | null
  sparkline?: number[]
  href?: string
}

const SHELL = "flex flex-col gap-2 rounded-xl border border-border bg-card p-4"

/** One KPI tile: eyebrow, value + unit, sparkline, period · change (§6). */
export function KpiTile({ name, value, unit, period, change, sparkline = [], href }: KpiTileProps) {
  const body = (
    <>
      <p className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">{name}</p>
      <p className="flex flex-wrap items-baseline gap-1 tabular-nums">
        <span className="text-3xl font-semibold md:text-4xl">{value}</span>
        {unit ? <span className="text-base font-normal text-muted-foreground">{unit}</span> : null}
      </p>
      <Sparkline points={sparkline} ariaLabel={`Xu hướng ${name}`} />
      {period || change ? (
        <p className="flex flex-wrap items-baseline gap-1 text-xs text-muted-foreground">
          {period ? <span>{period}</span> : null}
          {period && change ? <span aria-hidden="true">·</span> : null}
          {change ? (
            <span className={change.severity === "alert" ? "text-destructive" : undefined}>{change.text}</span>
          ) : null}
        </p>
      ) : null}
    </>
  )

  const className = cn(SHELL, enterClass())

  if (!href) return <div className={className}>{body}</div>

  return (
    <a
      href={href}
      className={cn(className, "hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring")}
    >
      {body}
    </a>
  )
}
