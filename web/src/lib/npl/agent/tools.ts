// Deterministic tools for the NPL study assistant. Every tool reads the
// published snapshot only (web/seed/npl/snapshot.json, fixture fallback) and
// returns its values together with citations (source, period, n, CI where
// relevant) so the model can only speak numbers the snapshot carries.
import { decoderModel, type DecoderSignal, type Snapshot, type Term } from "../view.ts"
import { bankCheck, publishedBankQuarter, scorecardRanks } from "../research-view.ts"

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
  const corrections = snapshot.multiple_testing
  return {
    data_period,
    reference_quarter: 1,
    null_effect_pp: 0,
    effects: snapshot.quarter_effects,
    benchmark: snapshot.kpis.benchmark,
    robustness: snapshot.robustness,
    heterogeneity: snapshot.heterogeneity,
    decision_rule: snapshot.decision_rule,
    reversal: snapshot.reversal,
    hypothesis_tests: snapshot.seasonal_review?.hypotheses ?? null,
    adjusted_significance: corrections ? {
      q: corrections.q,
      n_pvalues: corrections.n_pvalues,
      rows: corrections.rows.filter((row) => row.test_id.startsWith("M2.")),
      reading_vi: corrections.reading_vi,
      reading_en: corrections.reading_en,
    } : null,
    median_by_period: snapshot.series.median_by_period,
    citations: snapshot.quarter_effects.map((e) => termCitation("quarter effects (Q2/Q3/Q4 vs Q1)", e, `Q${e.quarter}`)),
    note_vi: "Đây là liên hệ trong dữ liệu, không phải nhân quả.",
    note_en: "Association in the data, not causation.",
  }
}

// --- bank_profile ----------------------------------------------------------

function bankQuarter(snapshot: Snapshot, code: string, period: string) {
  const publicSeries = snapshot.meta.publish_bank_series
  return {
    period,
    evidence: { vi: bankCheck(snapshot, code, period, "vi"), en: bankCheck(snapshot, code, period, "en") },
    decoder_row: publicSeries ? publishedBankQuarter(snapshot, code, period) ?? null : null,
    decomposition: publicSeries ? snapshot.decomposition?.rows.find((row) => row.bank_code === code && row.period === period) ?? null : null,
    scorecard: publicSeries ? snapshot.scorecard?.rows?.find((row) => row.bank_code === code && row.period === period) ?? null : null,
    seasonal: publicSeries ? snapshot.context?.seasonal_adjustment?.series.find((row) => row.bank_code === code && row.period === period) ?? null : null,
  }
}

export function bankProfile(snapshot: Snapshot, input: { code: string; period?: string }) {
  const code = input.code.trim().toUpperCase()
  const bank = snapshot.banks.find((b) => b.code === code)
  if (!bank) return { found: false as const, data_period: null, citations: [] as NplCitation[] }
  const period = input.period ?? bank.latest?.period ?? bank.quarters.at(-1)?.period
  const selected = period ? bankQuarter(snapshot, code, period) : null
  return {
    found: true as const,
    data_period: input.period ?? periodRange(bank.quarters[0]?.period, period),
    bank,
    selected,
    scorecard_indicators: snapshot.scorecard?.indicators ?? [],
    decoder: decoderCell(snapshot, code, period),
    citations: [cite("FiinQuant (FiinGroup)", period ?? null, input.period ? (bank.quarters.some((row) => row.period === period) ? 1 : null) : bank.years)],
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
    watch_list_group: 2,
    row: {
      period: period!,
      d_npl_pp: row?.d_npl_pp ?? cell?.d_npl_pp ?? null,
      adjusted_change_pp: snapshot.context?.seasonal_adjustment?.series.find((item) => item.bank_code === code && item.period === period)?.adjusted_change_pp
        ?? row?.adjusted_change_pp ?? null,
    },
    decoder: cell,
    citations: [cite("adjusted change (bank-quarter)", period, 1)],
  }
}

export function decoder(snapshot: Snapshot, input: { code: string; period?: string }) {
  const result = adjustedChange(snapshot, input)
  if (!result.found) return result
  return {
    ...result,
    selected: result.data_period ? bankQuarter(snapshot, result.code, result.data_period) : null,
    check_count: Object.keys(result.decoder?.checks ?? {}).length,
    monitored_loan_group: 2,
    citations: [cite("NPL decoder (bank-quarter)", result.data_period, 1)],
  }
}

// --- compare_banks ---------------------------------------------------------

export function compareBanks(snapshot: Snapshot, input: { codes: string[]; period?: string; trend?: boolean }) {
  if (input.codes.length > 4) throw new Error("compare at most 4 banks")
  const missing: string[] = []
  const rows = [...new Set(input.codes.map((raw) => raw.trim().toUpperCase()))].flatMap((code) => {
    const bank = snapshot.banks.find((b) => b.code === code)
    if (!bank) {
      missing.push(code)
      return []
    }
    const period = input.period ?? bank.latest?.period ?? null
    const selected = period ? bankQuarter(snapshot, code, period) : null
    const series = snapshot.meta.publish_bank_series ? bank.series ?? [] : []
    const point = series.find((row) => row.period === period)
    const ranks = period && snapshot.meta.publish_bank_series ? scorecardRanks(snapshot.scorecard?.rows, code, period) : null
    const quarter = bank.quarters.find((row) => row.period === period)
    const group2 = selected?.scorecard?.values.group2 ?? selected?.decoder_row?.g2_ratio
    return [{
      code: bank.code,
      name_vi: bank.name_vi,
      name_en: bank.name_en,
      ownership: bank.ownership,
      q4_change_median_pp: bank.q4_change_median_pp,
      q1_rebound_median_pp: bank.q1_rebound_median_pp,
      latest_period: bank.latest?.period ?? null,
      period,
      npl_pct: point?.npl_pct ?? selected?.decomposition?.npl_pct ?? null,
      group2_pct: group2 == null ? null : 100 * group2,
      coverage_pct: selected?.decoder_row?.coverage_contested ? null : point?.coverage_pct ?? null,
      denominator_pp: selected?.decomposition?.denominator_pp ?? null,
      numerator_pp: selected?.decomposition?.numerator_pp ?? null,
      npl_rank: ranks?.npl ?? null,
      composite_rank: ranks?.composite ?? null,
      d_npl_pp: selected?.decomposition?.d_npl_pp ?? quarter?.d_npl_pp ?? null,
      adjusted_change_pp: selected?.seasonal?.adjusted_change_pp
        ?? (input.period ? quarter?.adjusted_change_pp : bank.latest?.adjusted_change_pp) ?? null,
      forecast_next: bank.latest?.forecast_next ?? null,
      history: input.trend ? series : [],
    }]
  })
  const periods = rows.flatMap((row) => input.trend ? row.history.map((point) => point.period) : row.period ? [row.period] : []).sort()
  return {
    data_period: input.period ?? periodRange(periods[0], periods.at(-1)),
    requested_period: input.period ?? null,
    bank_count: rows.length,
    watch_list_group: 2,
    rows,
    missing,
    citations: rows.map((row) => cite("FiinQuant (FiinGroup)", row.period, null)),
  }
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
    watch_list_group: 2,
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
    windows: snapshot.market.windows ?? null,
    price_models: snapshot.market.m8 ?? null,
    regressions: snapshot.market.regressions,
    reading_vi: snapshot.market.reading_vi,
    reading_en: snapshot.market.reading_en,
    citations: [cite("market CAR around disclosure events", snapshot.market.period_end ?? null, snapshot.market.events_with_car)],
  }
}

export function mentorOls(snapshot: Snapshot) {
  const { decoder } = snapshot
  const regression = decoder && !Array.isArray(decoder) ? decoder.regression : undefined
  const fits = regression?.fiinquant ?? null
  return {
    data_period: periodRange(fits?.full.period?.[0], fits?.full.period?.at(-1)) ?? snapshotPeriod(snapshot),
    fits,
    regression,
    specification_en: "Quarterly change in NPL ratio on quarterly write-offs, change in Group 2 ratio, year-over-year loan growth and prior-quarter coverage, with bank fixed effects.",
    specification_vi: "Hồi quy thay đổi tỷ lệ nợ xấu theo quý trên tỷ lệ xóa nợ, thay đổi nợ nhóm 2, tăng trưởng dư nợ cùng kỳ và bao phủ quý trước, có hiệu ứng cố định theo ngân hàng.",
    citations: [cite("FiinQuant (FiinGroup)", snapshotPeriod(snapshot), fits?.full.n ?? null)],
  }
}

export function seasonalAdjustment(snapshot: Snapshot) {
  const seasonal = snapshot.context?.seasonal_adjustment
  return {
    data_period: snapshotPeriod(snapshot),
    counts: seasonal?.counts ?? null,
    reading_vi: seasonal?.reading_vi ?? null,
    reading_en: seasonal?.reading_en ?? null,
    baseline: snapshot.decision_rule?.q1_rise_baseline ?? null,
    holdout: snapshot.decision_rule?.q4_oos ?? null,
    citations: [cite("FiinQuant (FiinGroup)", snapshotPeriod(snapshot), seasonal?.counts.adjustable ?? null)],
  }
}

export function policyWindows(snapshot: Snapshot, { year }: { year?: number }) {
  const policy = snapshot.context?.policy
  return {
    data_period: year ? String(year) : snapshotPeriod(snapshot),
    policy,
    requested_year: year ?? null,
    year_estimate: policy?.q4_by_year.find((row) => row.year === year) ?? null,
    citations: [cite("Official Gazette and FiinQuant (FiinGroup)", snapshotPeriod(snapshot), policy?.n ?? null)],
  }
}

export function largestWriteoffs(snapshot: Snapshot, input: { period: string; measure?: "amount" | "share" }) {
  const measure = input.measure ?? "amount"
  const rows = snapshot.meta.publish_bank_series ? snapshot.banks.flatMap(({ code }) => {
    const row = publishedBankQuarter(snapshot, code, input.period)
    if (!row?.writeoff_quarter_flow || row.writeoff_vnd_bn == null || (measure === "share" && row.writeoff_ratio == null)) return []
    return [{ bank: code, amount_vnd_bn: row.writeoff_vnd_bn, share_pct: row.writeoff_ratio == null ? null : 100 * row.writeoff_ratio }]
  }) : []
  rows.sort((a, b) => measure === "share" ? b.share_pct! - a.share_pct! : b.amount_vnd_bn - a.amount_vnd_bn)
  return {
    data_period: input.period,
    measure,
    rows,
    observed_n: rows.length,
    panel_banks: snapshot.meta.n_banks,
    basis_en: "Provisions used as the published proxy for quarterly write-offs. Share uses opening loans.",
    basis_vi: "Dự phòng đã sử dụng là chỉ báo xóa nợ trong quý. Tỷ lệ tính trên dư nợ đầu quý.",
    citations: [cite("FiinQuant (FiinGroup) and financial statement notes", input.period, rows.length)],
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
    bank_quarter_follow_up: ["loan growth", "Group 2 watch-list loans", "write-offs", "provisions and coverage"],
    citations: [cite("snapshot limitations", snapshot.meta.period_end, snapshot.meta.n_bank_quarters)],
  }
}

// --- glossary --------------------------------------------------------------

const GLOSSARY: Record<string, { vi: string; en: string }> = {
  npl: {
    vi: "Tỷ lệ nợ xấu (NPL) là dư nợ nhóm 3–5 chia tổng dư nợ. Nhóm 2 là nợ cần chú ý và nằm ngoài tử số.",
    en: "The non-performing loan ratio (NPL ratio) is the balance of loans in Groups 3–5 divided by total loans. Group 2 is on the watch list and sits outside the numerator.",
  },
  "loan groups": {
    vi: "Nhóm 1 là nợ đủ tiêu chuẩn, nhóm 2 là nợ cần chú ý, nhóm 3 là nợ dưới tiêu chuẩn, nhóm 4 là nợ nghi ngờ, và nhóm 5 là nợ có khả năng mất vốn. Tỷ lệ nợ xấu dùng nhóm 3–5 trong tử số.",
    en: "The five loan groups are standard (1), watch-list (2), substandard (3), doubtful (4), and potential loss (5). The NPL ratio includes Groups 3–5 in its numerator.",
  },
  "write-off and recovery": {
    vi: "Xóa nợ bằng dự phòng đưa khoản nợ ra khỏi số dư nợ xấu trên bảng cân đối, người vay vẫn có nghĩa vụ trả. Thu hồi nợ là thực sự thu được tiền. Hãy xem riêng tiền thu hồi và dự phòng đã dùng nếu cần biết chất lượng tín dụng có cải thiện.",
    en: "A provision-funded write-off removes the loan from the reported NPL balance, and the borrower still owes the debt. Recovery means cash was actually collected. Check cash recoveries and provisions used separately when assessing improvement.",
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
    "npl ratio": "npl",
    "tỷ lệ nợ xấu": "npl",
    "loan groups": "loan groups",
    "five loan groups": "loan groups",
    "nhóm nợ": "loan groups",
    "write-off": "write-off and recovery",
    "write-offs": "write-off and recovery",
    "write-off and recovery": "write-off and recovery",
    "recovery": "write-off and recovery",
    "xóa nợ": "write-off and recovery",
    "thu hồi nợ": "write-off and recovery",
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
  mentor_ols: ReturnType<typeof mentorOls>
  seasonal_adjustment: ReturnType<typeof seasonalAdjustment>
  policy_windows: ReturnType<typeof policyWindows>
  largest_writeoffs: ReturnType<typeof largestWriteoffs>
}
