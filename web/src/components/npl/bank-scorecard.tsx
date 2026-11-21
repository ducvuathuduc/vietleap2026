import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { indicatorDirection, indicatorValue, type latestScorecard } from "@/lib/npl/research-view"
import { formatNumber, type Lang } from "@/lib/npl/view"

export function BankScorecard({ result, lang }: { result: ReturnType<typeof latestScorecard>; lang: Lang }) {
  const vi = lang === "vi"
  return (
    <section id="bank-scorecard" className="flex min-w-0 flex-col gap-2" aria-labelledby="bank-scorecard-title">
      <h2 className="text-lg font-semibold" id="bank-scorecard-title">{vi ? "Bảng chỉ báo tín dụng" : "Credit scorecard"}</h2>
      {!result ? <p className="text-sm text-muted-foreground">{vi ? "Chưa có bảng chỉ báo cho ngân hàng này." : "This bank’s scorecard is unavailable."}</p> : (
        <div className="min-w-0 overflow-hidden rounded-xl border border-border">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/40 px-3 py-2 text-sm">
            <p className="font-semibold tabular-nums">{result.row.period}</p>
            <p className="text-muted-foreground">
              {result.ranks ? (vi
                ? `Hạng theo nợ xấu ${result.ranks.npl}/${result.ranks.count}, hạng tổng hợp ${result.ranks.composite}/${result.ranks.count}`
                : `NPL rank ${result.ranks.npl}/${result.ranks.count}, composite rank ${result.ranks.composite}/${result.ranks.count}`)
                : vi ? "Chưa đủ dữ liệu để so hạng" : "Ranks are unavailable"}
            </p>
          </div>
          <Table aria-label={vi ? "Chỉ báo chất lượng tín dụng" : "Credit quality indicators"} className="min-w-[22rem]">
            <TableHeader>
              <TableRow>
                <TableHead className="whitespace-normal">{vi ? "Chỉ báo" : "Indicator"}</TableHead>
                <TableHead className="text-right">{vi ? "Giá trị" : "Value"}</TableHead>
                <TableHead className="text-right whitespace-normal">{vi ? "Phân vị" : "Percentile"}</TableHead>
                <TableHead>{vi ? "Hướng đọc" : "Direction"}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.indicators.map((item) => {
                const percentile = result.row.percentiles[item.id]
                return (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium whitespace-normal">{vi ? item.name_vi : item.name_en}</TableCell>
                    <TableCell className="text-right tabular-nums">{indicatorValue(result.row.values[item.id], item.unit, lang)}</TableCell>
                    <TableCell className="text-right tabular-nums">{percentile == null ? "—" : formatNumber(100 * percentile, lang, 0)}</TableCell>
                    <TableCell className="text-xs whitespace-normal text-muted-foreground">{indicatorDirection(item.direction, lang)}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          <p className="border-t border-border px-3 py-2 text-xs text-muted-foreground">
            {vi
              ? "Với các chỉ báo dùng để chấm điểm, phân vị cao hơn là vị trí thuận lợi hơn trong cùng quý."
              : "For scored indicators, higher percentiles indicate a more favourable position in the same quarter."}
          </p>
        </div>
      )}
    </section>
  )
}
