import type { Metadata } from "next"

import { KeyNumbers } from "@/components/npl/key-numbers"
import { NplHeatmap } from "@/components/npl/npl-heatmap"
import { QuarterBreakdown } from "@/components/npl/quarter-breakdown"
import { breakdownModel, heatmapModel, q4HoldoutReading } from "@/lib/npl/judge-view"
import { loadSnapshot } from "@/lib/npl/load"
import { formatNumber, langFromQuery, pageHref, SITE_TITLE, siteSubtitle } from "@/lib/npl/view"

export const instant = false

type Query = Record<string, string | string[] | undefined>

export async function generateMetadata({ searchParams }: { searchParams: Promise<Query> }): Promise<Metadata> {
  const lang = langFromQuery((await searchParams).lang)
  const { meta } = await loadSnapshot()
  return {
    title: SITE_TITLE[lang],
    description: siteSubtitle(lang, meta.n_banks, meta.period_start.slice(0, 4), meta.period_end.slice(0, 4)),
  }
}

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const query = await searchParams
  const lang = langFromQuery(query.lang)
  const snapshot = await loadSnapshot()
  const vi = lang === "vi"
  const { decomposition } = snapshot
  const heatmap = heatmapModel(snapshot, decomposition?.rows)
  const breakdown = breakdownModel(snapshot, decomposition?.rows ?? [], lang)
  const holdout = q4HoldoutReading(snapshot.decision_rule?.q4_oos, lang)
  const down = (quarter: string) => decomposition?.by_quarter.find((row) => row.quarter === quarter)?.share_falling_pct ?? null
  const benchmark = snapshot.kpis.benchmark
  const p = benchmark.p_wild_bootstrap ?? benchmark.p
  const [lo, hi] = benchmark.ci95
  const metrics = [
    { label: vi ? "Thay đổi nợ xấu, quý 4 so với quý 1" : "NPL change, Q4 versus Q1", value: benchmark.coef_pp, digits: 2, unit: vi ? " điểm %" : " pp" },
    { label: vi ? "Nợ xấu giảm ở quý 4 và quý 1" : "Share with NPL declines, Q4 and Q1", value: down("Q4"), compare: down("Q1"), digits: 1, unit: "%" },
    { label: vi ? "Cặp quý giảm rồi tăng lại" : "Quarter pairs down then back up", value: snapshot.reversal?.share_pct ?? null, digits: 1, unit: "%" },
  ]
  const steps = vi ? [
    "Tách phần do dư nợ tăng khỏi phần do số dư nợ xấu đổi.",
    "Đối chiếu nợ nhóm 2, xóa nợ và dự phòng.",
    "Xem tỷ lệ có tăng lại ở quý 1 năm sau không.",
  ] : [
    "Separate the effect of loan growth from the change in bad debt.",
    "Check group 2 loans, write-offs and provisions.",
    "See whether the ratio rises again in the next Q1.",
  ]
  return (
    <>
      <header className="flex min-w-0 flex-col gap-3 pt-3">
        <h1 className="max-w-4xl text-balance text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">
          {vi ? "Tỷ lệ nợ xấu thường đẹp hơn vào quý 4" : "Bad-debt ratios usually look better in Q4"}
        </h1>
        <p className="max-w-3xl text-pretty text-sm leading-relaxed text-muted-foreground sm:text-base">
          {vi
            ? "Dư nợ tăng và xóa nợ dồn vào cuối năm có thể kéo tỷ lệ xuống. Tỷ lệ này thường tăng trở lại vào quý 1."
            : "Year-end loan growth and concentrated write-offs can pull the ratio down. It often rises again in Q1."}
        </p>
        <KeyNumbers metrics={metrics} lang={lang} />
        <p className="text-xs text-muted-foreground">
          {lo != null && hi != null && (
            <>{vi ? "Khoảng tin cậy 95%" : "95% confidence interval"} [{formatNumber(lo, lang, 2)}, {formatNumber(hi, lang, 2)}]{" · "}</>
          )}
          n = {formatNumber(benchmark.n, lang, 0)}{p != null && ` · p = ${formatNumber(p, lang, 3)}`}
        </p>
      </header>
      <section className="flex min-w-0 flex-col gap-2" aria-labelledby="npl-map">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
          <h2 className="text-lg font-semibold" id="npl-map">
            {vi ? "Nợ xấu đổi ra sao theo từng quý?" : "How did NPL move each quarter?"}
          </h2>
          <a href="#q4-breakdown" className="text-sm font-medium underline underline-offset-4">
            {vi ? "Thử một ngân hàng" : "Try a bank"}
          </a>
        </div>
        <NplHeatmap model={heatmap} lang={lang} />
      </section>
      <section className="flex min-w-0 flex-col gap-2" aria-labelledby="q4-breakdown">
        <h2 className="text-lg font-semibold" id="q4-breakdown">
          {vi ? "Mổ xẻ một lần NPL giảm" : "Break down one NPL decline"}
        </h2>
        <QuarterBreakdown rows={breakdown} lang={lang}
          initialBank={typeof query.bank === "string" ? query.bank.toUpperCase() : undefined}
          initialYear={typeof query.year === "string" ? query.year : undefined} />
      </section>
      <section className="rounded-xl border border-border bg-muted/50 p-4" aria-labelledby="npl-steps">
        <h2 className="text-lg font-semibold" id="npl-steps">
          {vi ? "Đọc mức giảm quý 4 trong ba bước" : "Read a Q4 decline in three steps"}
        </h2>
        <ol className="mt-2 ml-5 grid list-decimal gap-2 text-sm sm:grid-cols-3 sm:gap-6">
          {steps.map((step) => <li key={step}>{step}</li>)}
        </ol>
        {holdout && (
          <div className="mt-4 max-w-4xl border-t border-border pt-3">
            <h3 className="text-sm font-semibold">{vi ? "Thử với dữ liệu chưa dùng để đặt quy tắc" : "Check on data held back from the rule"}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{holdout}</p>
          </div>
        )}
      </section>
      <footer className="flex flex-wrap justify-between gap-2 border-t border-border py-2 text-xs text-muted-foreground">
        <p>{vi ? "Nguồn" : "Source"} FiinQuant (FiinGroup), {vi ? "đến" : "through"} {snapshot.meta.period_end}</p>
        <a href={pageHref("/phuong-phap", lang)} className="underline underline-offset-4">{vi ? "Xem phương pháp" : "See the method"}</a>
      </footer>
    </>
  )
}
