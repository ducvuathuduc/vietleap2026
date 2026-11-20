import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { BankCompareChart, BankLines } from "@/components/npl/charts"
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
  const model = bankModel(loadSnapshot(), code, lang)
  if (!model) notFound()
  const vi = lang === "vi"
  return (
    <>
      <p className="text-sm text-muted-foreground">
        {vi ? "Cả nhóm: " : "Panel: "}
        {model.reminder}
      </p>
      <h1 className="text-xl font-semibold text-balance">{model.headline}</h1>
      <p className="text-sm text-muted-foreground">
        {model.ownership === "state" ? (vi ? "Nhà nước" : "State") : (vi ? "Tư nhân" : "Private")}
        {" · "}
        <a className="underline underline-offset-4" href={pageHref("/ngan-hang", lang)}>{vi ? "Về danh sách" : "Back to the list"}</a>
      </p>
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Trung bình theo quý của mã này, chấm là hệ số cả nhóm" : "This bank's quarterly mean, dots are the panel coefficients"}</h2>
        <BankCompareChart rows={model.chart} lang={lang} />
      </section>
      <section className="grid gap-3 sm:grid-cols-3">
        <article className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
          <h2 className="text-sm font-medium">{vi ? "Sau hiệu ứng quý" : "After the quarter effect"}</h2>
          <p className="mt-2 text-lg font-semibold tabular-nums">{model.adjusted == null ? "—" : `${formatNumber(model.adjusted, lang)} ${vi ? "điểm phần trăm" : "pp"}`}</p>
          <p className="text-sm text-muted-foreground">{model.latestPeriod ?? (vi ? "Chưa có quý gần nhất." : "No latest quarter.")}</p>
        </article>
        <article className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
          <h2 className="text-sm font-medium">{vi ? "Dự báo quý kế" : "Next-quarter forecast"}</h2>
          {model.forecast ? (
            <>
              <p className="mt-2 text-lg font-semibold tabular-nums">{formatNumber(model.forecast.npl, lang, 2)}%</p>
              <p className="text-sm text-muted-foreground">
                {model.forecast.period}: {formatNumber(model.forecast.lo, lang, 2)}% – {formatNumber(model.forecast.hi, lang, 2)}%
                {vi ? " (khoảng 80%)" : " (80% band)"}
              </p>
            </>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">{vi ? "Bản chụp không có dự báo quý kế cho mã này." : "This snapshot has no next-quarter forecast for this bank."}</p>
          )}
        </article>
        <article className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
          <h2 className="text-sm font-medium">{vi ? "Sai số kiểm định, cả nhóm" : "Backtest error, panel"}</h2>
          <p className="mt-2 text-sm">
            {vi
              ? `MAE mô hình ${formatNumber(model.mae.model, lang, 2)} điểm phần trăm, mức quý trước ${formatNumber(model.mae.lastValue, lang, 2)}, cùng quý năm trước ${formatNumber(model.mae.seasonalNaive, lang, 2)}.`
              : `Model MAE ${formatNumber(model.mae.model, lang, 2)} pp, last value ${formatNumber(model.mae.lastValue, lang, 2)}, same quarter last year ${formatNumber(model.mae.seasonalNaive, lang, 2)}.`}
          </p>
        </article>
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
              <li key={`${signal.id}-${signal.period}`}>{signal.period} · {signal.text}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">{vi ? "Bản chụp không có tín hiệu cho mã này." : "This snapshot has no signal for this bank."}</p>
        )}
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
    </>
  )
}
