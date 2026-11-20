"use client"

import { usePathname, useSearchParams } from "next/navigation"
import { useEffect } from "react"

import { buttonVariants } from "@/components/ui/button"
import { RATEWATCH_NAV } from "@/lib/nav"
import { cn } from "cn"

const EN_LABEL: Record<string, string> = {
  "/": "Rates today",
  "/ban-do": "Map",
  "/chinh-sach": "Policy",
  "/phuong-phap": "Method",
}

export function SiteBar() {
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
    window.location.assign(url.toString())
  }

  return (
    <header className="border-b border-border">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-2 px-4 py-2">
        <p className="mr-auto leading-tight">
          <span className="text-base font-semibold">RateWatch</span>
          <span className="block text-xs text-muted-foreground">{vi ? "Lãi suất hôm nay" : "Deposit rates"}</span>
        </p>
        <nav className="flex flex-wrap gap-1" aria-label={vi ? "Mục" : "Sections"}>
          {RATEWATCH_NAV.map((item) => {
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
                {vi ? item.title : EN_LABEL[item.url] ?? item.title}
              </a>
            )
          })}
        </nav>
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
