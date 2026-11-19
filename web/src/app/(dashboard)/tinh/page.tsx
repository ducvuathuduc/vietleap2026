import type { Metadata } from "next"
import Link from "next/link"

import { ChartFigure } from "@/components/judge/chart-figure"
import { Choropleth } from "@/components/judge/choropleth"
import { PageHeader } from "@/components/judge/page-header"
import { RangeChart } from "@/components/judge/range-chart"
import { SiteFooter } from "@/components/judge/site-footer"
import { TrustLine } from "@/components/judge/trust-line"
import { cn } from "cn"
import { PageShell } from "@/components/state"

import { JudgeEmpty, readMonitor } from "../judge-screen"
import { provincePage } from "../_lib/province-view"
import { ProvinceTable } from "./province-table"

export const metadata: Metadata = {
  title: "Tỉnh thành",
  description: "Tỉnh nào lệch khỏi trung vị cả nước, lệch bao nhiêu, và thuộc nhóm nào.",
}

const FRAME = "mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6"
const CHIP =
  "shrink-0 rounded-lg px-2.5 py-1 text-sm whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"

type SearchParams = Promise<{ nhom?: string | string[]; "giai-ngan"?: string | string[] }>

export default async function Page({ searchParams }: { searchParams: SearchParams }) {
  const { nhom, "giai-ngan": giaiNgan } = await searchParams
  const requested = Array.isArray(nhom) ? nhom[0] : nhom
  const requestedDisbursement = Array.isArray(giaiNgan) ? giaiNgan[0] : giaiNgan
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  const model = provincePage(monitor, requested?.trim() || null, requestedDisbursement?.trim() || null)

  return (
    <PageShell>
      <div className={FRAME}>
        <PageHeader
          level={model.level}
          headline={model.headline}
          lead={model.lead}
          generatedAt={model.generatedAt}
          actions={[{ label: "Xem dữ liệu", href: "/phuong-phap" }]}
        />

        {model.groups.length ? (
          <nav aria-label="Nhóm tỉnh" className="flex gap-2 overflow-x-auto pb-1">
            <Link href="/tinh" aria-current={model.activeGroup ? undefined : "page"} className={cn(CHIP, model.activeGroup ? "text-muted-foreground hover:bg-muted" : "bg-muted font-medium")}>
              Tất cả
            </Link>
            {model.groups.map((group) => (
              <a
                key={group.id}
                href={group.href}
                aria-current={model.activeGroup === group.id ? "page" : undefined}
                className={cn(CHIP, model.activeGroup === group.id ? "bg-muted font-medium" : "text-muted-foreground hover:bg-muted")}
              >
                {group.label}
                <span className="text-muted-foreground"> {group.range}</span>
                <span className="text-muted-foreground"> · {group.count}</span>
              </a>
            ))}
          </nav>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-2">
          {model.map ? (
            <ChartFigure
              id="ban-do"
              title={model.map.title}
              ariaLabel={model.map.ariaLabel}
              trust={model.map.trust}
              sourceIds={model.map.sourceIds}
              pointCount={model.map.pointCount}
              frequency={model.map.frequency}
            >
              <div className="[&_svg]:max-h-[320px] md:[&_svg]:max-h-[440px]">
                <Choropleth rows={model.map.rows} groups={model.map.groups} unit={model.map.unit} ariaLabel={model.map.ariaLabel} />
              </div>
            </ChartFigure>
          ) : null}
          {model.range ? (
            <ChartFigure
              id="khoang"
              title={model.range.title}
              ariaLabel={model.range.ariaLabel}
              trust={model.range.trust}
              sourceIds={model.range.sourceIds}
              pointCount={model.range.pointCount}
              frequency={model.range.frequency}
            >
              <RangeChart items={model.range.items} unit={model.range.unit} ariaLabel={model.range.ariaLabel} />
            </ChartFigure>
          ) : null}
        </div>

        <section id="bang-tinh" className="flex scroll-mt-20 flex-col gap-3">
          <h2 className="text-xl font-semibold">Bảng tỉnh</h2>
          {model.period ? <p className="text-xs text-muted-foreground">{model.period}</p> : null}
          <ProvinceTable rows={model.table} />
          {model.map?.trust ? <TrustLine {...model.map.trust} /> : null}
        </section>

        {model.disbursement ? (
          <section id="giai-ngan" className="flex scroll-mt-20 flex-col gap-3">
            <h2 className="text-xl font-semibold">{model.disbursement.headline}</h2>
            {model.disbursement.period ? <p className="text-xs text-muted-foreground">{model.disbursement.period}</p> : null}
            {model.disbursement.groups.length ? (
              <nav aria-label="Nhóm giải ngân" className="flex gap-2 overflow-x-auto pb-1">
                <Link href="/tinh" aria-current={model.disbursement.activeGroup ? undefined : "page"} className={cn(CHIP, model.disbursement.activeGroup ? "text-muted-foreground hover:bg-muted" : "bg-muted font-medium")}>
                  Tất cả
                </Link>
                {model.disbursement.groups.map((group) => (
                  <a
                    key={group.id}
                    href={group.href}
                    aria-current={model.disbursement?.activeGroup === group.id ? "page" : undefined}
                    className={cn(CHIP, model.disbursement?.activeGroup === group.id ? "bg-muted font-medium" : "text-muted-foreground hover:bg-muted")}
                  >
                    {group.label}
                    <span className="text-muted-foreground"> {group.range}</span>
                    <span className="text-muted-foreground"> · {group.count}</span>
                  </a>
                ))}
              </nav>
            ) : null}
            <div className="grid gap-4 lg:grid-cols-2">
              {model.disbursement.map ? (
                <ChartFigure
                  id="ban-do-giai-ngan"
                  title={model.disbursement.map.title}
                  ariaLabel={model.disbursement.map.ariaLabel}
                  trust={model.disbursement.map.trust}
                  sourceIds={model.disbursement.map.sourceIds}
                  pointCount={model.disbursement.map.pointCount}
                  frequency={model.disbursement.map.frequency}
                >
                  <div className="[&_svg]:max-h-[320px] md:[&_svg]:max-h-[440px]">
                    <Choropleth rows={model.disbursement.map.rows} groups={model.disbursement.map.groups} unit={model.disbursement.map.unit} ariaLabel={model.disbursement.map.ariaLabel} />
                  </div>
                </ChartFigure>
              ) : null}
              {model.disbursement.range ? (
                <ChartFigure
                  id="khoang-giai-ngan"
                  title={model.disbursement.range.title}
                  ariaLabel={model.disbursement.range.ariaLabel}
                  trust={model.disbursement.range.trust}
                  sourceIds={model.disbursement.range.sourceIds}
                  pointCount={model.disbursement.range.pointCount}
                  frequency={model.disbursement.range.frequency}
                >
                  <RangeChart items={model.disbursement.range.items} unit={model.disbursement.range.unit} ariaLabel={model.disbursement.range.ariaLabel} />
                </ChartFigure>
              ) : null}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="py-2 pr-3 font-medium">Tỉnh</th>
                    <th className="py-2 pr-3 font-medium">Nhóm</th>
                    <th className="py-2 pr-3 font-medium">Giá trị</th>
                    <th className="py-2 font-medium">Chênh trung vị</th>
                  </tr>
                </thead>
                <tbody>
                  {model.disbursement.table.map((row) => (
                    <tr key={row.href} className="border-b border-border">
                      <td className="py-2 pr-3">
                        <a href={row.href} className="underline underline-offset-4">{row.name}</a>
                      </td>
                      <td className="py-2 pr-3">{row.group}</td>
                      <td className="py-2 pr-3 tabular-nums">{row.valueText}</td>
                      <td className="py-2 tabular-nums">{row.gapText}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {model.disbursement.trust ? <TrustLine {...model.disbursement.trust} /> : null}
          </section>
        ) : null}

        <SiteFooter sources={model.footer.sources} generatedAt={model.footer.generatedAt} />
      </div>
    </PageShell>
  )
}
