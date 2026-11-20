// Deterministic tools for the NPL study assistant. Every tool reads the
// published snapshot only (web/seed/npl/snapshot.json, fixture fallback) and
// returns its values together with citations (source, period, n, CI where
// relevant) so the model can only speak numbers the snapshot carries.
import { decoderModel, type DecoderSignal, type Snapshot, type Term } from "../view.ts"

export interface NplCitation {
  source: string
  period: string | null
  n: number | null
  ci95: [number, number] | null
}

function cite(source: string, period: string | null, n: number | null, ci95: [number, number] | null = null): NplCitation {
  return { source, period, n, ci95 }
}

function toCi95(ci: (number | null)[] | null | undefined): [number, number] | null {
  const lo = ci?.[0]
  const hi = ci?.[1]
  return typeof lo === "number" && typeof hi === "number" ? ([lo, hi] as [number, number]) : null
}

function termCitation(prefix: string, term: Term, period: string | null): NplCitation {
  return cite(prefix, period, term.n, toCi95(term.ci95))
}

function periodRange(start: string | null | undefined, end: string | null | undefined): string | null {
  return start && end && start !== end ? `${start}–${end}` : end || start || null
}

function snapshotPeriod(snapshot: Snapshot): string | null {
  return periodRange(snapshot.meta.period_start, snapshot.meta.period_end)
}

type DecoderCheck = "flagged" | "clear" | "missing" | "inapplicable"

function decoderCell(snapshot: Snapshot, code: string, period: string | null | undefined) {
  if (!period || !snapshot.decoder) return null
  const lookup = (lang: "vi" | "en") => decoderModel(snapshot, lang, "all").rows
    .find((row) => row.bank === code)?.cells.find((cell) => cell?.period === period)
  const en = lookup("en")
  if (!en) return null
  const vi = lookup("vi")
  const { inputs, status } = en
  const fell = en.dNpl != null && en.dNpl < 0
  const check = (delta: number | null | undefined, flag: boolean, opposite: boolean): DecoderCheck => {
    if (!fell) return en.dNpl == null ? "missing" : "inapplicable"
    if (flag) return "flagged"
    if (delta == null) return status === "clean" ? "clear" : "missing"
    return opposite ? "flagged" : "clear"
  }
  // The view already reconciles overlapping publications and retains every active badge.
  const checks: Record<DecoderSignal["id"], DecoderCheck> = {
    S1: check(inputs.delta_g2_pp, status === "g2" || en.badges.includes("Group 2 rose"), (inputs.delta_g2_pp ?? 0) > 0),
    S2: check(inputs.delta_writeoff_pp, status === "writeoff" || en.badges.includes("Write-offs rose"), (inputs.delta_writeoff_pp ?? 0) > 0),
    S3: inputs.coverage_contested ? "missing" : check(inputs.d_coverage_pp, status === "coverage" || en.badges.includes("Coverage fell"), (inputs.d_coverage_pp ?? 0) < 0),
    S4: !fell || !period.endsWith("Q4")
      ? (en.dNpl == null ? "missing" : "inapplicable")
      : check(inputs.seasonal_band_available ? 0 : null, status === "seasonal" || en.badges.includes("Inside the year-end range"), false),
  }
  return {
    bank: code,
    period,
    d_npl_pp: en.dNpl,
    status,
    inputs,
    checks,
    reading_vi: vi?.reading ?? "",
    reading_en: en.reading,
  }
}

export type NplDecoderCell = NonNullable<ReturnType<typeof decoderCell>>

// --- overview --------------------------------------------------------------

export function overview(snapshot: Snapshot) {
  const last = snapshot.series.median_by_period.at(-1) ?? null
  return {
    data_period: snapshotPeriod(snapshot),
    headline: snapshot.headline,
    level: snapshot.kpis.level,
    benchmark: snapshot.kpis.benchmark,
    trend: snapshot.kpis.trend,
    last_median: last,
    citations: [
      cite("snapshot headline", snapshot.meta.period_end, snapshot.kpis.benchmark.n, toCi95(snapshot.kpis.benchmark.ci95)),
      cite("FiinQuant get_ratios (consolidated)", snapshot.meta.period_end, snapshot.meta.n_bank_quarters),
    ],
    note_vi: "Đây là liên hệ, không phải nhân quả; dự báo là phép tính, không phải lời hứa.",
    note_en: "M4–M6 results are association, not causation; forecasts are calculation, not a promise.",
  }
}

// --- quarter_effects -------------------------------------------------------

export function quarterEffects(snapshot: Snapshot) {
  const data_period = snapshotPeriod(snapshot)
  return {
    data_period,
    reference_quarter: 1,
    null_effect_pp: 0,
    effects: snapshot.quarter_effects,
    citations: snapshot.quarter_effects.map((e) => termCitation("quarter effects (Q2/Q3/Q4 vs Q1)", e, `Q${e.quarter}`)),
    note_vi: "Đây là liên hệ trong dữ liệu, không phải nhân quả.",
    note_en: "Association in the data, not causation.",
  }
}

// --- bank_profile ----------------------------------------------------------

export function bankProfile(snapshot: Snapshot, input: { code: string }) {
  const code = input.code.trim().toUpperCase()
  const bank = snapshot.banks.find((b) => b.code === code)
  if (!bank) return { found: false as const, data_period: null, citations: [] as NplCitation[] }
  return {
    found: true as const,
    data_period: periodRange(bank.quarters[0]?.period, bank.latest?.period ?? bank.quarters.at(-1)?.period),
    bank,
    decoder: decoderCell(snapshot, code, bank.latest?.period),
    citations: [cite("bank profile", bank.latest?.period ?? null, bank.years, null)],
  }
}

// --- adjusted_change -------------------------------------------------------

export function adjustedChange(snapshot: Snapshot, input: { code: string; period?: string }) {
  const code = input.code.trim().toUpperCase()
  const bank = snapshot.banks.find((b) => b.code === code)
  const period = input.period?.trim().toUpperCase() ?? bank?.latest?.period ?? null
  const row = bank?.quarters.find((q) => q.period === period) ?? null
  const cell = decoderCell(snapshot, code, period)
  if (!row && !cell) return { found: false as const, data_period: null, citations: [] as NplCitation[] }
  return {
    found: true as const,
    data_period: period,
    code,
    row: row ?? { period: cell!.period, d_npl_pp: cell!.d_npl_pp, adjusted_change_pp: null },
    decoder: cell,
    citations: [cite("adjusted change (bank-quarter)", period, 1)],
  }
}

export function decoder(snapshot: Snapshot, input: { code: string; period?: string }) {
  const result = adjustedChange(snapshot, input)
  if (!result.found) return result
  return {
    ...result,
    check_count: Object.keys(result.decoder?.checks ?? {}).length,
    monitored_loan_group: 2,
    citations: [cite("NPL decoder (bank-quarter)", result.data_period, 1)],
  }
}

// --- compare_banks ---------------------------------------------------------

export function compareBanks(snapshot: Snapshot, input: { codes: string[] }) {
  if (input.codes.length > 4) throw new Error("compare at most 4 banks")
  const rows: {
    code: string
    name_vi: string
    name_en: string
    ownership: "state" | "private"
    q4_change_median_pp: number | null
    q1_rebound_median_pp: number | null
    latest_period: string | null
    d_npl_pp: number | null
    adjusted_change_pp: number | null
    forecast_next: { period: string; npl_pct: number; lo80: number; hi80: number } | null
  }[] = []
  const missing: string[] = []
  for (const raw of input.codes) {
    const code = raw.trim().toUpperCase()
    const bank = snapshot.banks.find((b) => b.code === code)
    if (!bank) {
      missing.push(code)
      continue
    }
    rows.push({
      code: bank.code,
      name_vi: bank.name_vi,
      name_en: bank.name_en,
      ownership: bank.ownership,
      q4_change_median_pp: bank.q4_change_median_pp,
      q1_rebound_median_pp: bank.q1_rebound_median_pp,
      latest_period: bank.latest?.period ?? null,
      d_npl_pp: bank.quarters.find((q) => q.period === bank.latest?.period)?.d_npl_pp ?? null,
      adjusted_change_pp: bank.latest?.adjusted_change_pp ?? null,
      forecast_next: bank.latest?.forecast_next ?? null,
    })
  }
  return {
    data_period: periodRange(...latestPeriodBounds(rows)),
    rows,
    missing,
    citations: rows.map((row) => cite("bank medians and latest changes (FiinQuant panel)", row.latest_period, null)),
  }
}

function latestPeriodBounds(rows: { latest_period: string | null }[]): [string | undefined, string | undefined] {
  const periods = rows.flatMap((row) => row.latest_period ? [row.latest_period] : []).sort()
  return [periods[0], periods.at(-1)]
}

// --- forecast --------------------------------------------------------------

export function forecast(snapshot: Snapshot, input: { code: string }) {
  const code = input.code.trim().toUpperCase()
  const bank = snapshot.banks.find((b) => b.code === code)
  if (!bank) return { found: false as const, data_period: null, citations: [] as NplCitation[] }
  const next = bank.latest?.forecast_next ?? null
  if (!next) return { found: false as const, data_period: null, citations: [] as NplCitation[] }
  const series = (bank.series ?? []).filter((point) => point.period < next.period).map(({ period, npl_pct }) => ({ period, npl_pct }))
  return {
    found: true as const,
    data_period: periodRange(series[0]?.period, next.period),
    code,
    series,
    forecast: next,
    mae: snapshot.forecast.mae,
    backtest_period: snapshot.forecast.test_period,
    backtest_note_vi: snapshot.forecast.reading_vi || "Kiểm định trên các quý đã quan sát, so với dự báo giữ nguyên và dự báo mùa vụ.",
    backtest_note_en: snapshot.forecast.reading_en || "Backtest on observed quarters against last-value and seasonal baselines.",
    citations: [cite("forecast (model vs seasonal naive)", next.period, snapshot.forecast.backtest.length)],
    note_vi: "Đây là phép tính, không phải lời hứa.",
    note_en: "This is a calculation, not a promise.",
  }
}

// --- market_reaction -------------------------------------------------------

export function marketReaction(snapshot: Snapshot) {
  return {
    data_period: periodRange(snapshot.market.period_start, snapshot.market.period_end),
    events_with_car: snapshot.market.events_with_car,
    car_all: snapshot.market.car_by_day.filter((row) => row.group === "all"),
    regressions: snapshot.market.regressions,
    reading_vi: snapshot.market.reading_vi,
    reading_en: snapshot.market.reading_en,
    citations: [cite("market CAR around disclosure events", snapshot.market.period_end ?? null, snapshot.market.events_with_car)],
  }
}

// --- method ----------------------------------------------------------------

export function method(snapshot: Snapshot, input: { model_id: string }) {
  const id = input.model_id.trim().toUpperCase()
  const entry = snapshot.method.find((m) => m.id.toUpperCase() === id)
  if (!entry) return { found: false as const, data_period: null, valid_ids: snapshot.method.map((m) => m.id) }
  return {
    found: true as const,
    data_period: snapshotPeriod(snapshot),
    entry,
    null_effect_pp: /^M[2-6]$/.test(id) ? 0 : null,
    citations: [cite("study method", snapshot.meta.period_end, entry.n)],
  }
}

// --- limitations -----------------------------------------------------------

export function limitations(snapshot: Snapshot) {
  return {
    data_period: snapshotPeriod(snapshot),
    items: snapshot.limitations,
    legal: snapshot.legal,
    citations: [cite("snapshot limitations", snapshot.meta.period_end, snapshot.meta.n_bank_quarters)],
  }
}

// --- glossary --------------------------------------------------------------

const GLOSSARY: Record<string, { vi: string; en: string }> = {
  npl: {
    vi: "Nợ xấu (NPL): khoản cho vay mà người vay không trả được đúng hạn theo chuẩn của Ngân hàng Nhà nước.",
    en: "NPL: a loan the borrower is not repaying on schedule (non-performing loan).",
  },
  "adjusted change": {
    vi: "Thay đổi NPL sau khi loại bỏ hiệu ứng quý (so với quý 1) — đọc phần thay đổi sau hiệu ứng quý, không phải mức giảm thô.",
    en: "The NPL change after removing the quarter effect (versus Q1) — read it instead of the raw quarter-over-quarter move.",
  },
  "quarter effect": {
    vi: "Hiệu ứng quý: mức chênh lệch trung vị NPL của quý 2/3/4 so với quý 1 trong cùng năm.",
    en: "How much the median NPL differs in Q2/Q3/Q4 versus Q1 within the same year.",
  },
  "wild bootstrap": {
    vi: "Kiểm định wild cluster bootstrap theo cụm ngân hàng — p-value bền vững khi số ngân hàng ít.",
    en: "A wild cluster bootstrap over bank clusters — a sturdier p-value when banks are few.",
  },
  coverage: {
    vi: "Tỷ lệ bao phủ nợ xấu: dự phòng rủi ro tín dụng chia cho nợ xấu.",
    en: "Loan-loss reserves divided by NPLs.",
  },
  car: {
    vi: "Lợi suất bất thường tích luỹ (CAR) quanh sự kiện công bố báo cáo — so với ngày thường.",
    en: "Cumulative abnormal return around a disclosure event, versus normal days.",
  },
  ldr: {
    vi: "Tỷ lệ cho vay trên tiền gửi (LDR).",
    en: "Loan-to-deposit ratio.",
  },
  nim: {
    vi: "Thu nhập lãi thuần trên tài sản sinh lời (NIM).",
    en: "Net interest margin over earning assets.",
  },
}

export function glossary(snapshot: Snapshot, input: { term: string }) {
  void snapshot
  const aliases: Record<string, string> = {
    "nợ xấu": "npl",
    "no xau": "npl",
    "npl": "npl",
    "hiệu ứng quý": "quarter effect",
    "quarter effect": "quarter effect",
    "wild bootstrap": "wild bootstrap",
    "bao phủ nợ xấu": "coverage",
    "coverage": "coverage",
    "ldr": "ldr",
    "nim": "nim",
    "car": "car",
    "thay đổi đã điều chỉnh": "adjusted change",
    "adjusted change": "adjusted change",
  }
  const key = aliases[input.term.trim().toLowerCase()]
  const entry = key ? GLOSSARY[key] : undefined
  if (!entry) return { found: false as const, data_period: null, terms: Object.keys(GLOSSARY) }
  return {
    found: true as const,
    data_period: null,
    entry,
    citations: [cite("glossary (in-code dictionary)", null, null)],
  }
}

export type NplToolResults = {
  overview: ReturnType<typeof overview>
  quarter_effects: ReturnType<typeof quarterEffects>
  bank_profile: ReturnType<typeof bankProfile>
  adjusted_change: ReturnType<typeof adjustedChange>
  decoder: ReturnType<typeof decoder>
  compare_banks: ReturnType<typeof compareBanks>
  forecast: ReturnType<typeof forecast>
  market_reaction: ReturnType<typeof marketReaction>
  method: ReturnType<typeof method>
  limitations: ReturnType<typeof limitations>
  glossary: ReturnType<typeof glossary>
}
