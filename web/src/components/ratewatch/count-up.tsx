"use client"

import { useLayoutEffect, useState } from "react"

import { formatPct } from "@/lib/ratewatch/format"
import type { Lang } from "@/lib/ratewatch/view"

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

export function AnimatedPercents({ text, lang }: { text: string; lang: Lang }) {
  const parts = text.split(/(\d+(?:[.,]\d+)%)/g)
  return (
    <>
      {parts.map((part, index) => {
        const match = /^(\d+(?:[.,]\d+)?)%$/.exec(part)
        if (!match) return <span key={`${index}-${part}`}>{part}</span>
        const token = match[1] ?? ""
        const numeric = lang === "vi" ? Number(token.replace(/\./g, "").replace(",", ".")) : Number(token.replace(/,/g, ""))
        if (!Number.isFinite(numeric)) return <span key={`${index}-raw`}>{part}</span>
        return <CountUp key={`${index}-pct`} value={numeric} text={(value) => `${formatPct(value, 2, lang)}%`} />
      })}
    </>
  )
}

export function useCurveDraw(): boolean {
  const [draw, setDraw] = useState(false)
  useLayoutEffect(() => {
    const start = window.setTimeout(() => {
      if (motionOn()) setDraw(true)
    }, 0)
    const stop = window.setTimeout(() => setDraw(false), 1200)
    return () => {
      window.clearTimeout(start)
      window.clearTimeout(stop)
    }
  }, [])
  return draw
}
