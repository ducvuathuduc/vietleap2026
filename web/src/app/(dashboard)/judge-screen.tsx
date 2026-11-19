import { connection } from "next/server"

import { PageShell } from "@/components/state"
import { loadMonitor } from "@/lib/monitor/load"
import { MONITOR_EMPTY_VI, type JudgeView } from "@/lib/monitor/sections"

export function JudgeFallback() {
  return (
    <PageShell>
      <p className="px-4 text-sm text-muted-foreground lg:px-6">Đang đọc bản đã xuất bản.</p>
    </PageShell>
  )
}

export function JudgeArticle({ view }: { view: JudgeView }) {
  return (
    <PageShell>
      <article className="flex max-w-3xl flex-col gap-3 px-4 lg:px-6">
        <h1 className="text-2xl font-semibold tracking-tight">{view.headline}</h1>
        {view.question ? <p className="text-muted-foreground">{view.question}</p> : null}
        <ul className="flex list-disc flex-col gap-2 pl-5 text-sm">
          {view.sections.map((section) => (
            <li key={section.id}>{section.label}</li>
          ))}
        </ul>
      </article>
    </PageShell>
  )
}

export function JudgeEmpty() {
  return (
    <PageShell>
      <p className="px-4 text-sm lg:px-6">{MONITOR_EMPTY_VI}</p>
    </PageShell>
  )
}

export async function readMonitor() {
  await connection()
  return loadMonitor()
}
