"use client"

import { usePathname, useSearchParams } from "next/navigation"
import { useEffect } from "react"

import { NplAskDock } from "@/components/npl-ai/assistant"
import { buttonVariants } from "@/components/ui/button"
import { NPL_NAV } from "@/lib/nav"
import { cn } from "cn"

export function SiteBar({ bankCount, yearStart, yearEnd }: { bankCount: number; yearStart: string; yearEnd: string }) {
  const pathname = usePathname()
  const search = useSearchParams()
  const vi = search.get("lang") !== "en"
  useEffect(() => {
    document.documentElement.lang = vi ? "vi" : "en"
  }, [vi])

  function choose(next: "vi" | "en") {
    const url = new URL(window.location.href)
    if (next === "en") url.searchParams.set("lang", "en")
    else url.searchParams.delete("lang")
    window.location.assign(url.toString())
  }

  function open(path: string) {
    const url = new URL(window.location.href)
    url.pathname = path
    if (path === "/") url.searchParams.delete("own")
    url.searchParams.delete("drop")
    window.location.assign(url.toString())
  }

  return (
    <header className="border-b border-border">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-2 px-4 py-2">
        <div className="mr-auto">
          <p className="text-base font-semibold leading-tight">{vi ? "Sau tỷ lệ nợ xấu" : "Behind the NPL Ratio"}</p>
          <p className="text-xs text-muted-foreground">{vi ? `${bankCount} ngân hàng niêm yết, ${yearStart}–${yearEnd}` : `${bankCount} listed banks, ${yearStart}–${yearEnd}`}</p>
        </div>
        <nav className="flex flex-wrap gap-1" aria-label={vi ? "Mục" : "Sections"}>
          {NPL_NAV.map((item) => {
            const active = item.url === "/" ? pathname === "/" : pathname === item.url || pathname.startsWith(`${item.url}/`)
            return (
              <a
                key={item.url}
                href={item.url}
                className={cn(buttonVariants({ variant: active ? "secondary" : "ghost", size: "sm" }), "min-h-11")}
                aria-current={active ? "page" : undefined}
                onClick={(event) => {
                  event.preventDefault()
                  open(item.url)
                }}
              >
                {vi ? item.title : item.en}
              </a>
            )
          })}
        </nav>
        <NplAskDock />
        <div className="flex rounded-lg border border-border p-0.5" role="group" aria-label={vi ? "Ngôn ngữ" : "Language"}>
          <button type="button" className={cn(buttonVariants({ variant: vi ? "secondary" : "ghost", size: "sm" }), "min-h-11 min-w-11")} aria-pressed={vi} onClick={() => choose("vi")}>
            VI
          </button>
          <button type="button" className={cn(buttonVariants({ variant: vi ? "ghost" : "secondary", size: "sm" }), "min-h-11 min-w-11")} aria-pressed={!vi} onClick={() => choose("en")}>
            EN
          </button>
        </div>
      </div>
    </header>
  )
}
