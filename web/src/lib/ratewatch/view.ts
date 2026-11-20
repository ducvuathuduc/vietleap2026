import { formatPct, formatSheetDate, formatVnd } from "./format.ts"

export interface HeadlineInput {
  lang: "vi" | "en"
  bankName: string
  channel: string
  sheetDate: string
  shortRate: number | null
  shortFlat: boolean
  rate6: number | null
  rate12: number | null
  breakEven: number | null
  ceilingPct?: number
}

function channelLabel(channel: string, lang: "vi" | "en"): string {
  if (channel === "counter") return lang === "vi" ? "quầy" : "counter"
  return channel
}

export function buildHeadline(input: HeadlineInput): string {
  const lang = input.lang
  const date = formatSheetDate(input.sheetDate)
  const channel = channelLabel(input.channel, lang)
  const ceiling = input.ceilingPct ?? 4.75
  const pct = (value: number | null) => formatPct(value ?? Number.NaN, 2, lang)
  const short = input.shortFlat && input.shortRate === ceiling
    ? lang === "vi"
      ? `đứng ở trần ${pct(input.shortRate)}%/năm`
      : `sits on the ${pct(input.shortRate)}%/year ceiling`
    : lang === "vi"
      ? `là ${pct(input.shortRate)}%/năm`
      : `is ${pct(input.shortRate)}%/year`
  const r6 = pct(input.rate6)
  const r12 = pct(input.rate12)
  const be = pct(input.breakEven)
  if (lang === "en") {
    return `On the ${input.bankName} ${channel} sheet dated ${date}, terms of 1–5 months ${short}, 6 months is ${r6}%/year and 12 months is ${r12}%/year; rolling a 6-month deposit ties or beats the 12-month lock only if the next 6-month rate is at least ${be}%/year. This is a calculation, not a forecast.`
  }
  return `Trên biểu ${input.bankName} ${channel} đề ngày ${date}, kỳ 1–5 tháng ${short}, kỳ 6 tháng là ${r6}%/năm và kỳ 12 tháng là ${r12}%/năm; gửi 6 tháng rồi gửi tiếp chỉ hoà hoặc hơn khoản khoá 12 tháng khi lãi suất kỳ 6 tháng lần sau từ ${be}%/năm trở lên.`
}

export type Grade = "verified" | "single" | "contested"
export type Lang = "vi" | "en"

export interface RatePoint {
  term_months: number
  channel: string
  tier: string
  rate_pct: number
  grade: Grade
  grade_note: string
  readers?: { value: number }[]
}

export interface ChartBank {
  code: string
  name_vi?: string
  sheet_date: string | null
  sheet_url?: string
  rates: RatePoint[]
}

const GRADE_LABEL = {
  verified: { vi: "Đã kiểm 2 nguồn", en: "Checked, 2 sources" },
  single: { vi: "1 nguồn", en: "1 source" },
  contested: { vi: "Mâu thuẫn", en: "Contested" },
} as const

const GRADE_ORDER: Record<Grade, number> = { verified: 0, single: 1, contested: 2 }

export function gradeBadge(grade: Grade, note: string, lang: Lang): { label: string; detail: string } {
  const detail = grade === "single" && note.includes("agent_only") ? "agent_only" : ""
  return { label: GRADE_LABEL[grade][lang], detail }
}

export function chartPoints(bank: ChartBank, channel: string): { term: number; rate: number; grade: Grade; mark: boolean }[] {
  if (!bank.sheet_date) return []
  return bank.rates
    .filter((row) => row.channel === channel && (row.tier ?? "") === "" && row.grade !== "contested")
    .slice()
    .sort((left, right) => left.term_months - right.term_months)
    .map((row) => ({
      term: row.term_months,
      rate: row.rate_pct,
      grade: row.grade,
      mark: row.term_months === 6 || row.term_months === 12,
    }))
}

export interface TableRow {
  bankCode: string
  bankName: string
  term: number
  channel: string
  tier: string
  grade: Grade
  gradeLabel: string
  gradeDetail: string
  rateText: string
  sheetDate: string
  sourceUrl: string
}

export function tableRows(banks: ChartBank[], lang: Lang): TableRow[] {
  const rows: TableRow[] = []
  for (const bank of banks) {
    if (!bank.sheet_date) continue
    for (const rate of bank.rates) {
      const values = (rate.readers?.length ? rate.readers : [{ value: rate.rate_pct }]).map((reader) => reader.value)
      const unique = [...new Set(values)]
      const badge = gradeBadge(rate.grade, rate.grade_note, lang)
      rows.push({
        bankCode: bank.code,
        bankName: bank.name_vi ?? bank.code,
        term: rate.term_months,
        channel: rate.channel,
        tier: rate.tier,
        grade: rate.grade,
        gradeLabel: badge.label,
        gradeDetail: badge.detail,
        rateText: unique.map((value) => `${formatPct(value, 2, lang)}%`).join(" · "),
        sheetDate: formatSheetDate(bank.sheet_date),
        sourceUrl: bank.sheet_url ?? "",
      })
    }
  }
  rows.sort((left, right) => GRADE_ORDER[left.grade] - GRADE_ORDER[right.grade] || left.term - right.term)
  return rows
}

export interface Persona {
  id: string
  labelVi: string
  labelEn: string
  amount: number
  horizonMonths: number
  needDate: string
  onlineOk: boolean
  bankCode: string
  channel: "online" | "counter"
}

export function addMonths(iso: string, months: number): string {
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number)
  const date = new Date(Date.UTC(year!, (month! - 1) + months, day))
  const y = date.getUTCFullYear()
  const m = String(date.getUTCMonth() + 1).padStart(2, "0")
  const d = String(date.getUTCDate()).padStart(2, "0")
  return `${y}-${m}-${d}`
}

export function horizonMonths(from: string, to: string): number {
  const [y1, m1, d1] = from.slice(0, 10).split("-").map(Number)
  const [y2, m2, d2] = to.slice(0, 10).split("-").map(Number)
  let months = (y2! - y1!) * 12 + (m2! - m1!)
  if (d2! < d1!) months -= 1
  return Math.max(0, months)
}

export function personaPresets(asOf: string): Persona[] {
  const base: Omit<Persona, "needDate">[] = [
    {
      id: "need-5m",
      labelVi: "1,2 tỷ · cần sau 5 tháng",
      labelEn: "1.2 billion · needed in 5 months",
      amount: 1_200_000_000,
      horizonMonths: 5,
      onlineOk: true,
      bankCode: "OCB",
      channel: "online",
    },
    {
      id: "counter-500",
      labelVi: "500 triệu · gửi tại quầy",
      labelEn: "500 million · at the counter",
      amount: 500_000_000,
      horizonMonths: 6,
      onlineOk: false,
      bankCode: "STB",
      channel: "counter",
    },
    {
      id: "retire",
      labelVi: "3 tỷ · nghỉ hưu",
      labelEn: "3 billion · retirement",
      amount: 3_000_000_000,
      horizonMonths: 12,
      onlineOk: true,
      bankCode: "OCB",
      channel: "online",
    },
  ]
  return base.map((item) => ({ ...item, needDate: addMonths(asOf, item.horizonMonths) }))
}

export function clampCompare(codes: string[], focus: string): string[] {
  const seen = new Set<string>()
  const picked: string[] = []
  for (const code of codes) {
    if (!code || code === focus || seen.has(code)) continue
    seen.add(code)
    picked.push(code)
    if (picked.length === 3) break
  }
  return picked
}

export function rateForHorizon(
  rates: RatePoint[],
  channel: string,
  horizonMonths: number,
): { term: number; rate: number; grade: Grade } | null {
  const eligible = rates.filter((row) => row.channel === channel && (row.tier ?? "") === "" && row.term_months <= horizonMonths && row.grade !== "contested")
  const verified = eligible.filter((row) => row.grade === "verified")
  const pool = verified.length ? verified : eligible.filter((row) => row.grade === "single")
  const picked = pool.slice().sort((left, right) => right.term_months - left.term_months)[0]
  if (!picked) return null
  return { term: picked.term_months, rate: picked.rate_pct, grade: picked.grade }
}

export function keyNumbers(input: {
  lang: Lang
  ceilingPct: number
  horizonMonths: number
  channel: string
  focus: string
  breakEven: number | null
  banks: ChartBank[]
}): {
  yourRate: number | null
  yourTerm: number | null
  ceilingPct: number
  best: { code: string; rate: number; term: number } | null
  breakEven: number | null
  breakEvenLabel: string
} {
  const focus = input.banks.find((bank) => bank.code === input.focus)
  const yours = focus?.sheet_date ? rateForHorizon(focus.rates, input.channel, input.horizonMonths) : null
  let best: { code: string; rate: number; term: number } | null = null
  if (yours) {
    for (const bank of input.banks) {
      if (bank.code === input.focus || !bank.sheet_date) continue
      const row = bank.rates.find((rate) => rate.channel === input.channel && (rate.tier ?? "") === "" && rate.term_months === yours.term && rate.grade === "verified")
      if (!row) continue
      if (!best || row.rate_pct > best.rate) best = { code: bank.code, rate: row.rate_pct, term: row.term_months }
    }
  }
  return {
    yourRate: yours?.rate ?? null,
    yourTerm: yours?.term ?? null,
    ceilingPct: input.ceilingPct,
    best,
    breakEven: input.breakEven,
    breakEvenLabel: input.lang === "vi" ? "phép tính, không phải dự báo" : "a calculation, not a forecast",
  }
}

export function sourceIsMachineReadable(url: string): boolean {
  return /\.(csv|json|xml)(?:$|[?#])/i.test(url)
}

function usableRate(rates: RatePoint[], channel: string, term: number): number | null {
  const rows = rates.filter((row) => row.channel === channel && (row.tier ?? "") === "" && row.term_months === term && row.grade !== "contested")
  const verified = rows.find((row) => row.grade === "verified")
  const single = rows.find((row) => row.grade === "single")
  return (verified ?? single)?.rate_pct ?? null
}

const LEGAL: Record<string, { vi: string; en: string }> = {
  AGRIBANK: { vi: "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam", en: "Vietnam Bank for Agriculture and Rural Development" },
  BIDV: { vi: "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", en: "Joint Stock Commercial Bank for Investment and Development of Vietnam" },
  EXIMBANK: { vi: "Ngân hàng TMCP Xuất Nhập Khẩu Việt Nam", en: "Vietnam Export Import Commercial Joint Stock Bank" },
  HDB: { vi: "Ngân hàng TMCP Phát triển Thành phố Hồ Chí Minh", en: "Ho Chi Minh City Development Joint Stock Bank" },
  MSB: { vi: "Ngân hàng TMCP Hàng Hải Việt Nam", en: "Vietnam Maritime Commercial Joint Stock Bank" },
  OCB: { vi: "Ngân hàng TMCP Phương Đông", en: "Orient Commercial Joint Stock Bank" },
  PVCOMBANK: { vi: "Ngân hàng TMCP Đại Chúng Việt Nam", en: "Vietnam Public Joint Stock Bank" },
  STB: { vi: "Ngân hàng TMCP Sài Gòn Thương Tín", en: "Saigon Thuong Tin Commercial Joint Stock Bank" },
  TCB: { vi: "Ngân hàng TMCP Kỹ thương Việt Nam", en: "Vietnam Technological and Commercial Joint Stock Bank" },
  VCBNEO: { vi: "Ngân hàng số VCBNeo (thương hiệu số của Vietcombank)", en: "VCBNeo digital bank (Vietcombank's digital brand)" },
  VIETBANK: { vi: "Ngân hàng TMCP Việt Nam Thương Tín", en: "Viet Nam Thuong Tin Commercial Joint Stock Bank" },
}

const BRANCH_TO_SHEET: Record<string, string> = {
  AGB: "AGRIBANK",
  EIB: "EXIMBANK",
  PVCB: "PVCOMBANK",
  VBB: "VIETBANK",
}

export function sheetCode(code: string): string {
  return BRANCH_TO_SHEET[code] ?? code
}

export function branchCode(code: string): string {
  return Object.entries(BRANCH_TO_SHEET).find(([, sheet]) => sheet === code)?.[0] ?? code
}

export function bankMenuLabel(code: string, lang: Lang): string {
  const legal = LEGAL[code]
  return legal ? `${code} · ${legal[lang]}` : code
}

export function chartFinding(input: {
  lang: Lang
  bankName: string
  rate6: number | null
  shortRate: number | null
  shortFlat: boolean
  ceilingPct: number
}): string {
  const rate6 = formatPct(input.rate6 ?? Number.NaN, 2, input.lang)
  const ceiling = formatPct(input.ceilingPct, 2, input.lang)
  const short = formatPct(input.shortRate ?? Number.NaN, 2, input.lang)
  const capped = input.shortFlat && input.shortRate === input.ceilingPct
  if (input.lang === "en") {
    return capped
      ? `${input.bankName} pays ${rate6}% from the 6-month term; terms of 1–5 months are capped at ${ceiling}%`
      : `${input.bankName} pays ${rate6}% from the 6-month term; terms of 1–5 months are ${short}%`
  }
  return capped
    ? `${input.bankName} trả ${rate6}% từ kỳ 6 tháng; kỳ 1–5 tháng bị giới hạn ở ${ceiling}%`
    : `${input.bankName} trả ${rate6}% từ kỳ 6 tháng; kỳ 1–5 tháng là ${short}%`
}

export function screenCopy(input: {
  lang: Lang
  bankName: string
  channel: string
  term: number
  rate: number
  interestVnd: number
  amount: number
  ceilingRef: string
  gapPp: number
  capRef: string
  excessVnd: number
}): { yourSub: string; ceilingSub: string; insuredSub: string } {
  const vi = input.lang === "vi"
  const channel = input.channel === "counter" ? (vi ? "quầy" : "counter") : input.channel
  const money = (value: number) => formatVnd(value, input.lang)
  const gap = formatPct(Math.abs(input.gapPp), 2, input.lang)
  const decision = input.ceilingRef.includes("2411/QĐ-NHNN") ? (vi ? "QĐ 2411/QĐ-NHNN" : "Decision 2411/QĐ-NHNN") : input.ceilingRef
  const cap = input.capRef.includes("05/2026") ? (vi ? "TT 05/2026" : "Circular 05/2026") : input.capRef
  const ceilingSub = input.gapPp === 0
    ? (vi ? `${decision} · kỳ ${input.term} tháng của bạn bằng trần` : `${decision} · your ${input.term}-month rate is on the ceiling`)
    : vi
      ? `${decision} · kỳ ${input.term} tháng của bạn ${input.gapPp > 0 ? "cao hơn" : "thấp hơn"} ${gap} điểm %`
      : `${decision} · your ${input.term}-month rate is ${gap} percentage points ${input.gapPp > 0 ? "higher" : "lower"}`
  return {
    yourSub: vi
      ? `${input.bankName} ${channel} · ${input.term} tháng · = ${money(input.interestVnd)} trên ${money(input.amount)}`
      : `${input.bankName} ${channel} · ${input.term} months · = ${money(input.interestVnd)} on ${money(input.amount)}`,
    ceilingSub,
    insuredSub: vi ? `${cap} · phần vượt: ${money(input.excessVnd)}` : `${cap} · above the cap: ${money(input.excessVnd)}`,
  }
}

export function mapHeadline(input: {
  lang: Lang
  provinces: { name_vi: string; name_en: string; branches_total: number | null; branches_by_bank: Record<string, number> }[]
  bestBankCode: string | null
}): string {
  const ranked = input.provinces
    .filter((item) => item.branches_total !== null)
    .slice()
    .sort((left, right) => (right.branches_total ?? 0) - (left.branches_total ?? 0) || left.name_vi.localeCompare(right.name_vi, "vi"))
  const first = ranked[0]
  const second = ranked[1]
  if (!first || !second || first.branches_total === null || second.branches_total === null) return ""
  const name = (item: { name_vi: string; name_en: string }) => input.lang === "en" ? item.name_en : item.name_vi
  const count = (value: number) => value.toLocaleString(input.lang === "en" ? "en-US" : "vi-VN")
  const missing = input.bestBankCode === null
    ? null
    : input.provinces.filter((item) => (item.branches_by_bank[input.bestBankCode!] ?? 0) === 0).length
  if (input.lang === "en") {
    const tail = missing === null ? "" : `; ${count(missing)} provinces have no branch of the bank with the highest checked online rate`
    return `${name(first)} has ${count(first.branches_total)} OpenStreetMap bank points, ${name(second)} has ${count(second.branches_total)}${tail}.`
  }
  const tail = missing === null ? "" : `; ở ${count(missing)} tỉnh không có chi nhánh của ngân hàng trả lãi online cao nhất`
  return `${name(first)} có ${count(first.branches_total)} điểm giao dịch ngân hàng trên OpenStreetMap, ${name(second)} có ${count(second.branches_total)}${tail}.`
}

export function quantileSteps(values: number[]): { group: number; min: number; max: number }[] {
  const sorted = values.filter((value) => Number.isFinite(value)).slice().sort((left, right) => left - right)
  if (!sorted.length) return []
  const buckets = Math.min(5, sorted.length)
  const groups = []
  for (let index = 0; index < buckets; index += 1) {
    const start = Math.floor((index * sorted.length) / buckets)
    const end = Math.max(start, Math.floor(((index + 1) * sorted.length) / buckets) - 1)
    groups.push({ group: index, min: sorted[start]!, max: sorted[end]! })
  }
  return groups
}

export function provinceOffers(
  province: { branches_by_bank: Record<string, number>; best_counter_12m: { bank: string; rate_pct: number; grade: Grade } | null },
  banks: ChartBank[],
): { code: string; name: string; branches: number; counter: { term: number; rate: number; grade: Grade } | null; online: { term: number; rate: number; grade: Grade } | null }[] {
  return Object.entries(province.branches_by_bank).map(([code, branches]) => {
    const sheet = sheetCode(code)
    const bank = banks.find((item) => item.code === sheet)
    const verified12 = (channel: string) => {
      const picked = bank?.rates.find((row) => row.channel === channel && (row.tier ?? "") === "" && row.term_months === 12 && row.grade === "verified")
      return picked ? { term: 12, rate: picked.rate_pct, grade: picked.grade } : null
    }
    const published = province.best_counter_12m
    const counter = verified12("counter") ?? (
      published && (published.bank === code || published.bank === sheet) && published.grade === "verified"
        ? { term: 12, rate: published.rate_pct, grade: published.grade }
        : null
    )
    return { code: sheet, name: bank?.name_vi ?? code, branches, counter, online: verified12("online") }
  })
}

export function bandRates(rates: RatePoint[], channel: string): {
  shortRate: number | null
  shortFlat: boolean
  rate6: number | null
  rate12: number | null
} {
  const shorts = [1, 2, 3, 4, 5].map((term) => usableRate(rates, channel, term)).filter((rate): rate is number => rate !== null)
  const shortFlat = shorts.length > 0 && shorts.every((rate) => rate === shorts[0])
  return {
    shortRate: shortFlat ? shorts[0]! : null,
    shortFlat,
    rate6: usableRate(rates, channel, 6),
    rate12: usableRate(rates, channel, 12),
  }
}
