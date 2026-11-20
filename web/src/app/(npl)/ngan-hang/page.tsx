import type { Metadata } from "next"

import { DrillBoard } from "@/components/npl/drill-board"
import { buttonVariants } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { loadSnapshot } from "@/lib/npl/load"
import { bankRows, langFromQuery, overviewModel, pageHref, type Ownership } from "@/lib/npl/view"
import { cn } from "cn"

export const instant = false

export const metadata: Metadata = {
  title: "Ngân hàng",
  description: "Trung vị thay đổi NPL quý 4 và quý 1 của từng ngân hàng.",
}

type Query = Record<string, string | string[] | undefined>

function one(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? ""
}

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const query = await searchParams
  const lang = langFromQuery(query.lang)
  const own = one(query.own)
  const ownership: Ownership = own === "state" || own === "private" ? own : "all"
  const vi = lang === "vi"
  const snapshot = await loadSnapshot()
  const rows = bankRows(snapshot, ownership).map((bank) => ({
    code: bank.code,
    q4: bank.q4_change_median_pp,
    q1: bank.q1_rebound_median_pp,
  }))
  const repeat = overviewModel(snapshot, lang).repeat
  return (
    <>
      <p className="text-sm">{vi ? "Tỷ lệ nợ xấu giảm chưa chứng minh tín dụng tốt hơn." : "A falling NPL ratio is not proof of better credit."}</p>
      <h1 className="text-xl font-semibold text-balance">
        {vi ? "Ngân hàng nào có mức giảm quý 4 gần hệ số cả nhóm, và quý 1 có tăng lại không?" : "Which banks' Q4 decline is near the panel coefficient, and does Q1 rise again?"}
      </h1>
      <div className="flex flex-wrap gap-2">
        {(["all", "state", "private"] as const).map((item) => (
          <a
            key={item}
            href={pageHref("/ngan-hang", lang, { own: item === "all" ? undefined : item })}
            className={cn(buttonVariants({ variant: ownership === item ? "secondary" : "outline", size: "sm" }), "min-h-11")}
            aria-current={ownership === item ? "true" : undefined}
          >
            {item === "all" ? (vi ? "Cả nhóm" : "All") : item === "state" ? (vi ? "Nhà nước" : "State") : (vi ? "Tư nhân" : "Private")}
          </a>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">
        {vi ? "Cột đậm là trung vị thay đổi quý 4. Cột nhạt là trung vị quý 1. Sắp từ mức giảm quý 4 lớn nhất. Bấm một mã để mở trang ngân hàng." : "The first bar is the median Q4 change. The second is the median Q1 change. Sorted from the largest Q4 decline. Choose a ticker to open that bank."}
      </p>
      <DrillBoard rows={rows} lang={lang} />
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">
          {vi
            ? `${repeat.length} ngân hàng đảo chiều ở mọi cặp năm của mã đó.`
            : `${repeat.length} banks reversed in every year-pair they have.`}
        </h2>
        <div className="w-full min-w-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{vi ? "Mã" : "Ticker"}</TableHead>
                <TableHead>{vi ? "Cặp năm" : "Year-pairs"}</TableHead>
                <TableHead>{vi ? "Cặp đảo chiều" : "Reversed pairs"}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {repeat.map((row) => (
                <TableRow key={row.code}>
                  <TableCell>
                    <a className="underline underline-offset-4" href={pageHref(`/ngan-hang/${row.code}`, lang)}>{row.code}</a>
                  </TableCell>
                  <TableCell className="tabular-nums">{row.years}</TableCell>
                  <TableCell className="tabular-nums">{row.reversed}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>
    </>
  )
}
