"use client"

import { Badge } from "@/components/ui/badge"
import { formatPct } from "@/lib/ratewatch/format"
import type { SnapshotBank } from "@/lib/ratewatch/types"
import { gradeBadge, quantileSteps, rateForHorizon, type Grade, type Lang } from "@/lib/ratewatch/view"

const SHADES = [8, 18, 32, 48, 66]

function cellMap(bank: SnapshotBank, channel: string, lang: Lang) {
  const cells = new Map<number, { text: string; grade: Grade; note: string; rate: number }>()
  for (const rate of bank.rates) {
    if (rate.channel !== channel || (rate.tier ?? "") !== "") continue
    const values = (rate.readers?.length ? rate.readers : [{ value: rate.rate_pct }]).map((reader) => reader.value)
    const unique = [...new Set(values)]
    cells.set(rate.term_months, {
      text: unique.map((value) => `${formatPct(value, 2, lang)}%`).join(" · "),
      grade: rate.grade,
      note: rate.grade_note,
      rate: rate.rate_pct,
    })
  }
  return cells
}

export function HeatTable({
  banks,
  channel,
  sortTerm,
  lang,
  onSelect,
}: {
  banks: SnapshotBank[]
  channel: string
  sortTerm: number
  lang: Lang
  onSelect: (code: string) => void
}) {
  const vi = lang === "vi"
  const listed = banks.filter((bank) => bank.sheet_date)
  const maps = new Map(listed.map((bank) => [bank.code, cellMap(bank, channel, lang)]))
  const terms = [...new Set(listed.flatMap((bank) => [...(maps.get(bank.code)?.keys() ?? [])]))].sort((left, right) => left - right)
  const steps = quantileSteps(listed.flatMap((bank) => [...(maps.get(bank.code)?.values() ?? [])].map((cell) => cell.rate)))
  const shade = (rate: number) => {
    let group = 0
    for (const step of steps) {
      if (rate >= step.min && rate <= step.max) group = step.group
    }
    return `color-mix(in oklab, var(--foreground) ${SHADES[Math.min(SHADES.length - 1, group)] ?? 8}%, transparent)`
  }
  const score = (bank: SnapshotBank) => {
    const exact = maps.get(bank.code)?.get(sortTerm)
    if (exact) return exact.rate
    return rateForHorizon(bank.rates, channel, sortTerm)?.rate ?? null
  }
  const rows = listed.slice().sort((left, right) => {
    const a = score(left)
    const b = score(right)
    if (a === null && b === null) return left.code.localeCompare(right.code)
    if (a === null) return 1
    if (b === null) return -1
    return b - a || left.code.localeCompare(right.code)
  })
  return (
    <div className="max-w-full min-w-0 overflow-x-auto">
      <table className="w-max min-w-full border-separate border-spacing-0 text-xs">
        <caption className="caption-top pb-2 text-left text-sm">
          {vi ? `Sắp theo kỳ ${sortTerm} tháng. Ô đậm là lãi cao hơn.` : `Sorted by the ${sortTerm}-month term. Darker cells are higher rates.`}
        </caption>
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-card px-2 py-1 text-left">{vi ? "Ngân hàng" : "Bank"}</th>
            {terms.map((term) => (
              <th key={term} className="px-2 py-1 text-right">{term}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((bank) => (
            <tr key={bank.code}>
              <th className="sticky left-0 z-10 bg-card px-2 py-1 text-left font-medium">
                <button type="button" className="min-h-11 underline-offset-4 hover:underline" onClick={() => onSelect(bank.code)}>
                  {vi ? bank.name_vi : bank.name_en}
                </button>
              </th>
              {terms.map((term) => {
                const cell = maps.get(bank.code)?.get(term)
                if (!cell) return <td key={term} className="px-2 py-1 text-right text-muted-foreground">—</td>
                const badge = gradeBadge(cell.grade, cell.note, lang)
                return (
                  <td key={term} className="px-2 py-1 text-right tabular-nums" style={{ background: shade(cell.rate) }}>
                    <span className="block">{cell.text}</span>
                    <Badge variant="outline">{badge.label}</Badge>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
