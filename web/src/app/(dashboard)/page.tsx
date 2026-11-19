import type { Metadata } from "next"

import { InsightCard } from "@/components/judge/insight-card"
import { KpiTile } from "@/components/judge/kpi-tile"
import { PageHeader } from "@/components/judge/page-header"
import { SiteFooter } from "@/components/judge/site-footer"
import { TrustLine } from "@/components/judge/trust-line"
import { WatchList } from "@/components/judge/watch-list"
import { PageShell } from "@/components/state"

import { overviewPage } from "./_lib/overview"
import { JudgeEmpty, JudgeFigure, readMonitor } from "./judge-screen"

export const metadata: Metadata = {
  title: "Tổng quan",
  description: "Vốn của nền kinh tế đang kẹt ở đâu trên đường từ nguồn thu đến chi tiêu, đầu tư và tăng trưởng.",
}

export default async function Page() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />

  const model = overviewPage(monitor)
  return (
    <PageShell>
      <div className="mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6">
        <PageHeader
          level={model.level}
          headline={model.headline}
          lead={model.lead}
          generatedAt={model.generatedAt}
          actions={model.actions}
        />

        {model.kpis.length ? (
          <section aria-label="Chỉ số chính" className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
              {model.kpis.map((kpi) => (
                <KpiTile
                  key={kpi.id}
                  name={kpi.name}
                  value={kpi.value}
                  unit={kpi.unit}
                  period={kpi.period}
                  change={kpi.change}
                  sparkline={kpi.sparkline}
                />
              ))}
            </div>
            {model.kpiTrust ? <TrustLine {...model.kpiTrust} /> : null}
          </section>
        ) : null}

        {model.cards.length ? (
          <section aria-label="Kết luận chính" className="grid gap-4 md:grid-cols-3">
            {model.cards.map((card, index) => (
              <InsightCard
                key={`${card.sentence}-${index}`}
                eyebrow={card.eyebrow}
                value={card.value}
                unit={card.unit}
                period={card.period}
                sentence={card.sentence}
                action={card.action}
                source={card.source}
                indicatorHref={card.indicatorHref}
              />
            ))}
          </section>
        ) : null}

        {model.figure ? <JudgeFigure figure={model.figure} /> : null}

        <WatchList items={model.watch} />

        {model.recommendations.length ? (
          <section className="flex flex-col gap-2">
            <h2 className="text-xl font-semibold">Khuyến nghị</h2>
            <ul className="flex flex-col gap-3">
              {model.recommendations.map((item) => (
                <li key={item.id} className="flex flex-col gap-0.5 text-sm">
                  <a
                    href={item.href}
                    className="w-fit underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  >
                    {item.title}
                  </a>
                  {item.meta ? <span className="text-xs text-muted-foreground">{item.meta}</span> : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <SiteFooter sources={model.footer.sources} generatedAt={model.footer.generatedAt} />
      </div>
    </PageShell>
  )
}
