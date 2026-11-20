export const PAGE_SHELL = "min-h-full overflow-x-hidden bg-background text-foreground"
export const SERIES_ATTRIBUTION = "Nguồn: FiinQuant (FiinGroup)"
export const LARGE_BANKS = ["VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "STB"] as const
export const DECODER_DISCLAIMER = {
  vi: "Tool chỉ nêu cờ cần xem xét, không kết luận ngân hàng che giấu nợ xấu",
  en: "The tool only raises a flag to review. It does not conclude that a bank is hiding bad debt.",
}
export const BADGE_LABEL = {
  clean: { vi: "Cải thiện có cơ sở", en: "Improvement supported by the data" },
  g2: { vi: "Cờ vàng: nhóm 2 tăng", en: "Yellow flag: group 2 rose" },
  writeoff: { vi: "Cờ vàng: xóa nợ tăng", en: "Yellow flag: write-offs rose" },
  coverage: { vi: "Cờ vàng: bao phủ giảm", en: "Yellow flag: coverage fell" },
  seasonal: { vi: "Nhịp mùa vụ cuối năm", en: "Usual year-end movement" },
  missing: { vi: "Thiếu dữ liệu", en: "Missing data" },
} as const
const BADGE_SENTENCE = {
  clean: { vi: "NPL giảm và không có cờ trái chiều nào.", en: "NPL fell and none of the contrary flags fired." },
  g2: { vi: "NPL giảm nhưng tỷ lệ nợ nhóm 2 tăng.", en: "NPL fell while the group 2 loan ratio rose." },
  writeoff: { vi: "NPL giảm nhưng tỷ lệ xóa nợ tăng.", en: "NPL fell while the write-off ratio rose." },
  coverage: { vi: "NPL giảm nhưng dự phòng so với nợ xấu mỏng đi.", en: "NPL fell while provisions relative to NPL thinned." },
  seasonal: { vi: "Mức giảm quý 4 nằm trong dải quý 4 các năm khác của chính ngân hàng đó.", en: "The Q4 decline sits inside that bank's other Q4 changes." },
  missing: { vi: "Thiếu một đầu vào nên không gọi là cải thiện có cơ sở.", en: "An input is missing, so this is not called a supported improvement." },
} as const

export type Lang = "vi" | "en"
export type Ownership = "all" | "state" | "private"

export type Term = {
  coef_pp: number
  ci95: (number | null)[]
  p: number | null
  p_wild_bootstrap: number | null
  n: number
  clusters: number | null
}

export type QuarterEffect = Term & { quarter: number }

export type BankSeriesPoint = {
  period: string
  npl_pct: number | null
  coverage_pct: number | null
  ldr_pct: number | null
  nim_pct: number | null
  loan_growth_pct: number | null
}

export type BankQuarter = { period: string; d_npl_pp: number | null; adjusted_change_pp: number | null }

export type SnapshotBank = {
  code: string
  ticker: string
  name_vi: string
  name_en: string
  ownership: "state" | "private"
  q4_change_median_pp: number | null
  q1_rebound_median_pp: number | null
  down_then_up_years: number
  years: number
  quarter_means: { quarter: number; mean_pp: number | null }[]
  pairs: { year: number; q4_pp: number | null; q1_pp: number | null; reversed: boolean }[]
  latest: {
    period: string
    adjusted_change_pp: number | null
    forecast_next: { period: string; npl_pct: number; lo80: number; hi80: number } | null
  } | null
  signals: { id: string; period: string; text_vi: string; text_en: string }[]
  quarters: BankQuarter[]
  series?: BankSeriesPoint[]
}

export type Snapshot = {
  _fixture_note?: string
  meta: {
    snapshot_id: string
    generated_at: string
    period_start: string
    period_end: string
    n_banks: number
    n_bank_quarters: number
    publish_bank_series: boolean
    sources: { id: string; name: string; method: string; url: string; licence: string; retrieved_at: string; rows: number }[]
    quality: { id: string; name: string; status: string; detail: string }[]
    cleaning: { step: string; before: number; after: number; detail: string }[]
    schema: { table: string; keys: string; grain: string }[]
    eda: { href: string; summary_vi: string; summary_en: string }
  }
  headline: { vi: string; en: string; keys: string[] }
  kpis: {
    level: { npl_median_pct: number; period: string; n_banks: number }
    benchmark: Term
    trend: { down_then_up: { year: number; share_pct: number; n: number }[]; npl_4q_avg_median_pct: number | null; period: string }
  }
  series: { median_by_period: { period: string; npl_median_pct: number | null; npl_p25_pct: number | null; npl_p75_pct: number | null; coverage_median_pct: number | null; n_banks: number }[] }
  quarter_effects: QuarterEffect[]
  banks: SnapshotBank[]
  heterogeneity: { pre_period: string; high_banks: string[]; q4_high_npl: Term | null; q4_state: Term | null }
  linkage: { roa_absent: boolean; coverage_q4: Term | null; nim_q4: Term | null; loan_growth_q4: Term | null; roa_q4: Term | null }
  market: {
    car_by_day: { group: string; day: number; n: number; mean_car_pct: number | null; ci95: (number | null)[] | null }[]
    regressions: Record<string, { n: number | null; clusters: number | null; period?: string[] | null; terms: Record<string, Term | null>; unavailable_reason?: string | null }>
    events_with_car: number
    eligible_bank_quarters: number
    period_start: string | null
    period_end: string | null
    reading_vi: string
    reading_en: string
  }
  forecast: {
    backtest: { period: string; n: number; npl_pct: number | null; predicted_npl_pct: number | null; last_value: number | null; seasonal_naive: number | null }[]
    mae: { model: number; last_value: number; seasonal_naive: number }
    train_through: string
    test_period: string[]
    reading_vi: string
    reading_en: string
  }
  robustness: {
    leave_one_bank_out: { min: number | null; max: number | null }
    drop_2021_2022: Term | null
    state_vs_private: { state: Term | null; private: Term | null }
    state_vs_private_effects: { state: QuarterEffect[]; private: QuarterEffect[] }
    drop_effects: QuarterEffect[]
    median_regression: Term | null
    year_fe: Term | null
  }
  method: {
    id: string
    name_vi: string
    name_en: string
    spec_vi: string
    spec_en: string
    n: number
    reading_vi: string
    reading_en: string
    does_not_show_vi: string
    does_not_show_en: string
  }[]
  limitations: { vi: string; en: string }[]
  legal: { ref: string; text_vi: string; text_en: string }[]
  ai_use: { vi: string; en: string }[]
  decoder?: DecoderCell[] | PublishedDecoder
}

export type DecoderStatus = "clean" | "g2" | "writeoff" | "coverage" | "seasonal" | "missing" | "no_fall"
export type DecoderSignal = { id: "S1" | "S2" | "S3" | "S4"; text_vi: string; text_en: string }
export type DecoderRatio = { value: number | null; source: string | null; page: number | null }
export type DecoderInputs = {
  loans: number | null
  group2: number | null
  npl: number | null
  provision: number | null
  writeoff: number | null
  d_coverage_pp: number | null
  delta_g2_pp?: number | null
  delta_writeoff_pp?: number | null
  coverage_contested?: boolean
  ratios: { npl_ratio: DecoderRatio; g2_ratio: DecoderRatio; coverage: DecoderRatio; writeoff_ratio: DecoderRatio }
}
export type DecoderCell = {
  bank: string
  period: string
  d_npl_pp: number | null
  signals: DecoderSignal[]
  status: DecoderStatus
  inputs: DecoderInputs
}

export type Selection = { ownership: Ownership; dropEarly: boolean }

export type DataRow = {
  bank_code: string
  period: string
  d_npl_pp: number | null
  adjusted_change_pp: number | null
  npl_pct?: number | null
  coverage_pct?: number | null
  ldr_pct?: number | null
  nim_pct?: number | null
  loan_growth_pct?: number | null
}

const ABSENT_WILD = {
  vi: "Phép wild bootstrap theo cụm chưa có trong bản số liệu này.",
  en: "The wild cluster bootstrap is not in these figures.",
}

export function langFromQuery(value: string | string[] | undefined): Lang {
  const raw = Array.isArray(value) ? value[0] : value
  return raw === "en" ? "en" : "vi"
}

export function nextPeriod(period: string): string {
  const year = Number(period.slice(0, 4))
  const quarter = Number(period.slice(5))
  if (quarter === 4) return `${year + 1}Q1`
  return `${year}Q${quarter + 1}`
}

function previousPeriod(period: string): string {
  const year = Number(period.slice(0, 4))
  const quarter = Number(period.slice(5))
  if (quarter === 1) return `${year - 1}Q4`
  return `${year}Q${quarter - 1}`
}

function round4(value: number): number {
  return Math.round(value * 10000) / 10000
}

const FIIN_SOURCE = "FiinQuant (FiinGroup)"
const SIGNAL_TEXT = {
  S3: {
    text_vi: "Tỷ lệ nợ xấu giảm trong khi mức bao phủ nợ xấu giảm.",
    text_en: "The NPL ratio fell while NPL coverage declined.",
  },
  S4: {
    text_vi: "Mức giảm quý 4 nằm trong dải quý 4 các năm khác của ngân hàng này.",
    text_en: "The Q4 decline is inside this bank's range of other Q4 changes.",
  },
} as const

export function buildFiinQuantDecoder(
  banks: { code: string; series?: { period: string; npl_pct: number | null; coverage_pct: number | null }[] }[],
  periodEnd: string,
): DecoderCell[] {
  const window = [...new Set(banks.flatMap((bank) => (bank.series ?? []).map((row) => row.period)))]
    .filter((period) => period <= periodEnd)
    .sort()
  const cells: DecoderCell[] = []
  for (const bank of banks) {
    const points = new Map((bank.series ?? []).map((row) => [row.period, row]))
    const q4: { period: string; delta: number }[] = []
    for (const [period, row] of points) {
      const previous = points.get(previousPeriod(period))
      if (!period.endsWith("Q4") || row.npl_pct == null || previous?.npl_pct == null) continue
      q4.push({ period, delta: round4(row.npl_pct - previous.npl_pct) })
    }
    for (const period of window) {
      const row = points.get(period)
      const previous = points.get(previousPeriod(period))
      const dNpl = row?.npl_pct == null || previous?.npl_pct == null ? null : round4(row.npl_pct - previous.npl_pct)
      const dCoverage = row?.coverage_pct == null || previous?.coverage_pct == null ? null : round4(row.coverage_pct - previous.coverage_pct)
      const signals: DecoderSignal[] = []
      if (dNpl != null && dNpl < 0 && dCoverage != null && dCoverage < 0) signals.push({ id: "S3", ...SIGNAL_TEXT.S3 })
      if (dNpl != null && dNpl < 0 && period.endsWith("Q4")) {
        const others = q4.filter((item) => item.period !== period).map((item) => item.delta)
        if (others.length >= 2 && Math.min(...others) <= dNpl && dNpl <= Math.max(...others)) signals.push({ id: "S4", ...SIGNAL_TEXT.S4 })
      }
      const status: DecoderStatus = dNpl == null ? "missing" : dNpl >= 0 ? "no_fall" : signals.some((signal) => signal.id === "S3") ? "coverage" : signals.some((signal) => signal.id === "S4") ? "seasonal" : "missing"
      const ratio = (value: number | null): DecoderRatio => ({ value, source: value == null ? null : FIIN_SOURCE, page: null })
      cells.push({
        bank: bank.code,
        period,
        d_npl_pp: dNpl,
        signals,
        status,
        inputs: {
          loans: null,
          group2: null,
          npl: null,
          provision: null,
          writeoff: null,
          d_coverage_pp: dCoverage,
          ratios: {
            npl_ratio: ratio(row?.npl_pct ?? null),
            g2_ratio: { value: null, source: null, page: null },
            coverage: ratio(row?.coverage_pct ?? null),
            writeoff_ratio: { value: null, source: null, page: null },
          },
        },
      })
    }
  }
  return cells
}

type PublishedDecoder = {
  rows?: PublishedDecoderRow[]
  focus?: PublishedDecoderRow[]
  fiinquant_rows?: PublishedDecoderRow[]
  reading_vi?: string
  reading_en?: string
}

type PublishedDecoderRow = {
  bank_code?: string
  bank?: string
  period?: string
  npl_ratio?: number | null
  g2_ratio?: number | null
  coverage?: number | null
  loan_growth?: number | null
  nim?: number | null
  lagged_coverage?: number | null
  writeoff_ratio?: number | null
  delta_npl_ratio?: number | null
  delta_g2_ratio?: number | null
  delta_coverage?: number | null
  delta_writeoff_ratio?: number | null
  coverage_contested?: boolean
  coverage_source?: string | null
  loans_vnd_bn?: number | null
  group2_vnd_bn?: number | null
  npl_vnd_bn?: number | null
  provision_vnd_bn?: number | null
  writeoff_vnd_bn?: number | null
  status?: string
  signals?: { id?: string; text_vi?: string; text_en?: string }[]
}

function asPercent(value: number | null | undefined): number | null {
  return value == null ? null : round4(value * 100)
}

function publishedScore(row: PublishedDecoderRow): number {
  return (row.delta_npl_ratio != null ? 2 : 0) + (row.npl_ratio != null ? 1 : 0) + ((row.signals?.length ?? 0) > 0 ? 2 : 0)
}

function publishedStatus(row: PublishedDecoderRow): DecoderStatus {
  if (row.status === "missing") return "missing"
  const ids = (row.signals ?? []).map((signal) => signal.id)
  if (ids.includes("S3")) return "coverage"
  if (ids.includes("S1")) return "g2"
  if (ids.includes("S2")) return "writeoff"
  if (ids.includes("S4")) return "seasonal"
  if (row.status === "clean") return "clean"
  if (row.status === "not_applicable" || row.status === "no_fall") return "no_fall"
  if (row.delta_npl_ratio != null && row.delta_npl_ratio >= 0) return "no_fall"
  return "missing"
}

function publishedCell(row: PublishedDecoderRow): DecoderCell | null {
  const bank = row.bank_code ?? row.bank
  if (!bank || !row.period) return null
  const signals = (row.signals ?? []).flatMap<DecoderSignal>((signal) => {
    if (signal.id !== "S1" && signal.id !== "S2" && signal.id !== "S3" && signal.id !== "S4") return []
    return [{ id: signal.id, text_vi: signal.text_vi ?? "", text_en: signal.text_en ?? "" }]
  })
  const notes = "Thuyết minh BCTC / Financial statement notes"
  const ratio = (value: number | null | undefined, source: string): DecoderRatio => ({
    value: asPercent(value),
    source: value == null ? null : source,
    page: null,
  })
  return {
    bank,
    period: row.period,
    d_npl_pp: asPercent(row.delta_npl_ratio),
    signals,
    status: publishedStatus(row),
    inputs: {
      loans: row.loans_vnd_bn ?? null,
      group2: row.group2_vnd_bn ?? null,
      npl: row.npl_vnd_bn ?? null,
      provision: row.provision_vnd_bn ?? null,
      writeoff: row.writeoff_vnd_bn ?? null,
      d_coverage_pp: asPercent(row.delta_coverage),
      delta_g2_pp: asPercent(row.delta_g2_ratio),
      delta_writeoff_pp: asPercent(row.delta_writeoff_ratio),
      coverage_contested: row.coverage_contested,
      ratios: {
        npl_ratio: ratio(row.npl_ratio, FIIN_SOURCE),
        g2_ratio: ratio(row.g2_ratio, notes),
        coverage: ratio(row.coverage, row.coverage_source === "notes" ? notes : FIIN_SOURCE),
        writeoff_ratio: ratio(row.writeoff_ratio, notes),
      },
    },
  }
}

function publishedCells(bag: PublishedDecoder): DecoderCell[] {
  const merged = new Map<string, PublishedDecoderRow>()
  for (const list of [bag.rows, bag.focus, bag.fiinquant_rows]) {
    for (const row of list ?? []) {
      const bank = row.bank_code ?? row.bank
      if (!bank || !row.period) continue
      const key = `${bank}|${row.period}`
      const previous = merged.get(key)
      if (!previous || publishedScore(row) > publishedScore(previous)) merged.set(key, row)
    }
  }
  return [...merged.values()].flatMap((row) => {
    const cell = publishedCell(row)
    return cell ? [cell] : []
  })
}

function decoderCells(decoder: Snapshot["decoder"]): DecoderCell[] {
  if (!decoder) return []
  if (Array.isArray(decoder)) return decoder
  return publishedCells(decoder)
}

function decoderReading(cell: DecoderCell, lang: Lang): string {
  if (cell.status === "missing" && (cell.signals.length || cell.inputs.coverage_contested)) {
    const available = cell.signals.map((signal) => (lang === "vi" ? signal.text_vi : signal.text_en))
    if (cell.inputs.coverage_contested) available.push(lang === "vi" ? "Hai nguồn cho tỷ lệ bao phủ khác nhau" : "The two sources disagree on coverage")
    return `${BADGE_SENTENCE.missing[lang]} ${available.join(". ")}.`
  }
  const dG2 = cell.inputs.delta_g2_pp
  const dWriteoff = cell.inputs.delta_writeoff_pp
  if (cell.d_npl_pp != null && cell.d_npl_pp < 0 && ((dG2 != null && dG2 > 0) || (dWriteoff != null && dWriteoff > 0))) {
    const fall = formatNumber(Math.abs(cell.d_npl_pp), lang, 2)
    const contrary = dG2 != null && dG2 > 0
      ? (lang === "vi" ? `nợ nhóm 2 tăng ${formatNumber(dG2, lang, 2)} điểm %` : `group-2 loans rose ${formatNumber(dG2, lang, 2)} pp`)
      : (lang === "vi" ? `xóa nợ tăng ${formatNumber(dWriteoff ?? 0, lang, 2)} điểm %` : `write-offs rose ${formatNumber(dWriteoff ?? 0, lang, 2)} pp`)
    const page = cell.inputs.ratios.g2_ratio.page ?? cell.inputs.ratios.writeoff_ratio.page
    const where = page == null ? "" : (lang === "vi" ? `, cần xem thuyết minh trang ${page}` : `, see note page ${page}`)
    return lang === "vi"
      ? `NPL giảm ${fall} điểm %, nhưng ${contrary}: cờ vàng${where}.`
      : `NPL fell ${fall} pp, but ${contrary}: yellow flag${where}.`
  }
  const both = cell.signals.some((signal) => signal.id === "S3") && cell.signals.some((signal) => signal.id === "S4")
  if (both) {
    return lang === "vi"
      ? "NPL giảm, bao phủ giảm, và mức giảm quý 4 nằm trong dải các năm khác của ngân hàng này."
      : "NPL fell, coverage fell, and the Q4 decline sits inside this bank's other Q4 changes."
  }
  if (cell.status === "no_fall") {
    return lang === "vi" ? "NPL không giảm so với quý trước, nên không xét cờ cải thiện." : "NPL did not fall from the previous quarter, so this is not an improvement flag."
  }
  if (cell.status === "clean" || cell.status === "g2" || cell.status === "writeoff" || cell.status === "coverage" || cell.status === "seasonal" || cell.status === "missing") {
    return BADGE_SENTENCE[cell.status][lang]
  }
  return BADGE_SENTENCE.missing[lang]
}

export function decoderModel(snapshot: Snapshot, lang: Lang, scope: "preview" | "all" = "preview") {
  const cells = decoderCells(snapshot.decoder)
  const allPeriods = [...new Set(cells.map((cell) => cell.period))].sort()
  const periods = scope === "all" ? allPeriods : allPeriods.slice(-6)
  const grouped = new Map<string, Map<string, DecoderCell>>()
  for (const cell of cells) {
    const row = grouped.get(cell.bank) ?? new Map<string, DecoderCell>()
    row.set(cell.period, cell)
    grouped.set(cell.bank, row)
  }
  const rest = [...grouped.keys()].filter((code) => !(LARGE_BANKS as readonly string[]).includes(code)).sort((left, right) => left.localeCompare(right))
  const banks = [
    ...LARGE_BANKS.filter((code) => grouped.has(code)),
    ...(scope === "all" ? rest : []),
  ]
  return {
    title: lang === "vi" ? "NPL giảm quý này có cơ sở không?" : "Is this quarter's NPL decline supported?",
    note: lang === "vi"
      ? "Khi nợ xấu giảm, ô hiện phần đã biết: bao phủ có giảm hay không. Dải mùa vụ của chính ngân hàng đó cho biết quý 4 có nằm trong nhịp các năm khác hay không. Nhóm 2 và xóa nợ chưa có thì ghi bên dưới. Chỉ khi đủ bốn kiểm tra mới gọi là cải thiện có cơ sở."
      : "When bad debt falls, the cell shows what is already known, including whether coverage fell. That bank's own year-end range says whether the fourth quarter sits with its other years. Group 2 and write-offs are named underneath until they arrive. The cell calls the improvement supported only when all four checks pass.",
    disclaimer: DECODER_DISCLAIMER[lang],
    attribution: SERIES_ATTRIBUTION,
    moreLabel: scope === "preview" ? (lang === "vi" ? "Xem tất cả ngân hàng" : "See every bank") : null,
    moreHref: scope === "preview" ? pageHref("/giai-ma", lang) : null,
    periods,
    legend: (Object.keys(BADGE_LABEL) as (keyof typeof BADGE_LABEL)[]).map((status) => ({
      label: BADGE_LABEL[status][lang],
      sentence: BADGE_SENTENCE[status][lang],
    })),
    rows: banks.map((bank) => ({
      bank,
      cells: periods.map((period) => {
        const cell = grouped.get(bank)?.get(period)
        if (!cell) return null
        const label = cell.status === "no_fall" ? null : BADGE_LABEL[cell.status][lang]
        const face = cellFace(cell, lang)
        return {
          period,
          dNpl: cell.d_npl_pp,
          dNplText: cell.d_npl_pp == null ? "—" : formatNumber(cell.d_npl_pp, lang, 2),
          status: cell.status,
          label,
          badges: face.badges,
          pending: face.pending,
          largeMove: face.largeMove,
          signals: cell.signals.map((signal) => (lang === "vi" ? signal.text_vi : signal.text_en)),
          reading: decoderReading(cell, lang),
          inputs: cell.inputs,
        }
      }),
    })),
  }
}

export function formatNumber(value: number, lang: Lang, digits = 3): string {
  return new Intl.NumberFormat(lang === "vi" ? "vi-VN" : "en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

export function formatStamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Saigon",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date)
  const pick = (type: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === type)?.value ?? ""
  return `${pick("day")}/${pick("month")}/${pick("year")} ${pick("hour")}:${pick("minute")}`
}

export function formatGenerated(iso: string, lang: Lang): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat(lang === "en" ? "en-GB" : "vi-VN", {
    timeZone: "Asia/Saigon",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date)
}

function interval(ci: (number | null)[] | null | undefined): [number, number] | null {
  if (!ci || ci[0] == null || ci[1] == null) return null
  return [ci[0], ci[1]]
}

function everyYear(bank: SnapshotBank): boolean {
  return bank.years > 0 && bank.down_then_up_years === bank.years
}

function decisionSentence(term: Term, lang: Lang): string {
  const span = interval(term.ci95)
  const range = span
    ? lang === "vi"
      ? `khoảng 95% ${formatNumber(span[0], lang)} đến ${formatNumber(span[1], lang)}`
      : `95% interval ${formatNumber(span[0], lang)} to ${formatNumber(span[1], lang)}`
    : lang === "vi"
      ? "khoảng 95% chưa có"
      : "95% interval is not in these figures"
  return lang === "vi"
    ? `Chưa coi mức giảm NPL quý 4 là cải thiện bền. Đọc phần thay đổi sau hiệu ứng quý: ${formatNumber(term.coef_pp, lang)} điểm phần trăm so với quý 1 (${range}, n = ${term.n}).`
    : `Do not treat the Q4 NPL decline as a lasting improvement. Read the change after the quarter effect: ${formatNumber(term.coef_pp, lang)} pp versus Q1 (${range}, n = ${term.n}).`
}

function reversalTotals(rows: { share_pct: number; n: number }[]) {
  return rows.reduce((sum, row) => {
    sum.pairs += row.n
    sum.flips += Math.round((row.share_pct / 100) * row.n)
    return sum
  }, { flips: 0, pairs: 0 })
}

function plainHeadline(snapshot: Snapshot, lang: Lang): string {
  const coef = snapshot.kpis.benchmark.coef_pp
  const amount = formatNumber(Math.abs(coef), lang, 2)
  const { flips, pairs } = reversalTotals(snapshot.kpis.trend.down_then_up)
  const banks = snapshot.meta.n_banks
  const start = snapshot.meta.period_start.slice(0, 4)
  const end = snapshot.meta.period_end.slice(0, 4)
  if (lang === "vi") {
    const verb = coef < 0 ? "giảm" : "tăng"
    return `Quý 4 nào nợ xấu cũng đẹp hơn: trung bình ${verb} ${amount} điểm % so với quý 1, rồi quý 1 năm sau tăng lại ở ${flips}/${pairs} trường hợp (${banks} ngân hàng, ${start}–${end}).`
  }
  const verb = coef < 0 ? "falls" : "rises"
  return `Every Q4, bad debt looks better: on average it ${verb} ${amount} percentage points versus Q1, then the next Q1 rises again in ${flips}/${pairs} cases (${banks} banks, ${start}–${end}).`
}

function evidenceLine(term: Term, lang: Lang): string {
  const span = interval(term.ci95)
  const range = span
    ? `${formatNumber(span[0], lang, 2)} ${lang === "vi" ? "đến" : "to"} ${formatNumber(span[1], lang, 2)}`
    : lang === "vi" ? "chưa có" : "not in these figures"
  const wild = term.p_wild_bootstrap
  const wildText = wild == null
    ? lang === "vi" ? "p wild bootstrap chưa có" : "wild bootstrap p is not in these figures"
    : lang === "vi" ? `p wild bootstrap ${formatNumber(wild, lang, 3)}` : `wild bootstrap p ${formatNumber(wild, lang, 3)}`
  return lang === "vi"
    ? `Hồi quy hiệu ứng cố định theo ngân hàng; khoảng tin cậy 95% ${range}; n = ${term.n}; ${wildText}.`
    : `Bank fixed-effects regression; 95% confidence interval ${range}; n = ${term.n}; ${wildText}.`
}

function shareHelp(shares: { year: number; share: number }[], lang: Lang): string {
  if (!shares.length) return ""
  const latest = [...shares].sort((left, right) => left.year - right.year).at(-1)
  const highest = shares.reduce((best, row) => (row.share > best.share ? row : best))
  if (!latest) return ""
  const bit = (row: { year: number; share: number }) => `${formatNumber(row.share, lang, 1)}% ${lang === "vi" ? "năm" : "in"} ${row.year}`
  if (highest.year === latest.year) return bit(latest)
  return `${bit(latest)}; ${lang === "vi" ? "cao nhất" : "highest"} ${bit(highest)}`
}

const LARGE_MOVE_PP = 3
const FACE_TEXT = {
  coverageDown: { vi: "Bao phủ giảm", en: "Coverage fell" },
  coverageHold: { vi: "Bao phủ không giảm", en: "Coverage did not fall" },
  seasonal: { vi: "Trong nhịp mùa vụ", en: "Inside the year-end range" },
  g2Up: { vi: "Nhóm 2 tăng", en: "Group 2 rose" },
  g2Hold: { vi: "Nhóm 2 không tăng", en: "Group 2 did not rise" },
  writeoffUp: { vi: "Xóa nợ tăng", en: "Write-offs rose" },
  writeoffHold: { vi: "Xóa nợ không tăng", en: "Write-offs did not rise" },
  pending: { vi: "Chưa có nhóm 2, xóa nợ", en: "Group 2 and write-offs are not in yet" },
} as const

function cellFace(cell: DecoderCell, lang: Lang): { badges: string[]; pending: string | null; largeMove: boolean } {
  const largeMove = cell.d_npl_pp != null && Math.abs(cell.d_npl_pp) >= LARGE_MOVE_PP
  const fell = cell.d_npl_pp != null && cell.d_npl_pp < 0
  if (!fell) return { badges: [], pending: null, largeMove }
  if (cell.status === "clean") return { badges: [BADGE_LABEL.clean[lang]], pending: null, largeMove }
  const has = (id: DecoderSignal["id"]) => cell.signals.some((signal) => signal.id === id)
  const badges: string[] = []
  const coverage = cell.inputs.d_coverage_pp
  if (has("S3") || coverage != null) {
    badges.push(has("S3") || (coverage != null && coverage < 0) ? FACE_TEXT.coverageDown[lang] : FACE_TEXT.coverageHold[lang])
  }
  if (has("S4")) badges.push(FACE_TEXT.seasonal[lang])
  const g2 = cell.inputs.delta_g2_pp
  const g2Known = has("S1") || g2 != null
  if (g2Known) badges.push(has("S1") || (g2 != null && g2 > 0) ? FACE_TEXT.g2Up[lang] : FACE_TEXT.g2Hold[lang])
  const writeoff = cell.inputs.delta_writeoff_pp
  const writeoffKnown = has("S2") || writeoff != null
  if (writeoffKnown) badges.push(has("S2") || (writeoff != null && writeoff > 0) ? FACE_TEXT.writeoffUp[lang] : FACE_TEXT.writeoffHold[lang])
  const pending = g2Known && writeoffKnown
    ? null
    : !g2Known && !writeoffKnown
      ? FACE_TEXT.pending[lang]
      : lang === "vi"
        ? (g2Known ? "Chưa có xóa nợ" : "Chưa có nhóm 2")
        : (g2Known ? "Write-offs are not in yet" : "Group 2 is not in yet")
  return { badges, pending, largeMove }
}

function whySentences(level: Snapshot["kpis"]["level"], coef: number, shares: { year: number; share: number }[], lang: Lang): [string, string] {
  const latest = [...shares].sort((left, right) => left.year - right.year).at(-1)
  const highest = shares.reduce<(typeof shares)[number] | null>((best, row) => (!best || row.share > best.share ? row : best), null)
  const amount = formatNumber(Math.abs(coef), lang, 2)
  const levelText = formatNumber(level.npl_median_pct, lang, 2)
  if (!latest || !highest) {
    return lang === "vi"
      ? [`Nợ xấu trung vị quý ${level.period} là ${levelText}% trên ${level.n_banks} ngân hàng.`, "Chưa có tỷ lệ giảm rồi tăng lại."]
      : [`Median NPL in ${level.period} is ${levelText}% across ${level.n_banks} banks.`, "The down-then-up share is not in yet."]
  }
  const latestShare = formatNumber(latest.share, lang, 1)
  const highShare = formatNumber(highest.share, lang, 1)
  if (lang === "vi") {
    const high = highest.year === latest.year ? "" : `, cao nhất ${highShare}% năm ${highest.year}`
    return [
      `Nợ xấu trung vị quý ${level.period} là ${levelText}% trên ${level.n_banks} ngân hàng.`,
      `Quý 4 ${coef < 0 ? "thấp hơn" : "cao hơn"} quý 1 ${amount} điểm %. Năm ${latest.year} có ${latestShare}% ngân hàng giảm ở quý 4 rồi tăng ở quý 1${high}.`,
    ]
  }
  const high = highest.year === latest.year ? "" : `, and the high was ${highShare}% in ${highest.year}`
  return [
    `Median NPL in ${level.period} is ${levelText}% across ${level.n_banks} banks.`,
    `Q4 is ${amount} pp ${coef < 0 ? "lower" : "higher"} than Q1. In ${latest.year}, ${latestShare}% of banks fell in Q4 and rose in Q1${high}.`,
  ]
}

function barsFrom(effects: QuarterEffect[]) {
  return [...effects]
    .sort((left, right) => left.quarter - right.quarter)
    .map((effect) => {
      const span = interval(effect.ci95)
      return { quarter: effect.quarter, coef: effect.coef_pp, lo: span?.[0] ?? null, hi: span?.[1] ?? null }
    })
}

export function overviewModel(snapshot: Snapshot, lang: Lang, selection: Selection = { ownership: "all", dropEarly: false }) {
  const drop = snapshot.robustness.drop_2021_2022
  const dropEnabled = drop != null
  const useDrop = dropEnabled && selection.dropEarly && drop != null
  let benchmark = snapshot.kpis.benchmark
  let effects = snapshot.quarter_effects
  let sample: "baseline" | "state" | "private" | "drop_2021_2022" = "baseline"
  if (useDrop && drop) {
    benchmark = drop
    effects = snapshot.robustness.drop_effects
    sample = "drop_2021_2022"
  } else if (selection.ownership === "state" || selection.ownership === "private") {
    const group = snapshot.robustness.state_vs_private[selection.ownership]
    if (group) {
      benchmark = group
      effects = snapshot.robustness.state_vs_private_effects[selection.ownership]
      sample = selection.ownership
    }
  }
  const span = interval(benchmark.ci95)
  const wild = benchmark.p_wild_bootstrap
  const repeat = snapshot.banks
    .filter(everyYear)
    .map((bank) => ({ code: bank.code, years: bank.years, reversed: bank.down_then_up_years }))
    .sort((left, right) => left.code.localeCompare(right.code))
  const shares = snapshot.kpis.trend.down_then_up.map((row) => ({ year: row.year, share: row.share_pct, n: row.n }))
  const level = snapshot.kpis.level
  return {
    question: lang === "vi"
      ? "Mức giảm NPL quý 4 của ngân hàng niêm yết là cải thiện bền hay việc dọn sổ theo mùa?"
      : "Is the year-end fall in listed banks' NPL a lasting improvement or a seasonal clean-up?",
    headline: snapshot.headline[lang],
    plainHeadline: plainHeadline(snapshot, lang),
    evidenceLine: evidenceLine(snapshot.kpis.benchmark, lang),
    cards: [
      {
        title: lang === "vi" ? "Nợ xấu trung vị hiện nay" : "Median NPL now",
        value: level.npl_median_pct,
        digits: 2,
        suffix: "%",
        figure: `${formatNumber(level.npl_median_pct, lang, 2)}%`,
        help: `${level.period}, ${level.n_banks} ${lang === "vi" ? "ngân hàng" : "banks"}`,
      },
      {
        title: lang === "vi" ? "Quý 4 so với quý 1" : "Q4 versus Q1",
        value: snapshot.kpis.benchmark.coef_pp,
        digits: 2,
        suffix: lang === "vi" ? " điểm %" : " pp",
        figure: `${formatNumber(snapshot.kpis.benchmark.coef_pp, lang, 2)}${lang === "vi" ? " điểm %" : " pp"}`,
        help: lang === "vi" ? "so với quý 1" : "versus Q1",
      },
      {
        title: lang === "vi" ? "Giảm rồi tăng lại" : "Down, then up again",
        value: shares.at(-1)?.share ?? 0,
        digits: 1,
        suffix: "%",
        figure: shares.at(-1) ? `${formatNumber(shares.at(-1)?.share ?? 0, lang, 1)}%` : "—",
        help: shareHelp(shares, lang),
      },
    ],
    why: whySentences(level, snapshot.kpis.benchmark.coef_pp, shares, lang),
    decision: decisionSentence(benchmark, lang),
    level: {
      value: level.npl_median_pct,
      period: level.period,
      nBanks: level.n_banks,
      text: lang === "vi"
        ? `NPL trung vị ${level.period} là ${formatNumber(level.npl_median_pct, lang, 2)}% (${level.n_banks} ngân hàng).`
        : `Median NPL at ${level.period} is ${formatNumber(level.npl_median_pct, lang, 2)}% (${level.n_banks} banks).`,
    },
    benchmark: {
      coef: benchmark.coef_pp,
      ci: span,
      n: benchmark.n,
      clusters: benchmark.clusters,
      p: benchmark.p,
      wild,
      wildText: wild == null ? ABSENT_WILD[lang] : lang === "vi" ? `p wild bootstrap ${formatNumber(wild, lang, 4)}` : `wild bootstrap p ${formatNumber(wild, lang, 4)}`,
      sample,
      text: lang === "vi"
        ? `Quý 4 so với quý 1: ${formatNumber(benchmark.coef_pp, lang)} điểm phần trăm${span ? ` (khoảng 95% ${formatNumber(span[0], lang)} đến ${formatNumber(span[1], lang)})` : ""}, n = ${benchmark.n}${benchmark.clusters ? `, ${benchmark.clusters} ngân hàng` : ""}.`
        : `Q4 versus Q1: ${formatNumber(benchmark.coef_pp, lang)} pp${span ? ` (95% interval ${formatNumber(span[0], lang)} to ${formatNumber(span[1], lang)})` : ""}, n = ${benchmark.n}${benchmark.clusters ? `, ${benchmark.clusters} banks` : ""}.`,
    },
    trend: {
      shares,
      latestShare: shares.at(-1)?.share ?? null,
      repeatCount: repeat.length,
      fourQuarter: snapshot.kpis.trend.npl_4q_avg_median_pct,
      period: snapshot.kpis.trend.period,
      text: lang === "vi"
        ? `Tỷ lệ giảm rồi tăng: ${shares.map((row) => `${row.year} ${formatNumber(row.share, lang, 1)}% (n=${row.n})`).join(", ")}. ${repeat.length} ngân hàng đảo chiều ở mọi cặp năm của mã đó.`
        : `Down-then-up shares: ${shares.map((row) => `${row.year} ${formatNumber(row.share, lang, 1)}% (n=${row.n})`).join(", ")}. ${repeat.length} banks reversed in every year-pair they have.`,
    },
    series: snapshot.series.median_by_period.map((row) => ({
      period: row.period,
      median: row.npl_median_pct,
      p25: row.npl_p25_pct,
      p75: row.npl_p75_pct,
      nBanks: row.n_banks,
      q4: row.period.endsWith("Q4"),
    })),
    q4Mark: (() => {
      const marked = snapshot.series.median_by_period.filter((row) => row.period.endsWith("Q4") && row.npl_median_pct != null).at(-1)
      return marked ? { period: marked.period, label: lang === "vi" ? "Quý 4 giảm" : "Q4 dip" } : null
    })(),
    bars: barsFrom(effects),
    dropEnabled,
    dropReason: dropEnabled
      ? null
      : lang === "vi"
        ? "Công tắc bỏ 2021–2022 đang tắt vì bản số liệu chưa có hệ số đó."
        : "The 2021–2022 switch is off because that coefficient is not in these figures.",
    repeat,
    footer: {
      generatedAt: snapshot.meta.generated_at,
      sources: snapshot.meta.sources,
      method: (lang === "vi" ? snapshot.method.find((item) => item.id === "M2")?.spec_vi : snapshot.method.find((item) => item.id === "M2")?.spec_en) ?? "",
      legal: lang === "vi" ? snapshot.legal.at(-1)?.text_vi ?? "" : snapshot.legal.at(-1)?.text_en ?? "",
      publicLine: lang === "vi"
        ? `Nguồn: FiinQuant (FiinGroup), báo cáo tài chính hợp nhất; dữ liệu đến ${snapshot.meta.period_end}, cập nhật ${formatStamp(snapshot.meta.generated_at)}.`
        : `Source: FiinQuant (FiinGroup), consolidated financial statements; data through ${snapshot.meta.period_end}, updated ${formatStamp(snapshot.meta.generated_at)}.`,
    },
  }
}

export function bankRows(snapshot: Snapshot, ownership: Ownership) {
  return snapshot.banks
    .filter((bank) => ownership === "all" || bank.ownership === ownership)
    .slice()
    .sort((left, right) => {
      if (left.q4_change_median_pp == null && right.q4_change_median_pp == null) return left.code.localeCompare(right.code)
      if (left.q4_change_median_pp == null) return 1
      if (right.q4_change_median_pp == null) return -1
      return left.q4_change_median_pp - right.q4_change_median_pp || left.code.localeCompare(right.code)
    })
}

export function applyPublishFlag(snapshot: Snapshot, env: string | undefined = process.env.NPL_PUBLISH_BANK_SERIES): Snapshot {
  if (env !== "0" && snapshot.meta.publish_bank_series) return snapshot
  const hideLevels = (row: PublishedDecoderRow): PublishedDecoderRow => ({
    ...row, npl_ratio: null, coverage: null, loan_growth: null, nim: null, lagged_coverage: null,
  })
  const hiddenRatio = { value: null, source: null, page: null }
  const { decoder } = snapshot
  const hiddenDecoder = Array.isArray(decoder)
    ? decoder.map((cell) => ({ ...cell, inputs: {
        ...cell.inputs, ratios: { ...cell.inputs.ratios, npl_ratio: hiddenRatio, coverage: hiddenRatio },
      } }))
    : decoder && {
        ...decoder,
        rows: decoder.rows?.map(hideLevels),
        focus: decoder.focus?.map(hideLevels),
        fiinquant_rows: decoder.fiinquant_rows?.map(hideLevels),
      }
  return {
    ...snapshot,
    decoder: hiddenDecoder,
    meta: { ...snapshot.meta, publish_bank_series: false },
    banks: snapshot.banks.map((bank) => {
      const next = { ...bank }
      delete next.series
      return next
    }),
  }
}

export function bankModel(snapshot: Snapshot, code: string, lang: Lang) {
  const bank = snapshot.banks.find((item) => item.code.toUpperCase() === code.toUpperCase())
  if (!bank) return null
  const panel = snapshot.kpis.benchmark.coef_pp
  const change = bank.q4_change_median_pp
  const changeText = change == null
    ? lang === "vi"
      ? "Bản số liệu không có trung vị thay đổi quý 4 của ngân hàng này."
      : "These figures have no Q4-change median for this bank."
    : lang === "vi"
      ? `Trung vị thay đổi quý 4 là ${formatNumber(change, lang)} điểm phần trăm, so với hệ số cả nhóm ${formatNumber(panel, lang)}.`
      : `Median Q4 change is ${formatNumber(change, lang)} pp, against the panel coefficient ${formatNumber(panel, lang)}.`
  const matched = everyYear(bank)
  const headline = matched
    ? lang === "vi"
      ? `${bank.code} đảo chiều ở mọi cặp năm của ngân hàng này (${bank.down_then_up_years}/${bank.years}). ${changeText}`
      : `${bank.code} reversed in every year-pair on this file (${bank.down_then_up_years}/${bank.years}). ${changeText}`
    : lang === "vi"
      ? `${bank.code} không nằm trong danh sách đảo chiều mọi cặp năm. ${changeText}`
      : `${bank.code} is not in the every-year reversal list. ${changeText}`
  const lines = snapshot.meta.publish_bank_series && bank.series
    ? bank.series.map((row) => ({
        period: row.period,
        npl: row.npl_pct,
        coverage: row.coverage_pct,
        nim: row.nim_pct,
        ldr: row.ldr_pct,
        loanGrowth: row.loan_growth_pct,
      }))
    : null
  const forecast = bank.latest?.forecast_next
  return {
    code: bank.code,
    name: lang === "vi" ? bank.name_vi : bank.name_en,
    ownership: bank.ownership,
    everyYear: matched,
    headline,
    reminder: decisionSentence(snapshot.kpis.benchmark, lang),
    q4Median: bank.q4_change_median_pp,
    q1Median: bank.q1_rebound_median_pp,
    chart: [2, 3, 4].map((quarter) => ({
      quarter,
      bank: bank.quarter_means.find((row) => row.quarter === quarter)?.mean_pp ?? null,
      panel: snapshot.quarter_effects.find((row) => row.quarter === quarter)?.coef_pp ?? null,
    })),
    pairs: bank.pairs,
    adjusted: bank.latest?.adjusted_change_pp ?? null,
    latestPeriod: bank.latest?.period ?? null,
    forecast: forecast ? { period: forecast.period, npl: forecast.npl_pct, lo: forecast.lo80, hi: forecast.hi80 } : null,
    mae: {
      model: snapshot.forecast.mae.model,
      lastValue: snapshot.forecast.mae.last_value,
      seasonalNaive: snapshot.forecast.mae.seasonal_naive,
    },
    signals: bank.signals.map((signal) => ({ id: signal.id, period: signal.period, text: lang === "vi" ? signal.text_vi : signal.text_en })),
    lines,
    attribution: lines ? SERIES_ATTRIBUTION : null,
  }
}

const REGRESSION_LABEL: Record<string, { vi: string; en: string }> = {
  raw: { vi: "CAR trên biến động NPL gốc", en: "CAR on the raw NPL change" },
  adjusted: { vi: "CAR trên biến động NPL đã khử mùa vụ", en: "CAR on the seasonally adjusted NPL change" },
  raw_q4: { vi: "CAR quý 4 trên biến động NPL gốc", en: "Q4 CAR on the raw NPL change" },
  adjusted_q4: { vi: "CAR quý 4 trên biến động NPL đã khử mùa vụ", en: "Q4 CAR on the seasonally adjusted NPL change" },
  reported_or_deadline: { vi: "Ngày công bố nếu có, nếu không thì hạn", en: "Filing date when known, otherwise the deadline" },
  deadline_only: { vi: "Chỉ dùng hạn công bố", en: "Deadline only" },
  reported_or_deadline_q4: { vi: "Quý 4, ngày công bố nếu có", en: "Q4, filing date when known" },
  deadline_only_q4: { vi: "Quý 4, chỉ dùng hạn công bố", en: "Q4, deadline only" },
  actual_dates: { vi: "Quanh ngày công bố thực tế", en: "Around the actual filing date" },
  matched_actual: { vi: "Mẫu ghép theo ngày thực tế", en: "Sample matched on the actual date" },
  matched_deadline: { vi: "Mẫu ghép theo hạn công bố", en: "Sample matched on the deadline" },
}

const TERM_LABEL: Record<string, { vi: string; en: string }> = {
  d_npl_pct: { vi: "Hệ số", en: "Coefficient" },
  expected_d_npl_pct: { vi: "Phần dự kiến", en: "Expected change" },
  surprise_d_npl_pct: { vi: "Phần bất ngờ", en: "Surprise" },
}

function regressionBits(block: Snapshot["market"]["regressions"][string], lang: Lang): string[] {
  return Object.entries(block.terms).flatMap(([name, item]) => {
    if (!item || item.coef_pp == null) return []
    const title = TERM_LABEL[name]?.[lang] ?? (lang === "vi" ? "Hệ số" : "Coefficient")
    const span = interval(item.ci95)
    const range = span
      ? lang === "vi"
        ? ` (khoảng 95% ${formatNumber(span[0], lang)} đến ${formatNumber(span[1], lang)})`
        : ` (95% interval ${formatNumber(span[0], lang)} to ${formatNumber(span[1], lang)})`
      : ""
    return [`${title} ${formatNumber(item.coef_pp, lang)}${range}`]
  })
}

export function marketModel(snapshot: Snapshot, lang: Lang) {
  const days = [...new Set(snapshot.market.car_by_day.map((row) => row.day))].sort((left, right) => left - right)
  const points = days.map((day) => {
    const all = snapshot.market.car_by_day.find((row) => row.group === "all" && row.day === day)
    const q4 = snapshot.market.car_by_day.find((row) => row.group === "Q4" && row.day === day)
    return {
      day,
      all: all?.mean_car_pct ?? null,
      allLo: all?.ci95?.[0] ?? null,
      allHi: all?.ci95?.[1] ?? null,
      q4: q4?.mean_car_pct ?? null,
      q4Lo: q4?.ci95?.[0] ?? null,
      q4Hi: q4?.ci95?.[1] ?? null,
    }
  })
  const rows = Object.entries(snapshot.market.regressions).map(([id, block]) => {
    const bits = regressionBits(block, lang)
    const label = REGRESSION_LABEL[id]?.[lang] ?? (lang === "vi" ? "Phép hồi quy" : "Regression")
    const term = Object.values(block.terms).find((item) => item && item.coef_pp != null) ?? null
    const text = bits.length
      ? lang === "vi"
        ? `${label}: ${bits.join("; ")}, n = ${block.n ?? "—"}. Đây không phải quy tắc giao dịch.`
        : `${label}: ${bits.join("; ")}, n = ${block.n ?? "—"}. This is not a trading rule.`
      : lang === "vi"
        ? `${label}: chưa có số cho phép này.`
        : `${label}: this regression has no figure yet.`
    return { id, text, coef: term?.coef_pp ?? null }
  })
  return {
    groups: ["all", "Q4"] as const,
    points,
    rows,
    events: snapshot.market.events_with_car,
    eligible: snapshot.market.eligible_bank_quarters,
    reading: lang === "vi" ? snapshot.market.reading_vi : snapshot.market.reading_en,
  }
}

function termText(term: Term | null, lang: Lang): string {
  if (!term) return lang === "vi" ? "chưa có số" : "not in these figures"
  const span = interval(term.ci95)
  return lang === "vi"
    ? `${formatNumber(term.coef_pp, lang)} điểm phần trăm${span ? `, khoảng 95% ${formatNumber(span[0], lang)} đến ${formatNumber(span[1], lang)}` : ""}, n = ${term.n}`
    : `${formatNumber(term.coef_pp, lang)} pp${span ? `, 95% interval ${formatNumber(span[0], lang)} to ${formatNumber(span[1], lang)}` : ""}, n = ${term.n}`
}

export function methodModel(snapshot: Snapshot, lang: Lang) {
  const vi = lang === "vi"
  const sourceLines = snapshot.meta.sources.map((source) => `${source.name}: ${source.rows.toLocaleString(vi ? "vi-VN" : "en-US")} dòng`).join("; ")
  const leave = snapshot.robustness.leave_one_bank_out
  return {
    edaHref: snapshot.meta.eda.href,
    edaSummary: vi ? snapshot.meta.eda.summary_vi : snapshot.meta.eda.summary_en,
    stages: [
      { title: vi ? "Thu thập" : "Ingestion", body: sourceLines },
      { title: vi ? "Làm sạch" : "Cleaning", body: vi ? "Giá trị thiếu được giữ. Chênh lệch chỉ tính hai quý liên tiếp." : "Missing values are kept. Changes use consecutive quarters only." },
      { title: vi ? "Mô hình" : "Models", body: vi ? "M1 đến M7. Mỗi thẻ ghi thiết kế, cỡ mẫu, câu đọc và điều thẻ không cho thấy." : "M1 to M7. Each card states the design, the sample size, the reading, and what the card does not show." },
      {
        title: vi ? "Phục vụ" : "Serving",
        body: vi
          ? `${snapshot.meta.n_banks} ngân hàng, ${snapshot.meta.n_bank_quarters} ngân hàng-quý. Chuỗi gốc từng ngân hàng ${snapshot.meta.publish_bank_series ? "được" : "không"} đưa ra trang công khai.`
          : `${snapshot.meta.n_banks} banks, ${snapshot.meta.n_bank_quarters} bank-quarters. Per-bank raw series are ${snapshot.meta.publish_bank_series ? "published" : "not published"}.`,
      },
    ],
    cleaning: snapshot.meta.cleaning,
    schema: snapshot.meta.schema,
    quality: snapshot.meta.quality,
    models: snapshot.method.map((item) => ({
      id: item.id,
      name: vi ? item.name_vi : item.name_en,
      spec: vi ? item.spec_vi : item.spec_en,
      n: item.n,
      reading: vi ? item.reading_vi : item.reading_en,
      doesNotShow: vi ? item.does_not_show_vi : item.does_not_show_en,
    })),
    robustness: [
      { label: vi ? "Bỏ từng ngân hàng" : "Leave one bank out", text: vi ? `Hệ số quý 4 từ ${formatNumber(leave.min ?? 0, lang)} đến ${formatNumber(leave.max ?? 0, lang)}.` : `Q4 coefficient from ${formatNumber(leave.min ?? 0, lang)} to ${formatNumber(leave.max ?? 0, lang)}.` },
      { label: vi ? "Bỏ 2021–2022" : "Drop 2021–2022", text: termText(snapshot.robustness.drop_2021_2022, lang) },
      { label: vi ? "Nhà nước" : "State", text: termText(snapshot.robustness.state_vs_private.state, lang) },
      { label: vi ? "Tư nhân" : "Private", text: termText(snapshot.robustness.state_vs_private.private, lang) },
      { label: vi ? "Hồi quy trung vị" : "Median regression", text: termText(snapshot.robustness.median_regression, lang) },
      { label: vi ? "Thêm hiệu ứng năm" : "Year fixed effects", text: termText(snapshot.robustness.year_fe, lang) },
    ],
    linkageNote: snapshot.linkage.roa_absent
      ? vi
        ? "ROA không có trong nguồn. Thẻ liên hệ không dùng ROA."
        : "ROA is absent from the vendor feed. The linkage card does not use ROA."
      : vi
        ? "ROA có trong nguồn."
        : "ROA is in the source.",
    limitations: snapshot.limitations.map((item) => (vi ? item.vi : item.en)),
    legal: snapshot.legal.map((item) => ({ ref: item.ref, text: vi ? item.text_vi : item.text_en })),
    ai: snapshot.ai_use.map((item) => (vi ? item.vi : item.en)),
  }
}

export function dataRows(snapshot: Snapshot): DataRow[] {
  const raw = snapshot.meta.publish_bank_series
  const rows: DataRow[] = []
  for (const bank of snapshot.banks) {
    const series = new Map((bank.series ?? []).map((row) => [row.period, row]))
    const periods = new Set<string>(bank.quarters.map((row) => row.period))
    if (raw) for (const row of bank.series ?? []) periods.add(row.period)
    for (const period of periods) {
      const derived = bank.quarters.find((row) => row.period === period)
      const point = series.get(period)
      const record: DataRow = {
        bank_code: bank.code,
        period,
        d_npl_pp: derived?.d_npl_pp ?? null,
        adjusted_change_pp: derived?.adjusted_change_pp ?? null,
      }
      if (raw) {
        record.npl_pct = point?.npl_pct ?? null
        record.coverage_pct = point?.coverage_pct ?? null
        record.ldr_pct = point?.ldr_pct ?? null
        record.nim_pct = point?.nim_pct ?? null
        record.loan_growth_pct = point?.loan_growth_pct ?? null
      }
      rows.push(record)
    }
  }
  return sortDataRows(sortDataRows(rows, "period", 1), "bank_code", 1)
}

export function sortDataRows<T extends Record<string, string | number | null | undefined>>(rows: T[], key: keyof T, dir: 1 | -1): T[] {
  return rows.slice().sort((left, right) => {
    const a = left[key]
    const b = right[key]
    if ((a == null) && (b == null)) return 0
    if (a == null) return 1
    if (b == null) return -1
    if (typeof a === "number" && typeof b === "number") return (a - b) * dir
    return String(a).localeCompare(String(b)) * dir
  })
}

export function pageHref(path: string, lang: Lang, params?: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  if (lang === "en") search.set("lang", "en")
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) search.set(key, value)
  }
  const query = search.toString()
  return query ? `${path}?${query}` : path
}

function csvCell(value: string | number | null | undefined): string {
  if (value == null) return ""
  return String(value)
}

export function publicCsv(snapshot: Snapshot): string {
  const raw = snapshot.meta.publish_bank_series
  const headers = ["bank_code", "period", "d_npl_pp", "adjusted_change_pp"]
  if (raw) headers.push("npl_pct", "coverage_pct", "ldr_pct", "nim_pct", "loan_growth_pct")
  const lines = [headers.join(",")]
  for (const row of dataRows(snapshot)) {
    const cells = [row.bank_code, row.period, csvCell(row.d_npl_pp), csvCell(row.adjusted_change_pp)]
    if (raw) cells.push(csvCell(row.npl_pct), csvCell(row.coverage_pct), csvCell(row.ldr_pct), csvCell(row.nim_pct), csvCell(row.loan_growth_pct))
    lines.push(cells.join(","))
  }
  return lines.join("\n")
}
