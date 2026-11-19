import { cn } from "cn"

import { enterClass } from "./motion"

export interface RecommendationEvidence {
  /** Rule code from `rules[].id`, shown as the evidence label. */
  ruleId: string
  fact: string
  chartId?: string
  /** Explicit anchor; defaults to `#<chartId>`. */
  chartHref?: string
}

export interface RecommendationBlockProps {
  id: string
  title: string
  evidence: RecommendationEvidence[]
  /** "Hàm ý": the quantified consequence of not acting. */
  implication: string
  action: string
  agency: string
  horizon: string
  caveat?: string | null
}

const LABEL = "text-[11px] font-medium tracking-wider text-muted-foreground uppercase"

/** Bằng chứng → Hàm ý → Hành động → Cơ quan + horizon. */
export function RecommendationBlock({
  id,
  title,
  evidence,
  implication,
  action,
  agency,
  horizon,
  caveat,
}: RecommendationBlockProps) {
  return (
    <section
      id={id}
      className={cn("flex scroll-mt-20 flex-col gap-3 rounded-xl border border-border bg-card p-4", enterClass())}
    >
      <h2 className="text-xl font-semibold">{title}</h2>
      <dl className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <dt className={LABEL}>Bằng chứng</dt>
          <dd>
            <ul className="flex flex-col gap-1 text-sm">
              {evidence.map((item) => {
                const href = item.chartHref ?? (item.chartId ? `#${item.chartId}` : undefined)
                return (
                  <li key={`${item.ruleId}-${item.fact}`} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="text-xs text-muted-foreground">{item.ruleId}</span>
                    <span>{item.fact}</span>
                    {href ? (
                      <a
                        href={href}
                        className="text-xs underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                      >
                        Xem biểu đồ
                      </a>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className={LABEL}>Hàm ý</dt>
          <dd className="text-sm">{implication}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className={LABEL}>Hành động</dt>
          <dd className="text-sm">{action}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className={LABEL}>Cơ quan</dt>
          <dd className="flex flex-wrap items-baseline gap-2 text-sm">
            <span>{agency}</span>
            <span className="text-xs text-muted-foreground">{horizon}</span>
          </dd>
        </div>
      </dl>
      {caveat ? <p className="text-xs text-muted-foreground">{caveat}</p> : null}
    </section>
  )
}
