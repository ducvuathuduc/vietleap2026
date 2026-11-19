import { Suspense } from "react"

import { JudgeArticle, JudgeEmpty, JudgeFallback, readMonitor } from "../judge-screen"
import { provinceView } from "@/lib/monitor/sections"

export default function Page() {
  return (
    <Suspense fallback={<JudgeFallback />}>
      <Provinces />
    </Suspense>
  )
}

async function Provinces() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  return <JudgeArticle view={provinceView(monitor)} />
}
