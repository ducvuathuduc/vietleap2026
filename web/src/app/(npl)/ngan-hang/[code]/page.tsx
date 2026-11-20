import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { BankCompareChart, BankLines } from "@/components/npl/charts"
import { Glossary } from "@/components/npl/glossary"
import { HowToRead } from "@/components/npl/how-to-read"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { loadSnapshot } from "@/lib/npl/load"
import { bankModel, formatNumber, langFromQuery, pageHref } from "@/lib/npl/view"

export const instant = false

type Query = Record<string, string | string[] | undefined>

export async function generateMetadata({ params }: { params: Promise<{ code: string }> }): Promise<Metadata> {
  const { code } = await params
  return { title: code.toUpperCase() }
}

export default async function Page({ params, searchParams }: { params: Promise<{ code: string }>; searchParams: Promise<Query> }) {
  const { code } = await params
  const query = await searchParams
  const lang = langFromQuery(query.lang)
  const model = bankModel(await loadSnapshot(), code, lang)
  if (!model) notFound()
  const vi = lang === "vi"
  const adjusted = model.adjusted == null
    ? (vi
      ? "Bản số liệu không có phần thay đổi sau khi trừ nhịp chung của quý."
      : "These figures do not include the change after the usual quarter pattern is removed.")
    : (vi
      ? (model.latestPeriod
        ? `Ở ${model.latestPeriod}, phần thay đổi sau khi trừ nhịp chung của quý là ${formatNumber(model.adjusted, lang, 3)} điểm phần trăm.`
        : `Phần thay đổi sau khi trừ nhịp chung của quý là ${formatNumber(model.adjusted, lang, 3)} điểm phần trăm.`)
      : (model.latestPeriod
        ? `In ${model.latestPeriod}, the change after the usual quarter pattern is removed is ${formatNumber(model.adjusted, lang, 3)} percentage points.`
        : `The change after the usual quarter pattern is removed is ${formatNumber(model.adjusted, lang, 3)} percentage points.`))
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">{model.headline}</h1>
      <p className="text-sm text-muted-foreground">{model.reminder}</p>
      <p className="text-sm text-muted-foreground">
        {model.ownership === "state" ? (vi ? "Nhà nước" : "State") : (vi ? "Tư nhân" : "Private")}
      </p>
      <p className="text-sm">
        <a className="underline underline-offset-4" href={pageHref("/ngan-hang", lang)}>{vi ? "Về danh sách" : "Back to the list"}</a>
      </p>
      <Glossary lang={lang} />
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Trung bình theo quý của ngân hàng này, chấm là hệ số cả nhóm" : "This bank's quarterly mean, dots are the panel coefficients"}</h2>
        <BankCompareChart rows={model.chart} lang={lang} />
        <HowToRead
          label={vi ? "Cách đọc" : "How to read"}
          sentences={vi
            ? ["Cột là thay đổi trung bình của ngân hàng này theo quý, chấm là hệ số cả nhóm.", "Vạch 0 là không đổi. Chấm nằm ngoài cột khi ngân hàng này lệch khỏi cả nhóm."]
            : ["The bars are this bank's average change by quarter, and the dots are the panel coefficients.", "The zero line is no change. A dot sits off its bar when this bank differs from the panel."]}
        />
      </section>
      {model.lines ? (
        <section className="flex min-w-0 flex-col gap-2">
          <h2 className="text-base font-semibold">{vi ? "NPL, bao phủ, LDR, NIM và tăng trưởng dư nợ" : "NPL, coverage, LDR, NIM and loan growth"}</h2>
          <BankLines lang={lang} rows={model.lines} />
          <p className="text-sm text-muted-foreground">{model.attribution}</p>
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">
          {vi ? "Chuỗi NPL, bao phủ, LDR, NIM và tăng trưởng dư nợ gốc của từng ngân hàng chưa được phép công bố. Trang này chỉ hiện số đã tính." : "Per-bank raw NPL, coverage, LDR, NIM and loan-growth series are not cleared for publication. This page shows derived figures only."}
        </p>
      )}
      {model.lines ? null : (
        <HowToRead
          label={vi ? "Cách đọc" : "How to read"}
          sentences={vi
            ? ["Cột là thay đổi trung bình của ngân hàng này theo quý, chấm là hệ số cả nhóm.", "Chuỗi NPL, bao phủ, LDR, NIM và tăng trưởng dư nợ theo quý chưa được đưa ra trang này."]
            : ["The bars are this bank's average change by quarter, and the dots are the panel coefficients.", "The quarterly NPL, coverage, LDR, NIM and loan-growth lines are not on this page."]}
        />
      )}
      <p>{adjusted}</p>
      <section className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{vi ? "Quý kế" : "Next quarter"}</h2>
        {model.forecast ? (
          <>
            <p>
              {vi
                ? `Quý kế ${model.forecast.period}, nợ xấu ${formatNumber(model.forecast.npl, lang, 2)}%, dải từ ${formatNumber(model.forecast.lo, lang, 2)}% đến ${formatNumber(model.forecast.hi, lang, 2)}%.`
                : `Next quarter ${model.forecast.period}, NPL ${formatNumber(model.forecast.npl, lang, 2)}%, band from ${formatNumber(model.forecast.lo, lang, 2)}% to ${formatNumber(model.forecast.hi, lang, 2)}%.`}
            </p>
            <p>{vi ? "Đây là phép tính, không phải lời hứa." : "This is a calculation, not a promise."}</p>
            <p className="text-sm text-muted-foreground">
              {vi
                ? `Sai số mô hình ${formatNumber(model.mae.model, lang, 2)} điểm phần trăm. Sai số nếu lấy quý trước ${formatNumber(model.mae.lastValue, lang, 2)}. Sai số nếu lấy cùng quý năm trước ${formatNumber(model.mae.seasonalNaive, lang, 2)}.`
                : `Model error ${formatNumber(model.mae.model, lang, 2)} percentage points. Error if you repeat last quarter ${formatNumber(model.mae.lastValue, lang, 2)}. Error if you repeat the same quarter a year earlier ${formatNumber(model.mae.seasonalNaive, lang, 2)}.`}
            </p>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">{vi ? "Bản số liệu không có dự báo quý kế cho ngân hàng này." : "These figures have no next-quarter forecast for this bank."}</p>
        )}
      </section>
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Từng cặp năm" : "Each year-pair"}</h2>
        <div className="w-full min-w-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{vi ? "Năm quý 4" : "Q4 year"}</TableHead>
                <TableHead>{vi ? "Thay đổi quý 4" : "Q4 change"}</TableHead>
                <TableHead>{vi ? "Quý 1 sau" : "Next Q1"}</TableHead>
                <TableHead>{vi ? "Đảo chiều" : "Reversed"}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {model.pairs.map((row) => (
                <TableRow key={row.year}>
                  <TableCell className="tabular-nums">{row.year}</TableCell>
                  <TableCell className="tabular-nums">{row.q4_pp == null ? "" : formatNumber(row.q4_pp, lang)}</TableCell>
                  <TableCell className="tabular-nums">{row.q1_pp == null ? "" : formatNumber(row.q1_pp, lang)}</TableCell>
                  <TableCell>{row.reversed ? (vi ? "Có" : "Yes") : (vi ? "Không" : "No")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Tín hiệu" : "Signals"}</h2>
        {model.signals.length ? (
          <ul className="flex flex-col gap-1 text-sm">
            {model.signals.map((signal) => (
              <li key={`${signal.id}-${signal.period}`}>
                <span className="tabular-nums">{signal.period}</span> {signal.text}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">{vi ? "Bản số liệu không có tín hiệu cho ngân hàng này." : "These figures have no signal for this bank."}</p>
        )}
      </section>
    </>
  )
}
