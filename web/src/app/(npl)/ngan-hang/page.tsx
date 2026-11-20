import type { Metadata } from "next"

import { DrillBoard } from "@/components/npl/drill-board"
import { buttonVariants } from "@/components/ui/button"
import { loadSnapshot } from "@/lib/npl/load"
import { bankRows, langFromQuery, pageHref, type Ownership } from "@/lib/npl/view"
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
  const rows = bankRows(loadSnapshot(), ownership).map((bank) => ({
    code: bank.code,
    q4: bank.q4_change_median_pp,
    q1: bank.q1_rebound_median_pp,
  }))
  return (
    <>
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
    </>
  )
}
