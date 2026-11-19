import { Suspense } from "react"

import { JudgeArticle, JudgeEmpty, JudgeFallback, readMonitor } from "./judge-screen"
import { overviewView } from "@/lib/monitor/sections"

export default function Page() {
  return (
    <Suspense fallback={<JudgeFallback />}>
      <Overview />
    </Suspense>
  )
}

async function Overview() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  return <JudgeArticle view={overviewView(monitor)} />
}
