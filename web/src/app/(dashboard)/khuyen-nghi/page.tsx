import type { Metadata } from "next"
import { Suspense } from "react"

import { PageHeader } from "@/components/judge/page-header"
import { RecommendationBlock } from "@/components/judge/recommendation-block"
import { SiteFooter } from "@/components/judge/site-footer"
import { TrustLine } from "@/components/judge/trust-line"
import { PageShell } from "@/components/state"

import { JudgeTable } from "../_lib/judge-table"
import { JudgeEmpty, JudgeFigure, JudgePageSkeleton, readMonitor } from "../judge-screen"
import { recommendationPage } from "../_lib/recommendation-view"

export const metadata: Metadata = {
  title: "Khuyến nghị",
  description: "Việc cần làm trong kỳ tới, kèm bằng chứng, hàm ý, hành động và cơ quan.",
}

const FRAME = "mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6"
const LABEL = "text-[11px] font-medium tracking-wider text-muted-foreground uppercase"

export default function Page() {
  return (
    <Suspense fallback={<JudgePageSkeleton kpis={0} cards={3} figures={0} />}>
      <Recommendations />
    </Suspense>
  )
}

async function Recommendations() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  const model = recommendationPage(monitor)

  return (
    <PageShell>
      <div className={FRAME}>
        {model.headline ? (
          <PageHeader level={model.level} headline={model.headline} lead={model.lead} generatedAt={model.generatedAt} />
        ) : (
          <h1 className="text-3xl font-semibold tracking-tight text-balance">Chưa có việc cần làm trong bản đã xuất bản.</h1>
        )}

        {model.items.map((item) => (
          <div key={item.id} className="flex flex-col gap-3">
            {item.figures.length ? (
              <div className="hidden flex-col gap-4 md:flex">
                {item.figures.map((figure) => (
                  <JudgeFigure key={figure.id} figure={figure} />
                ))}
              </div>
            ) : null}
            <RecommendationBlock
              id={item.id}
              title={item.title}
              evidence={item.evidence.map((entry) => ({
                ruleId: entry.ruleId,
                fact: entry.fact,
                chartId: entry.chartId,
                chartHref: entry.chartHref,
              }))}
              implication={item.implication}
              action={item.action}
              agency={item.agency}
              horizon={item.horizon}
              caveat={item.caveat}
            />
            {item.evidence.some((entry) => entry.formula || entry.threshold) ? (
              <dl className="grid gap-3 md:grid-cols-2">
                {item.evidence.map((entry) => (
                  <div key={`${entry.ruleId}-${entry.fact}`} className="flex flex-col gap-2 text-sm">
                    {entry.formula ? (
                      <div>
                        <dt className={LABEL}>Công thức</dt>
                        <dd>{entry.formula}</dd>
                      </div>
                    ) : null}
                    {entry.threshold ? (
                      <div>
                        <dt className={LABEL}>Ngưỡng</dt>
                        <dd>{entry.threshold}</dd>
                      </div>
                    ) : null}
                  </div>
                ))}
              </dl>
            ) : null}
          </div>
        ))}

        {model.agencies ? (
          <section className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold">Cơ quan trung ương</h2>
            <p className="text-sm">
              Tỷ lệ giải ngân so với kế hoạch, cả nước {model.agencies.national}
              {model.agencies.period ? `, ${model.agencies.period}` : ""}.
            </p>
            <p className="text-xs text-muted-foreground">
              {model.agencies.groups.map((group) => `${group.label} ${group.range} · ${group.count}`).join("  ")}
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="py-2 pr-3 font-medium">Cơ quan</th>
                    <th className="py-2 pr-3 font-medium">Nhóm</th>
                    <th className="py-2 pr-3 font-medium">Tỷ lệ</th>
                    <th className="py-2 pr-3 font-medium">Chênh cả nước</th>
                    <th className="py-2 font-medium">Số tiền</th>
                  </tr>
                </thead>
                <tbody>
                  {model.agencies.rows.map((row) => (
                    <tr key={row.name} className="border-b border-border">
                      <td className="py-2 pr-3">{row.name}</td>
                      <td className="py-2 pr-3">{row.group}</td>
                      <td className="py-2 pr-3 tabular-nums">{row.rate}</td>
                      <td className="py-2 pr-3 tabular-nums">{row.gap}</td>
                      <td className="py-2 tabular-nums">{row.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <TrustLine
              sourceName={model.agencies.sourceName}
              lastUpdated={model.generatedAt}
              links={{ data: "/phuong-phap", definition: "/phuong-phap" }}
            />
          </section>
        ) : null}

        {model.rules.length ? (
          <section className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
            <h2 className="text-sm font-medium">Quy tắc</h2>
            <JudgeTable
              columns={[
                { key: "name", label: "Tên" },
                { key: "formula", label: "Công thức" },
                { key: "threshold", label: "Ngưỡng" },
                { key: "status", label: "Trạng thái" },
                { key: "agency", label: "Cơ quan" },
              ]}
              rows={model.rules.map((rule) => ({
                name: rule.name,
                formula: rule.formula,
                threshold: rule.threshold,
                status: rule.status,
                agency: rule.agency,
              }))}
            />
            <TrustLine
              sourceName={model.footer.sources.map((source) => source.name).join(", ")}
              lastUpdated={model.generatedAt}
              links={{ data: "/phuong-phap", definition: "/phuong-phap" }}
            />
          </section>
        ) : null}

        <SiteFooter sources={model.footer.sources} generatedAt={model.footer.generatedAt} />
      </div>
    </PageShell>
  )
}
