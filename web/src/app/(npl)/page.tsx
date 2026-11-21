import type { Metadata } from "next"

import { KeyNumbers } from "@/components/npl/key-numbers"
import { CreditCheck } from "@/components/npl/credit-check"
import { LoanDefinitions } from "@/components/npl/loan-definitions"
import { NplHeatmap } from "@/components/npl/npl-heatmap"
import { QuarterBreakdown } from "@/components/npl/quarter-breakdown"
import { breakdownModel, heatmapModel } from "@/lib/npl/judge-view"
import { loadSnapshot } from "@/lib/npl/load"
import { localizedMetadata, requestLanguage } from "@/lib/npl/locale"
import { RESEARCH_QUESTION } from "@/lib/npl/research-view"
import { pageHref, SITE_TITLE, siteSubtitle } from "@/lib/npl/view"

export const instant = false

type Query = Record<string, string | string[] | undefined>

export async function generateMetadata(): Promise<Metadata> {
  const [{ meta }, lang] = await Promise.all([loadSnapshot(), requestLanguage()])
  return localizedMetadata(lang, SITE_TITLE[lang], siteSubtitle(lang, meta.n_banks, meta.period_start.slice(0, 4), meta.period_end.slice(0, 4)))
}

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const [query, lang, snapshot] = await Promise.all([searchParams, requestLanguage(), loadSnapshot()])
  const vi = lang === "vi"
  const { decomposition } = snapshot
  const heatmap = heatmapModel(snapshot, decomposition?.rows)
  const breakdown = breakdownModel(snapshot, decomposition?.rows ?? [], lang)
  const codes = snapshot.banks.map(({ code }) => code)
  const requestedBank = typeof query.bank === "string" ? query.bank.toUpperCase() : ""
  const bank = codes.includes(requestedBank) ? requestedBank : codes.includes("MBB") ? "MBB" : codes[0] ?? ""
  const requestedPeriod = typeof query.period === "string" ? query.period.toUpperCase()
    : typeof query.year === "string" ? `${query.year}Q4` : "2025Q4"
  const period = heatmap.periods.includes(requestedPeriod) ? requestedPeriod : snapshot.meta.period_end
  const benchmark = snapshot.kpis.benchmark
  const disagreement = snapshot.scorecard?.disagreement.share
  const adjusted = snapshot.context?.seasonal_adjustment?.counts.seasonal_only_pct ?? null
  const metrics = [
    { label: vi ? "Thay đổi nợ xấu, quý 4 so với quý 1" : "NPL change, Q4 versus Q1", value: benchmark.coef_pp, digits: 2, unit: vi ? " điểm %" : " pp" },
    { label: vi ? "Lần nợ xấu giảm mà chất lượng tổng hợp xấu đi" : "NPL declines with worsening composite quality", value: disagreement == null ? null : disagreement * 100, digits: 1, unit: "%" },
    { label: vi ? "Lần giảm quý 4 có thể điều chỉnh và không còn giảm" : "Adjustable Q4 declines that disappeared", value: adjusted, digits: 1, unit: "%" },
  ]
  return (
    <>
      <header className="flex min-w-0 flex-col gap-3 pt-3">
        <h1 className="max-w-5xl text-balance text-[1.65rem] leading-tight font-semibold tracking-tight sm:text-4xl">
          {RESEARCH_QUESTION[lang]}
        </h1>
        <p className="max-w-3xl text-pretty text-sm leading-relaxed text-muted-foreground sm:text-base">
          {vi
            ? "Dư nợ tăng và xóa nợ dồn vào quý 4 có thể kéo tỷ lệ nợ xấu xuống, nên cần xem năm bằng chứng trước khi kết luận chất lượng tín dụng đã cải thiện."
            : "Year-end lending growth and concentrated write-offs can lower the NPL ratio, so check five pieces of evidence before concluding that credit quality improved."}
        </p>
        <KeyNumbers metrics={metrics} lang={lang} />
      </header>
      <CreditCheck snapshot={snapshot} bank={bank} period={period} lang={lang} />
      <LoanDefinitions lang={lang} />
      <section className="flex min-w-0 flex-col gap-2" aria-labelledby="npl-map">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
          <h2 className="text-lg font-semibold" id="npl-map">
            {vi ? "Nợ xấu đổi ra sao theo từng quý?" : "How did NPL move each quarter?"}
          </h2>
          <a href="#q4-breakdown" className="text-sm font-medium underline underline-offset-4">
            {vi ? "Thử một ngân hàng" : "Try a bank"}
          </a>
        </div>
        <p className="text-sm text-muted-foreground">
          {vi ? "Mỗi ô là mức thay đổi tỷ lệ trong một quý. Viền đậm đánh dấu quý 4."
            : "Each cell shows one quarter’s change. Dark borders mark Q4."}
        </p>
        <NplHeatmap model={heatmap} lang={lang} />
      </section>
      <section className="flex min-w-0 flex-col gap-2" aria-labelledby="q4-breakdown">
        <h2 className="text-lg font-semibold" id="q4-breakdown">
          {vi ? "Mổ xẻ một lần NPL giảm" : "Break down one NPL decline"}
        </h2>
        <p className="text-sm text-muted-foreground">
          {vi ? "Đọc từ quý 3 qua phần do dư nợ và do số dư nợ xấu đến tỷ lệ quý 4, rồi xem tiếp quý 1."
            : "Read from Q3 through the loan and bad-debt effects to Q4, then check the following Q1."}
        </p>
        <QuarterBreakdown rows={breakdown} lang={lang}
          initialBank={bank} initialYear={period.slice(0, 4)} />
      </section>
      <footer className="flex flex-wrap justify-between gap-2 border-t border-border py-2 text-xs text-muted-foreground">
        <p>{vi ? "Nguồn" : "Source"} FiinQuant (FiinGroup), {vi ? "đến" : "through"} {snapshot.meta.period_end}</p>
        <a href={pageHref("/phuong-phap", lang)} className="underline underline-offset-4">{vi ? "Xem phương pháp" : "See the method"}</a>
      </footer>
    </>
  )
}
