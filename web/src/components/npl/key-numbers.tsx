"use client"

import { CountUp } from "@/components/npl/count-up"
import { formatNumber, type Lang } from "@/lib/npl/view"

type Metric = { label: string; value: number | null; compare?: number | null; digits: number; unit: string }

export function KeyNumbers({ metrics, lang }: { metrics: Metric[]; lang: Lang }) {
  function number(value: number | null, digits: number, unit: string) {
    return value == null ? "—" : <CountUp value={value} text={(amount) => formatNumber(amount, lang, digits) + unit} />
  }

  return (
    <dl className="grid divide-y divide-border border-y border-border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
      {metrics.map((metric) => (
        <div key={metric.label} className="flex flex-col gap-0.5 py-2.5 sm:pr-4 sm:pl-4 sm:first:pl-0">
          <dt className="text-xs font-medium text-muted-foreground sm:text-sm">{metric.label}</dt>
          <dd className="text-2xl font-semibold tracking-tight tabular-nums sm:text-[1.75rem]">
            {number(metric.value, metric.digits, metric.unit)}
            {metric.compare != null && (
              <><span className="mx-2 text-sm font-normal text-muted-foreground">{lang === "vi" ? "so với" : "vs"}</span>
                {number(metric.compare, metric.digits, metric.unit)}</>
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}
