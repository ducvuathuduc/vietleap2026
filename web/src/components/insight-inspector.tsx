"use client"

import * as React from "react"
import { driver, type Driver } from "driver.js"
import "driver.js/dist/driver.css"

import { useDataset } from "@/components/dataset-provider"
import { InsightSheet } from "@/components/insight-sheet"
import { readInsightTarget, type InsightContext } from "@/lib/insight-target"
import { tourSteps } from "@/lib/tour-steps"

interface InspectorValue {
  inspecting: boolean
  setInspecting: (on: boolean) => void
  startTour: (pathname: string) => void
}

const InspectorContext = React.createContext<InspectorValue | null>(null)

function targetAt(x: number, y: number): Element | null {
  for (const el of document.elementsFromPoint(x, y)) {
    const t = el.closest("[data-insight-target]")
    if (t) return t
  }
  return null
}

/** "Explain anything": hover-highlight tagged elements with driver.js, click to ask the AI analyst in a Sheet. */
export function InsightInspectorProvider({ children }: { children: React.ReactNode }) {
  const { datasetId } = useDataset()
  const [inspecting, setInspecting] = React.useState(false)
  const [target, setTarget] = React.useState<InsightContext | null>(null)
  const [requestKey, setRequestKey] = React.useState(0)

  React.useEffect(() => {
    if (!inspecting || target) return // paused while the Sheet is open
    let current: Element | null = null
    let frame = 0
    let hl: Driver | null = null
    const clear = () => {
      hl?.destroy()
      hl = null
      current = null
    }
    const show = (el: Element) => {
      hl ??= driver({ animate: false, overlayOpacity: 0.2, stagePadding: 4, allowKeyboardControl: false, overlayClickBehavior: "none", showButtons: [] })
      hl.highlight({
        element: el,
        popover: { title: el.getAttribute("data-insight-label") ?? "Phần tử", description: "Bấm để hỏi AI về phần tử này · Esc để thoát", side: "bottom", align: "start" },
      })
    }
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const t = targetAt(e.clientX, e.clientY)
        if (t === current) return
        if (!t) return clear()
        current = t
        show(t)
      })
    }
    const onClick = (e: MouseEvent) => {
      const t = targetAt(e.clientX, e.clientY)
      const ctx = t && readInsightTarget(t)
      if (!ctx) return
      e.preventDefault()
      e.stopPropagation()
      clear()
      setRequestKey((k) => k + 1)
      setTarget(ctx)
    }
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setInspecting(false)
    window.addEventListener("pointermove", onMove)
    window.addEventListener("click", onClick, true)
    window.addEventListener("keydown", onKey)
    document.body.style.cursor = "help"
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener("pointermove", onMove)
      window.removeEventListener("click", onClick, true)
      window.removeEventListener("keydown", onKey)
      document.body.style.cursor = ""
      clear()
    }
  }, [inspecting, target])

  const startTour = React.useCallback((pathname: string) => {
    const steps = tourSteps(pathname, (s) => document.querySelector(s) !== null)
    if (steps.length === 0) return
    driver({
      showProgress: true,
      progressText: "{{current}}/{{total}}",
      nextBtnText: "Tiếp",
      prevBtnText: "Trước",
      doneBtnText: "Xong",
      steps: steps.map((s) => ({ element: s.selector, popover: { title: s.title, description: s.description } })),
    }).drive()
  }, [])

  const value = React.useMemo(() => ({ inspecting, setInspecting, startTour }), [inspecting, startTour])
  return (
    <InspectorContext.Provider value={value}>
      {children}
      <InsightSheet target={target} datasetId={datasetId} requestKey={requestKey} onClose={() => setTarget(null)} />
    </InspectorContext.Provider>
  )
}

export function useInsightInspector() {
  const ctx = React.useContext(InspectorContext)
  if (!ctx) throw new Error("useInsightInspector must be used inside <InsightInspectorProvider>")
  return ctx
}
