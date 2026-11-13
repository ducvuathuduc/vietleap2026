"use client"

import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import type { Kpi } from "@/lib/api/types"
import { TrendingUpIcon, TrendingDownIcon } from "lucide-react"
import { insightTarget } from "@/lib/insight-target"

export function SectionCards({ kpis }: { kpis: Kpi[] | undefined }) {
  return (
    <div className="grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-linear-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4 dark:*:data-[slot=card]:bg-card">
      {!kpis
        ? Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-36 rounded-xl" />)
        : kpis.map((k) => {
            const up = (k.delta_pct ?? 0) >= 0
            const Icon = up ? TrendingUpIcon : TrendingDownIcon
            return (
              <Card key={k.label} className="@container/card" {...insightTarget("kpi", k.label, k.label_vi || k.label, k)}>
                <CardHeader>
                  <CardDescription className="truncate">{k.label}</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                    {k.value}
                  </CardTitle>
                  {k.delta_pct !== null && (
                    <CardAction>
                      <Badge variant="outline">
                        <Icon
                        />
                        {up ? "+" : ""}
                        {k.delta_pct.toFixed(1)}%
                      </Badge>
                    </CardAction>
                  )}
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    {k.footer}{" "}
                    {k.delta_pct !== null && <Icon className="size-4" />}
                  </div>
                  <div className="line-clamp-1 text-muted-foreground">
                    {k.description}
                  </div>
                </CardFooter>
              </Card>
            )
          })}
    </div>
  )
}
