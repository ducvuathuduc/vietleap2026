import type { Metadata } from "next"

import { MedianChart, QuarterChart } from "@/components/npl/charts"
import { DecoderTable } from "@/components/npl/decoder-table"
import { HowToRead } from "@/components/npl/how-to-read"
import { KeyNumbers } from "@/components/npl/key-numbers"
import { buttonVariants } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { loadSnapshot } from "@/lib/npl/load"
import { decoderModel, langFromQuery, overviewModel, pageHref, type Lang, type Ownership } from "@/lib/npl/view"
import { cn } from "cn"

export const instant = false

export const metadata: Metadata = {
  title: "Nợ xấu ngân hàng",
  description: "Quý 4 nợ xấu thường giảm, rồi quý 1 tăng lại. Bảng cờ cho biết mức giảm đó có cơ sở không.",
}

type Query = Record<string, string | string[] | undefined>

function one(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? ""
}

function ownershipOf(value: string): Ownership {
  return value === "state" || value === "private" ? value : "all"
}

function readLabel(lang: Lang): string {
  return lang === "vi" ? "Cách đọc" : "How to read"
}

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const query = await searchParams
  const lang = langFromQuery(query.lang)
  const ownership = ownershipOf(one(query.own))
  const dropEarly = one(query.drop) === "1"
  const snapshot = loadSnapshot()
  const model = overviewModel(snapshot, lang, { ownership, dropEarly })
  const decoder = decoderModel(snapshot, lang)
  const vi = lang === "vi"
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">{model.plainHeadline}</h1>
      <p className="text-sm text-muted-foreground">{model.evidenceLine}</p>
      <KeyNumbers cards={model.cards} lang={lang} />
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Nợ xấu trung vị theo quý" : "Median NPL by quarter"}</h2>
        <MedianChart rows={model.series} lang={lang} mark={model.q4Mark} />
        <HowToRead
          label={readLabel(lang)}
          sentences={vi
            ? ["Đường là nợ xấu trung vị. Vùng mờ là khoảng giữa nhóm, chấm là quý 4.", "Nhịp giảm quý 4 rồi tăng quý 1 là điều bảng cờ bên dưới kiểm tra."]
            : ["The line is the median NPL. The band is the middle half of banks, and the dots are Q4.", "The Q4 fall and the next Q1 rise are what the flag table below checks."]}
        />
      </section>
      <DecoderTable model={decoder} lang={lang} />
      <HowToRead
        label={readLabel(lang)}
        sentences={vi
          ? ["Mỗi ô là nợ xấu thay đổi so với quý trước. Cờ vàng là dấu hiệu cần xem, không phải kết luận che giấu nợ.", "Bấm một ô để xem 5 đầu vào, bốn tỷ lệ và một câu đọc. Nhóm 2 và xóa nợ chưa có trong bản FiinQuant."]
          : ["Each cell is the NPL change from the previous quarter. A yellow flag is something to review, not a finding of hidden bad debt.", "Open a cell for the five inputs, four ratios and one sentence. Group 2 and write-offs are not in the FiinQuant file."]}
      />
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Bằng chứng thống kê" : "Statistical evidence"}</h2>
        <p className="text-sm font-medium">{vi ? "Kiểm tra độ vững" : "Robustness check"}</p>
        <div className="flex flex-wrap items-center gap-2">
          {(["all", "state", "private"] as const).map((item) => (
            <a
              key={item}
              href={pageHref("/", lang, { own: item === "all" ? undefined : item, drop: dropEarly && model.dropEnabled ? "1" : undefined })}
              className={cn(buttonVariants({ variant: ownership === item ? "secondary" : "outline", size: "sm" }), "min-h-11")}
              aria-current={ownership === item ? "true" : undefined}
            >
              {item === "all" ? (vi ? "Cả nhóm" : "All") : item === "state" ? (vi ? "Nhà nước" : "State") : (vi ? "Tư nhân" : "Private")}
            </a>
          ))}
          {model.dropEnabled ? (
            <a
              href={pageHref("/", lang, { own: ownership === "all" ? undefined : ownership, drop: dropEarly ? undefined : "1" })}
              className={cn(buttonVariants({ variant: dropEarly ? "secondary" : "outline", size: "sm" }), "min-h-11")}
              aria-current={dropEarly ? "true" : undefined}
            >
              {vi ? "Bỏ 2021–2022" : "Drop 2021–2022"}
            </a>
          ) : (
            <button type="button" className={cn(buttonVariants({ variant: "outline", size: "sm" }), "min-h-11")} disabled>
              {vi ? "Bỏ 2021–2022" : "Drop 2021–2022"}
            </button>
          )}
        </div>
        {model.dropReason ? <p className="text-sm text-muted-foreground">{model.dropReason}</p> : null}
        {dropEarly && model.dropEnabled && ownership !== "all" ? (
          <p className="text-sm text-muted-foreground">
            {vi ? "Đang dùng mẫu bỏ 2021–2022. Mẫu đó không tách nhà nước và tư nhân." : "Showing the sample that drops 2021–2022. That sample is not split by ownership."}
          </p>
        ) : null}
        <p className="text-sm">{model.decision}</p>
        <QuarterChart bars={model.bars} lang={lang} />
        <p className="text-sm text-muted-foreground">{model.benchmark.wildText}</p>
        <HowToRead
          label={readLabel(lang)}
          sentences={vi
            ? ["Cột là mức nợ xấu quý 2, 3 và 4 khác quý 1, sau khi trừ phần riêng của từng ngân hàng.", "Râu trên cột là khoảng tin cậy 95%. Quý 1 là mốc 0."]
            : ["The bars are how Q2, Q3 and Q4 differ from Q1 after each bank's own level is removed.", "The whiskers are the 95% confidence interval. Q1 is the zero line."]}
        />
      </section>
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">
          {vi ? `${model.repeat.length} ngân hàng đảo chiều ở mọi cặp năm của mã đó` : `${model.repeat.length} banks reversed in every year-pair they have`}
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
              {model.repeat.map((row) => (
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
        <HowToRead
          label={readLabel(lang)}
          sentences={vi
            ? ["Mỗi dòng là một ngân hàng giảm ở quý 4 rồi tăng ở quý 1 trong mọi năm đủ dữ liệu.", "Đây là mô tả từng mã, không phải khuyến nghị mua hoặc bán."]
            : ["Each row is a bank whose NPL fell in Q4 and rose in Q1 in every year with enough data.", "This describes the bank. It is not a buy or sell recommendation."]}
        />
      </section>
      <footer className="flex flex-col gap-2 border-t border-border pt-3 text-xs text-muted-foreground break-words">
        <p>{model.footer.legal}</p>
        <p>
          {model.footer.publicLine}{" "}
          <a className="underline underline-offset-4" href={pageHref("/phuong-phap", lang)}>{vi ? "Phương pháp →" : "Method →"}</a>
        </p>
      </footer>
    </>
  )
}
