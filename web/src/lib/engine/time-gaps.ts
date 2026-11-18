import type { TimeGapSummary } from "@/lib/api/types"

type Cadence = "Y" | "Q" | "M" | "D"

function parsePeriodIndex(period: string, hinted?: string | null): { cadence: Cadence; index: number } | null {
  const s = period.trim()
  if (/^\d{4}$/.test(s) && (!hinted || hinted === "Y")) {
    return { cadence: "Y", index: Number(s) }
  }
  const qm = /^(\d{4})-Q([1-4])$/i.exec(s)
  if (qm) {
    return { cadence: "Q", index: Number(qm[1]) * 4 + (Number(qm[2]) - 1) }
  }
  const mm = /^(\d{4})-(\d{2})$/.exec(s)
  if (mm) {
    const m = Number(mm[2])
    if (m >= 1 && m <= 12) return { cadence: "M", index: Number(mm[1]) * 12 + (m - 1) }
  }
  const dm = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s)
  if (dm) {
    const ms = Date.UTC(Number(dm[1]), Number(dm[2]) - 1, Number(dm[3]))
    if (Number.isFinite(ms)) return { cadence: "D", index: Math.floor(ms / 86_400_000) }
  }
  return null
}

function formatPeriodIndex(cadence: Cadence, index: number): string {
  if (cadence === "Y") return String(index)
  if (cadence === "Q") {
    const year = Math.floor(index / 4)
    const q = (index % 4) + 1
    return `${year}-Q${q}`
  }
  if (cadence === "M") {
    const year = Math.floor(index / 12)
    const m = (index % 12) + 1
    return `${year}-${String(m).padStart(2, "0")}`
  }
  const d = new Date(index * 86_400_000)
  return d.toISOString().slice(0, 10)
}

export function detectTimeGaps(periods: string[], freq?: string | null): TimeGapSummary {
  const parsed = periods
    .map((p) => parsePeriodIndex(String(p), freq))
    .filter((x): x is { cadence: Cadence; index: number } => x !== null)

  if (parsed.length < 2) {
    return { count: 0, samples: [], pct_missing: 0, expected_periods: parsed.length }
  }

  const cadence = parsed[0].cadence
  const sameCadence = parsed.filter((p) => p.cadence === cadence)
  if (sameCadence.length < 2) {
    return { count: 0, samples: [], pct_missing: 0, expected_periods: sameCadence.length }
  }

  const indices = Array.from(new Set(sameCadence.map((p) => p.index))).sort((a, b) => a - b)
  const minIdx = indices[0]
  const maxIdx = indices[indices.length - 1]
  const span = maxIdx - minIdx + 1

  if (span <= 1 || span > 5000) {
    return { count: 0, samples: [], pct_missing: 0, expected_periods: indices.length }
  }

  const present = new Set(indices)
  const missing: string[] = []
  for (let idx = minIdx; idx <= maxIdx; idx++) {
    if (!present.has(idx)) missing.push(formatPeriodIndex(cadence, idx))
  }

  const pct_missing = Number(((missing.length / span) * 100).toFixed(1))
  return {
    count: missing.length,
    samples: missing.slice(0, 5),
    pct_missing,
    expected_periods: span,
  }
}

export function computeMa3<T extends { value: number | null }>(points: T[]): (T & { ma3: number | null })[] {
  return points.map((pt, i) => {
    if (i < 2) return { ...pt, ma3: null }
    const a = points[i - 2]?.value
    const b = points[i - 1]?.value
    const c = pt.value
    if (
      typeof a !== "number" || !Number.isFinite(a) ||
      typeof b !== "number" || !Number.isFinite(b) ||
      typeof c !== "number" || !Number.isFinite(c)
    ) {
      return { ...pt, ma3: null }
    }
    return { ...pt, ma3: Number(((a + b + c) / 3).toFixed(2)) }
  })
}
