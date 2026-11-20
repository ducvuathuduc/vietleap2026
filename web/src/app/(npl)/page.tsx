import type { Metadata } from "next"

import { MedianChart } from "@/components/npl/charts"
import { DecoderTable } from "@/components/npl/decoder-table"
import { Glossary } from "@/components/npl/glossary"
import { HowToRead } from "@/components/npl/how-to-read"
import { KeyNumbers } from "@/components/npl/key-numbers"
import { loadSnapshot } from "@/lib/npl/load"
import { decoderModel, langFromQuery, overviewModel, pageHref } from "@/lib/npl/view"

export const instant = false

export const metadata: Metadata = {
  title: "Nợ xấu ngân hàng",
  description: "Quý 4 nợ xấu thường giảm, rồi quý 1 tăng lại. Bảng cờ cho biết mức giảm đó có cơ sở không.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const lang = langFromQuery((await searchParams).lang)
  const snapshot = await loadSnapshot()
  const model = overviewModel(snapshot, lang)
  const vi = lang === "vi"
  return (
    <>
      <p className="text-sm">
        {vi
          ? "Tỷ lệ nợ xấu giảm chưa chứng minh tín dụng tốt hơn. Hãy xem nợ nhóm 2, xóa nợ, dự phòng và nhịp cuối năm trước khi tin."
          : "A falling NPL ratio is not proof of better credit. Check group-2 loans, write-offs, provisions and the year-end pattern before you believe it."}
      </p>
      <h1 className="text-xl font-semibold text-balance">{model.plainHeadline}</h1>
      <p className="text-sm text-muted-foreground">{model.evidenceLine}</p>
      <Glossary lang={lang} />
      <KeyNumbers cards={model.cards} lang={lang} />
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Nợ xấu trung vị theo quý" : "Median NPL by quarter"}</h2>
        <MedianChart rows={model.series} lang={lang} mark={model.q4Mark} />
        <HowToRead
          label={vi ? "Cách đọc" : "How to read"}
          sentences={vi
            ? ["Đường là nợ xấu trung vị. Vùng mờ là khoảng giữa nhóm, chấm là quý 4.", "Nhịp giảm quý 4 rồi tăng quý 1 là điều bảng cờ bên dưới kiểm tra."]
            : ["The line is the median NPL. The band is the middle half of banks, and the dots are Q4.", "The Q4 fall and the next Q1 rise are what the flag table below checks."]}
        />
      </section>
      <DecoderTable model={decoderModel(snapshot, lang)} lang={lang} hideSource />
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Vì sao cần kiểm tra" : "Why this needs a check"}</h2>
        {model.why.map((sentence) => (
          <p key={sentence} className="text-sm">{sentence}</p>
        ))}
      </section>
      <p>
        <a className="text-sm underline underline-offset-4" href={pageHref("/phuong-phap", lang)}>
          {vi ? "Xem bằng chứng" : "See the evidence"}
        </a>
      </p>
      <footer className="border-t border-border pt-3 text-xs text-muted-foreground break-words">
        <p>
          {model.footer.publicLine}{" "}
          <a className="underline underline-offset-4" href={pageHref("/phuong-phap", lang)}>{vi ? "Phương pháp" : "Method"}</a>
        </p>
      </footer>
    </>
  )
}
