import type { Metadata } from "next"

import { MarketChart } from "@/components/npl/charts"
import { loadSnapshot } from "@/lib/npl/load"
import { langFromQuery, marketModel } from "@/lib/npl/view"

export const instant = false

export const metadata: Metadata = {
  title: "Thị trường",
  description: "Lợi suất bất thường tích lũy quanh hạn công bố và hồi quy CAR.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const lang = langFromQuery((await searchParams).lang)
  const model = marketModel(loadSnapshot(), lang)
  const vi = lang === "vi"
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">
        {vi ? "Giá có phản ứng với biến động NPL quanh hạn công bố không?" : "Does the price react to the NPL change around the disclosure deadline?"}
      </h1>
      <p className="text-sm text-muted-foreground">
        {vi
          ? `${model.events}/${model.eligible} sự kiện có CAR. Đường đậm là mọi quý, đường kia là quý 4. Vùng nhạt là khoảng 95%.`
          : `${model.events}/${model.eligible} events have a CAR. One line is every quarter, the other is Q4. The band is the 95% interval.`}
      </p>
      <MarketChart rows={model.points} lang={lang} />
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
