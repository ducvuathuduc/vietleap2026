import { Suspense } from "react"

import { JudgeArticle, JudgeEmpty, JudgeFallback, readMonitor } from "../judge-screen"
import { methodView } from "@/lib/monitor/sections"

export default function Page() {
  return (
    <Suspense fallback={<JudgeFallback />}>
      <Method />
    </Suspense>
  )
}

async function Method() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  return <JudgeArticle view={methodView(monitor)} />
}
