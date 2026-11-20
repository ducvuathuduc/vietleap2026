"use client"

import { useState, type ReactNode } from "react"
import { ArrowDownIcon, ArrowUpDownIcon, ArrowUpIcon } from "lucide-react"

import { MarketChart, QuarterChart } from "@/components/npl/charts"
import { pageHref, type Lang } from "@/lib/npl/view"
import type { ScreeningRow, SnapshotAnswers } from "@/lib/npl/agent/snapshot-answers"
import { BankCanvasChart, CompareCanvasChart, ForecastCanvasChart } from "./canvas-charts"
import { formatValue, openPage, overviewFigures, points, readResult } from "./canvas-data"

export type ListedTool = { id: string; name: string; input: unknown; output: unknown }
type Result = NonNullable<ReturnType<typeof readResult>>
type SortKey = "bank" | "npl_pp" | "group2_pp" | "writeoff_pct" | "coverage_pp" | "flags"

const FLAG_LABELS = {
  S1: { vi: "Nhóm 2", en: "Group 2" },
  S2: { vi: "Xóa nợ", en: "Write-offs" },
  S3: { vi: "Bao phủ", en: "Coverage" },
  S4: { vi: "Mùa vụ", en: "Seasonal" },
}

function bankLink(bank: string, period: string, waterfall: boolean, lang: Lang) {
  return waterfall
    ? `${pageHref("/", lang, { bank, year: period.slice(0, 4) })}#q4-breakdown`
    : pageHref(`/ngan-hang/${encodeURIComponent(bank)}`, lang)
}

function BanksTable({ rows, period, lang }: { rows: ScreeningRow[]; period: string; lang: Lang }) {
  const vi = lang === "vi"
  const [sort, setSort] = useState<{ key: SortKey; descending: boolean }>({ key: "bank", descending: false })
  const headings: [SortKey, string][] = [
    ["bank", vi ? "Mã" : "Bank"],
    ["npl_pp", vi ? "Nợ xấu" : "NPL"],
    ["group2_pp", vi ? "Nhóm 2" : "Group 2"],
    ["writeoff_pct", vi ? "Xóa nợ %" : "Write-offs %"],
    ["coverage_pp", vi ? "Bao phủ" : "Coverage"],
    ["flags", vi ? "Cờ vàng" : "Flags"],
  ]
  const sorted = [...rows].sort((left, right) => {
    const a = sort.key === "flags" ? left.flags.length : left[sort.key]
    const b = sort.key === "flags" ? right.flags.length : right[sort.key]
    if (a == null || b == null) return a === b ? left.bank.localeCompare(right.bank) : a == null ? 1 : -1
    const difference = typeof a === "string" ? a.localeCompare(String(b)) : a - Number(b)
    return difference ? (sort.descending ? -difference : difference) : left.bank.localeCompare(right.bank)
  })
  if (!rows.length) return null
  const cell = (value: number | null, digits = 2) => value == null
    ? <span aria-label={vi ? "Thiếu dữ liệu" : "Data unavailable"}>—</span>
    : formatValue(value, lang, "", digits)

  return (
    <>
      <div className="overflow-x-auto">
        <table aria-label={vi ? "Ngân hàng phù hợp" : "Matching banks"} className="w-full border-collapse text-left text-[11px] leading-snug">
          <thead className="bg-muted/60">
            <tr>
              {headings.map(([key, label]) => {
                const active = sort.key === key
                const Indicator = active ? sort.descending ? ArrowDownIcon : ArrowUpIcon : ArrowUpDownIcon
                return (
                  <th scope="col" key={key} className="px-1 py-1.5 font-medium"
                    aria-sort={active ? sort.descending ? "descending" : "ascending" : undefined}>
                    <button type="button" onClick={() => setSort({ key, descending: active && !sort.descending })}
                      className="inline-flex min-h-6 items-center gap-0.5 text-left underline-offset-2 hover:underline focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-ring">
                      {label}<Indicator className="size-2.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                    </button>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr key={row.bank} className="border-t border-border align-top">
                <th scope="row" className="px-1 py-2 font-semibold">
                  <a className="underline underline-offset-2" href={bankLink(row.bank, period, row.waterfall, lang)}>{row.bank}</a>
                </th>
                <td className="px-1 py-2 whitespace-nowrap tabular-nums">{cell(row.npl_pp)}</td>
                <td className="px-1 py-2 whitespace-nowrap tabular-nums">{cell(row.group2_pp, row.group2_pp != null && Math.abs(row.group2_pp) < .01 ? 3 : 2)}</td>
                <td className="px-1 py-2 whitespace-nowrap tabular-nums">{cell(row.writeoff_pct)}</td>
                <td className="px-1 py-2 whitespace-nowrap tabular-nums">{cell(row.coverage_pp)}</td>
                <td className="px-1 py-2 text-[10px]">{row.flags.map((flag) => FLAG_LABELS[flag][lang]).join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="px-2 pt-1.5 text-[11px] text-muted-foreground">
        {vi ? "Thay đổi tính bằng điểm %. Xóa nợ được ước tính từ dự phòng sử dụng trên dư nợ."
          : "Changes are in pp. Write-offs use provisions used as a share of loans."}
      </p>
    </>
  )
}

function Bars({ rows, unit, lang }: {
  rows: { label: string; value: number | null }[]
  unit: string
  lang: Lang
}) {
  const max = Math.max(...rows.map((row) => Math.abs(row.value ?? 0)), .01)
  return (
    <dl className="grid gap-2 p-2 text-xs">
      {rows.map(({ label, value }) => (
        <div key={label} className="grid grid-cols-[minmax(0,1fr)_minmax(2rem,0.8fr)_auto] items-center gap-2">
          <dt>{label}</dt>
          <dd aria-hidden="true" className="h-2 rounded-sm bg-muted">
            {value != null && <div className="h-2 rounded-sm bg-chart-3" style={{ width: `${Math.abs(value) / max * 100}%` }} />}
          </dd>
          <dd className="text-right font-semibold whitespace-nowrap tabular-nums">{formatValue(value, lang, unit)}</dd>
        </div>
      ))}
    </dl>
  )
}

type StudyResult = { [K in keyof SnapshotAnswers]: { name: K; output: SnapshotAnswers[K] } }[keyof SnapshotAnswers]

function readStudy(tool: ListedTool): StudyResult | null {
  if (!["screen_declines", "q4_drivers", "q1_rebound", "quarter_breakdown", "coverage_effect"].includes(tool.name)) return null
  if (!tool.output || typeof tool.output !== "object" || !("citations" in tool.output)) return null
  return { name: tool.name, output: tool.output } as StudyResult
}

function studyBody(result: StudyResult, lang: Lang): { body: ReactNode; href?: string } {
  const vi = lang === "vi"
  switch (result.name) {
    case "screen_declines":
      return { body: <BanksTable rows={result.output.rows} period={result.output.data_period} lang={lang} /> }
    case "q4_drivers": {
      const { loan_growth_part_pp, bad_debt_part_pp } = result.output
      const rows = [
        { label: vi ? "Do dư nợ" : "Loan growth", value: loan_growth_part_pp },
        { label: vi ? "Do số dư nợ xấu" : "Bad-debt change", value: bad_debt_part_pp },
      ]
      return { body: <Bars rows={rows} lang={lang} unit={points(lang)} />, href: pageHref("/", lang) + "#q4-breakdown" }
    }
    case "q1_rebound": {
      const { rates } = result.output
      if (!rates) return { body: null }
      return { body: <Bars lang={lang} unit="%" rows={[
        { label: vi ? "Sau mọi quý 4" : "After any Q4", value: rates.any_q4.share_pct },
        { label: vi ? "Sau quý 4 giảm" : "After Q4 fell", value: rates.q4_fell.share_pct },
        { label: vi ? "Sau quý 4 không giảm" : "After Q4 did not fall", value: rates.q4_not_fell.share_pct },
      ]} />, href: pageHref("/", lang) + "#npl-steps" }
    }
    case "quarter_breakdown": {
      const { bank, data_period, change_pp, q3_pct, q4_pct, q1_pct, loan_growth_part_pp, bad_debt_part_pp } = result.output
      const href = bankLink(bank, data_period, change_pp != null && change_pp < 0 && loan_growth_part_pp != null &&
        bad_debt_part_pp != null && q4_pct != null, lang)
      return { href, body: q4_pct == null ? null : <Bars lang={lang} unit="%" rows={[
        { label: "Q3", value: q3_pct }, { label: "Q4", value: q4_pct },
        { label: vi ? "Q1 năm sau" : "Next Q1", value: q1_pct },
      ]} /> }
    }
    case "coverage_effect": {
      const e = result.output.effect
      return { body: e && <QuarterChart lang={lang} bars={[{
        quarter: 4, coef: e.coef_pp, lo: e.ci95[0] ?? null, hi: e.ci95[1] ?? null,
      }]} /> }
    }
  }
}

function resultBody(result: Result, lang: Lang): ReactNode {
  const vi = lang === "vi"
  switch (result.name) {
    case "overview":
      return <dl className="grid gap-1.5 p-2 text-xs">{overviewFigures(result.output, lang).map(({ label, value }) => (
        <div className="flex items-baseline justify-between gap-2" key={label}>
          <dt>{label}</dt><dd className="font-semibold tabular-nums">{value}</dd>
        </div>
      ))}</dl>
    case "quarter_effects":
      return <QuarterChart lang={lang} bars={result.output.effects.map((row) => ({
        quarter: row.quarter, coef: row.coef_pp, lo: row.ci95[0] ?? null, hi: row.ci95[1] ?? null,
      }))} />
    case "bank_profile":
      return result.output.bank.series?.length ? <BankCanvasChart lang={lang} rows={result.output.bank.series} /> : null
    case "compare_banks":
      return result.output.rows.length ? <CompareCanvasChart lang={lang} rows={result.output.rows} /> : null
    case "decoder":
    case "adjusted_change":
      return <Bars lang={lang} unit={points(lang)} rows={[
        { label: vi ? "Thay đổi công bố" : "Reported change", value: result.output.row.d_npl_pp },
        { label: vi ? "Sau điều chỉnh mùa vụ" : "After seasonal adjustment", value: result.output.row.adjusted_change_pp },
      ]} />
    case "forecast":
      return <ForecastCanvasChart lang={lang} output={result.output} />
    case "market_reaction":
      return result.output.car_all.length ? <MarketChart lang={lang} rows={result.output.car_all.map((row) => ({
        day: row.day, all: row.mean_car_pct, allLo: row.ci95?.[0] ?? null, allHi: row.ci95?.[1] ?? null,
        q4: null, q4Lo: null, q4Hi: null,
      }))} /> : null
    default:
      return null
  }
}

export function AnswerEvidence({ tools, lang }: { tools: ListedTool[]; lang: Lang }) {
  const vi = lang === "vi"
  const study = tools.map(readStudy).find((result) => result != null)
  const matched = tools.flatMap((tool) => {
    const result = readResult(tool.name, tool.output)
    return result ? [{ tool, result }] : []
  })
  const chosen = matched.find(({ result }) => !["method", "glossary", "limitations"].includes(result.name)) ?? matched[0]
  if (!study && !chosen) return null

  const figure = study ? studyBody(study, lang) : null
  const legacy = chosen?.result
  const body = figure ? figure.body : legacy ? resultBody(legacy, lang) : null
  const period = study?.output.data_period ?? legacy?.output.data_period
  const methodological = !study && legacy && ["method", "glossary", "limitations"].includes(legacy.name)
  const href = figure?.href ?? (!study && chosen ? openPage(chosen.tool.name, chosen.tool.input, lang) : null)
  const source = methodological ? vi ? "Phương pháp nghiên cứu" : "Study methodology" : "FiinQuant (FiinGroup)"

  return (
    <figure aria-label={vi ? "Số liệu đối chiếu" : "Answer evidence"} className="min-w-0 overflow-hidden rounded-lg border border-border">
      {body}
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-2 py-2 text-[11px] text-muted-foreground">
        <span>{vi ? "Nguồn" : "Source"} {source}{period ? ` (${period})` : ""}</span>
        {href && <a href={href} className="font-medium text-foreground underline underline-offset-2">{vi ? "Xem trên trang" : "See on the page"}</a>}
      </figcaption>
    </figure>
  )
}
