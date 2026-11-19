import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"

import { KnowBox } from "@/components/judge/know-box"
import { PageHeader } from "@/components/judge/page-header"
import { SiteFooter } from "@/components/judge/site-footer"
import { TrustLine } from "@/components/judge/trust-line"
import { PageShell } from "@/components/state"
import { loadPublishedMonitor } from "@/lib/monitor/load"

import { JudgeEmpty, readMonitor } from "../../judge-screen"
import { provinceDetail } from "../../_lib/province-view"

const FRAME = "mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6"
const LINK =
  "w-fit underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"

type Params = Promise<{ code: string }>

/** Every province in the published payload is prerendered; any other code falls through to 404. */
export async function generateStaticParams() {
  try {
    const monitor = await loadPublishedMonitor()
    return monitor ? monitor.province.rows.map((row) => ({ code: row.code })) : []
  } catch {
    return []
  }
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { code } = await params
  try {
    const monitor = await loadPublishedMonitor()
    const detail = monitor ? provinceDetail(monitor, code) : null
    return {
      title: detail?.name ?? "Tỉnh thành",
      description: detail
        ? `Số liệu của ${detail.name} so với trung vị cả nước.`
        : "Tỉnh thành chưa có trong bản đã xuất bản.",
    }
  } catch {
    return { title: "Tỉnh thành", description: "Tỉnh thành chưa có trong bản đã xuất bản." }
  }
}

export default async function Page({ params }: { params: Params }) {
  const { code } = await params
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  const model = provinceDetail(monitor, code)
  if (!model) notFound()

  return (
    <PageShell>
      <div className={FRAME}>
        <PageHeader level={model.level} headline={model.headline} lead={model.lead} generatedAt={model.generatedAt} />
        <p className="text-sm text-muted-foreground">Nhóm: {model.group}</p>

        {model.trust ? (
          <section className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold">So với trung vị cả nước</h2>
            <dl className="flex flex-col gap-3">
              {model.metrics.map((metric) => (
                <div key={metric.id} className="flex flex-col gap-0.5 border-b border-border pb-3">
                  <dt className="text-sm font-medium">{metric.name}</dt>
                  <dd className="text-sm">
                    {metric.valueText}
                    <span className="text-muted-foreground"> · trung vị {metric.medianText} · chênh {metric.gapText}</span>
                  </dd>
                  {metric.period ? <dd className="text-xs text-muted-foreground">{metric.period}</dd> : null}
                </div>
              ))}
            </dl>
            <TrustLine {...model.trust} />
          </section>
        ) : null}

        {model.know ? (
          <KnowBox
            definition={model.know.definition}
            note={model.know.note}
            unit={model.know.unit}
            frequency={model.know.frequency}
          />
        ) : null}

        <Link href={model.backHref} className={LINK}>
          Về bảng tỉnh
        </Link>
        <SiteFooter sources={model.footer.sources} generatedAt={model.footer.generatedAt} />
      </div>
    </PageShell>
  )
}
