import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"

import { EmptyState } from "@/components/judge/empty-state"
import { InsightCard } from "@/components/judge/insight-card"
import { KnowBox } from "@/components/judge/know-box"
import { PageHeader } from "@/components/judge/page-header"
import { SiteFooter } from "@/components/judge/site-footer"
import { WatchList } from "@/components/judge/watch-list"
import { PageShell } from "@/components/state"
import { cn } from "cn"
import { SECTORS } from "@/lib/nav"

import type { SectorId } from "../../../../lib/monitor/types"

import { DEFINITIONS_HREF, sectorIdFromSlug, sectorTitle } from "../../_lib/common"
import { sectorPage } from "../../_lib/sector"
import { JudgeEmpty, JudgeFigure, JudgeTableBlock, readMonitor } from "../../judge-screen"

type Params = Promise<{ sector: string }>

/** The five sector tabs are the only valid slugs, so their pages are prerendered. */
export function generateStaticParams() {
  return SECTORS.map((sector) => ({ sector: sector.slug }))
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { sector } = await params
  const id = sectorIdFromSlug(sector)
  const title = id ? sectorTitle(id) : "Ngành"
  return { title, description: `Số liệu và kết luận của ngành ${title}.` }
}

export default async function Page({ params }: { params: Params }) {
  const { sector } = await params
  const id = sectorIdFromSlug(sector)
  if (!id) notFound()

  return <Sector id={id} />
}

async function Sector({ id }: { id: SectorId }) {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />

  const model = sectorPage(monitor, id)
  return (
    <PageShell>
      <div className="mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6">
        <nav aria-label="Chọn ngành" className="flex gap-1 overflow-x-auto pb-1">
          {model.tabs.map((tab) => (
            <Link
              key={tab.id}
              href={tab.href}
              aria-current={tab.active ? "page" : undefined}
              className={cn(
                "shrink-0 rounded-lg px-2.5 py-1 text-sm whitespace-nowrap transition-colors",
                tab.active
                  ? "bg-muted font-medium text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
                "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>

        <PageHeader level={model.level} headline={model.headline} generatedAt={model.footer.generatedAt} />

        {model.hasData ? null : (
          <EmptyState
            message={`Bản đã xuất bản chưa có thẻ kết luận hay biểu đồ cho ngành ${model.title}.`}
            link={{ label: "Xem dữ liệu & phương pháp", href: DEFINITIONS_HREF }}
          />
        )}

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

        {model.figures.length ? (
          <div className={cn("grid gap-4", model.figures.length > 1 && "lg:grid-cols-2")}>
            {model.figures.map((figure) => (
              <JudgeFigure key={figure.id} figure={figure} />
            ))}
          </div>
        ) : null}

        {model.heatmap ? <JudgeFigure figure={model.heatmap} /> : null}

        {model.tables.map((table) => (
          <JudgeTableBlock key={table.id} table={table} />
        ))}

        <WatchList items={model.watch} />

        {model.knowBoxes.length ? (
          <section aria-label="Điều cần biết" className="grid gap-4 md:grid-cols-2">
            {model.knowBoxes.map((box) => (
              <KnowBox
                key={box.id}
                definition={box.definition}
                note={box.note}
                unit={box.unit}
                frequency={box.frequency}
                title={`Điều cần biết: ${box.name}`}
              />
            ))}
          </section>
        ) : null}

        <SiteFooter sources={model.footer.sources} generatedAt={model.footer.generatedAt} />
      </div>
    </PageShell>
  )
}
