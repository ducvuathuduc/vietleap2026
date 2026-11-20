import { breakEvenRenewal, ceilingStats, insuredSplit, interest, plan, type CeilingStats, type InsuredSplit, type Plan, type RateRow } from "./calc.ts"
import { formatSheetDate } from "./format.ts"
import {
  addMonths,
  bandRates,
  buildHeadline,
  chartFinding,
  chartPoints,
  screenCopy,
  clampCompare,
  horizonMonths,
  keyNumbers,
  rateForHorizon,
  sourceIsMachineReadable,
  type Lang,
} from "./view.ts"
import type { Snapshot, SnapshotBank } from "./types.ts"

export interface Selection {
  amount: number
  need: string
  online: boolean
  bank: string
  compare: string[]
  lang: Lang
  asOf: string
}

export interface ChartRow {
  term: number
  [code: string]: number | null
}

function asOfDate(snapshot: Snapshot): string {
  return snapshot.meta.generated_at.slice(0, 10)
}

export function selectionFromParams(
  params: Record<string, string | string[] | undefined>,
  snapshot: Snapshot,
): Selection {
  const asOf = asOfDate(snapshot)
  const one = (key: string) => {
    const value = params[key]
    return Array.isArray(value) ? value[0] : value
  }
  const amount = Number(one("amount"))
  const online = one("online")
  const compare = (one("cmp") ?? "").split(",").map((code) => code.trim()).filter(Boolean)
  const lang = one("lang") === "en" ? "en" : "vi"
  return {
    amount: Number.isFinite(amount) && amount >= 0 ? amount : 500_000_000,
    need: one("need") || addMonths(asOf, 6),
    online: online === "0" ? false : true,
    bank: (one("bank") || "OCB").toUpperCase(),
    compare,
    lang,
    asOf,
  }
}

function focusBank(snapshot: Snapshot, code: string): SnapshotBank {
  return snapshot.banks.find((bank) => bank.code === code) ?? snapshot.banks.find((bank) => bank.code === "OCB") ?? snapshot.banks[0]!
}

export function rateOptions(snapshot: Snapshot): RateRow[] {
  const rows: RateRow[] = []
  for (const bank of snapshot.banks) {
    for (const rate of bank.rates) {
      rows.push({
        bank_code: bank.code,
        term_months: rate.term_months,
        channel: rate.channel,
        tier: rate.tier,
        rate_pct: rate.rate_pct,
        grade: rate.grade,
        source_url: rate.readers[0]?.source_url || bank.sheet_url,
        sheet_date: bank.sheet_date,
      })
    }
  }
  return rows
}

export function saverModel(snapshot: Snapshot, selection: Selection) {
  const channel = selection.online ? "online" : "counter"
  const bank = focusBank(snapshot, selection.bank)
  const months = horizonMonths(selection.asOf, selection.need)
  const band = bandRates(bank.rates, channel)
  const breakEven = band.rate6 !== null && band.rate12 !== null ? breakEvenRenewal(band.rate12, 12, band.rate6, 6) : null
  const name = selection.lang === "en" ? bank.name_en : bank.name_vi
  const headline = bank.sheet_date && band.shortRate !== null && band.shortFlat && band.rate6 !== null && band.rate12 !== null && breakEven !== null
    ? buildHeadline({
        lang: selection.lang,
        bankName: name,
        channel,
        sheetDate: bank.sheet_date,
        shortRate: band.shortRate,
        shortFlat: true,
        rate6: band.rate6,
        rate12: band.rate12,
        breakEven,
        ceilingPct: snapshot.policy.ceiling.pct,
      })
    : selection.lang === "vi"
      ? `${name} chưa đủ kỳ đã kiểm trên kênh này để viết một câu quyết định.`
      : `${name} does not have enough checked terms on this channel for a decision sentence.`
  const numbers = keyNumbers({
    lang: selection.lang,
    ceilingPct: snapshot.policy.ceiling.pct,
    horizonMonths: months,
    channel,
    focus: bank.code,
    breakEven,
    banks: snapshot.banks,
  })
  const compare = clampCompare(selection.compare, bank.code)
  const series = [bank.code, ...compare].flatMap((code) => {
    const item = snapshot.banks.find((candidate) => candidate.code === code)
    if (!item) return []
    const points = chartPoints(item, channel)
    return points.length
      ? [{
          code,
          name: selection.lang === "en" ? item.name_en : item.name_vi,
          sheetDate: item.sheet_date ? formatSheetDate(item.sheet_date) : "",
          sourceUrl: item.sheet_url,
          points,
        }]
      : []
  })
  const terms = [...new Set(series.flatMap((item) => item.points.map((point) => point.term)))].sort((left, right) => left - right)
  const rows: ChartRow[] = terms.map((term) => {
    const row: ChartRow = { term }
    for (const item of series) {
      row[item.code] = item.points.find((point) => point.term === term)?.rate ?? null
    }
    return row
  })
  const interestVnd = numbers.yourRate !== null && numbers.yourTerm ? interest(selection.amount, numbers.yourRate, numbers.yourTerm) : null
  const insuredVnd = Math.min(selection.amount, snapshot.policy.cap.vnd)
  const excessVnd = Math.max(0, selection.amount - snapshot.policy.cap.vnd)
  const gapPp = numbers.yourRate === null ? null : numbers.yourRate - snapshot.policy.ceiling.pct
  const copy = interestVnd !== null && numbers.yourTerm !== null && numbers.yourRate !== null && gapPp !== null
    ? screenCopy({
        lang: selection.lang,
        bankName: name,
        channel,
        term: numbers.yourTerm,
        rate: numbers.yourRate,
        interestVnd,
        amount: selection.amount,
        ceilingRef: snapshot.policy.ceiling.legal_ref,
        gapPp,
        capRef: snapshot.policy.cap.legal_ref,
        excessVnd,
      })
    : null
  const chartTitle = band.rate6 !== null
    ? chartFinding({
        lang: selection.lang,
        bankName: name,
        rate6: band.rate6,
        shortRate: band.shortRate,
        shortFlat: band.shortFlat,
        ceilingPct: snapshot.policy.ceiling.pct,
      })
    : name
  const plans = plan(selection.amount, months, selection.online, rateOptions(snapshot), snapshot.policy.cap.vnd, {}, false)
  const splitOptions = snapshot.banks.flatMap((item) => {
    if (!item.sheet_date) return []
    const picked = rateForHorizon(item.rates, channel, months)
    if (!picked || picked.grade !== "verified") return []
    return [{ bank_code: item.code, term_months: picked.term, rate_pct: picked.rate }]
  })
  const split = insuredSplit(selection.amount, snapshot.policy.cap.vnd, splitOptions)
  return {
    headline,
    chartTitle,
    figures: {
      interestVnd,
      insuredVnd,
      excessVnd,
      gapPp,
      yourSub: copy?.yourSub ?? "",
      ceilingSub: copy?.ceilingSub ?? "",
      insuredSub: copy?.insuredSub ?? "",
    },
    numbers,
    chart: { series, rows },
    plans,
    split,
    bank,
    channel,
    horizonMonths: months,
    breakEven,
    compare,
  }
}

export interface PolicyKink {
  stats: CeilingStats
  depositorsPct: number
  valuePct: number
  basis: string
  source: string
  premiumPct: number
  premiumRef: string
  ceilingPct: number
  ceilingRef: string
  capVnd: number
  publications: { code: string; name: string; url: string; machineReadable: boolean }[]
}

export function policyModel(snapshot: Snapshot): PolicyKink {
  const rows: { bank_code: string; term_months: number; rate_pct: number; grade: string }[] = []
  for (const bank of snapshot.banks) {
    const channel = bank.rates.some((rate) => rate.channel === "online" && rate.tier === "") ? "online" : "counter"
    for (const rate of bank.rates) {
      if (rate.tier !== "" || rate.channel !== channel) continue
      rows.push({ bank_code: bank.code, term_months: rate.term_months, rate_pct: rate.rate_pct, grade: rate.grade })
    }
  }
  return {
    stats: ceilingStats(rows, snapshot.policy.ceiling.pct),
    depositorsPct: snapshot.policy.insured_coverage.depositors_pct,
    valuePct: snapshot.policy.insured_coverage.value_pct,
    basis: snapshot.policy.insured_coverage.basis,
    source: snapshot.policy.insured_coverage.source,
    premiumPct: snapshot.policy.premium.pct,
    premiumRef: snapshot.policy.premium.legal_ref,
    ceilingPct: snapshot.policy.ceiling.pct,
    ceilingRef: snapshot.policy.ceiling.legal_ref,
    capVnd: snapshot.policy.cap.vnd,
    publications: snapshot.banks.map((bank) => ({
      code: bank.code,
      name: bank.name_vi,
      url: bank.sheet_url,
      machineReadable: sourceIsMachineReadable(bank.sheet_url),
    })),
  }
}

export type { InsuredSplit, Plan }
