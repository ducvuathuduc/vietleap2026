import type { Metadata } from "next"

import { LegalFooter } from "@/components/ratewatch/legal-footer"
import { policyModel, selectionFromParams } from "@/lib/ratewatch/decide"
import { formatPct, formatVnd } from "@/lib/ratewatch/format"
import { loadSnapshot } from "@/lib/ratewatch/load"

export const instant = false

export const metadata: Metadata = {
  title: "Chính sách",
  description: "Trần lãi suất dưới 6 tháng, hạn mức bảo hiểm tiền gửi và việc công bố lãi suất.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const snapshot = loadSnapshot()
  const selection = selectionFromParams(await searchParams, snapshot)
  const model = policyModel(snapshot)
  const vi = selection.lang === "vi"
  const lang = selection.lang
  const jump = model.stats.jump_5_6_pp_median
  const readable = model.publications.filter((item) => item.machineReadable).length
  const pct = (value: number, digits = 2) => formatPct(value, digits, lang)
  const money = (value: number) => formatVnd(value, lang)
  return (
    <>
      <h1 className="text-xl font-semibold leading-snug text-balance">
        {vi
          ? `Trần ${pct(model.ceilingPct)}%/năm. ${model.stats.at_ceiling} trên ${model.stats.quotes_1_5m} dòng kỳ 1–5 tháng đứng ở trần. ${model.stats.above} dòng cao hơn trần; công thức đếm cả dòng mâu thuẫn, và dòng mâu thuẫn không vào phép tính. Bước nhảy 5 sang 6 tháng, trung vị trên ${model.stats.n_banks_graded} ngân hàng mà cả hai kỳ không mâu thuẫn, là ${jump === null ? "chưa đủ cặp" : `${pct(jump)} điểm phần trăm`}.`
          : `Ceiling ${pct(model.ceilingPct)}%/year. ${model.stats.at_ceiling} of ${model.stats.quotes_1_5m} quotes at 1–5 months sit on it. ${model.stats.above} quotes are above the ceiling; the count includes contested rows, and contested rows do not enter a calculation. The median 5-to-6-month jump across ${model.stats.n_banks_graded} banks whose both legs are not contested is ${jump === null ? "not available" : `${pct(jump)} percentage points`}.`}
      </h1>
      <p className="text-sm text-muted-foreground">
        {model.ceilingRef}. {vi ? "Mỗi ngân hàng lấy một kênh, online nếu có." : "One channel per bank, online when that sheet exists."}
      </p>
      <section className="grid gap-3 sm:grid-cols-3">
        <article className="rounded-xl bg-card p-3 ring-1 ring-foreground/10">
          <h2 className="text-sm font-medium">{vi ? `${pct(model.depositorsPct)}% người gửi được phủ hết. Nguồn: ${model.source}.` : `${pct(model.depositorsPct)}% of depositors are fully covered. Source: ${model.source}.`}</h2>
          <p className="text-lg font-semibold">{pct(model.depositorsPct)}%</p>
        </article>
        <article className="rounded-xl bg-card p-3 ring-1 ring-foreground/10">
          <h2 className="text-sm font-medium">{vi ? `${pct(model.valuePct)}% giá trị được phủ hết. Nguồn: ${model.source}.` : `${pct(model.valuePct)}% of value is fully covered. Source: ${model.source}.`}</h2>
          <p className="text-lg font-semibold">{pct(model.valuePct)}%</p>
        </article>
        <article className="rounded-xl bg-card p-3 ring-1 ring-foreground/10">
          <h2 className="text-sm font-medium">{vi ? `Phí ${pct(model.premiumPct)}%/năm. ${model.premiumRef}.` : `Premium ${pct(model.premiumPct)}%/year. ${model.premiumRef}.`}</h2>
          <p className="text-lg font-semibold">{pct(model.premiumPct)}%{vi ? "/năm" : "/year"}</p>
          <p className="text-xs text-muted-foreground">{model.premiumRef}</p>
        </article>
      </section>
      <p className="text-sm">{model.basis}</p>
      <p className="text-xs break-words">
        <a href={model.source} className="underline underline-offset-4" rel="noreferrer">{model.source}</a>
      </p>
      <p className="text-sm">
        {vi
          ? `Hạn mức đang áp dụng là ${money(model.capVnd)} gốc và lãi tại một tổ chức.`
          : `The cap in force is ${money(model.capVnd)} of principal and interest at one institution.`}
      </p>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">
          {vi
            ? `Không ngân hàng nào trong bản này công bố lãi suất dạng file máy đọc (${readable}/${model.publications.length}).`
            : `No bank in this edition publishes rates as a machine-readable file (${readable}/${model.publications.length}).`}
        </h2>
        <ul className="flex flex-col gap-1 text-sm">
          {model.publications.map((item) => (
            <li key={item.code} className="break-words">
              {item.name}: {item.machineReadable ? (vi ? "có file" : "file") : (vi ? "trang HTML hoặc PDF" : "HTML or PDF page")}
              {" · "}
              <a href={item.url} className="underline underline-offset-4" rel="noreferrer">{item.url}</a>
            </li>
          ))}
        </ul>
      </section>
      <section className="flex flex-col gap-2 text-sm">
        <h2 className="text-base font-semibold">{vi ? `4 việc đọc được từ trần ${pct(model.ceilingPct)}% và hạn mức ${money(model.capVnd)}. ${model.ceilingRef}.` : `4 readings from the ${pct(model.ceilingPct)}% ceiling and the ${money(model.capVnd)} cap. ${model.ceilingRef}.`}</h2>
        <ul className="flex list-disc flex-col gap-2 pl-5">
          <li>
            {vi
              ? "Kỳ dưới 6 tháng dính trần. Kỳ đúng 6 tháng là chỗ ngân hàng tự đặt lãi suất."
              : "Terms under 6 months hit the ceiling. A term of exactly 6 months is where the bank sets the rate."}
          </li>
          <li>
            {vi
              ? "Phần gốc và lãi vượt 350 triệu tại một ngân hàng không nằm trong hạn mức Thông tư 05."
              : "Principal plus interest above 350 million at one bank is outside the Circular 05 cap."}
          </li>
          <li>
            {vi
              ? "Phí 0,15%/năm là đồng hạng, tổ chức nộp, không phải giá theo nợ xấu của từng ngân hàng."
              : "The 0.15%/year premium is flat, paid by the institution, not priced off that bank's problem loans."}
          </li>
          <li>
            {vi
              ? "Vì không có file máy đọc, mỗi con số trên màn hình phải kèm ngày biểu và liên kết trang đã đọc."
              : "With no machine-readable file, every figure on the screen keeps its sheet date and the page that was read."}
          </li>
        </ul>
      </section>
      <LegalFooter snapshot={snapshot} lang={selection.lang} />
    </>
  )
}
