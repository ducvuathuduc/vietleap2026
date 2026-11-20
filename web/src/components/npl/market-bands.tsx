import { formatNumber, type Lang } from "@/lib/npl/view"

export type MarketBand = { id: string; label: string; median: number | null }

export function MarketBands({ rows, lang, reading }: { rows: MarketBand[]; lang: Lang; reading: string }) {
  const vi = lang === "vi"
  const top = Math.max(0, ...rows.map((row) => row.median ?? 0)) || 1
  return (
    <figure className="rounded-xl border border-border bg-card p-3 sm:p-4">
      <figcaption className="mb-3 text-sm text-muted-foreground">
        {vi ? "Giá cổ phiếu so với giá trị sổ sách, theo nhóm tỷ lệ nợ xấu." : "Share price relative to book value, grouped by NPL ratio."}
      </figcaption>
      <ol className="flex flex-col gap-2">
        {rows.map((row) => (
          <li key={row.id} className="grid grid-cols-[6rem_minmax(0,1fr)_3.5rem] items-center gap-2 text-sm sm:gap-3">
            <span>{row.label}</span>
            <div aria-hidden="true" className="h-5 rounded-sm bg-muted">
              {row.median != null && <div className="h-5 rounded-sm bg-chart-3" style={{ width: `${row.median / top * 100}%` }} />}
            </div>
            <span className="text-right font-medium tabular-nums">
              {row.median == null ? "—" : `${formatNumber(row.median, lang, 2)}×`}
            </span>
          </li>
        ))}
      </ol>
      <p className="mt-4 border-t border-border pt-3 text-sm font-medium">{reading}</p>
    </figure>
  )
}
