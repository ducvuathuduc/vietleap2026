import { Suspense } from "react"

import { SiteBar } from "@/components/npl/site-bar"

export default function NplLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-full overflow-x-hidden bg-background text-foreground">
      <Suspense fallback={<header className="h-14 border-b border-border" />}>
        <SiteBar />
      </Suspense>
      <div className="mx-auto flex w-full max-w-6xl min-w-0 flex-col gap-4 px-4 py-3">{children}</div>
    </div>
  )
}
