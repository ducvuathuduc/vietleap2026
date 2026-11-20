import type { Metadata } from "next"

import { DataTable } from "@/components/npl/data-table"
import { HowToRead } from "@/components/npl/how-to-read"
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
  const snapshot = await loadSnapshot()
  const rows = dataRows(snapshot)
  const vi = lang === "vi"
  const raw = snapshot.meta.publish_bank_series
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">
        {vi
          ? `${rows.length} dòng, mỗi dòng là một ngân hàng trong một quý.`
          : `${rows.length} rows. Each row is one bank in one quarter.`}
      </h1>
      <p>
        <a className="text-sm underline underline-offset-4" href={pageHref("/du-lieu/csv", lang)}>
          {vi ? "Tải bảng" : "Download the table"}
        </a>
      </p>
      {raw ? <p className="text-sm text-muted-foreground">{SERIES_ATTRIBUTION}</p> : null}
      <DataTable rows={rows} raw={raw} lang={lang} />
      <HowToRead
        label={vi ? "Cách đọc" : "How to read"}
        sentences={vi
          ? ["Biến động NPL là nợ xấu tăng hoặc giảm bao nhiêu điểm phần trăm so với quý trước.", "Bấm tên cột để xếp các dòng, và cột sau hiệu ứng quý đã trừ nhịp riêng của quý đó."]
          : ["NPL change is how many percentage points bad debt rose or fell versus the previous quarter.", "Click a column name to sort the rows, and the after-quarter-effect column removes that quarter's usual move."]}
      />
    </>
  )
}
