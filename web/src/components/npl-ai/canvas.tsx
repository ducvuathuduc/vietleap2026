"use client"

import { useId, useState } from "react"
import { ArrowDownIcon, ArrowUpDownIcon, ArrowUpIcon } from "lucide-react"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { bankCheck } from "@/lib/npl/research-view"
import { pageHref, type Lang } from "@/lib/npl/view"
import {
  BankCanvasChart, CompareCanvasChart, ForecastCanvasChart, MarketCanvasChart, MetricBarsChart, QuarterNplChart,
} from "./canvas-charts"
import {
  bankCanvasMode, comparisonHistory, findAnswerCanvas, formatValue, hasBankChecks, hasComparisonHistory, openPage, overviewFigures, points,
  sortEvidenceRows, toolLabel, type CsvCell, type ListedTool,
} from "./canvas-data"

export type { ListedTool } from "./canvas-data"
type CanvasResult = NonNullable<ReturnType<typeof findAnswerCanvas>>
type Column<T> = {
  label: string
  value: (row: T) => CsvCell
  numeric?: boolean
  digits?: number
}

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

function EvidenceTable<T>({
  label, lang, rows, columns, rowKey, rowLink, sortable = false, initialSort = 0, initialDescending = false,
}: {
  label: string
  lang: Lang
  rows: T[]
  columns: Column<T>[]
  rowKey: (row: T) => string
  rowLink?: (row: T) => string
  sortable?: boolean
  initialSort?: number
  initialDescending?: boolean
}) {
  const [sort, setSort] = useState({ column: initialSort, descending: initialDescending })
  const sorted = sortable ? sortEvidenceRows(rows, columns[sort.column].value, sort.descending, lang) : rows
  return (
    <Table aria-label={label} className="text-sm">
      <TableHeader className="bg-muted/50">
        <TableRow>
          {columns.map(({ label, numeric }, index) => {
            const active = sortable && sort.column === index
            const Indicator = active ? (sort.descending ? ArrowDownIcon : ArrowUpIcon) : ArrowUpDownIcon
            return (
              <TableHead key={label} scope="col"
                className={`h-10 px-3 text-xs normal-case tracking-normal ${numeric ? "text-right" : ""}`}
                aria-sort={active ? (sort.descending ? "descending" : "ascending") : undefined}>
                {sortable ? (
                  <button type="button" onClick={() => setSort({ column: index, descending: active && !sort.descending })}
                    className="inline-flex min-h-8 items-center gap-1.5 rounded-sm underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-ring">
                    {label}
                    <Indicator className={`size-3.5 shrink-0 ${active ? "text-foreground" : "text-muted-foreground"}`} aria-hidden="true" />
                  </button>
                ) : label}
              </TableHead>
            )
          })}
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((row) => {
          const name = columns[0].value(row)
          return (
            <TableRow key={rowKey(row)}>
              <th scope="row" className="min-w-20 px-3 py-2.5 text-left align-top font-semibold whitespace-nowrap">
                {rowLink ? <a className="underline underline-offset-2" href={rowLink(row)}>{name}</a> : name}
              </th>
              {columns.slice(1).map(({ label, value, numeric, digits }) => {
                const cell = value(row)
                const precision = digits ?? (typeof cell === "number" && cell !== 0 && Math.abs(cell) < 0.01 ? 3 : 2)
                return (
                  <TableCell key={label} className={`px-3 py-2.5 align-top ${numeric ? "text-right tabular-nums" : "whitespace-pre-line"}`}>
                    {cell == null ? <span aria-label={lang === "vi" ? "Thiếu dữ liệu" : "Data unavailable"}>—</span>
                      : typeof cell === "number" ? formatValue(cell, lang, "", precision) : cell}
                  </TableCell>
                )
              })}
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

function BankChecksTable({ evidence, label, lang }: { evidence: ReturnType<typeof bankCheck>; label: string; lang: Lang }) {
  const vi = lang === "vi"
  return (
    <EvidenceTable label={label} lang={lang} rows={evidence.checks} rowKey={(row) => row.id} columns={[
      { label: vi ? "Chỉ báo" : "Indicator", value: (row) => row.label },
      { label: vi ? "Giá trị" : "Value", value: (row) => row.value },
      { label: vi ? "Đánh giá" : "Assessment", value: (row) => row.verdict },
    ]} />
  )
}

function EvidenceBody({ result, lang }: { result: CanvasResult; lang: Lang }) {
  const vi = lang === "vi"
  const label = toolLabel(result.name, lang)
  const bankHeading = vi ? "Ngân hàng" : "Bank"
  const pp = points(lang).trim()
  switch (result.name) {
    case "screen_declines":
      return (
        <>
          <EvidenceTable label={label} lang={lang} rows={result.output.rows} rowKey={(row) => row.bank}
            rowLink={(row) => bankLink(row.bank, result.output.data_period, row.waterfall, lang)} sortable
            columns={[
              { label: bankHeading, value: (row) => row.bank },
              { label: `${vi ? "Δ Nợ xấu" : "Δ NPL"} (${pp})`, value: (row) => row.npl_pp, numeric: true },
              { label: `${vi ? "Δ Nợ nhóm 2" : "Δ Group 2"} (${pp})`, value: (row) => row.group2_pp, numeric: true },
              { label: vi ? "Xóa nợ (% dư nợ)" : "Write-offs (% of loans)", value: (row) => row.writeoff_pct, numeric: true },
              { label: `${vi ? "Δ Bao phủ" : "Δ Coverage"} (${pp})`, value: (row) => row.coverage_pp, numeric: true },
              { label: vi ? "Tín hiệu" : "Flags", value: (row) => row.flags.map((flag) => FLAG_LABELS[flag][lang]).join(", ") || null },
            ]} />
          <p className="px-3 py-2 text-xs text-muted-foreground">
            {vi ? "Xóa nợ được ước tính từ dự phòng đã sử dụng." : "Write-offs are estimated from provisions used."}
          </p>
        </>
      )
    case "rank_gap":
      return (
        <EvidenceTable label={label} lang={lang} rows={result.output.rows} rowKey={(row) => row.bank_code}
          rowLink={(row) => bankLink(row.bank_code, row.period, false, lang)} sortable initialSort={3} initialDescending
          columns={[
            { label: bankHeading, value: (row) => row.bank_code },
            { label: vi ? "Hạng nợ xấu" : "NPL rank", value: (row) => row.npl_place, numeric: true, digits: 0 },
            { label: vi ? "Hạng tổng hợp" : "Composite rank", value: (row) => row.composite_place, numeric: true, digits: 0 },
            { label: vi ? "Chênh lệch hạng" : "Rank gap", value: (row) => row.composite_place - row.npl_place, numeric: true, digits: 0 },
          ]} />
      )
    case "largest_writeoffs":
      return (
        <>
          <EvidenceTable label={label} lang={lang} rows={result.output.rows} rowKey={(row) => row.bank}
            rowLink={(row) => bankLink(row.bank, result.output.data_period, false, lang)} sortable
            initialSort={result.output.measure === "share" ? 2 : 1} initialDescending
            columns={[
              { label: bankHeading, value: (row) => row.bank },
              { label: vi ? "Xóa nợ (tỷ VND)" : "Write-offs (VND bn)", value: (row) => row.amount_vnd_bn, numeric: true, digits: 1 },
              { label: vi ? "% dư nợ đầu quý" : "% of opening loans", value: (row) => row.share_pct, numeric: true },
            ]} />
          <p className="px-3 py-2 text-xs text-muted-foreground">
            {vi ? "Xóa nợ được ước tính từ dự phòng đã sử dụng." : "Write-offs are estimated from provisions used."}
          </p>
        </>
      )
    case "early_warning": {
      const labels = [
        ["npl_only", vi ? "Chỉ tỷ lệ nợ xấu" : "NPL only"],
        ["npl_group2", vi ? "Thêm nợ nhóm 2" : "Add Group 2"],
        ["full", vi ? "Đầy đủ chỉ báo" : "Full indicators"],
      ] as const
      const rows = labels.flatMap(([key, name]) => {
        const auc = result.output.fits?.[key]?.auc?.estimate
        return auc == null ? [] : [{ name, auc }]
      })
      return (
        <EvidenceTable label={label} lang={lang} rows={rows} rowKey={(row) => row.name} columns={[
          { label: vi ? "Chỉ báo dự báo" : "Predictors", value: (row) => row.name },
          { label: "AUC", value: (row) => row.auc, numeric: true, digits: 3 },
        ]} />
      )
    }
    case "q4_drivers":
      return (
        <MetricBarsChart lang={lang} metric={vi ? "Đóng góp vào thay đổi" : "Contribution to NPL change"} unit={points(lang)} rows={[
          { label: vi ? "Dư nợ" : "Loan growth", value: result.output.loan_growth_part_pp },
          { label: vi ? "Số dư nợ xấu" : "Bad-debt balance", value: result.output.bad_debt_part_pp },
        ]} />
      )
    case "q1_rebound": {
      const { rates } = result.output
      return rates && (
        <MetricBarsChart lang={lang} metric={vi ? "Tỷ lệ trường hợp tăng lại" : "Share that rebounded"} unit="%" rows={[
          { label: vi ? "Mọi Q4" : "All Q4s", value: rates.any_q4.share_pct },
          { label: vi ? "Q4 giảm" : "Q4 fell", value: rates.q4_fell.share_pct },
          { label: vi ? "Q4 không giảm" : "Q4 did not fall", value: rates.q4_not_fell.share_pct },
        ]} />
      )
    }
    case "quarter_breakdown": {
      const { data_period, q3_period, q1_period, q3_pct, q4_pct, q1_pct } = result.output
      const rows = [
        ...(q3_period ? [{ period: q3_period, value: q3_pct }] : []),
        { period: data_period, value: q4_pct },
        ...(q1_period ? [{ period: q1_period, value: q1_pct }] : []),
      ]
      return <QuarterNplChart lang={lang} rows={rows} />
    }
    case "coverage_effect":
    case "quarter_effects": {
      const effects = result.name === "quarter_effects" ? result.output.effects : result.output.effect ? [{ ...result.output.effect, quarter: 4 }] : []
      return (
        <MetricBarsChart lang={lang} metric={result.name === "coverage_effect" ? (vi ? "Thay đổi bao phủ" : "Coverage change") : (vi ? "Thay đổi nợ xấu" : "NPL change")}
          unit={points(lang)} zeroLabel={vi ? "So với quý 1" : "Versus Q1"}
          rows={effects.map(({ quarter, coef_pp, ci95: [lo, hi] }) => ({
            label: `Q${quarter}`, value: coef_pp,
            interval: lo != null && hi != null ? [lo, hi] : undefined,
          }))} />
      )
    }
    case "overview":
      return (
        <EvidenceTable label={label} lang={lang} rows={overviewFigures(result.output, lang)} rowKey={(row) => row.label} columns={[
          { label: vi ? "Chỉ số" : "Metric", value: (row) => row.label },
          { label: vi ? "Giá trị" : "Value", value: (row) => row.value, numeric: true },
          { label: vi ? "Kỳ" : "Period", value: (row) => row.period == null ? result.output.data_period : String(row.period) },
        ]} />
      )
    case "bank_profile": {
      const mode = bankCanvasMode(result.output, result.tool.input)
      if (mode === "trend" && result.output.bank.series) return <BankCanvasChart lang={lang} rows={result.output.bank.series} />
      const evidence = result.output.selected?.evidence[lang]
      return evidence && <BankChecksTable evidence={evidence} label={label} lang={lang} />
    }
    case "compare_banks": {
      const { rows, requested_period } = result.output
      if (hasComparisonHistory(result.output)) return <CompareCanvasChart lang={lang} rows={rows} />
      return (
        <EvidenceTable label={label} lang={lang} rows={rows} rowKey={(row) => row.code}
          rowLink={(row) => bankLink(row.code, row.period ?? "", false, lang)} sortable columns={[
            { label: bankHeading, value: (row) => row.code },
            ...(!requested_period ? [{ label: vi ? "Kỳ" : "Period", value: (row: (typeof rows)[number]) => row.period ?? row.latest_period }] : []),
            { label: vi ? "Nợ xấu (%)" : "NPL (%)", value: (row) => row.npl_pct ?? null, numeric: true },
            { label: vi ? "Nhóm 2 (%)" : "Group 2 (%)", value: (row) => row.group2_pct ?? null, numeric: true },
            { label: `${vi ? "Δ Nợ xấu" : "Δ NPL"} (${pp})`, value: (row) => row.d_npl_pp, numeric: true },
            { label: `${vi ? "Δ Sau điều chỉnh" : "Adjusted Δ"} (${pp})`, value: (row) => row.adjusted_change_pp, numeric: true },
            ...(requested_period ? [{ label: `${vi ? "Do dư nợ" : "Loan contribution"} (${pp})`,
              value: (row: (typeof rows)[number]) => row.denominator_pp, numeric: true }] : []),
          ]} />
      )
    }
    case "decoder":
      if (result.output.selected && hasBankChecks(result.output.selected)) {
        return <BankChecksTable evidence={result.output.selected.evidence[lang]} label={label} lang={lang} />
      }
      return <ReportedChangeChart row={result.output.row} lang={lang} />
    case "adjusted_change":
      return <ReportedChangeChart row={result.output.row} lang={lang} />
    case "forecast":
      return <ForecastCanvasChart lang={lang} output={result.output} />
    case "market_reaction":
      return <MarketCanvasChart lang={lang} rows={result.output.car_all} />
    default:
      return null
  }
}

function ReportedChangeChart({ row, lang }: { row: { d_npl_pp: number | null; adjusted_change_pp: number | null }; lang: Lang }) {
  const vi = lang === "vi"
  return (
    <MetricBarsChart lang={lang} metric={vi ? "Thay đổi tỷ lệ nợ xấu" : "Change in NPL ratio"} unit={points(lang)} rows={[
      { label: vi ? "Công bố" : "Reported", value: row.d_npl_pp },
      { label: vi ? "Đã điều chỉnh" : "Seasonally adjusted", value: row.adjusted_change_pp },
    ]} />
  )
}

function evidenceCaption(result: CanvasResult, lang: Lang) {
  const vi = lang === "vi"
  let title = toolLabel(result.name, lang)
  let period = result.output.data_period
  let href = openPage(result.name, result.tool.input, lang)
  const range = (start: string | null | undefined, end: string | null | undefined) =>
    start && end && start !== end ? `${start}–${end}` : start ?? end ?? period
  const through = () => period && /^\d{4}Q[1-4]$/.test(period) ? `${vi ? "Dữ liệu đến" : "Data through"} ${period}` : period

  switch (result.name) {
    case "q4_drivers":
      period = through()
      href += "#q4-breakdown"
      break
    case "quarter_breakdown": {
      const { bank, data_period, q3_period, q1_period, change_pp, loan_growth_part_pp, bad_debt_part_pp } = result.output
      title = `${bank}: ${title}`
      period = range(q3_period ?? data_period, q1_period ?? data_period)
      href = bankLink(bank, data_period, change_pp != null && change_pp < 0 && loan_growth_part_pp != null && bad_debt_part_pp != null, lang)
      break
    }
    case "q1_rebound":
      period = through()
      href = pageHref("/phuong-phap", lang) + "#seasonal-models"
      break
    case "coverage_effect":
      period = through()
      break
    case "early_warning":
      period = through()
      href = pageHref("/phuong-phap", lang) + "#early-warning"
      break
    case "bank_profile":
      title = `${result.output.bank.code}: ${title}`
      if (bankCanvasMode(result.output, result.tool.input) === "trend") {
        period = range(result.output.bank.series?.[0]?.period, result.output.bank.series?.at(-1)?.period)
      } else {
        period = result.output.selected?.period ?? period
      }
      break
    case "forecast":
    case "decoder":
    case "adjusted_change":
      title = `${result.output.code}: ${title}`
      break
    case "compare_banks": {
      if (hasComparisonHistory(result.output)) {
        const timeline = comparisonHistory(result.output.rows)
        title = vi ? "So sánh tỷ lệ nợ xấu qua các quý" : "NPL comparison by quarter"
        period = range(timeline[0].period, timeline.at(-1)?.period)
      }
      break
    }
  }
  return { title, period, href }
}

export function hasAnswerCanvas(tools: ListedTool[]): boolean {
  return findAnswerCanvas(tools) != null
}

export function AnswerEvidence({ tools, lang }: { tools: ListedTool[]; lang: Lang }) {
  const titleId = useId()
  const result = findAnswerCanvas(tools)
  if (!result) return null

  const vi = lang === "vi"
  const { title, period, href } = evidenceCaption(result, lang)
  const source = result.name === "largest_writeoffs"
    ? (vi ? "FiinQuant (FiinGroup) và thuyết minh báo cáo tài chính" : "FiinQuant (FiinGroup) and financial statement notes")
    : "FiinQuant (FiinGroup)"
  return (
    <figure aria-labelledby={titleId} className="min-w-0 overflow-hidden rounded-lg border border-border bg-card text-card-foreground">
      <div id={titleId} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-b px-3 py-2.5">
        <span className="text-sm font-semibold leading-snug">{title}</span>
        {period && <span className="text-xs font-medium text-muted-foreground tabular-nums">{period}</span>}
      </div>
      <EvidenceBody key={result.tool.id} result={result} lang={lang} />
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-t px-3 py-2.5 text-xs text-muted-foreground">
        <span>{vi ? "Nguồn" : "Source"}: {source}</span>
        <a href={href} className="font-medium text-foreground underline underline-offset-2">{vi ? "Xem trên trang" : "See on the page"}</a>
      </figcaption>
    </figure>
  )
}
