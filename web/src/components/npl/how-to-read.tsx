"use client"

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
export function HowToRead({ label, sentences }: { label: string; sentences: [string, string] }) {
  return (
    <Collapsible>
      <CollapsibleTrigger className="min-h-11 text-left text-sm underline underline-offset-4">
        {label}
      </CollapsibleTrigger>
      <CollapsibleContent className="flex flex-col gap-1 pt-1 text-sm text-muted-foreground">
        <p>{sentences[0]}</p>
        <p>{sentences[1]}</p>
      </CollapsibleContent>
    </Collapsible>
  )
}
