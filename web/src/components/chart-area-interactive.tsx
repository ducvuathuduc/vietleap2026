"use client"

import * as React from "react"
import { Area, ComposedChart, Line, CartesianGrid, XAxis, YAxis } from "recharts"

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Toggle } from "@/components/ui/toggle"
import { fmtNum } from "@/lib/format"
import type { TimeGapSummary, TimePoint } from "@/lib/api/types"
import { insightTarget } from "@/lib/insight-target"

export const description = "An interactive area chart of the main time trend"

const RANGES = [
  { value: "all", label: "Tất cả các kỳ", short: "Tất cả", n: Infinity },
  { value: "12", label: "12 kỳ gần nhất", short: "12 kỳ", n: 12 },
  { value: "6", label: "6 kỳ gần nhất", short: "6 kỳ", n: 6 },
]

export function ChartAreaInteractive({
  points,
  title,
  subtitle,
  metricLabel,
  gaps,
}: {
  points: TimePoint[] | undefined
  title: string
  subtitle: string
  metricLabel: string
  gaps?: TimeGapSummary | null
}) {
  const isMobile = useIsMobile()
  const [userRange, setTimeRange] = React.useState<string | null>(null)
  const [showMa3, setShowMa3] = React.useState(true)
  const timeRange = userRange ?? (isMobile ? "6" : "all")

  const chartConfig = {
    value: {
      label: metricLabel,
      color: "var(--chart-1)",
    },
    ma3: {
      label: "MA3 (3 kỳ)",
      color: "var(--chart-2)",
    },
    n: {
      label: "Số quan sát",
      color: "var(--primary)",
    },
  } satisfies ChartConfig

  const n = RANGES.find((r) => r.value === timeRange)?.n ?? Infinity
  const filteredData = (points ?? []).slice(Number.isFinite(n) ? -n : 0)
  const hasMa3 = filteredData.some((p) => typeof p.ma3 === "number" && Number.isFinite(p.ma3))

  return (
    <Card className="@container/card" {...insightTarget("chart", "timeseries", title, { title, subtitle, metric: metricLabel, points: points?.slice(-24), gaps })}>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">{title}</CardTitle>
        <CardDescription className="flex flex-wrap items-center gap-2">
          <span className="hidden @[540px]/card:block">
            {subtitle}
          </span>
          <span className="@[540px]/card:hidden">{metricLabel}</span>
          {gaps && gaps.count > 0 && (
            <Badge variant="outline" className="font-normal">
              Thiếu {gaps.count} kỳ ({gaps.samples.slice(0, 3).join(", ")}{gaps.count > 3 ? "…" : ""})
            </Badge>
          )}
        </CardDescription>
        <CardAction>
          <div className="flex flex-wrap items-center gap-2">
            {hasMa3 && (
              <Toggle
                pressed={showMa3}
                onPressedChange={setShowMa3}
                variant="outline"
                size="sm"
                aria-label="Bật hoặc tắt đường trung bình trượt 3 kỳ (MA3)"
              >
                MA3
              </Toggle>
            )}
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
              items={RANGES.map((r) => ({ label: r.short, value: r.value }))}
            >
              <SelectTrigger
                className="flex w-28 **:data-[slot=select-value]:block **:data-[slot=select-value]:truncate @[767px]/card:hidden"
                size="sm"
                aria-label="Khoảng thời gian"
              >
                <SelectValue placeholder="Tất cả" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                {RANGES.map((r) => (
                  <SelectItem key={r.value} value={r.value} className="rounded-lg">
                    {r.short}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardAction>
      </CardHeader>
      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
        {!points ? (
          <Skeleton className="h-[280px] w-full" />
        ) : filteredData.length === 0 ? (
          <div className="flex h-[280px] items-center justify-center text-sm text-muted-foreground">
            Chưa có quan sát theo thời gian.
          </div>
        ) : (
          <Tabs defaultValue="chart">
            <TabsList variant="line" aria-label="Kiểu hiển thị">
              <TabsTrigger value="chart">Biểu đồ</TabsTrigger>
              <TabsTrigger value="table">Bảng số liệu</TabsTrigger>
            </TabsList>
            <TabsContent value="chart">
              <ChartContainer
                config={chartConfig}
                className="aspect-auto h-[280px] w-full"
              >
                <ComposedChart data={filteredData}>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="period"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    minTickGap={32}
                  />
                  <YAxis tickLine={false} axisLine={false} width="auto" tickFormatter={(value) => fmtNum(Number(value))} domain={["auto", "auto"]} />
                  <ChartTooltip
                    cursor={false}
                    content={
                      <ChartTooltipContent
                        labelFormatter={(value) => String(value)}
                        formatter={(value, name) => (
                          <span className="font-mono font-medium tabular-nums">
                            {name === "ma3" ? "MA3 (3 kỳ)" : metricLabel}: {fmtNum(Number(value))}
                          </span>
                        )}
                        indicator="dot"
                      />
                    }
                  />
                  <Area
                    dataKey="value"
                    type="linear"
                    fill="var(--color-value)"
                    fillOpacity={0.08}
                    stroke="none"
                    isAnimationActive={false}
                  />
                  <Line
                    dataKey="value"
                    type="linear"
                    dot={filteredData.length === 1} strokeWidth={2.5} isAnimationActive={false}
                    stroke="var(--color-value)"
                  />
                  {hasMa3 && showMa3 && (
                    <Line
                      dataKey="ma3"
                      type="linear" isAnimationActive={false}
                      fill="none"
                      stroke="var(--color-ma3)"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={false}
                      connectNulls={false}
                    />
                  )}
                </ComposedChart>
              </ChartContainer>
            </TabsContent>
            <TabsContent value="table" className="max-h-[280px] overflow-auto">
              <Table aria-label={title}>
                <TableHeader><TableRow>
                  <TableHead>Kỳ</TableHead><TableHead className="text-right">{metricLabel}</TableHead>
                  {hasMa3 && showMa3 && <TableHead className="text-right">MA3</TableHead>}
                  <TableHead className="text-right">Số quan sát</TableHead>
                </TableRow></TableHeader>
                <TableBody>{filteredData.map((point) => (
                  <TableRow key={point.period}>
                    <TableCell>{point.period}</TableCell>
                    <TableCell className="text-right tabular-nums">{point.value == null ? "—" : fmtNum(point.value)}</TableCell>
                    {hasMa3 && showMa3 && <TableCell className="text-right tabular-nums">{point.ma3 == null ? "—" : fmtNum(point.ma3)}</TableCell>}
                    <TableCell className="text-right tabular-nums">{point.n}</TableCell>
                  </TableRow>
                ))}</TableBody>
              </Table>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  )
}
