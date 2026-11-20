"use client"

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import type { Lang } from "@/lib/ratewatch/view"

export function ChartHelp({ lang, children }: { lang: Lang; children: string }) {
  const vi = lang === "vi"
  return (
    <Collapsible>
      <CollapsibleTrigger className="min-h-11 text-left text-sm underline underline-offset-4">
        {vi ? "Cách đọc biểu đồ" : "How to read the chart"}
      </CollapsibleTrigger>
      <CollapsibleContent className="pb-2 text-sm text-muted-foreground">{children}</CollapsibleContent>
    </Collapsible>
  )
}
