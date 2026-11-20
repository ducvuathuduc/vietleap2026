// RateWatch analytics: the TypeScript port of engine/vlkit/ratewatch/analytics.py.
// Simple interest only, on posted rows. No forecast and no regression enters the
// decision path; the break-even renewal rate is a calculation on today's posted
// rates, not a posted rate and not a forecast.
//
// Behaviour must stay identical to the Python engine (same fixture
// tests/fixtures/ratewatch/analytics_cases.json, same results): rates are
// percent per year, money is VND, interest at maturity is simple
// (P * r * months/12, or P * r * days/365 for a day count), and both ports
// evaluate the same expressions in the same order so float results match.

export const INSURED_CAP_VND = 350_000_000 // Thong tu 05/2026/TT-NHNN Dieu 3
export const CEILING_PCT = 4.75 // Quyet dinh 2411/QD-NHNN, 1 to <6 months
const GRADED = ["verified", "single"] // grades that feed decision medians

export interface RateRow {
  bank_code: string
  term_months: number
  channel: string
  tier: string
  rate_pct: number
  grade: string
  source_url: string
  sheet_date: string | null
}

export interface SplitOption {
  bank_code: string
  term_months: number
  rate_pct: number
}

export interface SplitAllocation {
  bank_code: string
  amount: number
  interest_vnd: number
  total_vnd: number
}

export interface InsuredSplit {
  allocations: SplitAllocation[]
  allocated_vnd: number
  remainder_vnd: number
  fully_insured: boolean
  insured_share: number
}

export interface PlanAmount {
  bank_code: string
  amount: number
}

export interface Plan {
  kind: "single" | "ladder_6_renewal" | "split"
  early_withdrawal: boolean
  interest_vnd: number
  value_at_horizon: number
  idle_months: number | null
  second_leg_assumption?: string
  insured_share: number
  rows: RateRow[]
  amounts: PlanAmount[]
}

export interface CeilingJump {
  bank_code: string
  jump_pp: number
  graded: boolean
}

export interface CeilingStats {
  quotes_1_5m: number
  at_ceiling: number
  above: number
  jumps: CeilingJump[]
  jump_5_6_pp_median: number | null
  n_banks: number
  n_banks_graded: number
  grade_basis: string
}

export function interest(P: number, ratePct: number, months?: number, days?: number, basis = "at_maturity"): number {
  if (basis !== "at_maturity") throw new Error(`unsupported interest basis: ${basis}`)
  if ((months === undefined) === (days === undefined)) throw new Error("provide exactly one of months or days")
  if (P < 0) throw new Error("P must be >= 0")
  if (months !== undefined) {
    if (months < 0) throw new Error("months must be >= 0")
    return P * (ratePct / 100) * (months / 12)
  }
  const d = days as number
  if (d < 0) throw new Error("days must be >= 0")
  return P * (ratePct / 100) * (d / 365)
}

export function breakEvenRenewal(rLong: number, longM: number, rShort: number, shortM: number): number {
  if (longM <= shortM) throw new Error("long_m must exceed short_m")
  const growLong = 1 + (rLong / 100) * (longM / 12)
  const growShort = 1 + (rShort / 100) * (shortM / 12)
  if (growShort <= 0) throw new Error("short leg growth factor must be positive")
  const f = (growLong / growShort - 1) * (12 / (longM - shortM))
  return f * 100
}

export function earlyWithdrawal(
  P: number,
  postedRate: number,
  demandRate: number,
  heldMonths: number
): { interest_vnd: number; if_posted_vnd: number; forgone_vnd: number } {
  if (heldMonths < 0) throw new Error("held_months must be >= 0")
  const interestVnd = P * (demandRate / 100) * (heldMonths / 12)
  const ifPostedVnd = P * (postedRate / 100) * (heldMonths / 12)
  return {
    interest_vnd: interestVnd,
    if_posted_vnd: ifPostedVnd,
    forgone_vnd: ifPostedVnd - interestVnd,
  }
}

export function realRate(nominalPct: number, cpiYoyPct: number): number {
  return ((1 + nominalPct / 100) / (1 + cpiYoyPct / 100) - 1) * 100
}

function growthFactor(ratePct: number, termMonths: number): number {
  return 1 + (ratePct / 100) * (termMonths / 12)
}

export function insuredSplit(amount: number, cap: number = INSURED_CAP_VND, options: SplitOption[] = []): InsuredSplit {
  if (amount < 0) throw new Error("amount must be >= 0")
  const allocations: SplitAllocation[] = []
  let remaining = amount
  const used = new Map<string, number>()
  for (const opt of options) {
    const bank = opt.bank_code
    const factor = growthFactor(opt.rate_pct, opt.term_months)
    const room = cap / factor - (used.get(bank) ?? 0)
    const alloc = Math.min(remaining, Math.max(room, 0))
    if (alloc <= 0) continue
    const interestVnd = alloc * (opt.rate_pct / 100) * (opt.term_months / 12)
    allocations.push({
      bank_code: bank,
      amount: alloc,
      interest_vnd: interestVnd,
      total_vnd: alloc + interestVnd,
    })
    used.set(bank, (used.get(bank) ?? 0) + alloc)
    remaining -= alloc
  }
  const allocated = amount - remaining
  return {
    allocations,
    allocated_vnd: allocated,
    remainder_vnd: remaining,
    fully_insured: remaining <= 0,
    insured_share: amount > 0 ? allocated / amount : 1.0,
  }
}

// Posted rows that may feed a plan: verified rows always, single rows only when
// allowSingle, contested rows never; online rows only when onlineOk.
function eligibleRows(options: RateRow[], onlineOk: boolean, allowSingle: boolean): RateRow[] {
  const eligible: RateRow[] = []
  for (const row of options) {
    if (!onlineOk && row.channel === "online") continue
    if (row.grade === "verified" || (allowSingle && row.grade === "single")) eligible.push(row)
  }
  return eligible
}

// Deterministic order: best rate first, then shorter term, counter before
// online, then bank/tier; stable, so equal keys keep the caller's order.
function sortedRows(rows: RateRow[]): RateRow[] {
  return [...rows].sort(
    (a, b) =>
      b.rate_pct - a.rate_pct ||
      a.term_months - b.term_months ||
      (a.channel ?? "").localeCompare(b.channel ?? "") ||
      a.bank_code.localeCompare(b.bank_code) ||
      (a.tier ?? "").localeCompare(b.tier ?? "")
  )
}

function insuredShare(amount: number, growth: number, cap: number): number {
  if (amount <= 0) return 1.0
  return Math.min(1, cap / growth / amount)
}

export function plan(
  amount: number,
  horizonMonths: number,
  onlineOk: boolean,
  options: RateRow[],
  cap: number = INSURED_CAP_VND,
  demandRates: Record<string, number> = {},
  allowSingle = false
): Plan[] {
  const eligible = sortedRows(eligibleRows(options, onlineOk, allowSingle))
  const plans: Plan[] = []

  // per bank: shortest term beyond the horizon (early withdrawal forfeits the
  // posted rate, so the shortest term dominates)
  const shortestBeyond = new Map<string, RateRow>()
  for (const row of eligible) {
    if (row.term_months > horizonMonths) {
      const cur = shortestBeyond.get(row.bank_code)
      if (cur === undefined || row.term_months < cur.term_months) shortestBeyond.set(row.bank_code, row)
    }
  }

  // value at the horizon: for term <= horizon the term grows, then the idle
  // months earn the bank's demand rate (0 when none is given); a term beyond
  // the horizon is withdrawn early at the demand rate. Ranked by this value.
  const horizonFactor = (bank: string, ratePct: number, term: number): number =>
    growthFactor(ratePct, term) * growthFactor(demandRates[bank] ?? 0, horizonMonths - term)

  for (const row of eligible) {
    const bank = row.bank_code
    const term = row.term_months
    let factorH: number
    let value: number
    let idle: number
    let early: boolean
    if (term <= horizonMonths) {
      factorH = horizonFactor(bank, row.rate_pct, term)
      value = amount * factorH
      idle = horizonMonths - term
      early = false
    } else {
      if (shortestBeyond.get(bank) !== row || demandRates[bank] === undefined) continue
      factorH = growthFactor(demandRates[bank], horizonMonths)
      value = amount * factorH
      idle = 0
      early = true
    }
    plans.push({
      kind: "single",
      early_withdrawal: early,
      interest_vnd: value - amount,
      value_at_horizon: value,
      idle_months: idle,
      insured_share: insuredShare(amount, early ? factorH : growthFactor(row.rate_pct, term), cap),
      rows: [row],
      amounts: [{ bank_code: bank, amount }],
    })
  }

  const six = eligible.filter((row) => row.term_months === 6)
  if (horizonMonths > 6 && six.length > 0) {
    const row6 = six[0] // eligible is rate-sorted, so this is the best 6-month row
    const rest = horizonMonths - 6
    // the second leg renews at the same bank's posted row for the remaining
    // months (same channel); with no such row the ladder is not emitted
    const row2 =
      eligible.find(
        (r) => r.bank_code === row6.bank_code && r.term_months === rest && (r.channel ?? "") === (row6.channel ?? "")
      ) ?? null
    if (row2 !== null) {
      const r6 = row6.rate_pct
      const r2 = row2.rate_pct
      const leg1 = amount * (r6 / 100) * (6 / 12)
      const leg2 = (amount + leg1) * (r2 / 100) * (rest / 12)
      const growth = growthFactor(r6, 6) * growthFactor(r2, rest)
      const value = amount + leg1 + leg2
      plans.push({
        kind: "ladder_6_renewal",
        early_withdrawal: false,
        interest_vnd: leg1 + leg2,
        value_at_horizon: value,
        idle_months: 0,
        second_leg_assumption: "same posted rate as today",
        insured_share: insuredShare(amount, growth, cap),
        rows: [row6, row2],
        amounts: [{ bank_code: row6.bank_code, amount }],
      })
    }
  }

  // split: per bank the eligible option with the best value at the horizon
  // (term <= horizon at maturity, then idle months at the demand rate; beyond
  // it, early withdrawal at the demand rate), then greedy fill best horizon
  // factor first under the cap
  const best = new Map<string, { row: RateRow; pseudo: SplitOption; factorH: number }>()
  for (const row of eligible) {
    const bank = row.bank_code
    let pseudo: SplitOption
    if (row.term_months <= horizonMonths) {
      pseudo = { bank_code: bank, term_months: row.term_months, rate_pct: row.rate_pct }
    } else if (demandRates[bank] !== undefined) {
      pseudo = { bank_code: bank, term_months: horizonMonths, rate_pct: demandRates[bank] }
    } else {
      continue
    }
    const factorH = horizonFactor(bank, pseudo.rate_pct, pseudo.term_months)
    const cur = best.get(bank)
    if (cur === undefined || factorH > cur.factorH) best.set(bank, { row, pseudo, factorH })
  }
  const ordered = [...best.values()].sort((a, b) => b.factorH - a.factorH)
  const split = insuredSplit(amount, cap, ordered.map((b) => b.pseudo))
  if (split.allocations.length >= 2) {
    const rowsByBank = new Map(ordered.map((b) => [b.row.bank_code, b.row]))
    const factorHByBank = new Map(ordered.map((b) => [b.row.bank_code, b.factorH]))
    const interestVnd = split.allocations.reduce((s, a) => s + a.amount * (factorHByBank.get(a.bank_code) - 1), 0)
    plans.push({
      kind: "split",
      early_withdrawal: false,
      interest_vnd: interestVnd,
      value_at_horizon: amount + interestVnd,
      idle_months: null,
      insured_share: split.insured_share,
      rows: split.allocations.map((a) => rowsByBank.get(a.bank_code) as RateRow),
      amounts: split.allocations.map((a) => ({ bank_code: a.bank_code, amount: a.amount })),
    })
  }

  plans.sort(
    (a, b) =>
      b.value_at_horizon - a.value_at_horizon ||
      (a.kind < b.kind ? -1 : a.kind > b.kind ? 1 : 0) ||
      a.rows[0].bank_code.localeCompare(b.rows[0].bank_code) ||
      a.rows[0].term_months - b.rows[0].term_months
  )
  return plans
}

function median(values: number[]): number {
  const xs = [...values].sort((a, b) => a - b)
  const n = xs.length
  if (n === 0) throw new Error("median of empty sequence")
  if (n % 2 === 1) return xs[(n - 1) / 2]
  return (xs[n / 2 - 1] + xs[n / 2]) / 2
}

export function ceilingStats(
  rows: { bank_code: string; term_months: number; rate_pct: number; grade?: string }[],
  ceilingPct: number = CEILING_PCT
): CeilingStats {
  // Ceiling picture for the 1 to <6 month band. quotes_1_5m / at_ceiling /
  // above count every posted row in the band; the median jump uses graded
  // banks only (both legs verified or single). grade_basis names the grades
  // behind that median.
  const short = rows.filter((r) => r.term_months >= 1 && r.term_months < 6)
  const atCeiling = short.filter((r) => Math.abs(r.rate_pct - ceilingPct) <= 1e-9).length
  const above = short.filter((r) => r.rate_pct > ceilingPct + 1e-9).length

  const cells = new Map<string, { rates: number[]; graded: boolean }>()
  for (const r of rows) {
    if (r.term_months !== 5 && r.term_months !== 6) continue
    const key = `${r.bank_code}|${r.term_months}`
    const cell = cells.get(key) ?? { rates: [], graded: true }
    cell.rates.push(r.rate_pct)
    if (!GRADED.includes(r.grade ?? "")) cell.graded = false
    cells.set(key, cell)
  }

  const banks = [...new Set([...cells.keys()].map((k) => k.split("|")[0]))].sort()
  const jumps: CeilingJump[] = []
  for (const bank of banks) {
    const c5 = cells.get(`${bank}|5`)
    const c6 = cells.get(`${bank}|6`)
    if (!c5 || !c6) continue
    jumps.push({
      bank_code: bank,
      jump_pp: median(c6.rates) - median(c5.rates),
      graded: c5.graded && c6.graded,
    })
  }
  const gradedJumps = jumps.filter((j) => j.graded).map((j) => j.jump_pp)
  return {
    quotes_1_5m: short.length,
    at_ceiling: atCeiling,
    above,
    jumps,
    jump_5_6_pp_median: gradedJumps.length > 0 ? median(gradedJumps) : null,
    n_banks: jumps.length,
    n_banks_graded: gradedJumps.length,
    grade_basis: "verified+single",
  }
}
