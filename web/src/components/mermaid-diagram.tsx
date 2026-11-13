"use client"

import * as React from "react"
import { useTheme } from "next-themes"

import { ErrorState } from "@/components/state"
import { Skeleton } from "@/components/ui/skeleton"

/** Renders Mermaid source (ERD / lineage flowchart) client-side; mermaid is loaded lazily. */
export function MermaidDiagram({ code, label }: { code: string; label: string }) {
  const { resolvedTheme } = useTheme()
  const id = React.useId().replace(/[^a-zA-Z0-9]/g, "")
  const key = `${resolvedTheme}:${code}`
  const [out, setOut] = React.useState<{ key: string; svg?: string; error?: string } | null>(null)

  React.useEffect(() => {
    let alive = true
    import("mermaid")
      .then(async ({ default: mermaid }) => {
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: resolvedTheme === "dark" ? "dark" : "default" })
        const { svg } = await mermaid.render(`mmd${id}`, code)
        if (alive) setOut({ key, svg })
      })
      .catch((e: Error) => alive && setOut({ key, error: `Không vẽ được sơ đồ: ${e.message}` }))
    return () => {
      alive = false
    }
  }, [code, id, key, resolvedTheme])

  const svg = out?.key === key ? out.svg : undefined
  const error = out?.key === key ? out.error : undefined
  if (error) return <ErrorState error={error} />
  if (!svg) return <Skeleton className="h-64 w-full rounded-xl" />
  return (
    <div className="w-full overflow-auto rounded-lg border">
      <div role="img" aria-label={label} className="min-w-max p-4" dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  )
}
