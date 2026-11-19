import { Suspense } from "react"
import { notFound } from "next/navigation"

import { JudgeArticle, JudgeEmpty, JudgeFallback, readMonitor } from "../../judge-screen"
import { provinceDetailView } from "@/lib/monitor/sections"

export default function Page({ params }: { params: Promise<{ code: string }> }) {
  return (
    <Suspense fallback={<JudgeFallback />}>
      <Province params={params} />
    </Suspense>
  )
}

async function Province({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  const view = provinceDetailView(monitor, code)
  if (!view) notFound()
  return <JudgeArticle view={view} />
}
