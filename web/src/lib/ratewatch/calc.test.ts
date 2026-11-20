// Run: node --test src/lib/ratewatch/calc.test.ts
// Every case lives in tests/fixtures/ratewatch/analytics_cases.json and is
// mirrored by tests/ratewatch/test_analytics.py against the Python engine.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

import {
  breakEvenRenewal,
  ceilingStats,
  earlyWithdrawal,
  insuredSplit,
  interest,
  plan,
  realRate,
  type RateRow,
  type SplitOption,
} from "./calc.ts"

interface InterestCase {
  name: string
  P: number
  rate_pct: number
  months?: number
  days?: number
  basis?: string
  expected?: number
  expect_error?: boolean
}

interface BreakEvenCase {
  name: string
  r_long: number
  long_m: number
  r_short: number
  short_m: number
  expected_4dp?: number
  expect_error?: boolean
}

interface EarlyWithdrawalCase {
  name: string
  P: number
  posted_rate: number
  demand_rate: number
  held_months: number
  expected_interest_vnd: number
  expected_if_posted_vnd: number
  expected_forgone_vnd: number
}

interface RealRateCase {
  name: string
  nominal_pct: number
  cpi_yoy_pct: number
  expected_4dp: number
}

interface SplitExpected {
  n_allocations: number
  banks: string[]
  interest_vnd?: number
  remainder_vnd: number
  fully_insured: boolean
  insured_share_4dp: number
  total_at_cap?: boolean
}

interface InsuredSplitCase {
  name: string
  amount: number
  cap: number
  options: SplitOption[]
  expected: SplitExpected
}

interface PlanExpected {
  kind: string
  banks: string[]
  terms: number[]
  interest_vnd: number
  value_at_horizon: number
  idle_months: number | null
  insured_share_4dp: number
  early_withdrawal?: boolean
  second_leg_assumption?: string
}

interface PlanCase {
  name: string
  amount: number
  horizon_months: number
  online_ok: boolean
  cap: number
  demand_rates: Record<string, number>
  allow_single: boolean
  options: RateRow[]
  expected: PlanExpected[]
}

interface BruteForceCase {
  amount: number
  horizon_months: number
  online_ok: boolean
  cap: number
  grid_steps: number
  demand_rates: Record<string, number>
  options: RateRow[]
}

interface CeilingJump {
  bank_code: string
  jump_pp: number
  graded: boolean
}

interface CeilingCase {
  name: string
  rows: { bank_code: string; term_months: number; rate_pct: number; grade: string }[]
  ceiling_pct: number
  expected: {
    quotes_1_5m: number
    at_ceiling: number
    above: number
    n_banks: number
    n_banks_graded: number
    jump_5_6_pp_median: number | null
    jumps: CeilingJump[]
  }
}

interface AnalyticsCases {
  tolerances: { vnd: number; pct: number; pp: number; share: number }
  interest: InterestCase[]
  break_even: BreakEvenCase[]
  early_withdrawal: EarlyWithdrawalCase[]
  real_rate: RealRateCase[]
  insured_split: InsuredSplitCase[]
  plan: PlanCase[]
  plan_brute_force: BruteForceCase
  ceiling_stats: CeilingCase[]
}

const CASES = JSON.parse(
  readFileSync(new URL("../../../../tests/fixtures/ratewatch/analytics_cases.json", import.meta.url), "utf-8")
) as AnalyticsCases
const TOL = CASES.tolerances

function sameRow(row: RateRow, options: RateRow[]): boolean {
  return options.some((o) => {
    try {
      assert.deepStrictEqual(row, o)
      return true
    } catch {
      return false
    }
  })
}

test("interest: simple interest at maturity, months/12 or actual/365", () => {
  for (const c of CASES.interest) {
    if (c.expect_error) {
      assert.throws(() => interest(c.P, c.rate_pct, c.months, c.days, c.basis ?? "at_maturity"))
      continue
    }
    const got = interest(c.P, c.rate_pct, c.months, c.days, c.basis ?? "at_maturity")
    assert.ok(Math.abs(got - (c.expected as number)) <= TOL.vnd, c.name)
  }
})

test("break_even_renewal: hand-checked OCB 6.4078 and Sacombank 4.9587", () => {
  for (const c of CASES.break_even) {
    if (c.expect_error) {
      assert.throws(() => breakEvenRenewal(c.r_long, c.long_m, c.r_short, c.short_m))
      continue
    }
    const f = breakEvenRenewal(c.r_long, c.long_m, c.r_short, c.short_m)
    assert.equal(Math.round(f * 10000) / 10000, c.expected_4dp, c.name)
    assert.ok(Math.abs(f - (c.expected_4dp as number)) <= TOL.pct, c.name)
  }
})

test("early_withdrawal: demand rate on the held period, posted leg and forgone difference", () => {
  for (const c of CASES.early_withdrawal) {
    const got = earlyWithdrawal(c.P, c.posted_rate, c.demand_rate, c.held_months)
    assert.ok(Math.abs(got.interest_vnd - c.expected_interest_vnd) <= TOL.vnd, c.name)
    assert.ok(Math.abs(got.if_posted_vnd - c.expected_if_posted_vnd) <= TOL.vnd, c.name)
    assert.ok(Math.abs(got.forgone_vnd - c.expected_forgone_vnd) <= TOL.vnd, c.name)
    assert.equal(got.forgone_vnd, got.if_posted_vnd - got.interest_vnd, c.name)
  }
})

test("real_rate: Fisher, percent in percent out", () => {
  for (const c of CASES.real_rate) {
    const got = realRate(c.nominal_pct, c.cpi_yoy_pct)
    assert.equal(Math.round(got * 10000) / 10000, c.expected_4dp, c.name)
    assert.ok(Math.abs(got - c.expected_4dp) <= TOL.pct, c.name)
  }
})

test("insured_split: per-bank amounts under the cap, remainder flagged", () => {
  for (const c of CASES.insured_split) {
    const got = insuredSplit(c.amount, c.cap, c.options)
    const exp = c.expected
    assert.equal(got.allocations.length, exp.n_allocations, c.name)
    assert.deepEqual(
      got.allocations.map((a) => a.bank_code),
      exp.banks,
      c.name
    )
    assert.ok(Math.abs(got.remainder_vnd - exp.remainder_vnd) <= TOL.vnd, c.name)
    assert.equal(got.fully_insured, exp.fully_insured, c.name)
    assert.ok(Math.abs(got.insured_share - exp.insured_share_4dp) <= TOL.share, c.name)
    if (exp.interest_vnd !== undefined) {
      const total = got.allocations.reduce((s, a) => s + a.interest_vnd, 0)
      assert.ok(Math.abs(total - exp.interest_vnd) <= TOL.vnd, c.name)
    }
    for (const a of got.allocations) {
      assert.ok(a.total_vnd <= c.cap + 1e-6, c.name)
      assert.ok(Math.abs(a.total_vnd - (a.amount + a.interest_vnd)) <= 1e-9, c.name)
    }
    if (exp.total_at_cap) {
      const total = got.allocations[0].total_vnd
      assert.ok(total >= c.cap - TOL.vnd && total <= c.cap + 1e-6, c.name)
    }
  }
})

function assertPlans(plans: ReturnType<typeof plan>, expected: PlanExpected[], name: string): void {
  assert.equal(plans.length, expected.length, name)
  for (let i = 0; i < plans.length; i++) {
    const got = plans[i]
    const exp = expected[i]
    assert.equal(got.kind, exp.kind, name)
    assert.deepEqual(
      got.amounts.map((a) => a.bank_code),
      exp.banks,
      name
    )
    assert.deepEqual(
      got.rows.map((r) => r.term_months),
      exp.terms,
      name
    )
    assert.ok(Math.abs(got.interest_vnd - exp.interest_vnd) <= TOL.vnd, name)
    assert.ok(Math.abs(got.value_at_horizon - exp.value_at_horizon) <= TOL.vnd, name)
    assert.equal(got.idle_months, exp.idle_months, name)
    assert.ok(Math.abs(got.insured_share - exp.insured_share_4dp) <= TOL.share, name)
    if (exp.second_leg_assumption !== undefined) {
      assert.equal(got.second_leg_assumption, exp.second_leg_assumption, name)
    }
    assert.equal(got.early_withdrawal, exp.early_withdrawal ?? false, name)
  }
  const values = plans.map((p) => p.value_at_horizon)
  assert.deepEqual(
    [...values].sort((a, b) => b - a),
    values,
    name
  )
}

test("plan: ranked single, ladder and split plans from verified rows", () => {
  for (const c of CASES.plan) {
    const got = plan(c.amount, c.horizon_months, c.online_ok, c.options, c.cap, c.demand_rates, c.allow_single)
    assertPlans(got, c.expected, c.name)
    for (const p of got) {
      for (const row of p.rows) assert.ok(sameRow(row, c.options), c.name)
    }
  }
})

test("plan split greedy matches brute force for 3 banks", () => {
  const c = CASES.plan_brute_force
  const got = plan(c.amount, c.horizon_months, c.online_ok, c.options, c.cap, c.demand_rates, false)
  const splits = got.filter((p) => p.kind === "split")
  assert.equal(splits.length, 1)
  const split = splits[0]
  for (const alloc of split.amounts) {
    const row = c.options.find((o) => o.bank_code === alloc.bank_code) as RateRow
    const g = 1 + (row.rate_pct / 100) * (row.term_months / 12)
    assert.ok(alloc.amount + alloc.amount * (g - 1) <= c.cap + 1e-6)
  }

  const banks = c.options.map((o) => {
    const g = 1 + (o.rate_pct / 100) * (o.term_months / 12)
    const d = c.demand_rates[o.bank_code] ?? 0
    const gH =
      o.term_months <= c.horizon_months
        ? g * (1 + (d / 100) * ((c.horizon_months - o.term_months) / 12))
        : 1 + (d / 100) * (c.horizon_months / 12)
    return { g, gH, room: c.cap / g }
  })
  const unit = c.amount / c.grid_steps
  let best = 0
  const rec = (i: number, remaining: number, total: number): void => {
    if (i === banks.length) {
      best = Math.max(best, total)
      return
    }
    const { gH, room } = banks[i]
    const top = Math.min(remaining, room)
    for (let u = 0; u <= Math.round(top / unit); u++) {
      const alloc = u * unit
      rec(i + 1, remaining - alloc, total + alloc * (gH - 1))
    }
  }
  rec(0, c.amount, 0)
  assert.ok(best > 0)
  assert.ok(split.interest_vnd >= best - TOL.vnd)
})

test("ceiling_stats: counts and median jump over graded banks only", () => {
  for (const c of CASES.ceiling_stats) {
    const got = ceilingStats(c.rows, c.ceiling_pct)
    const exp = c.expected
    assert.equal(got.quotes_1_5m, exp.quotes_1_5m, c.name)
    assert.equal(got.at_ceiling, exp.at_ceiling, c.name)
    assert.equal(got.above, exp.above, c.name)
    assert.equal(got.n_banks, exp.n_banks, c.name)
    assert.equal(got.n_banks_graded, exp.n_banks_graded, c.name)
    assert.deepEqual(
      got.jumps.map((j) => j.bank_code),
      exp.jumps.map((j) => j.bank_code),
      c.name
    )
    for (let i = 0; i < got.jumps.length; i++) {
      assert.ok(Math.abs(got.jumps[i].jump_pp - exp.jumps[i].jump_pp) <= TOL.pp, c.name)
      assert.equal(got.jumps[i].graded, exp.jumps[i].graded, c.name)
    }
    if (exp.jump_5_6_pp_median === null) {
      assert.equal(got.jump_5_6_pp_median, null, c.name)
    } else {
      assert.ok(Math.abs((got.jump_5_6_pp_median as number) - exp.jump_5_6_pp_median) <= TOL.pp, c.name)
    }
  }
})
