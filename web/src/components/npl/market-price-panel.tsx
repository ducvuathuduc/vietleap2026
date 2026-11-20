"use client"

import { useState } from "react"
import { CartesianGrid, Line, LineChart, ReferenceArea, XAxis, YAxis } from "recharts"

import { Button } from "@/components/ui/button"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import type { marketPriceModel } from "@/lib/npl/judge-view"
import { formatNumber, type Lang } from "@/lib/npl/view"

type PriceView = ReturnType<typeof marketPriceModel>
type MarketTarget = "basket" | "vnindex"

export function MarketPricePanel({ targets, lang }: { targets: Record<MarketTarget, PriceView>; lang: Lang }) {
  const vi = lang === "vi"
  const [selection, setSelection] = useState<MarketTarget>("basket")
  const model = targets[selection]
  const start = model.points.find((point) => point.test)?.month
  const end = model.points.findLast((point) => point.test)?.month
  const labels = {
    actual: vi ? "Giá thực tế" : "Actual price",
    predicted: vi ? "Giá dự báo" : "Predicted price",
    test: vi ? "Giai đoạn kiểm tra" : "Test period",
  }
  const config = {
    actual: { label: labels.actual, color: "var(--chart-5)" },
    predicted: { label: labels.predicted, color: "var(--destructive)" },
  } satisfies ChartConfig
  const groups = { basket: vi ? "Rổ cổ phiếu ngân hàng" : "Bank stock basket", vnindex: "VNINDEX" }
  const verdict = model.lowerError == null ? null : model.lowerError
    ? (vi ? "Dự báo bằng nợ xấu có sai số thấp hơn." : "The NPL forecast had the lower error.")
    : (vi ? "Dự báo bằng nợ xấu không vượt cách giữ giá tháng trước." : "The NPL model did not beat holding last month's price.")

  return (
    <div className="min-w-0 rounded-xl border border-border bg-card p-3 sm:p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label={vi ? "Chọn nhóm cổ phiếu" : "Choose a stock group"}>
          {(Object.keys(groups) as MarketTarget[]).map((target) => (
            <Button key={target} type="button" variant={selection === target ? "default" : "outline"} size="sm"
              aria-pressed={selection === target} onClick={() => setSelection(target)}>
              {groups[target]}
            </Button>
          ))}
        </div>
        {start && end && <p className="text-xs text-muted-foreground">{labels.test} {start} – {end}</p>}
      </div>
      <ChartContainer config={config} className="aspect-auto h-[18rem] w-full min-w-0 sm:h-[22rem]" initialDimension={{ width: 680, height: 300 }}>
        <LineChart accessibilityLayer data={model.points} margin={{ top: 12, left: 4, right: 18, bottom: 6 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="month" tickLine={false} axisLine={false} minTickGap={36} interval="preserveStartEnd" tick={{ fontSize: 11 }} />
          <YAxis width={48} tickLine={false} axisLine={false} tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
          {start && end && <ReferenceArea x1={start} x2={end} fill="var(--chart-1)" fillOpacity={0.38} strokeOpacity={0} />}
          <ChartTooltip content={<ChartTooltipContent />} />
          <Line dataKey="actual" stroke="var(--color-actual)" strokeWidth={2.5} dot={false} isAnimationActive={false} />
          <Line dataKey="predicted" stroke="var(--color-predicted)" strokeWidth={2} strokeDasharray="6 4" dot={false} isAnimationActive={false} />
        </LineChart>
      </ChartContainer>
      <ul className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">
        <li className="flex items-center gap-1.5"><span className="w-5 border-b-2 border-chart-5" aria-hidden="true" />{labels.actual}</li>
        <li className="flex items-center gap-1.5"><span className="w-5 border-b-2 border-dashed border-destructive" aria-hidden="true" />{labels.predicted}</li>
        {start && <li className="flex items-center gap-1.5"><span className="size-3 bg-chart-1/40" aria-hidden="true" />{labels.test}</li>}
      </ul>
      <div className="mt-3 grid gap-1 border-t border-border pt-3 text-sm" aria-live="polite">
        {verdict && <p className="font-medium">{verdict}</p>}
        {model.modelMae != null && model.baselineMae != null && (
          <p className="text-muted-foreground">
            {vi ? "Sai số giá trung bình" : "Mean absolute price error"}{" "}
            <span className="font-medium text-foreground">{formatNumber(model.modelMae, lang, 2)}</span>{" "}
            {vi ? "điểm với dự báo, so với" : "points for the model versus"}{" "}
            <span className="font-medium text-foreground">{formatNumber(model.baselineMae, lang, 2)}</span>{" "}
            {vi ? "điểm khi giữ giá tháng trước." : "points for holding last month's price."}
          </p>
        )}
      </div>
    </div>
  )
}
