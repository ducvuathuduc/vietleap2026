import Link from "next/link"

import { QuarterChart } from "@/components/npl/charts"
import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { DECODER_DISCLAIMER, type Lang } from "@/lib/npl/view"
import type { NplDecoderCell } from "@/lib/npl/agent/tools"

import { BankCanvasChart, CompareCanvasChart, ForecastCanvasChart } from "./canvas-charts"
import { CHECKS, INPUTS, RATIOS, csvRows, decoderStatus, formatValue, inputSummary, openPage, overviewFigures, points, readResult, toolLabel, type CsvCell } from "./canvas-data"
import { visibleText } from "./question-lang"

export type ListedTool = { id: string; name: string; input: unknown; output: unknown }
export type CanvasCard = ListedTool & { lang: Lang }
type Result = NonNullable<ReturnType<typeof readResult>>

export function AskCanvas({
  cards,
  pinned,
  onTogglePin,
  onOpenPage,
  lang,
}: {
  cards: CanvasCard[]
  pinned: ReadonlySet<string>
  onTogglePin: (id: string) => void
  onOpenPage: () => void
  lang: Lang
}) {
  return (
    <section className="flex min-h-0 min-w-0 flex-col gap-3 overflow-y-auto" aria-label={lang === "vi" ? "Số liệu" : "Figures"}>
      {cards.map((card) => (
        <ResultCard key={card.id} card={card} pinned={pinned.has(card.id)} onTogglePin={() => onTogglePin(card.id)} onOpenPage={onOpenPage} />
      ))}
    </section>
  )
}

function ResultCard({ card, pinned, onTogglePin, onOpenPage }: { card: CanvasCard; pinned: boolean; onTogglePin: () => void; onOpenPage: () => void }) {
  const vi = card.lang === "vi"
  const result = readResult(card.name, card.output)
  return (
    <Card role="article" size="sm" lang={card.lang} className="min-w-0 shrink-0">
      <CardHeader>
        <CardTitle role="heading" aria-level={3}>{result ? finding(result, card.lang) : toolLabel(card.name, card.lang)}</CardTitle>
        <CardDescription>{result ? sourceLine(result, card.lang) : missing(card.lang)}</CardDescription>
      </CardHeader>
      {result ? <CardContent className="min-w-0"><CardBody result={result} lang={card.lang} /></CardContent> : null}
      <CardFooter className="flex-wrap gap-2">
        <Button type="button" variant={pinned ? "secondary" : "outline"} size="sm" aria-pressed={pinned} onClick={onTogglePin}>
          {vi ? "Ghim" : "Pin"}
        </Button>
        <Link href={openPage(card.name, card.input, card.lang)} onNavigate={onOpenPage} className={buttonVariants({ variant: "outline", size: "sm" })}>
          {vi ? "Mở trang" : "Open page"}
        </Link>
        <Button type="button" variant="outline" size="sm" onClick={() => downloadCsv(card.name, csvRows(result, card.lang))}>
          {vi ? "Tải CSV" : "Download CSV"}
        </Button>
      </CardFooter>
    </Card>
  )
}

function finding(result: Result, lang: Lang): string {
  const vi = lang === "vi"
  switch (result.name) {
    case "overview": {
      const { level } = result.output
      const value = formatValue(level.npl_median_pct, lang, "%")
      return vi ? `Nợ xấu trung vị ${level.period} ở mức ${value}` : `Median NPL in ${level.period} was ${value}`
    }
    case "quarter_effects": {
      const q4 = result.output.effects.find((effect) => effect.quarter === 4)
      return q4
        ? `${vi ? "Chênh lệch quý 4 so với quý 1" : "Q4 difference versus Q1"} · ${formatValue(q4.coef_pp, lang, points(lang))}`
        : toolLabel(result.name, lang)
    }
    case "bank_profile": {
      const { bank } = result.output
      const latest = bank.series?.at(-1)
      const value = formatValue(latest?.npl_pct, lang, "%")
      return latest?.npl_pct != null
        ? `${bank.code} · ${vi ? "Nợ xấu" : "NPL"} ${value} (${latest.period})`
        : `${bank.code} · ${vi ? "Diễn biến nợ xấu" : "NPL over time"}`
    }
    case "compare_banks": {
      const rows = result.output.rows.filter((row) => row.adjusted_change_pp != null)
      const largest = rows.reduce<(typeof rows)[number] | undefined>((max, row) =>
        !max || row.adjusted_change_pp! > max.adjusted_change_pp! ? row : max, undefined)
      const label = vi ? "Biến động đã điều chỉnh" : "Adjusted change"
      return largest ? `${largest.code} · ${label} ${formatValue(largest.adjusted_change_pp, lang, points(lang))}` : label
    }
    case "decoder":
    case "adjusted_change": {
      const { code, row, decoder } = result.output
      const status = decoder ? decoderStatus(decoder.status, lang) : toolLabel(result.name, lang)
      return `${code} ${row.period} · ${status}`
    }
    case "forecast": {
      const { code, forecast } = result.output
      return `${code} · ${vi ? "Dự báo" : "Forecast"} ${formatValue(forecast.npl_pct, lang, "%")} (${forecast.period})`
    }
    case "market_reaction":
      return vi ? `Phản ứng giá qua ${result.output.events_with_car} công bố` : `Price reaction across ${result.output.events_with_car} disclosures`
    case "method":
      return visibleText(vi ? result.output.entry.name_vi : result.output.entry.name_en)
    default:
      return toolLabel(result.name, lang)
  }
}

function CardBody({ result, lang }: { result: Result; lang: Lang }) {
  const vi = lang === "vi"
  switch (result.name) {
    case "overview":
      return (
        <dl className="grid grid-cols-3 gap-2">
          {overviewFigures(result.output, lang).map(({ label, value, period }) => (
            <div key={label} className="rounded-md bg-muted p-2">
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="text-base font-semibold tabular-nums">{value}</dd>
              {period ? <dd className="text-xs text-muted-foreground">{period}</dd> : null}
            </div>
          ))}
        </dl>
      )
    case "quarter_effects": {
      const bars = result.output.effects.map((row) => ({ quarter: row.quarter, coef: row.coef_pp, lo: row.ci95[0] ?? null, hi: row.ci95[1] ?? null }))
      return (
        <div className="space-y-2">
          {bars.length ? <QuarterChart bars={bars} lang={lang} /> : <p className="text-sm">{missing(lang)}</p>}
          <p className="text-xs text-muted-foreground">
            {vi ? "Các vạch biểu thị khoảng tin cậy 95%. Đây là liên hệ trong dữ liệu, không phải nhân quả." : "Whiskers show 95% confidence intervals. This is an association in the data, not causation."}
          </p>
        </div>
      )
    }
    case "bank_profile": {
      const { bank, decoder } = result.output
      return (
        <div className="space-y-2">
          {bank.series?.length ? <BankCanvasChart rows={bank.series} lang={lang} /> : <p className="text-sm">{missing(lang)}</p>}
          {bank.latest && (
            <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {vi ? "Kiểm tra kỳ" : "Decoder for"} {bank.latest.period}
              <Badge variant="outline" className="h-auto whitespace-normal">{decoder ? decoderStatus(decoder.status, lang) : missing(lang)}</Badge>
            </p>
          )}
        </div>
      )
    }
    case "compare_banks":
      return (
        <div className="space-y-2">
          {result.output.rows.length ? <CompareCanvasChart rows={result.output.rows} lang={lang} /> : <p className="text-sm">{missing(lang)}</p>}
          {result.output.rows.length > 0 && <p className="text-xs text-muted-foreground">{result.output.rows.map((row) => `${row.code} ${row.latest_period ?? "—"}`).join(" · ")}</p>}
          {result.output.missing.length > 0 && <p className="text-xs text-muted-foreground">{vi ? "Chưa có số liệu" : "No data"} · {result.output.missing.join(", ")}</p>}
        </div>
      )
    case "adjusted_change":
    case "decoder": {
      const { row, decoder } = result.output
      return (
        <div className="space-y-3 text-sm">
          <p>{vi ? "Biến động nợ xấu" : "NPL change"} <strong>{formatValue(row.d_npl_pp, lang, points(lang))}</strong> · {vi ? "Đã điều chỉnh mùa vụ" : "Seasonally adjusted"} <strong>{formatValue(row.adjusted_change_pp, lang, points(lang))}</strong></p>
          {decoder ? <DecoderDetails cell={decoder} lang={lang} /> : <p>{vi ? "Chưa có dữ liệu cho các bước kiểm tra kỳ này." : "Decoder inputs for this quarter are unavailable."}</p>}
        </div>
      )
    }
    case "forecast": {
      const { backtest_note_vi, backtest_note_en, backtest_period, mae, note_vi, note_en } = result.output
      const period = [backtest_period[0], backtest_period.at(-1)].filter(Boolean).join("–")
      return (
        <div className="space-y-2">
          <ForecastCanvasChart output={result.output} lang={lang} />
          <p className="text-xs"><strong>{vi ? "Kiểm định dự báo" : "Backtest"}{period ? ` (${period})` : ""}.</strong> {visibleText(vi ? backtest_note_vi : backtest_note_en)}</p>
          <p className="text-xs text-muted-foreground">
            {vi ? "Sai số tuyệt đối trung bình" : "Mean absolute error"} · {vi ? "dự báo" : "forecast"} {formatValue(mae.model, lang, points(lang))} · {vi ? "giữ nguyên" : "last value"} {formatValue(mae.last_value, lang, points(lang))} · {vi ? "cùng quý năm trước" : "seasonal baseline"} {formatValue(mae.seasonal_naive, lang, points(lang))}
          </p>
          <p className="text-xs text-muted-foreground">{vi ? note_vi : note_en}</p>
        </div>
      )
    }
    case "market_reaction":
      return <p className="text-sm">{visibleText(vi ? result.output.reading_vi : result.output.reading_en) || missing(lang)}</p>
    case "method": {
      const { entry } = result.output
      return <p className="text-sm">{visibleText(vi ? entry.reading_vi : entry.reading_en)} {visibleText(vi ? entry.does_not_show_vi : entry.does_not_show_en)}</p>
    }
    case "limitations":
      return <ul className="list-disc space-y-1 ps-4 text-sm">{result.output.items.map((item) => <li key={item.en}>{visibleText(item[lang])}</li>)}</ul>
    case "glossary":
      return <p className="text-sm">{visibleText(result.output.entry[lang])}</p>
  }
}

function DecoderDetails({ cell, lang }: { cell: NplDecoderCell; lang: Lang }) {
  const vi = lang === "vi"
  const checkStatus = {
    flagged: vi ? "Có cờ" : "Flagged",
    clear: vi ? "Không có cờ" : "No flag",
    missing: vi ? "Thiếu dữ liệu" : "Missing data",
    inapplicable: vi ? "Không áp dụng" : "Not applicable",
  }
  return (
    <div className="space-y-2">
      <p>{vi ? cell.reading_vi : cell.reading_en}</p>
      <ul className="space-y-1">
        {CHECKS.map(([key, labelVi, labelEn]) => (
          <li key={key} className="flex flex-wrap items-center justify-between gap-1 text-xs">
            {vi ? labelVi : labelEn}
            <Badge variant={cell.checks[key] === "flagged" ? "secondary" : "outline"}>{checkStatus[cell.checks[key]]}</Badge>
          </li>
        ))}
      </ul>
      <Collapsible>
        <CollapsibleTrigger className={buttonVariants({ variant: "outline", size: "sm" })}>{vi ? "Đầu vào & nguồn" : "Inputs & sources"}</CollapsibleTrigger>
        <CollapsibleContent className="mt-2 space-y-2 text-xs">
          <dl className="space-y-1">
            {INPUTS.map(([key, labelVi, labelEn]) => (
              <div key={key} className="flex justify-between gap-2">
                <dt>{vi ? labelVi : labelEn}</dt>
                <dd className="tabular-nums">{formatValue(cell.inputs[key], lang, vi ? " tỷ đồng" : " VND bn")}</dd>
              </div>
            ))}
          </dl>
          <ul className="space-y-1">
            {RATIOS.map(([key, labelVi, labelEn]) => {
              const ratio = cell.inputs.ratios[key]
              return <li key={key}>{vi ? labelVi : labelEn} · {formatValue(ratio.value, lang, "%")}{ratio.source ? ` · ${ratio.source}` : ""}{ratio.page == null ? "" : ` · ${vi ? "trang" : "p."} ${ratio.page}`}</li>
            })}
          </ul>
        </CollapsibleContent>
      </Collapsible>
      <p className="text-xs text-muted-foreground">{DECODER_DISCLAIMER[lang]}</p>
    </div>
  )
}

export function AnswerSources({ tools, lang }: { tools: ListedTool[]; lang: Lang }) {
  const vi = lang === "vi"
  return (
    <Collapsible>
      <CollapsibleTrigger className={buttonVariants({ variant: "outline", size: "sm" })}>
        {vi ? "Nguồn & phép tính" : "Sources & calculation"}
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-2 pt-2 text-xs">
        {tools.length === 0 ? <p className="text-muted-foreground">{vi ? "Chưa có phép tính." : "No calculation for this answer."}</p> : null}
        {tools.map((tool) => {
          const result = readResult(tool.name, tool.output)
          const inputs = result?.name === "method" ? finding(result, lang) : inputSummary(tool.name, tool.input, lang)
          return (
            <div key={tool.id} className="rounded-md border border-border p-2">
              <p className="font-medium">{toolLabel(tool.name, lang)}</p>
              <p className="text-muted-foreground">{vi ? "Đầu vào" : "Inputs"} · {inputs}</p>
              {result ? <>
                <p className="text-muted-foreground">{sourceLine(result, lang)}</p>
                {result.output.data_period ? <p className="text-muted-foreground">{vi ? "Kỳ dữ liệu" : "Data period"} · {result.output.data_period}</p> : null}
                <ReturnedNumbers result={result} lang={lang} />
              </> : <p className="text-muted-foreground">{missing(lang)}</p>}
            </div>
          )
        })}
      </CollapsibleContent>
    </Collapsible>
  )
}

function ReturnedNumbers({ result, lang }: { result: Result; lang: Lang }) {
  const vi = lang === "vi"
  const pp = (value: number | null | undefined) => formatValue(value, lang, points(lang))
  const pct = (value: number | null | undefined) => formatValue(value, lang, "%")
  let numbers: string[]
  switch (result.name) {
    case "overview":
      numbers = overviewFigures(result.output, lang).map((item) => `${item.label} · ${item.value}`)
      if (result.output.last_median?.coverage_median_pct != null) {
        numbers.push(`${vi ? "Bao phủ trung vị" : "Median coverage"} · ${pct(result.output.last_median.coverage_median_pct)} (${result.output.last_median.period})`)
      }
      break
    case "quarter_effects":
      numbers = result.output.effects.map((row) => `Q${row.quarter} · ${pp(row.coef_pp)} (${pp(row.ci95[0])} – ${pp(row.ci95[1])}; n = ${row.n})`)
      break
    case "bank_profile": {
      const { bank } = result.output
      const last = bank.series?.at(-1)
      numbers = [
        `${last?.period ?? bank.latest?.period ?? "—"} · NPL ${pct(last?.npl_pct)} · ${vi ? "bao phủ" : "coverage"} ${pct(last?.coverage_pct)}`,
        `${vi ? "Trung vị quý 4" : "Q4 median"} ${pp(bank.q4_change_median_pp)} · ${vi ? "quý 1" : "Q1"} ${pp(bank.q1_rebound_median_pp)}`,
        `${vi ? "Đã điều chỉnh" : "Adjusted change"} · ${pp(bank.latest?.adjusted_change_pp)}`,
      ]
      break
    }
    case "compare_banks":
      numbers = result.output.rows.map((row) => `${row.code} ${row.latest_period ?? ""} · ${vi ? "gốc" : "raw"} ${pp(row.d_npl_pp)} · ${vi ? "đã điều chỉnh" : "adjusted"} ${pp(row.adjusted_change_pp)}`)
      break
    case "adjusted_change":
    case "decoder": {
      const { row, decoder } = result.output
      numbers = [`${vi ? "Biến động gốc" : "Raw change"} ${pp(row.d_npl_pp)} · ${vi ? "đã điều chỉnh" : "adjusted"} ${pp(row.adjusted_change_pp)}`]
      if (decoder) numbers.push(...RATIOS.map(([key, labelVi, labelEn]) => `${vi ? labelVi : labelEn} · ${pct(decoder.inputs.ratios[key].value)}`))
      break
    }
    case "forecast": {
      const { forecast, mae } = result.output
      numbers = [
        `${forecast.period} · ${pct(forecast.npl_pct)} (${vi ? "khoảng 80%" : "80% interval"} ${pct(forecast.lo80)} – ${pct(forecast.hi80)})`,
        `${vi ? "Sai số trung bình" : "Mean absolute error"} · ${pp(mae.model)} · ${vi ? "giữ nguyên" : "last value"} ${pp(mae.last_value)} · ${vi ? "mùa vụ" : "seasonal"} ${pp(mae.seasonal_naive)}`,
      ]
      break
    }
    case "market_reaction":
      numbers = [
        `${result.output.events_with_car} ${vi ? "công bố có lợi suất" : "disclosures with returns"}`,
        ...result.output.car_all.map((row) => `${vi ? "Lợi suất bất thường tích lũy, ngày" : "Cumulative abnormal return, day"} ${row.day} · ${pct(row.mean_car_pct)} (${pct(row.ci95?.[0])} – ${pct(row.ci95?.[1])}; n = ${row.n})`),
      ]
      break
    case "method":
      numbers = [`${vi ? "Số quan sát" : "Observations"} · ${result.output.entry.n}`]
      break
    default:
      return null
  }
  if (numbers.length === 0) return null
  return <ul className="mt-1 space-y-1">{numbers.map((number) => <li key={number}>{number}</li>)}</ul>
}

function sourceLine(result: Result, lang: Lang): string {
  const vi = lang === "vi"
  if (result.name === "glossary") return vi ? "Nguồn · Chú giải của nghiên cứu" : "Source · Study glossary"
  const sources = new Set(["FiinQuant (FiinGroup)"])
  if ((result.name === "decoder" || result.name === "adjusted_change") && result.output.decoder) {
    for (const ratio of Object.values(result.output.decoder.inputs.ratios)) if (ratio.source) sources.add(ratio.source)
  }
  return `${vi ? "Nguồn" : "Source"} · ${[...sources].join(" · ")}`
}

function missing(lang: Lang): string {
  return lang === "vi" ? "Chưa có số liệu công bố." : "No published figures available."
}

function downloadCsv(name: string, rows: CsvCell[][]): void {
  const body = rows.map((row) => row.map(csvCell).join(",")).join("\r\n")
  const blob = new Blob(["\uFEFF", body], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = `npl-${name.replace(/[^a-z_]/g, "")}.csv`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function csvCell(value: CsvCell): string {
  if (value == null || typeof value === "number") return value == null ? "" : String(value)
  const text = /^[=+@-]/.test(value) ? `'${value}` : value
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}
