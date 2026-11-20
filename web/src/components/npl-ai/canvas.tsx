import { BankLines, DrillChart, ForecastBand, QuarterChart } from "@/components/npl/charts"
import { Button, buttonVariants } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { formatNumber, type Lang } from "@/lib/npl/view"

import { visibleText } from "./question-lang"

export type CanvasCard = {
  id: string
  name: string
  lang: Lang
  input: unknown
  output: unknown
}

export type ListedTool = {
  id: string
  name: string
  input: unknown
}

const LABELS: Record<string, { vi: string; en: string }> = {
  overview: { vi: "Tổng quan", en: "Overview" },
  quarter_effects: { vi: "Hiệu ứng quý", en: "Quarter effect" },
  bank_profile: { vi: "Hồ sơ ngân hàng", en: "Bank profile" },
  compare_banks: { vi: "So sánh", en: "Comparison" },
  forecast: { vi: "Dự báo", en: "Forecast" },
  market_reaction: { vi: "Thị trường", en: "Market" },
  method: { vi: "Phương pháp", en: "Method" },
  limitations: { vi: "Giới hạn", en: "Limitations" },
  glossary: { vi: "Giải thích", en: "Explanation" },
  adjusted_change: { vi: "Thay đổi đã điều chỉnh", en: "Adjusted change" },
}

const FILES: Record<string, string> = {
  overview: "tong-quan",
  quarter_effects: "hieu-ung-quy",
  bank_profile: "ho-so-ngan-hang",
  compare_banks: "so-sanh",
  forecast: "du-bao",
  market_reaction: "thi-truong",
  method: "phuong-phap",
  limitations: "gioi-han",
  glossary: "giai-thich",
  adjusted_change: "thay-doi",
}

type LineRow = {
  period: string
  npl: number | null
  coverage: number | null
  nim: number | null
  ldr: number | null
  loanGrowth: number | null
}

export function AskCanvas({
  cards,
  pinned,
  onTogglePin,
  tools,
  lang,
}: {
  cards: CanvasCard[]
  pinned: ReadonlySet<string>
  onTogglePin: (id: string) => void
  tools: ListedTool[]
  lang: Lang
}) {
  const vi = lang === "vi"
  return (
    <section className="flex min-h-0 min-w-0 flex-col gap-3" aria-label={vi ? "Số liệu" : "Figures"}>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto">
        {cards.map((card) => (
          <ResultCard key={card.id} card={card} pinned={pinned.has(card.id)} onTogglePin={onTogglePin} />
        ))}
      </div>
      <SourcesList tools={tools} lang={lang} />
    </section>
  )
}

function ResultCard({
  card,
  pinned,
  onTogglePin,
}: {
  card: CanvasCard
  pinned: boolean
  onTogglePin: (id: string) => void
}) {
  const vi = card.lang === "vi"
  const href = withLang(openPath(card.name, card.input, card.output), card.lang)
  return (
    <article className="flex min-w-0 flex-col gap-2 rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="mr-auto text-sm font-medium">{toolLabel(card.name, card.lang)}</p>
        <Button type="button" variant={pinned ? "secondary" : "outline"} size="sm" aria-pressed={pinned} onClick={() => onTogglePin(card.id)}>
          {vi ? "Ghim" : "Pin"}
        </Button>
        <a href={href} className={buttonVariants({ variant: "outline", size: "sm" })}>
          {vi ? "Mở trang" : "Open the page"}
        </a>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => downloadCsv(fileName(card.name, card.id), csvRows(card.name, card.output, card.lang))}
        >
          {vi ? "Tải số" : "Download numbers"}
        </Button>
      </div>
      <CardBody name={card.name} output={card.output} lang={card.lang} />
      <p className="text-xs text-muted-foreground">Nguồn: FiinQuant (FiinGroup)</p>
    </article>
  )
}

function CardBody({ name, output, lang }: { name: string; output: unknown; lang: Lang }) {
  const data = record(output)
  if (!data || data.found === false) {
    return <p className="text-sm">{lang === "vi" ? "Không có trong snapshot." : "Not in the snapshot."}</p>
  }
  if (name === "quarter_effects") return <QuarterBody output={data} lang={lang} />
  if (name === "bank_profile") return <BankBody output={data} lang={lang} />
  if (name === "compare_banks") return <CompareBody output={data} lang={lang} />
  if (name === "forecast") return <ForecastBody output={data} lang={lang} />
  if (name === "limitations") {
    const lines = limitationLines(data, lang)
    if (lines.length === 0) return <p className="text-sm">{lang === "vi" ? "Không có trong snapshot." : "Not in the snapshot."}</p>
    return (
      <div className="flex flex-col gap-2">
        {lines.map((line, index) => (
          <p key={index} className="text-sm">
            {line}
          </p>
        ))}
      </div>
    )
  }
  const text = prose(name, data, lang)
  return <p className="text-sm">{text || (lang === "vi" ? "Không có trong snapshot." : "Not in the snapshot.")}</p>
}

function QuarterBody({ output, lang }: { output: Record<string, unknown>; lang: Lang }) {
  const bars = quarterBars(output)
  const note = clean(lang === "vi" ? output.note_vi : output.note_en)
  return (
    <div className="flex min-w-0 flex-col gap-2">
      {bars.length > 0 ? (
        <QuarterChart bars={bars} lang={lang} />
      ) : (
        <p className="text-sm">{lang === "vi" ? "Không có hiệu ứng quý trong snapshot." : "No quarter effect is in the snapshot."}</p>
      )}
      {note ? <p className="text-sm">{note}</p> : null}
    </div>
  )
}

function BankBody({ output, lang }: { output: Record<string, unknown>; lang: Lang }) {
  const bank = record(output.bank)
  if (!bank) return <p className="text-sm">{lang === "vi" ? "Không có trong snapshot." : "Not in the snapshot."}</p>
  const summary = bankSummary(bank, lang)
  const signals = signalTexts(bank, lang)
  const series = Array.isArray(bank.series) ? lineRows(bank.series) : null
  return (
    <div className="flex min-w-0 flex-col gap-2">
      {summary ? <p className="text-sm">{summary}</p> : null}
      {series ? <BankLines rows={series} lang={lang} /> : null}
      {signals.map((text, index) => (
        <p key={index} className="text-sm">
          {text}
        </p>
      ))}
    </div>
  )
}

function CompareBody({ output, lang }: { output: Record<string, unknown>; lang: Lang }) {
  const rows = compareRows(output)
  const missing = stringList(output.missing)
  return (
    <div className="flex min-w-0 flex-col gap-2">
      {rows.length > 0 ? (
        <DrillChart rows={rows} lang={lang} onPick={noopPick} />
      ) : (
        <p className="text-sm">{lang === "vi" ? "Không có ngân hàng để so sánh." : "No banks to compare."}</p>
      )}
      {missing.length > 0 ? (
        <p className="text-sm">
          {lang === "vi" ? `Không có ${missing.join(", ")} trong snapshot.` : `${missing.join(", ")} is not in the snapshot.`}
        </p>
      ) : null}
    </div>
  )
}

function ForecastBody({ output, lang }: { output: Record<string, unknown>; lang: Lang }) {
  const point = forecastPoint(output)
  const note = clean(lang === "vi" ? output.note_vi : output.note_en)
  if (!point) return <p className="text-sm">{note || (lang === "vi" ? "Không có trong snapshot." : "Not in the snapshot.")}</p>
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <ForecastBand point={point} lang={lang} />
      {note ? <p className="text-sm">{note}</p> : null}
    </div>
  )
}

function SourcesList({ tools, lang }: { tools: ListedTool[]; lang: Lang }) {
  const vi = lang === "vi"
  return (
    <Collapsible className="shrink-0">
      <CollapsibleTrigger type="button" className={buttonVariants({ variant: "outline", size: "sm" })}>
        {vi ? "Nguồn & phép tính" : "Sources & calculation"}
      </CollapsibleTrigger>
      <CollapsibleContent className="flex flex-col gap-2 pt-2">
        {tools.length === 0 ? (
          <p className="text-sm text-muted-foreground">{vi ? "Chưa có phép tính." : "No calculation yet."}</p>
        ) : (
          tools.map((tool) => (
            <div key={tool.id} className="flex flex-col gap-1">
              <p className="text-sm font-medium">{toolLabel(tool.name, lang)}</p>
              <p className="text-sm text-muted-foreground">{inputSentence(tool.name, tool.input, lang)}</p>
            </div>
          ))
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}

function toolLabel(name: string, lang: Lang): string {
  const label = LABELS[name]
  if (!label) return lang === "vi" ? "Phép tính" : "Calculation"
  return label[lang]
}

function inputSentence(name: string, input: unknown, lang: Lang): string {
  const vi = lang === "vi"
  const data = record(input) ?? {}
  const code = asString(data.code).trim().toUpperCase()
  const period = asString(data.period).trim().toUpperCase()
  if (name === "adjusted_change" && code && period) {
    return vi ? `Ngân hàng ${code}, kỳ ${period}.` : `Bank ${code}, period ${period}.`
  }
  if ((name === "bank_profile" || name === "forecast" || name === "adjusted_change") && code) {
    return vi ? `Ngân hàng ${code}.` : `Bank ${code}.`
  }
  if (name === "compare_banks") {
    const codes = stringList(data.codes).map((item) => item.trim().toUpperCase()).filter(Boolean)
    if (codes.length > 0) return vi ? `Các ngân hàng ${codes.join(", ")}.` : `Banks ${codes.join(", ")}.`
  }
  if (name === "glossary") {
    const term = clean(data.term)
    if (term) return vi ? `Thuật ngữ ${term}.` : `Term ${term}.`
  }
  if (name === "method") return vi ? "Một phần của phương pháp nghiên cứu." : "One part of the study method."
  return vi ? "Dùng snapshot đã xuất bản." : "Uses the published snapshot."
}

function prose(name: string, output: Record<string, unknown>, lang: Lang): string {
  const vi = lang === "vi"
  if (name === "overview") {
    const level = record(output.level)
    const median = asNumber(level?.npl_median_pct)
    const period = asString(level?.period)
    const levelLine =
      median == null
        ? ""
        : vi
          ? `Trung vị nợ xấu ${formatNumber(median, lang, 2)}%${period ? ` (${period})` : ""}.`
          : `Median NPL ${formatNumber(median, lang, 2)}%${period ? ` (${period})` : ""}.`
    const headline = record(output.headline)
    const head = clean(vi ? headline?.vi : headline?.en)
    return [levelLine, head].filter(Boolean).join(" ")
  }
  if (name === "adjusted_change") return adjustedSentence(output, lang)
  if (name === "market_reaction") return clean(vi ? output.reading_vi : output.reading_en)
  if (name === "method") {
    const entry = record(output.entry)
    const reading = clean(vi ? entry?.reading_vi : entry?.reading_en)
    const limit = clean(vi ? entry?.does_not_show_vi : entry?.does_not_show_en)
    return [reading, limit].filter(Boolean).join(" ")
  }
  if (name === "glossary") {
    const entry = record(output.entry)
    return clean(vi ? entry?.vi : entry?.en)
  }
  if (name === "bank_profile") {
    const bank = record(output.bank)
    return bank ? bankSummary(bank, lang) : ""
  }
  return ""
}

function adjustedSentence(output: Record<string, unknown>, lang: Lang): string {
  const row = record(output.row)
  const period = asString(row?.period)
  const raw = asNumber(row?.d_npl_pp)
  const adjusted = asNumber(row?.adjusted_change_pp)
  const rawText = raw == null ? "" : formatNumber(raw, lang, 2)
  const adjustedText = adjusted == null ? "" : formatNumber(adjusted, lang, 2)
  if (lang === "vi") {
    return [period, rawText ? `thay đổi thô ${rawText} điểm phần trăm` : "", adjustedText ? `đã điều chỉnh ${adjustedText} điểm phần trăm` : ""]
      .filter(Boolean)
      .join(", ")
  }
  return [period, rawText ? `raw change ${rawText} percentage points` : "", adjustedText ? `adjusted change ${adjustedText} percentage points` : ""]
    .filter(Boolean)
    .join(", ")
}

function bankSummary(bank: Record<string, unknown>, lang: Lang): string {
  const vi = lang === "vi"
  const code = asString(bank.code)
  const ownership = bank.ownership === "state" ? (vi ? "nhà nước" : "state") : bank.ownership === "private" ? (vi ? "tư nhân" : "private") : ""
  const q4 = asNumber(bank.q4_change_median_pp)
  const q1 = asNumber(bank.q1_rebound_median_pp)
  const latest = record(bank.latest)
  const period = asString(latest?.period)
  const adjusted = asNumber(latest?.adjusted_change_pp)
  const who = [code, ownership].filter(Boolean).join(" ")
  const q4Text = q4 == null ? "" : formatNumber(q4, lang, 2)
  const q1Text = q1 == null ? "" : formatNumber(q1, lang, 2)
  const adjustedText = adjusted == null ? "" : formatNumber(adjusted, lang, 2)
  const adjustedClause = adjustedText
    ? vi
      ? `${period ? `kỳ ${period} ` : ""}đã điều chỉnh ${adjustedText} điểm phần trăm`
      : `${period ? `period ${period} ` : ""}adjusted ${adjustedText} percentage points`
    : ""
  if (vi) {
    return [who, q4Text ? `trung vị quý 4 ${q4Text} điểm phần trăm` : "", q1Text ? `quý 1 ${q1Text} điểm phần trăm` : "", adjustedClause]
      .filter(Boolean)
      .join(", ")
  }
  return [who, q4Text ? `median Q4 change ${q4Text} percentage points` : "", q1Text ? `Q1 rebound ${q1Text} percentage points` : "", adjustedClause]
    .filter(Boolean)
    .join(", ")
}

function signalTexts(bank: Record<string, unknown>, lang: Lang): string[] {
  if (!Array.isArray(bank.signals)) return []
  return bank.signals.flatMap((item) => {
    const row = record(item)
    const text = clean(lang === "vi" ? row?.text_vi : row?.text_en)
    return text ? [text] : []
  })
}

function limitationLines(output: Record<string, unknown>, lang: Lang): string[] {
  if (!Array.isArray(output.items)) return []
  return output.items.flatMap((item) => {
    const row = record(item)
    const text = clean(lang === "vi" ? row?.vi : row?.en)
    return text ? [text] : []
  })
}

function quarterBars(output: Record<string, unknown>): { quarter: number; coef: number; lo: number | null; hi: number | null }[] {
  if (!Array.isArray(output.effects)) return []
  return output.effects.flatMap((item) => {
    const row = record(item)
    const quarter = asNumber(row?.quarter)
    const coef = asNumber(row?.coef_pp)
    if (quarter == null || coef == null) return []
    const ci = Array.isArray(row?.ci95) ? row.ci95 : []
    return [{ quarter, coef, lo: asNumber(ci[0]), hi: asNumber(ci[1]) }]
  })
}

function lineRows(series: unknown[]): LineRow[] {
  return series.map((item) => {
    const row = record(item)
    return {
      period: asString(row?.period),
      npl: asNumber(row?.npl_pct),
      coverage: asNumber(row?.coverage_pct),
      nim: asNumber(row?.nim_pct),
      ldr: asNumber(row?.ldr_pct),
      loanGrowth: asNumber(row?.loan_growth_pct),
    }
  })
}

function compareRows(output: Record<string, unknown>): { code: string; q4: number | null; q1: number | null }[] {
  if (!Array.isArray(output.rows)) return []
  return output.rows.flatMap((item) => {
    const row = record(item)
    const code = asString(row?.code)
    if (!code) return []
    return [{ code, q4: asNumber(row?.q4_change_median_pp), q1: asNumber(row?.q1_rebound_median_pp) }]
  })
}

function forecastPoint(output: Record<string, unknown>): { period: string; npl: number; lo: number; hi: number } | null {
  const forecast = record(output.forecast)
  const period = asString(forecast?.period)
  const npl = asNumber(forecast?.npl_pct)
  const lo = asNumber(forecast?.lo80)
  const hi = asNumber(forecast?.hi80)
  if (!period || npl == null || lo == null || hi == null) return null
  return { period, npl, lo, hi }
}

function openPath(name: string, input: unknown, output: unknown): string {
  if (name === "market_reaction") return "/thi-truong"
  if (name === "method" || name === "limitations") return "/phuong-phap"
  if (name === "bank_profile" || name === "adjusted_change" || name === "forecast") {
    const code = bankCodeOf(input, output)
    if (code) return `/ngan-hang/${encodeURIComponent(code)}`
  }
  return "/"
}

function bankCodeOf(input: unknown, output: unknown): string {
  const fromInput = asString(record(input)?.code).trim().toUpperCase()
  if (fromInput) return fromInput
  return asString(record(record(output)?.bank)?.code).trim().toUpperCase()
}

function withLang(path: string, lang: Lang): string {
  return lang === "en" ? `${path}?lang=en` : path
}

function csvRows(name: string, output: unknown, lang: Lang): string[][] {
  const data = record(output) ?? {}
  if (data.found === false) {
    return [["text"], [lang === "vi" ? "Không có trong snapshot." : "Not in the snapshot."]]
  }
  if (name === "quarter_effects") {
    const rows = [["quarter", "coef", "lo", "hi"]]
    for (const bar of quarterBars(data)) rows.push([String(bar.quarter), num(bar.coef, lang), num(bar.lo, lang), num(bar.hi, lang)])
    return rows
  }
  if (name === "bank_profile") {
    const bank = record(data.bank)
    const series = Array.isArray(bank?.series) ? lineRows(bank.series) : null
    if (series) {
      const rows = [["period", "npl", "coverage", "nim", "ldr", "loan_growth"]]
      for (const row of series) rows.push([row.period, num(row.npl, lang), num(row.coverage, lang), num(row.nim, lang), num(row.ldr, lang), num(row.loanGrowth, lang)])
      rows.push(["q4_change_median_pp", num(asNumber(bank?.q4_change_median_pp), lang)])
      rows.push(["q1_rebound_median_pp", num(asNumber(bank?.q1_rebound_median_pp), lang)])
      rows.push(["adjusted_change_pp", num(asNumber(record(bank?.latest)?.adjusted_change_pp), lang)])
      return rows
    }
    return [
      ["field", "value"],
      ["code", asString(bank?.code)],
      ["q4_change_median_pp", num(asNumber(bank?.q4_change_median_pp), lang)],
      ["q1_rebound_median_pp", num(asNumber(bank?.q1_rebound_median_pp), lang)],
      ["adjusted_change_pp", num(asNumber(record(bank?.latest)?.adjusted_change_pp), lang)],
    ]
  }
  if (name === "compare_banks") {
    const rows = [["code", "q4", "q1"]]
    for (const row of compareRows(data)) rows.push([row.code, num(row.q4, lang), num(row.q1, lang)])
    return rows
  }
  if (name === "forecast") {
    const point = forecastPoint(data)
    return [
      ["period", "npl", "lo", "hi"],
      [point?.period ?? "", num(point?.npl ?? null, lang), num(point?.lo ?? null, lang), num(point?.hi ?? null, lang)],
    ]
  }
  if (name === "overview") {
    const level = record(data.level)
    const benchmark = record(data.benchmark)
    const ci = Array.isArray(benchmark?.ci95) ? benchmark.ci95 : []
    return [
      ["field", "value"],
      ["npl_median_pct", num(asNumber(level?.npl_median_pct), lang)],
      ["period", asString(level?.period)],
      ["coef_pp", num(asNumber(benchmark?.coef_pp), lang)],
      ["lo", num(asNumber(ci[0]), lang)],
      ["hi", num(asNumber(ci[1]), lang)],
    ]
  }
  if (name === "adjusted_change") {
    const row = record(data.row)
    return [
      ["period", "raw_pp", "adjusted_pp"],
      [asString(row?.period), num(asNumber(row?.d_npl_pp), lang), num(asNumber(row?.adjusted_change_pp), lang)],
    ]
  }
  return [
    ["text"],
    [prose(name, data, lang)],
  ]
}

function num(value: number | null, lang: Lang): string {
  return value == null ? "" : formatNumber(value, lang, 2)
}

function fileName(name: string, id: string): string {
  const base = FILES[name] ?? "so-lieu"
  const suffix = id.replace(/[^a-z0-9]/gi, "").slice(-6) || "card"
  return `${base}-${suffix}.csv`
}

function downloadCsv(filename: string, rows: string[][]): void {
  const body = rows.map((row) => row.map(csvCell).join(",")).join("\r\n")
  const blob = new Blob(["\uFEFF", body], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function csvCell(value: string): string {
  if (/[",\r\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`
  return value
}

function clean(value: unknown): string {
  return visibleText(asString(value)).trim()
}

function record(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : ""
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === "string")
}

function noopPick() {
  return undefined
}
