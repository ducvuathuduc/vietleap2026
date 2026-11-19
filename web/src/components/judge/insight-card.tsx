import { Card, CardContent } from "@/components/ui/card"
import { cn } from "cn"

import { enterClass } from "./motion"

export interface InsightCardAction {
  text: string
  href?: string
}

export interface InsightCardProps {
  /** Indicator name, kept out of the conclusion sentence (§7.2). */
  eyebrow?: string
  /** Formatted value, e.g. "4,2". */
  value: string
  unit?: string
  /** Formatted period, e.g. "T10/2026". */
  period?: string
  /** §7.3: one sentence, 25–35 words. */
  sentence: string
  action?: InsightCardAction | null
  /** "World Bank WDI · T10/2026" — publisher plus period. */
  source?: string | null
  indicatorHref?: string
}

/** One insight card: number · sentence · action · source (§6). */
export function InsightCard({
  eyebrow,
  value,
  unit,
  period,
  sentence,
  action,
  source,
  indicatorHref,
}: InsightCardProps) {
  return (
    <Card size="sm" className={cn("gap-3 rounded-xl shadow-none", enterClass())}>
      <CardContent className="flex flex-col gap-2">
        {eyebrow ? (
          <p className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">{eyebrow}</p>
        ) : null}
        <p className="flex flex-wrap items-baseline gap-1 tabular-nums">
          <span className="text-3xl font-semibold">{value}</span>
          {unit ? <span className="text-base font-normal text-muted-foreground">{unit}</span> : null}
          {period ? <span className="text-xs text-muted-foreground">{period}</span> : null}
        </p>
        <h2 className="text-sm leading-relaxed font-normal">
          {indicatorHref ? (
            <a
              href={indicatorHref}
              className="hover:underline hover:underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              {sentence}
            </a>
          ) : (
            sentence
          )}
        </h2>
        {action ? (
          <p className="text-sm">
            {action.href ? (
              <a
                href={action.href}
                className="underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                {action.text}
              </a>
            ) : (
              action.text
            )}
          </p>
        ) : null}
        {source ? <p className="text-xs text-muted-foreground">{source}</p> : null}
      </CardContent>
    </Card>
  )
}
