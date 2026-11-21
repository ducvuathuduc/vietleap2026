"use client"

import { usePathname, useSearchParams } from "next/navigation"

import { NplAskDock } from "@/components/npl-ai/assistant"
import { buttonVariants } from "@/components/ui/button"
import { NPL_NAV } from "@/lib/nav"
import { SITE_TITLE, siteSubtitle, type Lang } from "@/lib/npl/view"
import { cn } from "cn"

export function SiteBar({ lang, bankCount, yearStart, yearEnd }: { lang: Lang; bankCount: number; yearStart: string; yearEnd: string }) {
  const pathname = usePathname()
  const search = useSearchParams()
  const vi = lang === "vi"
  const subtitle = siteSubtitle(lang, bankCount, yearStart, yearEnd)

  function hrefFor(path: string, stripOwn: boolean) {
    const params = new URLSearchParams(search.toString())
    if (stripOwn) params.delete("own")
    params.delete("drop")
    params.set("lang", lang)
    return `${path}?${params}`
  }

  function langHref(next: Lang) {
    const params = new URLSearchParams(search.toString())
    params.set("lang", next)
    return `${pathname}?${params}`
  }

  function sections(block: boolean) {
    return NPL_NAV.map((item) => {
      const active = item.url === "/" ? pathname === "/" : pathname === item.url || pathname.startsWith(`${item.url}/`)
      return (
        <a
          key={item.url}
          href={hrefFor(item.url, item.url === "/")}
          className={cn(buttonVariants({ variant: active ? "secondary" : "ghost", size: "sm" }), "min-h-11", block && "w-full justify-start")}
          aria-current={active ? "page" : undefined}
        >
          {vi ? item.title : item.en}
        </a>
      )
    })
  }

  return (
    <header className="border-b border-border">
      <a href="#content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-background focus:px-3 focus:py-2">
        {vi ? "Đến nội dung" : "Skip to content"}
      </a>
      <div className="mx-auto w-full max-w-6xl px-4 py-2">
        <div className="flex flex-nowrap items-center gap-2 md:flex-wrap">
          <div className="mr-auto min-w-0 flex-1 md:flex-none">
            <p className="text-base font-semibold leading-tight">{SITE_TITLE[lang]}</p>
            <p className="hidden max-w-[25rem] text-xs leading-snug text-muted-foreground md:block">{subtitle}</p>
          </div>
          <nav className="hidden md:flex flex-wrap gap-1" aria-label={vi ? "Mục" : "Sections"}>
            {sections(false)}
          </nav>
          <details className="relative shrink-0 md:hidden">
            <summary className={cn(buttonVariants({ variant: "outline", size: "sm" }), "min-h-11 cursor-pointer list-none [&::-webkit-details-marker]:hidden")}>
              {vi ? "Mục" : "Menu"}
            </summary>
            <nav className="absolute right-0 z-50 mt-1 flex w-52 flex-col rounded-lg border border-border bg-background p-1 shadow-md" aria-label={vi ? "Mục" : "Sections"}>
              {sections(true)}
            </nav>
          </details>
          <div className="shrink-0">
            <NplAskDock lang={lang} />
          </div>
          <div className="flex shrink-0 rounded-lg border border-border p-0.5" role="group" aria-label={vi ? "Ngôn ngữ" : "Language"}>
            <a href={langHref("vi")} className={cn(buttonVariants({ variant: vi ? "secondary" : "ghost", size: "sm" }), "min-h-11 min-w-11")} aria-current={vi ? "true" : undefined}>
              VI
            </a>
            <a href={langHref("en")} className={cn(buttonVariants({ variant: vi ? "ghost" : "secondary", size: "sm" }), "min-h-11 min-w-11")} aria-current={vi ? undefined : "true"}>
              EN
            </a>
          </div>
        </div>
        <p className="pt-1 text-xs leading-snug text-muted-foreground md:hidden">{subtitle}</p>
      </div>
    </header>
  )
}
