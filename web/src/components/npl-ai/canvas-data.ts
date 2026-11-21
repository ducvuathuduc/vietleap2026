import type { NplDecoderCell, NplToolResults } from "../../lib/npl/agent/tools.ts"
import type { SnapshotAnswers } from "../../lib/npl/agent/snapshot-answers.ts"
import { BADGE_LABEL, formatNumber, pageHref, type Lang } from "../../lib/npl/view.ts"

export const TOOL_LABELS = {
  overview: { vi: "Số liệu toàn nhóm", en: "Panel figures" },
  quarter_effects: { vi: "Ước tính hiệu ứng quý", en: "Quarter effect estimates" },
  bank_profile: { vi: "Hồ sơ ngân hàng", en: "Bank profile" },
  compare_banks: { vi: "So sánh ngân hàng", en: "Bank comparison" },
  forecast: { vi: "Dự báo nợ xấu", en: "NPL forecast" },
  market_reaction: { vi: "Phản ứng thị trường", en: "Market reaction" },
  method: { vi: "Phương pháp nghiên cứu", en: "Study method" },
  limitations: { vi: "Giới hạn nghiên cứu", en: "Study limitations" },
  glossary: { vi: "Giải thích thuật ngữ", en: "Glossary" },
  adjusted_change: { vi: "Thay đổi đã điều chỉnh", en: "Adjusted change" },
  decoder: { vi: "Kiểm tra nợ xấu", en: "NPL decoder" },
  largest_writeoffs: { vi: "Xếp hạng xóa nợ", en: "Write-off rankings" },
} satisfies Partial<Record<keyof NplToolResults, Record<Lang, string>>>

type Name = keyof typeof TOOL_LABELS
type Successful<K extends Name> = Exclude<NplToolResults[K], { found: false }>
type Result = { [K in Name]: { name: K; output: Successful<K> } }[Name]
const STUDY_LABELS = {
  screen_declines: { vi: "Nợ xấu giảm, nợ nhóm 2 tăng", en: "Falling NPL, rising Group 2" },
  q4_drivers: { vi: "Yếu tố làm thay đổi nợ xấu quý 4", en: "Drivers of Q4 NPL change" },
  q1_rebound: { vi: "Tỷ lệ nợ xấu tăng lại vào quý 1", en: "Frequency of a Q1 NPL rebound" },
  quarter_breakdown: { vi: "Tỷ lệ nợ xấu quanh quý 4", en: "NPL around Q4" },
  coverage_effect: { vi: "Thay đổi tỷ lệ bao phủ quý 4", en: "Q4 coverage change" },
  rank_gap: { vi: "Chênh lệch thứ hạng tín dụng", en: "Credit-quality rank gaps" },
  early_warning: { vi: "Kiểm tra cảnh báo sớm", en: "Early warning comparison" },
} satisfies Partial<Record<keyof SnapshotAnswers, Record<Lang, string>>>

type StudyName = keyof typeof STUDY_LABELS
type StudyResult = { [K in StudyName]: { name: K; output: SnapshotAnswers[K] } }[StudyName]
export type ListedTool = { id: string; name: string; input: unknown; output: unknown }
type CanvasResult = (StudyResult | Result) & { tool: ListedTool }
export type ForecastResult = Successful<"forecast">
export type CompareResult = Successful<"compare_banks">
export type CsvCell = string | number | null

export function readResult(name: string, output: unknown): Result | null {
  if (!Object.hasOwn(TOOL_LABELS, name) || !output || typeof output !== "object") return null
  if ("found" in output && output.found === false) return null
  // The completed chat tool part carries the deterministic result for this tool name.
  return { name, output } as Result
}

export function toolLabel(name: string, lang: Lang): string {
  if (Object.hasOwn(STUDY_LABELS, name)) return STUDY_LABELS[name as StudyName][lang]
  return Object.hasOwn(TOOL_LABELS, name) ? TOOL_LABELS[name as Name][lang] : lang === "vi" ? "Phép tính" : "Calculation"
}

function readStudy(tool: ListedTool): StudyResult | null {
  if (!Object.hasOwn(STUDY_LABELS, tool.name)) return null
  if (!tool.output || typeof tool.output !== "object" || !("citations" in tool.output)) return null
  return { name: tool.name, output: tool.output } as StudyResult
}

export function bankCanvasMode(output: Successful<"bank_profile">, input: unknown): "trend" | "checks" | null {
  const explicitPeriod = Boolean(input && typeof input === "object" && "period" in input && typeof input.period === "string")
  if (!explicitPeriod && output.bank?.series?.some((row) => row.npl_pct != null || row.coverage_pct != null)) return "trend"
  return hasBankChecks(output.selected) ? "checks" : null
}

export function hasBankChecks(selected: Successful<"bank_profile">["selected"] | undefined): boolean {
  return Boolean(selected?.evidence.en.checks.length &&
    (selected.decoder_row || selected.decomposition || selected.scorecard || selected.seasonal || selected.evidence.en.reportedChange != null))
}

function hasFigures(result: StudyResult | Result, input: unknown): boolean {
  switch (result.name) {
    case "screen_declines":
    case "rank_gap":
    case "largest_writeoffs": return Boolean(result.output.rows?.length)
    case "compare_banks": return hasComparisonHistory(result.output) || (result.output.rows ?? []).some((row) =>
      row.npl_pct != null || row.group2_pct != null || row.d_npl_pp != null || row.adjusted_change_pp != null ||
      (result.output.requested_period != null && row.denominator_pp != null))
    case "early_warning": return Object.values(result.output.fits ?? {}).some((fit) => fit?.auc?.estimate != null)
    case "q4_drivers": return result.output.loan_growth_part_pp != null || result.output.bad_debt_part_pp != null
    case "q1_rebound": return Object.values(result.output.rates ?? {}).some((rate) => rate.share_pct != null)
    case "quarter_breakdown": return result.output.q4_pct != null
    case "coverage_effect": return result.output.effect?.coef_pp != null
    case "overview": return Boolean(result.output.level && result.output.benchmark && result.output.trend)
    case "quarter_effects": return Boolean(result.output.effects?.length)
    case "bank_profile": return bankCanvasMode(result.output, input) != null
    case "decoder": return hasBankChecks(result.output.selected) || result.output.row?.d_npl_pp != null || result.output.row?.adjusted_change_pp != null
    case "adjusted_change": return result.output.row?.d_npl_pp != null || result.output.row?.adjusted_change_pp != null
    case "forecast": return result.output.forecast?.npl_pct != null
    case "market_reaction": return result.output.car_all?.some((row) => row.mean_car_pct != null) ?? false
    default: return false
  }
}

export function findAnswerCanvas(tools: ListedTool[]): CanvasResult | null {
  let fallback: CanvasResult | null = null
  for (const tool of tools) {
    const study = readStudy(tool)
    if (study && hasFigures(study, tool.input)) return { ...study, tool }
    if (fallback) continue
    const result = readResult(tool.name, tool.output)
    if (result && hasFigures(result, tool.input)) fallback = { ...result, tool }
  }
  return fallback
}

export function sortEvidenceRows<T>(rows: T[], value: (row: T) => CsvCell, descending: boolean, lang: Lang): T[] {
  return [...rows].sort((left, right) => {
    const a = value(left)
    const b = value(right)
    if (a === null || b === null) return Number(a === null) - Number(b === null)
    const difference = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), lang)
    return descending ? -difference : difference
  })
}

export function hasComparisonHistory(output: CompareResult): boolean {
  return !output.requested_period && Boolean(output.rows?.some((row) => row.history?.some((point) => point.npl_pct != null)))
}

export function comparisonHistory(rows: { code: string; history?: { period: string; npl_pct: number | null }[] }[]) {
  const series = rows.map(({ code, history }) => ({ code, values: new Map(history?.map((row) => [row.period, row.npl_pct])) }))
  const periods = [...new Set(series.flatMap(({ values }) => [...values.keys()]))].sort()
  return periods.map((period) => ({
    period,
    ...Object.fromEntries(series.map(({ code, values }) => [code, values.get(period) ?? null])),
  }))
}

export function formatValue(value: number | null | undefined, lang: Lang, suffix = "", digits = 2): string {
  return value == null ? "—" : `${formatNumber(value, lang, digits)}${suffix}`
}

export function points(lang: Lang): string {
  return lang === "vi" ? " điểm %" : " pp"
}

export function decoderStatus(status: NplDecoderCell["status"], lang: Lang): string {
  if (status === "no_fall") return lang === "vi" ? "Nợ xấu không giảm" : "NPL did not fall"
  return BADGE_LABEL[status][lang]
}

export const CHECKS = [
  ["S1", "Nợ nhóm 2 tăng", "Group 2 loans rose"],
  ["S2", "Xóa nợ tăng", "Write-offs rose"],
  ["S3", "Tỷ lệ bao phủ giảm", "Coverage fell"],
  ["S4", "Mức giảm nằm trong nhịp mùa vụ", "Decline within the seasonal range"],
] as const

export const INPUTS = [
  ["loans", "Dư nợ khách hàng", "Customer loans"],
  ["group2", "Nợ nhóm 2", "Group 2 loans"],
  ["npl", "Nợ xấu", "Non-performing loans"],
  ["provision", "Dự phòng cuối kỳ", "Provision balance"],
  ["writeoff", "Xóa nợ trong kỳ", "Write-offs in the quarter"],
] as const

export const RATIOS = [
  ["npl_ratio", "Tỷ lệ nợ xấu", "NPL ratio"],
  ["g2_ratio", "Tỷ lệ nợ nhóm 2", "Group 2 ratio"],
  ["coverage", "Tỷ lệ bao phủ", "NPL coverage"],
  ["writeoff_ratio", "Tỷ lệ xóa nợ", "Write-off ratio"],
] as const

type ForecastRow = {
  period: string
  observed?: number | null
  estimate?: number
  band?: [number, number]
  error?: [number, number]
}

export function forecastRows(output: Pick<ForecastResult, "forecast" | "series">): ForecastRow[] {
  const rows: ForecastRow[] = output.series.map((row) => ({ period: row.period, observed: row.npl_pct }))
  const last = rows.at(-1)
  if (last?.observed != null) {
    last.estimate = last.observed
    last.band = [last.observed, last.observed]
  }
  const { period, npl_pct, lo80, hi80 } = output.forecast
  rows.push({ period, estimate: npl_pct, band: [lo80, hi80], error: [npl_pct - lo80, hi80 - npl_pct] })
  return rows
}

export function overviewFigures(output: Successful<"overview">, lang: Lang) {
  const vi = lang === "vi"
  const trend = output.trend.down_then_up.at(-1)
  return [
    { label: vi ? "Nợ xấu trung vị" : "Median NPL", value: formatValue(output.level.npl_median_pct, lang, "%"), period: output.level.period },
    { label: vi ? "Quý 4 so với quý 1" : "Q4 versus Q1", value: formatValue(output.benchmark.coef_pp, lang, points(lang)), period: null },
    { label: vi ? "Giảm rồi tăng lại" : "Down, then up again", value: formatValue(trend?.share_pct, lang, "%", 1), period: trend?.year },
  ]
}

export function openPage(name: string, input: unknown, lang: Lang): string {
  if (name === "market_reaction") return pageHref("/thi-truong", lang)
  if (name === "method" || name === "limitations" || name === "glossary") return pageHref("/phuong-phap", lang)
  if (name === "decoder" || name === "adjusted_change") return pageHref("/giai-ma", lang)
  if (name === "compare_banks" || name === "largest_writeoffs") return pageHref("/ngan-hang", lang)
  if ((name === "bank_profile" || name === "forecast") && input && typeof input === "object" && "code" in input && typeof input.code === "string") {
    return pageHref(`/ngan-hang/${encodeURIComponent(input.code.trim().toUpperCase())}`, lang)
  }
  return pageHref("/", lang)
}

export function inputSummary(name: string, input: unknown, lang: Lang): string {
  const vi = lang === "vi"
  const data = input && typeof input === "object" ? input as Record<string, unknown> : {}
  const parts: string[] = []
  if (typeof data.code === "string") parts.push(`${vi ? "Ngân hàng" : "Bank"} ${data.code.trim().toUpperCase()}`)
  if (typeof data.period === "string") parts.push(`${vi ? "Kỳ" : "Period"} ${data.period.trim().toUpperCase()}`)
  if (Array.isArray(data.codes)) parts.push(data.codes.filter((code): code is string => typeof code === "string").map((code) => code.trim().toUpperCase()).join(", "))
  if (typeof data.term === "string") parts.push(`${vi ? "Thuật ngữ" : "Term"} ${data.term}`)
  if (name === "method") parts.push(vi ? "Chủ đề phương pháp được hỏi" : "Requested method topic")
  return parts.filter(Boolean).join(" · ") || (vi ? "Dữ liệu nghiên cứu đã công bố" : "Published study data")
}

export function csvRows(result: Result | null, lang: Lang): CsvCell[][] {
  if (!result) return [["text"], [lang === "vi" ? "Chưa có số liệu công bố." : "No published figures available."]]
  switch (result.name) {
    case "overview": {
      const { level, benchmark, trend } = result.output
      const last = trend.down_then_up.at(-1)
      return [
        ["metric", "period", "value", "n", "lower_95_pp", "upper_95_pp"],
        ["median_npl_pct", level.period, level.npl_median_pct, level.n_banks, null, null],
        ["q4_vs_q1_pp", result.output.data_period, benchmark.coef_pp, benchmark.n, benchmark.ci95[0] ?? null, benchmark.ci95[1] ?? null],
        ["down_then_up_pct", last?.year ?? null, last?.share_pct ?? null, last?.n ?? null, null, null],
      ]
    }
    case "quarter_effects":
      return [["quarter", "coefficient_pp", "lower_95_pp", "upper_95_pp", "n"], ...result.output.effects.map((row): CsvCell[] => [row.quarter, row.coef_pp, row.ci95[0] ?? null, row.ci95[1] ?? null, row.n])]
    case "bank_profile": {
      const { bank } = result.output
      return [
        ["bank", "period", "npl_pct", "coverage_pct", "adjusted_change_pp", "decoder_status"],
        ...(bank.series ?? []).map((row): CsvCell[] => [
          bank.code, row.period, row.npl_pct, row.coverage_pct,
          row.period === bank.latest?.period ? bank.latest.adjusted_change_pp : null,
          row.period === result.output.decoder?.period ? result.output.decoder.status : null,
        ]),
        ...(!bank.series?.length && bank.latest ? [[bank.code, bank.latest.period, null, null, bank.latest.adjusted_change_pp, result.output.decoder?.status ?? null]] : []),
      ]
    }
    case "compare_banks":
      return [["bank", "period", "change_pp", "adjusted_change_pp"], ...result.output.rows.map((row): CsvCell[] => [row.code, row.period ?? row.latest_period, row.d_npl_pp, row.adjusted_change_pp])]
    case "largest_writeoffs":
      return [["bank", "period", "amount_vnd_bn", "share_pct"], ...result.output.rows.map((row): CsvCell[] => [row.bank, result.output.data_period, row.amount_vnd_bn, row.share_pct])]
    case "adjusted_change":
    case "decoder": {
      const { code, row, decoder } = result.output
      return [
        ["bank", "period", "metric", "value", "source", "page"],
        [code, row.period, "raw_change_pp", row.d_npl_pp, null, null],
        [code, row.period, "adjusted_change_pp", row.adjusted_change_pp, null, null],
        ...(decoder ? [
          ...CHECKS.map(([key]) => [code, row.period, key, decoder.checks[key], null, null]),
          ...INPUTS.map(([key]) => [code, row.period, key, decoder.inputs[key], null, null]),
          ...RATIOS.map(([key]) => [code, row.period, key, decoder.inputs.ratios[key].value, decoder.inputs.ratios[key].source, decoder.inputs.ratios[key].page]),
        ] : []),
      ]
    }
    case "forecast": {
      const { forecast, series, mae, backtest_period } = result.output
      const backtest = backtest_period.length ? [backtest_period[0], backtest_period.at(-1)].filter(Boolean).join("–") : null
      return [
        ["period", "metric", "value", "lower_80_pct", "upper_80_pct"],
        ...series.map((row): CsvCell[] => [row.period, "observed_npl_pct", row.npl_pct, null, null]),
        [forecast.period, "forecast_npl_pct", forecast.npl_pct, forecast.lo80, forecast.hi80],
        [backtest, "forecast_mae_pp", mae.model, null, null],
        [backtest, "last_value_mae_pp", mae.last_value, null, null],
        [backtest, "seasonal_mae_pp", mae.seasonal_naive, null, null],
      ]
    }
    case "market_reaction":
      return [["day", "mean_car_pct", "lower_95_pct", "upper_95_pct", "n"], ...result.output.car_all.map((row): CsvCell[] => [row.day, row.mean_car_pct, row.ci95?.[0] ?? null, row.ci95?.[1] ?? null, row.n])]
    case "method":
      return [["text", "n"], [lang === "vi" ? result.output.entry.reading_vi : result.output.entry.reading_en, result.output.entry.n]]
    case "limitations":
      return [["text"], ...result.output.items.map((item) => [item[lang]])]
    case "glossary":
      return [["text"], [result.output.entry[lang]]]
  }
}
