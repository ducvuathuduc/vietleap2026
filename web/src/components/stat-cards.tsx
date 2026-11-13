"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

export interface StatItem {
  label: string
  value: string
  badge?: string
  footer?: string
  hint?: string
  /** data-insight-target props from insightTarget() — makes the card inspectable */
  target?: Record<string, string>
}

/** dashboard-01 SectionCards layout for arbitrary stats (same grid + card classes). */
export function StatCards({ items }: { items: StatItem[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-linear-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4 dark:*:data-[slot=card]:bg-card">
      {items.map((k) => (
        <Card key={k.label} className="@container/card" {...k.target}>
          <CardHeader>
            <CardDescription className="truncate">{k.label}</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">{k.value}</CardTitle>
            {k.badge && (
              <CardAction>
                <Badge variant="outline">{k.badge}</Badge>
              </CardAction>
            )}
          </CardHeader>
          {(k.footer || k.hint) && (
            <CardFooter className="flex-col items-start gap-1.5 text-sm">
              {k.footer && <div className="line-clamp-1 flex gap-2 font-medium">{k.footer}</div>}
              {k.hint && <div className="text-muted-foreground">{k.hint}</div>}
            </CardFooter>
          )}
        </Card>
      ))}
    </div>
  )
}
