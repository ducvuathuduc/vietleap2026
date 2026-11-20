"use client"

import { useLayoutEffect, useState } from "react"

let sessionStart: number | null = null

function motionOn(): boolean {
  if (typeof window === "undefined") return false
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false
  const now = performance.now()
  if (sessionStart === null) sessionStart = now
  return now - sessionStart < 80
}

export function CountUp({ value, text }: { value: number; text: (value: number) => string }) {
  const [shown, setShown] = useState<number | null>(null)
  const [source, setSource] = useState(value)
  if (source !== value) {
    setSource(value)
    setShown(null)
  }
  useLayoutEffect(() => {
    let frame = 0
    let stop = false
    const timer = window.setTimeout(() => {
      if (!motionOn()) return
      const target = value
      const start = performance.now()
      const tick = (now: number) => {
        if (stop) return
        const t = Math.min(1, (now - start) / 1200)
        const eased = 1 - (1 - t) ** 3
        setShown(target * eased)
        if (t < 1) frame = requestAnimationFrame(tick)
      }
      frame = requestAnimationFrame(tick)
    }, 0)
    return () => {
      stop = true
      window.clearTimeout(timer)
      cancelAnimationFrame(frame)
    }
  }, [value])
  return <span className="tabular-nums">{text(shown === null ? value : shown)}</span>
}

