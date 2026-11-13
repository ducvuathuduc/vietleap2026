"use client"

import * as React from "react"
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"

import { useIsMobile } from "@/hooks/use-mobile"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"
import { Skeleton } from "@/components/ui/skeleton"
import { fmtNum } from "@/lib/format"
import type { TimePoint } from "@/lib/api/types"

export const description = "An interactive area chart of the main time trend"

const RANGES = [
  { value: "all", label: "All periods", n: Infinity },
  { value: "12", label: "Last 12 periods", n: 12 },
  { value: "6", label: "Last 6 periods", n: 6 },
]

export function ChartAreaInteractive({
  points,
  title,
  subtitle,
  metricLabel,
}: {
  points: TimePoint[] | undefined
  title: string
  subtitle: string
  metricLabel: string
}) {
  const isMobile = useIsMobile()
  const [userRange, setTimeRange] = React.useState<string | null>(null)
  const timeRange = userRange ?? (isMobile ? "6" : "all")

  const chartConfig = {
    value: {
      label: metricLabel,
      color: "var(--primary)",
    },
    n: {
      label: "Records",
      color: "var(--primary)",
    },
  } satisfies ChartConfig

  const n = RANGES.find((r) => r.value === timeRange)?.n ?? Infinity
  const filteredData = (points ?? []).filter((p) => p.value !== null).slice(Number.isFinite(n) ? -n : 0)

  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          <span className="hidden @[540px]/card:block">
            {subtitle}
          </span>
          <span className="@[540px]/card:hidden">{metricLabel}</span>
        </CardDescription>
        <CardAction>
          <ToggleGroup
            multiple={false}
            value={timeRange ? [timeRange] : []}
            onValueChange={(value) => {
              setTimeRange(value[0] ?? "all")
            }}
            variant="outline"
            className="hidden *:data-[slot=toggle-group-item]:px-4! @[767px]/card:flex"
          >
            {RANGES.map((r) => (
              <ToggleGroupItem key={r.value} value={r.value}>{r.label}</ToggleGroupItem>
            ))}
          </ToggleGroup>
          <Select
            value={timeRange}
            onValueChange={(value) => {
              if (value !== null) {
                setTimeRange(value)
              }
            }}
            items={RANGES.map((r) => ({ label: r.label, value: r.value }))}
          >
            <SelectTrigger
              className="flex w-40 **:data-[slot=select-value]:block **:data-[slot=select-value]:truncate @[767px]/card:hidden"
              size="sm"
              aria-label="Select a value"
            >
              <SelectValue placeholder="All periods" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              {RANGES.map((r) => (
                <SelectItem key={r.value} value={r.value} className="rounded-lg">
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardAction>
      </CardHeader>
      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
        {!points ? (
          <Skeleton className="h-[250px] w-full" />
        ) : filteredData.length === 0 ? (
          <div className="flex h-[250px] items-center justify-center text-sm text-muted-foreground">
            No time column detected in this dataset.
          </div>
        ) : (
          <ChartContainer
            config={chartConfig}
            className="aspect-auto h-[250px] w-full"
          >
            <AreaChart data={filteredData}>
              <defs>
                <linearGradient id="fillValue" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="var(--color-value)"
                    stopOpacity={1.0}
                  />
                  <stop
                    offset="95%"
                    stopColor="var(--color-value)"
                    stopOpacity={0.1}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="period"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                minTickGap={32}
              />
              <YAxis hide domain={["auto", "auto"]} />
              <ChartTooltip
                cursor={false}
                content={
                  <ChartTooltipContent
                    labelFormatter={(value) => String(value)}
                    formatter={(value) => (
                      <span className="font-mono font-medium tabular-nums">
                        {metricLabel}: {fmtNum(Number(value))}
                      </span>
                    )}
                    indicator="dot"
                  />
                }
              />
              <Area
                dataKey="value"
                type="natural"
                fill="url(#fillValue)"
                stroke="var(--color-value)"
              />
            </AreaChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
