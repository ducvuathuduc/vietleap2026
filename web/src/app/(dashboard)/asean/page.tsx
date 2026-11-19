import type { Metadata } from "next"
import Link from "next/link"

import { PageHeader } from "@/components/judge/page-header"
import { SiteFooter } from "@/components/judge/site-footer"
import { cn } from "cn"
import { PageShell } from "@/components/state"

import { aseanPage } from "../_lib/asean"
import { JudgeEmpty, JudgeFigure, JudgeTableBlock, readMonitor } from "../judge-screen"

export const metadata: Metadata = {
  title: "Chỉ số & ASEAN",
  description: "Việt Nam đứng ở đâu trong ASEAN theo từng chỉ số kinh tế vĩ mô và tài chính.",
}

// The indicator comes from `?indicator=` (a request-time read), and the page must render its body
// before the first byte, so it is intentionally a blocking route instead of a streamed shell.
export const instant = false

type SearchParams = Promise<{ indicator?: string | string[] }>

export default async function Page({ searchParams }: { searchParams: SearchParams }) {
  const { indicator } = await searchParams
  const requested = Array.isArray(indicator) ? indicator[0] : indicator
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  const model = aseanPage(monitor, requested ?? null)
  if (!model) {
    return <JudgeEmpty title="Chưa có số liệu so sánh ASEAN" message="Bản đã xuất bản chưa có chỉ số nào so sánh được với các nước ASEAN." />
  }

  return (
    <PageShell>
      <div className="mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6">
        <PageHeader level={model.level} headline={model.headline} generatedAt={model.footer.generatedAt} />

        <section aria-label="Chọn chỉ số" className="flex flex-col gap-2">
          <nav className="flex flex-wrap gap-1">
            {model.selector.map((item) => (
              <Link
                key={item.id}
                href={item.href}
                aria-current={item.active ? "page" : undefined}
                className={cn(
                  "rounded-lg px-2.5 py-1 text-sm transition-colors",
                  item.active
                    ? "bg-muted font-medium text-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <p className="text-xs text-muted-foreground">{model.yearNote}</p>
        </section>

        {model.figures.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {model.figures.map((figure) => (
              <div key={figure.id} className={figure.body?.kind === "line" ? "lg:col-span-2" : undefined}>
                <JudgeFigure figure={figure} />
              </div>
            ))}
          </div>
        ) : null}

        {model.table ? <JudgeTableBlock table={model.table} /> : null}

        <SiteFooter sources={model.footer.sources} generatedAt={model.footer.generatedAt} />
      </div>
    </PageShell>
  )
}
