import type { Metadata } from "next"

import { MarketChart } from "@/components/npl/charts"
import { HowToRead } from "@/components/npl/how-to-read"
import { loadSnapshot } from "@/lib/npl/load"
import { langFromQuery, marketModel, type Lang } from "@/lib/npl/view"

export const instant = false

export const metadata: Metadata = {
  title: "Thị trường",
  description: "Lợi suất bất thường quanh hạn công bố và câu đọc của hồi quy.",
}

type Query = Record<string, string | string[] | undefined>

function readLabel(lang: Lang): string {
  return lang === "vi" ? "Cách đọc" : "How to read"
}

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const lang = langFromQuery((await searchParams).lang)
  const model = marketModel(await loadSnapshot(), lang)
  const vi = lang === "vi"
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">
        {vi
          ? "Lợi suất bất ngờ quanh hạn công bố khác không theo cụm ngân hàng, nhưng bootstrap chưa bác bỏ trường hợp không có phản ứng."
          : "The surprise return around the disclosure deadline differs from zero across bank clusters, but the bootstrap does not rule out no reaction."}
      </h1>
      <p className="text-sm text-muted-foreground">
        {vi
          ? `${model.events}/${model.eligible} ngân hàng-quý có lợi suất bất thường quanh hạn công bố.`
          : `${model.events}/${model.eligible} bank-quarters have an abnormal return around the disclosure deadline.`}
      </p>
      <MarketChart rows={model.points} lang={lang} />
      <HowToRead
        label={readLabel(lang)}
        sentences={vi
          ? ["Trục ngang là số ngày quanh hạn công bố. Đường là lợi suất bất thường tích lũy.", "Một đường là mọi quý, đường kia là quý 4. Vùng nhạt là khoảng 95%."]
          : ["The horizontal axis counts days around the disclosure deadline. The lines are cumulative abnormal returns.", "One line is every quarter and the other is the fourth quarter. The pale band is the 95% interval."]}
      />
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Hồi quy, nói bằng lời" : "Regressions, in words"}</h2>
        <ul className="flex flex-col gap-2 text-sm">
          {model.rows.map((row) => (
            <li key={row.id}>{row.text}</li>
          ))}
        </ul>
        <p className="text-sm text-muted-foreground">{model.reading}</p>
      </section>
    </>
  )
}
