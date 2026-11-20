"use client"

import { DrillChart } from "@/components/npl/charts"
import { buttonVariants } from "@/components/ui/button"
import { pageHref, type Lang } from "@/lib/npl/view"
import { cn } from "cn"

export function DrillBoard({
  rows,
  lang,
}: {
  rows: { code: string; q4: number | null; q1: number | null }[]
  lang: Lang
}) {
  function open(code: string) {
    if (!code) return
    window.location.assign(pageHref(`/ngan-hang/${code}`, lang))
  }

  return (
    <>
      <DrillChart rows={rows} lang={lang} onPick={open} />
      <ul className="flex flex-wrap gap-2">
        {rows.map((row) => (
          <li key={row.code}>
            <a className={cn(buttonVariants({ variant: "outline", size: "sm" }), "min-h-11")} href={pageHref(`/ngan-hang/${row.code}`, lang)}>
              {row.code}
            </a>
          </li>
        ))}
      </ul>
    </>
  )
}
