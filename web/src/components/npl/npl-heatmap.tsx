"use client"

import { useState, type KeyboardEvent } from "react"

import type { HeatmapCell, heatmapModel } from "@/lib/npl/judge-view"
import { formatNumber, pageHref, type Lang } from "@/lib/npl/view"

function cellFill(change: number | null) {
  if (change == null) return {
    backgroundColor: "var(--background)",
    backgroundImage: "repeating-linear-gradient(135deg, var(--border) 0 1px, transparent 1px 4px)",
  }
  if (change === 0) return { backgroundColor: "var(--muted)" }
  // Give the neutral chart token a teal hue here while keeping its theme lightness.
  const color = change < 0 ? "oklch(from var(--chart-2) l 0.13 190)" : "var(--destructive)"
  const strength = Math.min(Math.abs(change), 1.5) / 1.5
  return { backgroundColor: `color-mix(in oklab, ${color} ${20 + strength * 70}%, var(--background))` }
}

function describe(bank: string, period: string, cell: HeatmapCell, lang: Lang) {
  const pct = (value: number | null) => value == null ? "—" : `${formatNumber(value, lang, 2)}%`
  const change = cell.change == null ? "—" : `${cell.change > 0 ? "+" : ""}${formatNumber(cell.change, lang, 2)}`
  return lang === "vi"
    ? `${bank}, ${period}. Nợ xấu ${pct(cell.before)} đến ${pct(cell.after)}. Thay đổi ${change} điểm %.`
    : `${bank}, ${period}. NPL ${pct(cell.before)} to ${pct(cell.after)}. Change ${change} pp.`
}

const MOVES = {
  ArrowUp: [-1, 0],
  ArrowDown: [1, 0],
  ArrowLeft: [0, -1],
  ArrowRight: [0, 1],
} as const

export function NplHeatmap({ model, lang }: { model: ReturnType<typeof heatmapModel>; lang: Lang }) {
  const vi = lang === "vi"
  const { periods, rows } = model
  const years = [...new Set(periods.map((period) => period.slice(0, 4)))]
  const [hover, setHover] = useState("")
  const [focus, setFocus] = useState("")
  const [active, setActive] = useState([0, 0])

  function move(event: KeyboardEvent<HTMLAnchorElement>, row: number, column: number) {
    const delta = MOVES[event.key as keyof typeof MOVES]
    if (!delta) return
    event.preventDefault()
    const nextRow = row + delta[0]
    const nextColumn = column + delta[1]
    event.currentTarget.closest("table")?.querySelector<HTMLAnchorElement>(
      `[data-cell="${nextRow}-${nextColumn}"]`,
    )?.focus()
  }

  if (!rows.length || !periods.length) {
    return <p className="text-sm text-muted-foreground">{vi ? "Chưa công bố chuỗi theo ngân hàng." : "Bank-level history is unavailable."}</p>
  }

  return (
    <figure className="min-w-0 rounded-xl border border-border bg-card px-3 py-2 sm:px-4">
      <figcaption className="flex flex-wrap items-center gap-x-5 gap-y-1 pb-2 text-xs text-muted-foreground">
        {[
          { change: -1, label: vi ? "Nợ xấu giảm" : "NPL fell" },
          { change: 0, label: vi ? "Không đổi" : "Flat" },
          { change: 1, label: vi ? "Nợ xấu tăng" : "NPL rose" },
          { change: null, label: vi ? "Thiếu số liệu" : "Missing data" },
        ].map(({ change, label }) => (
          <span className="inline-flex items-center gap-1.5" key={label}>
            <span className="size-3 rounded-[2px] border border-border" style={cellFill(change)} aria-hidden="true" />
            {label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-1 rounded-sm bg-primary" aria-hidden="true" />
          {vi ? "Quý 4" : "Fourth quarter"}
        </span>
      </figcaption>
      <div className="overflow-x-auto" onPointerLeave={() => setHover("")}>
        <table aria-label={vi ? "Thay đổi tỷ lệ nợ xấu theo quý và ngân hàng" : "Quarterly changes in NPL by bank"} className="w-full min-w-[44rem] table-fixed border-separate border-spacing-x-0.5 border-spacing-y-px text-xs">
          <thead>
            <tr>
              <th scope="col" rowSpan={2} className="sticky left-0 z-10 w-14 bg-card pr-1.5 text-left font-medium text-muted-foreground">
                {vi ? "Mã CK" : "Ticker"}
              </th>
              {years.map((year) => (
                <th key={year} scope="colgroup" colSpan={periods.filter((period) => period.startsWith(year)).length}
                  className="border-b border-border pb-0.5 font-medium text-muted-foreground">{year}</th>
              ))}
            </tr>
            <tr>
              {periods.map((period) => (
                <th scope="col" key={period} aria-label={period} className={period.endsWith("Q4") ? "rounded-sm bg-primary font-medium text-primary-foreground" : "font-normal text-muted-foreground"}>
                  <span aria-hidden="true">{period.slice(4)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(({ bank, cells }, i) => (
              <tr key={bank}>
                <th scope="row" className="sticky left-0 z-10 bg-card pr-1.5 text-left text-[10px] leading-3 font-medium">{bank}</th>
                {cells.map((cell, j) => {
                  const period = periods[j]
                  const title = describe(bank, period, cell, lang)
                  const q4 = period.endsWith("Q4")
                  return (
                    <td key={period} className={q4 ? "border-x border-primary/40" : undefined}>
                      <a href={pageHref(`/ngan-hang/${bank}`, lang)} aria-label={title} title={title}
                        data-cell={`${i}-${j}`} tabIndex={active[0] === i && active[1] === j ? 0 : -1}
                        onPointerEnter={() => setHover(title)}
                        onFocus={() => { setActive([i, j]); setFocus(title) }} onBlur={() => setFocus("")}
                        onKeyDown={(event) => move(event, i, j)}
                        className="block h-4 rounded-[2px] hover:ring-1 hover:ring-inset hover:ring-foreground focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-foreground focus-visible:outline-none sm:h-3"
                        style={cellFill(cell.change)}
                      />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p aria-live="polite" className="mt-2 min-h-8 border-t border-border pt-2 text-xs text-muted-foreground">
        {focus || hover || (vi
          ? "Chọn một ô để xem ngân hàng. Di chuột hoặc dùng phím mũi tên để xem số liệu."
          : "Select a cell to open the bank. Hover or use the arrow keys to read the figures.")}
      </p>
    </figure>
  )
}
