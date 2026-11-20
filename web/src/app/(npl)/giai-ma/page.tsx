import type { Metadata } from "next"

import { DecoderTable } from "@/components/npl/decoder-table"
import { HowToRead } from "@/components/npl/how-to-read"
import { loadSnapshot } from "@/lib/npl/load"
import { decoderModel, langFromQuery, pageHref } from "@/lib/npl/view"

export const instant = false

export const metadata: Metadata = {
  title: "Giải mã nợ xấu",
  description: "Cờ nợ xấu của mọi ngân hàng niêm yết, mọi quý đã có số.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const lang = langFromQuery((await searchParams).lang)
  const model = decoderModel(await loadSnapshot(), lang, "all")
  const vi = lang === "vi"
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">{vi ? "Mọi ngân hàng, mọi quý: cờ vàng là dấu hiệu cần xem, không phải kết luận che giấu nợ." : "Every bank, every quarter: a yellow flag is a sign to review, not a conclusion that a bank is hiding bad debt."}</h1>
      <p><a className="text-sm underline underline-offset-4" href={pageHref("/", lang)}>{vi ? "Về tám ngân hàng lớn" : "Back to the eight large banks"}</a></p>
      <DecoderTable model={model} lang={lang} />
      <HowToRead
        label={vi ? "Cách đọc" : "How to read"}
        sentences={vi
          ? ["Mỗi ô là nợ xấu đổi so với quý trước; bấm ô để xem câu đọc, 5 đầu vào và bốn tỷ lệ.", "Chọn quý hoặc trạng thái để lọc: ô không khớp thành gạch ngang, và khi đã chọn trạng thái thì hàng không còn ô khớp sẽ ẩn."]
          : ["Each cell is the NPL change versus the previous quarter; open it for the reading, five inputs and four ratios.", "Choose a quarter or a status to filter: a cell that does not match becomes a dash, and once a status is selected a bank row hides when none of its cells match."]}
      />
    </>
  )
}
