import { ChartBody } from "@/components/judge/chart-body"
import { ChartFigure } from "@/components/judge/chart-figure"
import { EmptyState } from "@/components/judge/empty-state"
import { TrustLine } from "@/components/judge/trust-line"
import { PageShell } from "@/components/state"
import { Skeleton } from "@/components/ui/skeleton"
import { loadPublishedMonitor } from "@/lib/monitor/load"
import { DEFINITIONS_HREF } from "./_lib/common"
import type { FigureModel } from "./_lib/chart-block"
import type { TableModel } from "./_lib/asean"
import { JudgeTable } from "./_lib/judge-table"
import type { JudgeView } from "@/lib/monitor/sections"

/**
 * Reads the published payload on the server; null means nothing has been published yet.
 * A payload that is missing or half-written must not blank the page, so a read error
 * falls back to the same empty state. The read is cached, so it lands in the initial HTML.
 */
export async function readMonitor() {
  try {
    return await loadPublishedMonitor()
  } catch {
    return null
  }
}

export function JudgeEmpty({
  title = "Chưa có dữ liệu đã xuất bản",
  message = "Bản đã xuất bản chưa có số liệu cho phần này.",
}: {
  title?: string
  message?: string
}) {
  return (
    <PageShell>
      <div className="mx-auto w-full max-w-[1200px] px-4 md:px-6">
        <EmptyState
          title={title}
          message={message}
          link={{ label: "Xem dữ liệu & phương pháp", href: DEFINITIONS_HREF }}
        />
      </div>
    </PageShell>
  )
}

/** One chart: numbered caption, empty/partial states and a citation line. */
export function JudgeFigure({ figure }: { figure: FigureModel }) {
  return (
    <ChartFigure
      id={figure.id}
      number={figure.number}
      title={figure.title}
      ariaLabel={figure.ariaLabel}
      trust={figure.trust}
      note={figure.note}
      sourceIds={figure.sourceIds}
      pointCount={figure.pointCount}
      frequency={figure.frequency}
    >
      <ChartBody body={figure.body} label={figure.ariaLabel} />
    </ChartFigure>
  )
}

/** One table: title, URL-state sort/page/filter, citation line. */
export function JudgeTableBlock({ table }: { table: TableModel }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <h2 className="text-sm font-medium">{table.title}</h2>
      <JudgeTable columns={table.columns} rows={table.rows} />
      <TrustLine {...table.trust} />
    </section>
  )
}

/** Loading shell that mirrors the page layout, used by `loading.tsx` and Suspense. */
export function JudgePageSkeleton({
  kpis = 6,
  cards = 3,
  figures = 1,
}: {
  kpis?: number
  cards?: number
  figures?: number
}) {
  return (
    <PageShell>
      <div className="mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6" aria-busy="true" aria-label="Đang tải">
        <div className="flex flex-col gap-3">
          <Skeleton className="h-4 w-44" />
          <Skeleton className="h-9 w-full max-w-3xl" />
          <Skeleton className="h-5 w-full max-w-2xl" />
        </div>
        {kpis ? (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
            {Array.from({ length: kpis }, (_, index) => (
              <Skeleton key={index} className="h-28 rounded-xl" />
            ))}
          </div>
        ) : null}
        {cards ? (
          <div className="grid gap-4 md:grid-cols-3">
            {Array.from({ length: cards }, (_, index) => (
              <Skeleton key={index} className="h-40 rounded-xl" />
            ))}
          </div>
        ) : null}
        {figures ? (
          <div className="grid gap-4">
            {Array.from({ length: figures }, (_, index) => (
              <Skeleton key={index} className="h-72 rounded-xl" />
            ))}
          </div>
        ) : null}
      </div>
    </PageShell>
  )
}

/**
 * Legacy list view still used by the pages outside this wave; it keeps the section
 * ids so those routes build while their own layouts land.
 */
export function JudgeFallback() {
  return <JudgePageSkeleton kpis={0} cards={0} figures={0} />
}

export function JudgeArticle({ view }: { view: JudgeView }) {
  return (
    <PageShell>
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-3 px-4 md:px-6">
        <h1 className="text-3xl font-semibold tracking-tight text-balance">{view.headline}</h1>
        {view.question ? <p className="text-base text-muted-foreground">{view.question}</p> : null}
        <ul className="flex list-disc flex-col gap-2 pl-5 text-sm">
          {view.sections.map((section) => (
            <li key={section.id}>{section.label}</li>
          ))}
        </ul>
      </div>
    </PageShell>
  )
}
