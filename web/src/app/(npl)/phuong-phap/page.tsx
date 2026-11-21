import type { Metadata } from "next"

import { QuarterChart } from "@/components/npl/charts"
import { EconometricModels } from "@/components/npl/econometric-models"
import { HowToRead } from "@/components/npl/how-to-read"
import { buttonVariants } from "@/components/ui/button"
import { loadSnapshot } from "@/lib/npl/load"
import { localizedMetadata, requestLanguage } from "@/lib/npl/locale"
import {
  formatNumber,
  formatStamp,
  methodModel,
  overviewModel,
  pageHref,
  type Lang,
  type Ownership,
} from "@/lib/npl/view"
import { cn } from "cn"

export const instant = false

export async function generateMetadata(): Promise<Metadata> {
  const lang = await requestLanguage()
  return lang === "vi"
    ? localizedMetadata(lang, "Phương pháp", "Câu kết luận, kiểm tra độ vững, các mô hình, lược đồ và nguồn của bản NPL.")
    : localizedMetadata(lang, "Method", "Review the NPL study conclusions, robustness checks, models, data schema, and sources.")
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

function sourceTitle(name: string, vi: boolean): string {
  const text = name.toLowerCase()
  if (text.includes("fiin")) {
    return vi
      ? "FiinQuant (FiinGroup), báo cáo tài chính hợp nhất"
      : "FiinQuant (FiinGroup), group financial statements"
  }
  if (text.includes("deadline") || text.includes("article") || text.includes("lịch")) {
    return vi ? "Lịch hạn công bố báo cáo" : "Disclosure deadline calendar"
  }
  if (text.includes("world") || text.includes("fb.ast")) {
    return vi ? "Chỉ số Ngân hàng Thế giới" : "World Bank indicators"
  }
  if (text.includes("sbv") || text.includes("nhnn") || text.includes("hệ thống")) {
    return vi ? "Số liệu hệ thống Ngân hàng Nhà nước" : "State Bank system figures"
  }
  if (text.includes("techcombank")) {
    return vi ? "Báo cáo tài chính Techcombank" : "Techcombank financial statements"
  }
  if (text.includes("legal") || text.includes("văn bản")) {
    return vi ? "Sổ văn bản pháp luật" : "Legal register"
  }
  if (text.includes("filing") || text.includes("công bố")) {
    return vi ? "Ngày công bố báo cáo" : "Filing dates"
  }
  if (text.includes("price") || text.includes("giá") || text.includes("valuation") || text.includes("foreign")) {
    return vi ? "Giá và giao dịch trên thị trường" : "Market prices and trading"
  }
  return vi ? "Nguồn số liệu" : "Data source"
}

function sourceSentence(
  source: { name: string; retrieved_at: string; rows: number },
  lang: Lang,
): string {
  const vi = lang === "vi"
  const title = sourceTitle(source.name, vi)
  const rows = formatNumber(source.rows, lang, 0)
  const when = formatStamp(source.retrieved_at)
  return vi ? `${title}. ${rows} dòng, lấy lúc ${when}.` : `${title}. ${rows} rows, retrieved ${when}.`
}

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const [query, lang] = await Promise.all([searchParams, requestLanguage()])
  const ownership = ownershipOf(one(query.own))
  const dropEarly = one(query.drop) === "1"
  const snapshot = await loadSnapshot()
  const selected = overviewModel(snapshot, lang, { ownership, dropEarly })
  const model = methodModel(snapshot, lang)
  const audit = snapshot.pdf_audit?.headline
  const vi = lang === "vi"
  return (
    <>
      <div className="grid gap-2">
        <h1 className="text-2xl font-semibold text-balance">{vi ? "Cách kiểm tra bằng chứng" : "How to test the evidence"}</h1>
        <p className="text-sm text-muted-foreground">
          {vi ? "So sánh các quý trong cùng ngân hàng, kiểm tra khả năng dự báo ở các quý giữ lại và ước tính biến động sau khi bỏ nhịp mùa vụ."
            : "Compare quarters within the same bank, test the forecasts on held-out quarters, and estimate how NPL moves after seasonal adjustment."}
        </p>
      </div>
      <EconometricModels snapshot={snapshot} lang={lang} />
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Kiểm tra độ vững" : "Robustness check"}</h2>
        <div className="flex flex-wrap items-center gap-2">
          {(["all", "state", "private"] as const).map((item) => (
            <a
              key={item}
              href={pageHref("/phuong-phap", lang, { own: item === "all" ? undefined : item, drop: dropEarly && selected.dropEnabled ? "1" : undefined })}
              className={cn(buttonVariants({ variant: ownership === item ? "secondary" : "outline", size: "sm" }), "min-h-11")}
              aria-current={ownership === item ? "true" : undefined}
            >
              {item === "all" ? (vi ? "Cả nhóm" : "All") : item === "state" ? (vi ? "Nhà nước" : "State") : (vi ? "Tư nhân" : "Private")}
            </a>
          ))}
          {selected.dropEnabled ? (
            <a
              href={pageHref("/phuong-phap", lang, { own: ownership === "all" ? undefined : ownership, drop: dropEarly ? undefined : "1" })}
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
        {selected.dropReason ? <p className="text-sm text-muted-foreground">{selected.dropReason}</p> : null}
        {dropEarly && selected.dropEnabled && ownership !== "all" ? (
          <p className="text-sm text-muted-foreground">
            {vi ? "Đang dùng mẫu bỏ 2021–2022. Mẫu đó không tách nhà nước và tư nhân." : "Showing the sample that drops 2021–2022. That sample is not split by ownership."}
          </p>
        ) : null}
        <QuarterChart bars={selected.bars} lang={lang} />
        <p className="text-sm text-muted-foreground">{selected.decision}</p>
        <HowToRead
          label={readLabel(lang)}
          sentences={vi
            ? ["Cột là mức nợ xấu quý 2, 3 và 4 khác quý 1, sau khi trừ phần riêng của từng ngân hàng.", "Râu trên cột là khoảng tin cậy 95%. Quý 1 là mốc 0."]
            : ["The bars are how Q2, Q3 and Q4 differ from Q1 after each bank's own level is removed.", "The whiskers are the 95% confidence interval. Q1 is the zero line."]}
        />
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">{vi ? "Các phân tích bổ sung" : "Supporting analyses"}</h2>
        <ul className="flex flex-col gap-3 text-sm">
          {model.models.filter((item) => item.id !== "M6").map((item) => (
            <li key={item.id} className="flex flex-col gap-1">
              <p className="font-medium">{item.name}</p>
              <p>{item.reading}</p>
              <p className="text-muted-foreground">{item.doesNotShow}</p>
            </li>
          ))}
        </ul>
        <p className="text-sm">
          <a className="underline underline-offset-4" href={pageHref("/thi-truong", lang)}>
            {vi ? "Xem phân tích phản ứng thị trường" : "See the market reaction analysis"}
          </a>
        </p>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Nguồn" : "Sources"}</h2>
        {audit && audit.comparable > 0 && <p className="text-sm">
          {vi
            ? `Đối chiếu báo cáo gốc: ${audit.matched}/${audit.comparable} dòng có thể so sánh khớp với số liệu trích xuất.`
            : `Original filing cross-check: ${audit.matched} of ${audit.comparable} comparable rows matched the extracted figures.`}
        </p>}
        <ul className="flex flex-col gap-2 text-sm">
          {snapshot.meta.sources.map((source) => (
            <li key={source.id}>{sourceSentence(source, lang)}</li>
          ))}
        </ul>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Giới hạn" : "Limitations"}</h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
          {model.limitations.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Việc dùng AI" : "AI use"}</h2>
        <p className="text-sm">{model.ai.join(" ")}</p>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Pháp lý" : "Legal"}</h2>
        {model.legal.map((item) => (
          <p key={item.ref} className="text-sm break-words"><span className="font-medium">{item.ref}. </span>{item.text}</p>
        ))}
      </section>
    </>
  )
}
