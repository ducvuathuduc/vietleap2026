import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { bankCheck } from "@/lib/npl/research-view"
import { formatNumber, pageHref, type Lang, type Snapshot } from "@/lib/npl/view"

const selectStyle = "h-11 w-full min-w-0 rounded-lg border border-input bg-background px-2 text-sm focus-visible:outline-2 focus-visible:outline-ring sm:h-9 sm:min-w-26"

export function CreditCheck({ snapshot, bank, period, lang }: {
  snapshot: Snapshot
  bank: string
  period: string
  lang: Lang
}) {
  const vi = lang === "vi"
  const periods = snapshot.series.median_by_period.map(({ period }) => period).sort().reverse()
  const model = bankCheck(snapshot, bank, period, lang)
  const value = (amount: number | null) => amount == null ? "—" : `${formatNumber(amount, lang, 2)} ${vi ? "điểm %" : "pp"}`
  return (
    <section id="bank-check" className="scroll-mt-3 rounded-xl border border-border bg-card" aria-labelledby="bank-check-title">
      <div className="flex flex-wrap items-end justify-between gap-x-5 gap-y-3 border-b border-border p-3 sm:p-4">
        <div>
          <h2 id="bank-check-title" className="text-lg font-semibold">{vi ? "Kiểm tra một ngân hàng" : "Check a bank"}</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {vi ? "Đọc năm bằng chứng trong cùng một quý." : "Read five pieces of evidence for the same quarter."}
          </p>
        </div>
        <form action="/#bank-check" method="get" className="grid w-full grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-end gap-2 sm:w-auto">
          <input type="hidden" name="lang" value={lang} />
          <label className="grid gap-1 text-xs font-medium">
            {vi ? "Ngân hàng" : "Bank"}
            <select className={selectStyle} name="bank" defaultValue={bank}>
              {snapshot.banks.map((item) => <option key={item.code} value={item.code}>{item.code}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-xs font-medium">
            {vi ? "Quý" : "Quarter"}
            <select className={selectStyle} name="period" defaultValue={period}>
              {periods.map((quarter) => <option key={quarter} value={quarter}>{quarter}</option>)}
            </select>
          </label>
          <Button type="submit" className="h-11 sm:h-9">{vi ? "Xem kết quả" : "Show evidence"}</Button>
        </form>
      </div>
      <dl className="divide-y divide-border">
        {model.checks.map((item) => (
          <div key={item.id} className="grid gap-x-4 gap-y-1.5 px-3 py-2.5 sm:grid-cols-[minmax(8rem,1fr)_minmax(8rem,1fr)_minmax(7rem,0.85fr)_minmax(0,2fr)] sm:items-baseline sm:px-4">
            <dt className="text-sm font-medium">{item.label}</dt>
            <dd className="grid min-w-0 grid-cols-[1fr_auto] items-baseline gap-x-2 gap-y-1 text-sm sm:col-span-3 sm:grid-cols-[minmax(8rem,1fr)_minmax(7rem,0.85fr)_minmax(0,2fr)] sm:gap-x-4">
              <span className="font-semibold whitespace-pre-line tabular-nums">{item.value}</span>
              <Badge variant={item.tone === "watch" ? "default" : "outline"}>{item.verdict}</Badge>
              <span className="col-span-2 text-xs leading-relaxed text-muted-foreground sm:col-span-1 sm:text-sm">{item.why}</span>
            </dd>
          </div>
        ))}
      </dl>
      <div className="grid gap-x-4 gap-y-2 rounded-b-xl border-t border-border bg-muted/45 px-3 py-3 text-sm sm:grid-cols-2 sm:px-4">
        <p>
          {vi ? "Nợ xấu công bố" : "Reported NPL change"} <strong>{value(model.reportedChange)}</strong>
          <span className="mx-2 text-muted-foreground">/</span>
          {vi ? "Sau điều chỉnh mùa vụ" : "After seasonal adjustment"} <strong>{value(model.adjustedChange)}</strong>
        </p>
        <p>
          {model.ranks
            ? (vi ? `Hạng theo nợ xấu ${model.ranks.npl}/${model.ranks.count}, hạng chất lượng tổng hợp ${model.ranks.composite}/${model.ranks.count}.`
              : `NPL rank ${model.ranks.npl}/${model.ranks.count}, composite quality rank ${model.ranks.composite}/${model.ranks.count}.`)
            : (vi ? "Chưa đủ dữ liệu để so hạng." : "The two ranks are unavailable for this quarter.")}{" "}
          <a className="font-medium underline underline-offset-4" href={pageHref(`/ngan-hang/${bank}`, lang)}>
            {vi ? `Xem hồ sơ ${bank}` : `Open ${bank} profile`}
          </a>
        </p>
      </div>
    </section>
  )
}
