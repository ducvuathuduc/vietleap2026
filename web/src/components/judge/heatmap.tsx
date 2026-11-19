import { cn } from "cn"

import { formatNumber, formatPeriod } from "@/lib/monitor/format"

import { pctileToStep, stepFill, stepTextClass } from "./labels"

export interface HeatCell {
  period: string
  value: number | null
  pctile: number | null
}

export interface HeatmapRow {
  indicatorId: string
  /** Indicator name (`indicators[].name_vi`). */
  label: string
  cells: HeatCell[]
}

export interface HeatmapProps {
  rows: HeatmapRow[]
  unit?: string
  ariaLabel: string
  highlightId?: string
}

/**
 * Server-rendered HTML table: rows are indicators, columns are periods,
 * fill is `pctile_12m` on 5 grey steps. A null pctile leaves the cell blank and the
 * first column stays sticky while the periods scroll horizontally.
 */
export function Heatmap({ rows, unit, ariaLabel, highlightId }: HeatmapProps) {
  const periods = [...new Set(rows.flatMap((row) => row.cells.map((cell) => cell.period)))].sort()
  if (!rows.length || !periods.length) return null

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs text-muted-foreground">
        {unit ? `Đơn vị: ${unit} · ` : ""}Thang xám theo phân vị 12 tháng; ô không tô là chưa có phân vị, dấu – là chưa có số liệu.
      </p>
      <div className="w-full overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <caption className="sr-only">{ariaLabel}</caption>
          <thead>
            <tr>
              <th
                scope="col"
                className="sticky left-0 z-10 border-b border-border bg-card px-2 py-1 text-left font-medium text-muted-foreground"
              >
                Chỉ số
              </th>
              {periods.map((period) => (
                <th
                  key={period}
                  scope="col"
                  className="border-b border-border px-2 py-1 text-right font-normal whitespace-nowrap text-muted-foreground"
                >
                  {formatPeriod(period)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const byPeriod = new Map(row.cells.map((cell) => [cell.period, cell]))
              return (
                <tr key={row.indicatorId}>
                  <th
                    scope="row"
                    className={cn(
                      "sticky left-0 z-10 bg-card px-2 py-1 text-left font-normal",
                      row.indicatorId === highlightId ? "font-medium text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {row.label}
                  </th>
                  {periods.map((period) => {
                    const cell = byPeriod.get(period)
                    const step = pctileToStep(cell?.pctile)
                    const value = cell?.value
                    const shown = typeof value === "number" && Number.isFinite(value) ? formatNumber(value) : ""
                    return (
                      <td
                        key={period}
                        className={cn("px-2 py-1 text-right tabular-nums", stepTextClass(step))}
                        style={step === null ? undefined : { backgroundColor: stepFill(step) }}
                      >
                        {shown ? (
                          <span
                            title={
                              step === null ? shown : `${shown}${unit ? ` ${unit}` : ""} · phân vị ${formatNumber(cell?.pctile)}`
                            }
                          >
                            {shown}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">–</span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
