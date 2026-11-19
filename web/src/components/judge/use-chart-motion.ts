"use client"

import * as React from "react"

const FIRST_RENDER_MS = 1200
const REDUCE_QUERY = "(prefers-reduced-motion: reduce)"

function subscribeReduceMotion(onChange: () => void) {
  const query = window.matchMedia(REDUCE_QUERY)
  query.addEventListener("change", onChange)
  return () => query.removeEventListener("change", onChange)
}

function getReduceMotion() {
  return window.matchMedia(REDUCE_QUERY).matches
}

/**
 * AMENDMENTS §3: Recharts may animate on first mount only (400 ms ease-out) and
 * must be off under `prefers-reduced-motion: reduce`. Later filter changes render
 * without animation because the timer has already expired.
 */
export function useChartAnimation() {
  const reduceMotion = React.useSyncExternalStore(subscribeReduceMotion, getReduceMotion, () => false)
  const [firstRender, setFirstRender] = React.useState(true)

  React.useEffect(() => {
    const timer = window.setTimeout(() => setFirstRender(false), FIRST_RENDER_MS)
    return () => window.clearTimeout(timer)
  }, [])

  return {
    isAnimationActive: firstRender && !reduceMotion,
    animationDuration: 400,
    animationEasing: "ease-out" as const,
  }
}
