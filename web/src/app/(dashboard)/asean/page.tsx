import { Suspense } from "react"

import { JudgeArticle, JudgeEmpty, JudgeFallback, readMonitor } from "../judge-screen"
import { aseanView } from "@/lib/monitor/sections"

export default function Page() {
  return (
    <Suspense fallback={<JudgeFallback />}>
      <Asean />
    </Suspense>
  )
}

async function Asean() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  return <JudgeArticle view={aseanView(monitor)} />
}
