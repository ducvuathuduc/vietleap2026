import { Suspense } from "react"

import { JudgeArticle, JudgeEmpty, JudgeFallback, readMonitor } from "../judge-screen"
import { recommendationView } from "@/lib/monitor/sections"

export default function Page() {
  return (
    <Suspense fallback={<JudgeFallback />}>
      <Recommendations />
    </Suspense>
  )
}

async function Recommendations() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  return <JudgeArticle view={recommendationView(monitor)} />
}
