import { Suspense } from "react"
import { notFound } from "next/navigation"

import { JudgeArticle, JudgeEmpty, JudgeFallback, readMonitor } from "../../judge-screen"
import { sectorView } from "@/lib/monitor/sections"
import { sectorBySlug } from "@/lib/nav"

export default function Page({ params }: { params: Promise<{ sector: string }> }) {
  return (
    <Suspense fallback={<JudgeFallback />}>
      <Sector params={params} />
    </Suspense>
  )
}

async function Sector({ params }: { params: Promise<{ sector: string }> }) {
  const { sector } = await params
  const known = sectorBySlug(sector)
  if (!known) notFound()
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  return <JudgeArticle view={sectorView(monitor, known.id, known.title)} />
}
