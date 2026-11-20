import type { Metadata } from "next"

import { DataTable } from "@/components/npl/data-table"
import { loadSnapshot } from "@/lib/npl/load"
import { SERIES_ATTRIBUTION, dataRows, langFromQuery, pageHref } from "@/lib/npl/view"

export const instant = false

export const metadata: Metadata = {
  title: "Dữ liệu",
  description: "Bảng ngân hàng theo quý của các số đã tính.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const lang = langFromQuery((await searchParams).lang)
  const snapshot = loadSnapshot()
  const rows = dataRows(snapshot)
  const vi = lang === "vi"
  const raw = snapshot.meta.publish_bank_series
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">
        {vi
          ? `${rows.length} dòng ngân hàng-quý. ${raw ? "Có chuỗi gốc." : "Chỉ số đã tính; chuỗi gốc chưa công bố."}`
          : `${rows.length} bank-quarter rows. ${raw ? "Raw series are included." : "Derived figures only; raw series are not published."}`}
      </h1>
      <p>
        <a className="text-sm underline underline-offset-4" href={pageHref("/du-lieu/csv", lang)}>
          {vi ? "Tải CSV các cột công khai" : "Download the CSV of public columns"}
        </a>
      </p>
      {raw ? <p className="text-sm text-muted-foreground">{SERIES_ATTRIBUTION}</p> : null}
      <DataTable rows={rows} raw={raw} lang={lang} />
    </>
  )
}
