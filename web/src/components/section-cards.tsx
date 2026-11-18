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
    <div className="grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
      {!kpis
        ? Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-36 rounded-xl" />)
        : kpis.map((k) => {
            const up = (k.delta_pct ?? 0) >= 0
            const Icon = up ? TrendingUpIcon : TrendingDownIcon
            const deltaClass = up
              ? "border-emerald-600/30 bg-emerald-50 text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-950 dark:text-emerald-300"
              : "border-red-600/30 bg-red-50 text-red-700 dark:border-red-400/30 dark:bg-red-950 dark:text-red-300"
            return (
              <Card key={k.label} className="@container/card" {...insightTarget("kpi", k.label, k.label_vi || k.label, k)}>
                <CardHeader>
                  <CardDescription title={k.label_vi || k.label} className="line-clamp-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{k.label_vi || k.label}</CardDescription>
                  <CardTitle className="text-3xl font-semibold tracking-tight tabular-nums @[250px]/card:text-4xl">
                    {k.value}
                  </CardTitle>
                  {k.delta_pct !== null && (
                    <CardAction>
                      <Badge variant="outline" className={deltaClass}>
                        <Icon
                        />
                        {up ? "+" : ""}
                        {k.delta_pct.toFixed(1)}%
                      </Badge>
                    </CardAction>
                  )}
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 border-t-0 bg-transparent text-sm">
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
