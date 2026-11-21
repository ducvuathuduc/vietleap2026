import { Suspense } from "react"

import { SiteBar } from "@/components/npl/site-bar"
import { loadSnapshot } from "@/lib/npl/load"
import { requestLanguage } from "@/lib/npl/locale"

export default async function NplLayout({ children }: { children: React.ReactNode }) {
  const [snapshot, lang] = await Promise.all([loadSnapshot(), requestLanguage()])
  const yearStart = snapshot.meta.period_start.slice(0, 4)
  const yearEnd = snapshot.meta.period_end.slice(0, 4)
  return (
    <div className="min-h-full overflow-x-hidden bg-background text-foreground">
      <Suspense fallback={<header className="h-14 border-b border-border" />}>
        <SiteBar lang={lang} bankCount={snapshot.meta.n_banks} yearStart={yearStart} yearEnd={yearEnd} />
      </Suspense>
      <main id="content" className="mx-auto flex w-full max-w-6xl min-w-0 flex-col gap-4 px-4 py-3">{children}</main>
    </div>
  )
}
