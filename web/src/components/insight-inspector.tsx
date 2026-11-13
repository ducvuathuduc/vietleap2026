"use client"

import * as React from "react"
import { usePathname, useRouter } from "next/navigation"
import { driver, type Config, type Driver, type DriveStep } from "driver.js"
import "driver.js/dist/driver.css"
import { toast } from "sonner"

import { useDataset } from "@/components/dataset-provider"
import { InsightSheet } from "@/components/insight-sheet"
import { escapeHtml, stepSelector, type Story } from "@/lib/analyst/story"
import { readInsightTarget, type InsightContext } from "@/lib/insight-target"
import { tourSteps, targetSelector, type DiscoveredTarget } from "@/lib/tour-steps"

interface InspectorValue {
  inspecting: boolean
  setInspecting: (on: boolean) => void
  startTour: (pathname: string) => void
  /** Narrated top-insight walkthrough (AI or offline engine). */
  startStory: () => void
  storyLoading: boolean
}

const InspectorContext = React.createContext<InspectorValue | null>(null)

const TOUR_TEXT: Partial<Config> = {
  showProgress: true,
  progressText: "{{current}}/{{total}}",
  nextBtnText: "Tiếp →",
  prevBtnText: "← Trước",
  doneBtnText: "Xong",
  closeBtnLabel: "Đóng (Esc)",
  allowKeyboardControl: true, // ←/→ navigate, Esc closes
  skipMissingElement: true, // an element that unmounted mid-tour is skipped, never a crash
  waitForElement: 1500,
  smoothScroll: true,
  stagePadding: 6,
}

function targetAt(x: number, y: number): Element | null {
  for (const el of document.elementsFromPoint(x, y)) {
    const t = el.closest("[data-insight-target]")
    if (t) return t
  }
  return null
}

function exists(selector: string): boolean {
  try {
    return document.querySelector(selector) !== null
  } catch {
    return false // invalid selector
  }
}

function discoverTargets(): DiscoveredTarget[] {
  return [...document.querySelectorAll("[data-insight-target]")]
    .filter((el) => (el as HTMLElement).offsetParent !== null || el.getClientRects().length > 0)
    .map((el) => ({ selector: targetSelector(el.getAttribute("data-insight-target") ?? ""), label: el.getAttribute("data-insight-label") ?? "Phần tử" }))
}

/** Resolve when `selector` is in the DOM (or after `timeoutMs`). */
function waitFor(selector: string, timeoutMs: number): Promise<boolean> {
  return new Promise((resolve) => {
    if (exists(selector)) return resolve(true)
    const t0 = performance.now()
    const id = window.setInterval(() => {
      if (exists(selector)) {
        window.clearInterval(id)
        resolve(true)
      } else if (performance.now() - t0 > timeoutMs) {
        window.clearInterval(id)
        resolve(false)
      }
    }, 120)
  })
}

function storySteps(story: Story): DriveStep[] {
  const intro: DriveStep = {
    popover: {
      title: "Câu chuyện dữ liệu",
      description: `${escapeHtml(story.headline)}<br><br><small>${story.mode === "llm" ? `Lời dẫn: ${escapeHtml(story.model ?? "AI")} · số liệu đã đối chiếu với engine` : "Chế độ offline: lời dẫn lấy nguyên văn từ engine"} · ←/→ để chuyển, Esc để thoát</small>`,
    },
  }
  const body = story.steps.map<DriveStep>((s) => ({
    element: () => (document.querySelector(stepSelector(s.id)) ?? document.querySelector(stepSelector(s.id, "table-row"))) as Element,
    popover: {
      title: `#${s.rank} · ${escapeHtml(s.title)}`,
      description: [
        escapeHtml(s.narration),
        `<br><br><small>Kiểm định: ${escapeHtml(s.stats)}</small>`,
        s.action ? `<br><small><b>Hành động:</b> ${escapeHtml(s.action)}</small>` : "",
      ].join(""),
    },
  }))
  const outro: DriveStep = { popover: { title: "Từ dữ liệu đến quyết định", description: escapeHtml(story.closing) } }
  return [intro, ...body, outro]
}

/** "Explain anything": hover-highlight tagged elements with driver.js, click to ask the AI analyst in a Sheet. */
export function InsightInspectorProvider({ children }: { children: React.ReactNode }) {
  const { datasetId } = useDataset()
  const pathname = usePathname()
  const router = useRouter()
  const [inspecting, setInspecting] = React.useState(false)
  const [target, setTarget] = React.useState<InsightContext | null>(null)
  const [requestKey, setRequestKey] = React.useState(0)
  const [storyLoading, setStoryLoading] = React.useState(false)
  const tourRef = React.useRef<Driver | null>(null)
  const storyRun = React.useRef(0)

  const stopTour = React.useCallback(() => {
    try {
      tourRef.current?.destroy()
    } catch {
      /* already torn down */
    }
    tourRef.current = null
  }, [])

  const runTour = React.useCallback(
    (steps: DriveStep[]) => {
      stopTour()
      if (steps.length === 0) return
      setInspecting(false)
      try {
        const d = driver({ ...TOUR_TEXT, steps, onDestroyed: () => (tourRef.current === d ? (tourRef.current = null) : undefined) })
        tourRef.current = d
        d.drive()
      } catch (e) {
        tourRef.current = null
        toast.error(`Không mở được hướng dẫn: ${(e as Error).message}`)
      }
    },
    [stopTour]
  )

  // Leaving a page ends any tour whose elements belong to it (a story navigates first, then starts).
  React.useEffect(() => stopTour, [pathname, stopTour])

  React.useEffect(() => {
    if (!inspecting || target) return // paused while the Sheet is open
    let current: Element | null = null
    let frame = 0
    let hl: Driver | null = null
    const clear = () => {
      try {
        hl?.destroy()
      } catch {
        /* element already gone */
      }
      hl = null
      current = null
    }
    const show = (el: Element) => {
      if (!el.isConnected) return clear()
      try {
        hl ??= driver({ animate: false, overlayOpacity: 0.2, stagePadding: 4, allowKeyboardControl: false, overlayClickBehavior: "none", showButtons: [] })
        hl.highlight({
          element: el,
          popover: { title: escapeHtml(el.getAttribute("data-insight-label") ?? "Phần tử"), description: "Bấm để hỏi AI về phần tử này · Esc để thoát", side: "bottom", align: "start" },
        })
      } catch {
        clear()
      }
    }
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const t = targetAt(e.clientX, e.clientY)
        if (t === current && t?.isConnected) return
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
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return
      e.preventDefault()
      setInspecting(false)
    }
    // content moved under a still pointer → drop the stale highlight
    const onScroll = () => current && !current.isConnected && clear()
    window.addEventListener("pointermove", onMove)
    window.addEventListener("click", onClick, true)
    window.addEventListener("keydown", onKey)
    window.addEventListener("scroll", onScroll, true)
    document.body.style.cursor = "help"
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener("pointermove", onMove)
      window.removeEventListener("click", onClick, true)
      window.removeEventListener("keydown", onKey)
      window.removeEventListener("scroll", onScroll, true)
      document.body.style.cursor = ""
      clear()
    }
  }, [inspecting, target, pathname])

  const startTour = React.useCallback(
    (path: string) => {
      const steps = tourSteps(path, exists, discoverTargets())
      if (steps.length === 0) {
        toast.info("Trang này chưa có phần tử để hướng dẫn — hãy chọn dataset trước.")
        return
      }
      runTour(steps.map((s) => ({ element: s.selector, popover: { title: escapeHtml(s.title), description: escapeHtml(s.description) } })))
    },
    [runTour]
  )

  const startStory = React.useCallback(async () => {
    if (!datasetId) {
      toast.info("Chọn một dataset ở thanh trên cùng trước khi kể chuyện.")
      return
    }
    const run = ++storyRun.current
    setStoryLoading(true)
    setInspecting(false)
    stopTour()
    try {
      const res = await fetch("/api/story", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ datasetId }) })
      const body = (await res.json()) as Story & { detail?: string }
      if (!res.ok) throw new Error(body.detail ?? res.statusText)
      if (run !== storyRun.current) return // superseded by a newer click
      if (body.steps.length === 0) {
        toast.info(body.headline)
        return
      }
      if (pathname !== "/insights") router.push("/insights")
      const ready = await waitFor(stepSelector(body.steps[0].id), 10_000)
      if (run !== storyRun.current) return
      if (!ready) toast.warning("Chưa thấy thẻ insight trên trang — câu chuyện vẫn chạy, bước thiếu sẽ được bỏ qua.")
      runTour(storySteps(body))
    } catch (e) {
      toast.error(`Không dựng được câu chuyện: ${(e as Error).message}`)
    } finally {
      if (run === storyRun.current) setStoryLoading(false)
    }
  }, [datasetId, pathname, router, runTour, stopTour])

  const value = React.useMemo(
    () => ({ inspecting, setInspecting, startTour, startStory: () => void startStory(), storyLoading }),
    [inspecting, startTour, startStory, storyLoading]
  )
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
