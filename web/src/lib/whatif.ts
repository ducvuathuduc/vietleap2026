import type { DriversResponse, SavedScenario, WhatIfChange } from "@/lib/api/types"

export const MAX_SLIDERS = 5
export const MAX_SAVED_SCENARIOS = 4

export type WhatIfFeatureInfo = DriversResponse["whatif_features"][number]

export function defaultTopDrivers(
  drivers: DriversResponse | null | undefined,
  limit = MAX_SLIDERS
): WhatIfFeatureInfo[] {
  if (!drivers || !drivers.whatif_features.length) return []
  const byName = new Map(drivers.whatif_features.map((f) => [f.name, f]))
  const ordered: WhatIfFeatureInfo[] = []
  const seen = new Set<string>()
  for (const imp of drivers.drivers?.importance ?? []) {
    const feat = byName.get(imp.feature)
    if (feat && !seen.has(feat.name)) {
      seen.add(feat.name)
      ordered.push(feat)
    }
  }
  for (const feat of drivers.whatif_features) {
    if (!seen.has(feat.name)) {
      seen.add(feat.name)
      ordered.push(feat)
    }
  }
  return ordered.slice(0, limit)
}

export function isZeroVector(changes: WhatIfChange[]): boolean {
  return changes.length === 0 || changes.every((c) => c.pct_change === 0)
}

export function hasZeroCrossing(ci90: [number | null, number | null]): boolean {
  const [lo, hi] = ci90
  if (lo === null || hi === null) return false
  return (lo < 0 && hi > 0) || (lo > 0 && hi < 0)
}

export function formatUnitMode(feat: { name: string; mean: number; sd: number }): {
  disabled: boolean
  mode: "constant" | "sd_step" | "pct_mean"
  unitLabel: string
} {
  if (!Number.isFinite(feat.sd) || feat.sd === 0) {
    return { disabled: true, mode: "constant", unitLabel: "Biến không đổi (sd = 0)" }
  }
  if (!Number.isFinite(feat.mean) || feat.mean <= 0 || Math.abs(feat.mean) < feat.sd * 0.1) {
    return {
      disabled: false,
      mode: "sd_step",
      unitLabel: "Trung bình ≤ 0 hoặc gần 0 — bước chỉnh tính tương đương theo SD",
    }
  }
  return { disabled: false, mode: "pct_mean", unitLabel: "% so với trung bình" }
}

export interface StorageLike {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

export function scenariosKey(datasetId: string): string {
  return `vlk:whatif:scenarios:${datasetId}`
}

function resolveStorage(storage?: StorageLike): StorageLike | null {
  if (storage) return storage
  if (typeof window !== "undefined" && window.localStorage) return window.localStorage
  return null
}

export function loadLocalScenarios(datasetId: string, storage?: StorageLike): SavedScenario[] {
  const s = resolveStorage(storage)
  if (!s || !datasetId) return []
  try {
    const raw = s.getItem(scenariosKey(datasetId))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.slice(0, MAX_SAVED_SCENARIOS).filter(
      (item): item is SavedScenario =>
        typeof item === "object" &&
        item !== null &&
        typeof item.name === "string" &&
        typeof item.result === "object" &&
        item.result !== null
    )
  } catch {
    return []
  }
}

export function saveLocalScenario(
  datasetId: string,
  scenario: SavedScenario,
  storage?: StorageLike
): SavedScenario[] {
  const cur = loadLocalScenarios(datasetId, storage).filter((x) => x.name !== scenario.name)
  const next = [scenario, ...cur].slice(0, MAX_SAVED_SCENARIOS)
  const s = resolveStorage(storage)
  if (s && datasetId) {
    try {
      s.setItem(scenariosKey(datasetId), JSON.stringify(next))
    } catch {
      /* ignore quota errors */
    }
  }
  return next
}

export function removeLocalScenario(
  datasetId: string,
  name: string,
  storage?: StorageLike
): SavedScenario[] {
  const next = loadLocalScenarios(datasetId, storage).filter((x) => x.name !== name)
  const s = resolveStorage(storage)
  if (s && datasetId) {
    try {
      s.setItem(scenariosKey(datasetId), JSON.stringify(next))
    } catch {
      /* ignore quota errors */
    }
  }
  return next
}

export function createScenarioRequester<T>(
  fetcher: (changes: WhatIfChange[], signal: AbortSignal) => Promise<T>,
  options: { debounceMs?: number; minIntervalMs?: number } = {}
) {
  const debounceMs = options.debounceMs ?? 250
  const minIntervalMs = options.minIntervalMs ?? 500
  let timer: ReturnType<typeof setTimeout> | null = null
  let controller: AbortController | null = null
  let lastSentAt = 0
  let pendingResolve: ((v: T | null) => void) | null = null

  const clearPending = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    if (pendingResolve) {
      pendingResolve(null)
      pendingResolve = null
    }
    if (controller) {
      controller.abort()
      controller = null
    }
  }

  return {
    trigger(changes: WhatIfChange[]): Promise<T | null> {
      clearPending()
      return new Promise<T | null>((resolve, reject) => {
        pendingResolve = resolve
        const sinceLast = Date.now() - lastSentAt
        const delay = Math.max(debounceMs, Math.max(0, minIntervalMs - sinceLast))
        timer = setTimeout(() => {
          timer = null
          const ac = new AbortController()
          controller = ac
          lastSentAt = Date.now()
          const finishResolve = pendingResolve
          pendingResolve = null
          fetcher(changes, ac.signal).then(
            (val) => {
              if (controller === ac) controller = null
              finishResolve?.(val)
            },
            (err: unknown) => {
              if (controller === ac) controller = null
              if ((err as { name?: string })?.name === "AbortError") {
                finishResolve?.(null)
              } else {
                reject(err)
              }
            }
          )
        }, delay)
      })
    },
    cancel: clearPending,
  }
}
