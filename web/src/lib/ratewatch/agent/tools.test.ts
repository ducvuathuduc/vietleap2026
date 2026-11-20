// Run: node --test src/lib/ratewatch/agent/tools.test.ts
// Every tool is deterministic on the fixture snapshot (web/seed/ratewatch/snapshot.fixture.json).
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

import type { Snapshot } from "../types.ts"
import {
  banksInProvince,
  bankProfile,
  breakEven,
  compareBanks,
  explainMetric,
  getCurve,
  insuredSplit,
  planDeposit,
  policyParam,
  makeRatewatchTools,
  type Citation,
} from "./tools.ts"

// The fixture is read directly (load.ts uses a bundler-only JSON import).
const snapshot = JSON.parse(
  readFileSync(new URL("../../../../seed/ratewatch/snapshot.fixture.json", import.meta.url), "utf8"),
) as Snapshot

function assertCitations(citations: Citation[], min = 1) {
  assert.ok(citations.length >= min, `expected >= ${min} citations`)
  for (const c of citations) {
    assert.equal(typeof c.source_url, "string")
    assert.equal(typeof c.observed_at, "string")
    assert.ok("bank" in c && "term_months" in c && "channel" in c && "grade" in c && "sheet_date" in c)
  }
}

test("get_curve: OCB online verified points with citations", () => {
  const res = getCurve(snapshot, { bank: "OCB", channel: "online" })
  assert.equal(res.bank_code, "OCB")
  assert.equal(res.sheet_date, "2026-11-06")
  const byTerm = new Map(res.points.map((p) => [p.term_months, p]))
  assert.equal(byTerm.get(5)!.rate_pct, 4.75)
  assert.equal(byTerm.get(5)!.grade, "verified")
  assert.equal(byTerm.get(6)!.rate_pct, 6.0)
  assert.equal(byTerm.get(12)!.rate_pct, 6.3)
  assertCitations(res.citations, 5)
  assert.ok(res.citations.every((c) => c.bank === "OCB" && c.channel === "online"))
})

test("get_curve: unknown bank returns found: false", () => {
  const res = getCurve(snapshot, { bank: "ACB", channel: "online" })
  assert.equal(res.found, false)
})

test("compare_banks: three banks at 6 months, missing banks reported", () => {
  const res = compareBanks(snapshot, { banks: ["OCB", "STB", "TCB"], term: 6 })
  assert.equal(res.term_months, 6)
  const ocb = res.rows.find((r) => r.bank_code === "OCB" && r.channel === "online")!
  assert.equal(ocb.rate_pct, 6.0)
  assert.equal(ocb.grade, "verified")
  const stb = res.rows.find((r) => r.bank_code === "STB" && r.channel === "counter")!
  assert.equal(stb.rate_pct, 5.7)
  const tcb = res.rows.find((r) => r.bank_code === "TCB" && r.channel === "counter")!
  assert.equal(tcb.grade, "contested")
  assert.deepEqual(res.missing, [])
  assertCitations(res.citations, 3)
})

test("compare_banks: banks absent from the snapshot are listed as missing", () => {
  const res = compareBanks(snapshot, { banks: ["OCB", "ACB", "MB"], term: 6 })
  assert.deepEqual(res.missing, ["ACB", "MB"])
  assert.ok(res.rows.every((r) => r.bank_code !== "ACB" && r.bank_code !== "MB"))
})

test("compare_banks: more than 3 banks throws (schema bound)", () => {
  assert.throws(() => compareBanks(snapshot, { banks: ["OCB", "STB", "TCB", "HDB"], term: 6 }))
})

test("plan_deposit: 1.2 billion for 5 months online, best verified single plan first", () => {
  const res = planDeposit(snapshot, { amount: 1_200_000_000, horizon_months: 5, online_ok: true })
  assert.equal(res.amount, 1_200_000_000)
  assert.ok(res.plans.length >= 1)
  const top = res.plans[0]!
  assert.equal(top.kind, "single")
  assert.equal(top.rows[0]!.bank_code, "OCB")
  assert.equal(top.rows[0]!.rate_pct, 4.75)
  assert.equal(top.rows[0]!.term_months, 5)
  // simple interest: P * r * months/12
  assert.ok(Math.abs(top.interest_vnd - 1_200_000_000 * 0.0475 * (5 / 12)) < 1)
  assertCitations(res.citations, 1)
})

test("plan_deposit: split plan keeps every allocation inside the insured cap", () => {
  const res = planDeposit(snapshot, { amount: 1_200_000_000, horizon_months: 6, online_ok: true })
  const split = res.plans.find((p) => p.kind === "split")
  assert.ok(split, "expected a split plan")
  const perBank = new Map(split!.amounts.map((a) => [a.bank_code, a.amount]))
  for (const amount of perBank.values()) assert.ok(amount <= snapshot.policy.cap.vnd + 1e-6)
})

test("break_even: OCB online 6->12 months is a calculation, not a forecast", () => {
  const res = breakEven(snapshot, { bank: "OCB", channel: "online", short_m: 6, long_m: 12 })
  assert.equal(res.bank_code, "OCB")
  assert.equal(res.short_rate, 6.0)
  assert.equal(res.long_rate, 6.3)
  // (1 + 0.063) = (1 + 0.06*6/12) * (1 + f*6/12) -> f = 6.4078%/year (hand-checked in X-JUDGE)
  assert.ok(Math.abs(res.break_even_pct - 6.407766990291262) < 1e-9)
  assert.match(res.note_vi, /phép tính, không phải dự báo/)
  assertCitations(res.citations, 2)
})

test("break_even: STB counter 6->12 needs only 4.96% on renewal, below today's 5.7%", () => {
  const res = breakEven(snapshot, { bank: "STB", channel: "counter", short_m: 6, long_m: 12 })
  assert.equal(res.short_rate, 5.7)
  assert.equal(res.long_rate, 5.4)
  // (1 + 0.054) = (1 + 0.057*6/12) * (1 + f*6/12) -> f = 4.9587%/year, below the posted 5.7%
  assert.ok(Math.abs(res.break_even_pct - 4.958677685950441) < 1e-9)
  assert.ok(res.break_even_pct < res.short_rate)
})

test("break_even: contested leg refuses to compute", () => {
  const res = breakEven(snapshot, { bank: "OCB", channel: "counter", short_m: 6, long_m: 12 })
  assert.equal(res.error, "contested")
})

test("insured_split: 800 million splits under the 350 million cap", () => {
  const res = insuredSplit(snapshot, { amount: 800_000_000 })
  assert.equal(res.cap_vnd, 350_000_000)
  assert.ok(res.allocations.length >= 2)
  for (const a of res.allocations) {
    assert.ok(a.amount <= 350_000_000 + 1e-6)
    assert.ok(Math.abs(a.interest_vnd - a.amount * (a.rate_pct / 100) * (a.term_months / 12)) < 1)
  }
  assert.equal(res.allocated_vnd, 800_000_000)
  assert.equal(res.fully_insured, true)
  assertCitations(res.citations, 2)
})

test("insured_split: named banks only", () => {
  const res = insuredSplit(snapshot, { amount: 700_000_000, banks: ["OCB", "STB"] })
  assert.ok(res.allocations.every((a) => a.bank_code === "OCB" || a.bank_code === "STB"))
})

test("bank_profile: fixture has no profile yet, tool says so with citations", () => {
  const res = bankProfile(snapshot, { bank: "OCB" })
  assert.equal(res.bank_code, "OCB")
  assert.equal(res.profile, null)
  assert.ok(res.message_vi.length > 0)
  assertCitations(res.citations, 1)
})

test("policy_param: ceiling, cap, premium, insured_coverage", () => {
  const ceiling = policyParam(snapshot, { param: "ceiling" })
  assert.equal(ceiling.values.pct, 4.75)
  assert.match(ceiling.values.legal_ref, /2411/)
  const cap = policyParam(snapshot, { param: "cap" })
  assert.equal(cap.values.vnd, 350_000_000)
  const premium = policyParam(snapshot, { param: "premium" })
  assert.equal(premium.values.pct, 0.15)
  const coverage = policyParam(snapshot, { param: "insured_coverage" })
  assert.equal(coverage.values.depositors_pct, 93.68)
  assert.equal(coverage.values.value_pct, 19.06)
  assertCitations(ceiling.citations, 1)
})

test("banks_in_province: Cần Thơ resolves by name and pcode and returns the recorded branch counts", () => {
  const recorded = snapshot.geo.provinces.find((item) => item.pcode === "VN92")
  assert.ok(recorded)
  assert.equal(recorded.branches_total, 143)
  assert.equal(recorded.deposits_bn, null)
  assert.equal(recorded.branches_by_bank.STB, 11)
  for (const province of ["Cần Thơ", "VN92", "can tho"]) {
    const res = banksInProvince(snapshot, { province })
    assert.equal(res.found, true)
    assert.equal(res.province!.pcode, "VN92")
    assert.equal(res.province!.branches_total, 143)
    assert.deepEqual(res.province!.branches_by_bank, recorded.branches_by_bank)
    assert.match(res.note_vi, /chi nhánh/)
  }
  assertCitations(banksInProvince(snapshot, { province: "Cần Thơ" }).citations, 1)
})

test("banks_in_province: unknown province returns found: false", () => {
  const res = banksInProvince(snapshot, { province: "Mặt Trăng" })
  assert.equal(res.found, false)
})

test("explain_metric: break-even text carries the not-a-forecast wording", () => {
  const res = explainMetric(snapshot, { metric: "break_even" })
  assert.match(res.text_vi, /phép tính/)
  assert.match(res.text_vi, /không phải dự báo/)
  assert.match(res.text_en, /calculation/i)
})

test("explain_metric: insured split mentions the 350 million cap from the snapshot", () => {
  const res = explainMetric(snapshot, { metric: "insured_split" })
  assert.ok(res.text_vi.includes("350"))
})

test("makeRatewatchTools exposes the nine typed tools", () => {
  const tools = makeRatewatchTools(snapshot)
  const names = Object.keys(tools).sort()
  assert.deepEqual(names, [
    "bank_profile",
    "banks_in_province",
    "break_even",
    "compare_banks",
    "explain",
    "get_curve",
    "insured_split",
    "plan_deposit",
    "policy",
  ])
  for (const t of Object.values(tools)) assert.ok(typeof (t as { execute?: unknown }).execute === "function")
})
