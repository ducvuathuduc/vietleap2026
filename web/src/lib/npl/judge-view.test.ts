import assert from "node:assert/strict"
import { test } from "node:test"

import { breakdownModel, heatmapModel, marketPriceModel, q4HoldoutReading, waterfallModel, type BankBreakdown } from "./judge-view.ts"
import type { Snapshot } from "./view.ts"

test("describes the held-out Q4 check using the published periods and counts", () => {
  const result = {
    train_through: "2023Q4", scored_period: "2024Q4", outcome_period: "2025Q1",
    improving: { n: 5, reversals: 1 }, within_normal_season: { n: 14, reversals: 9 },
  }
  assert.match(q4HoldoutReading(result, "en") ?? "", /2023Q4.*2024Q4.*2025Q1.*1 of 5.*9 of 14/)
  assert.match(q4HoldoutReading(result, "vi") ?? "", /2023Q4.*2024Q4.*2025Q1.*1[/]5.*9[/]14/)
  assert.equal(q4HoldoutReading({ ...result, improving: { n: 0, reversals: 0 } }, "en"), null)
  assert.equal(q4HoldoutReading(undefined, "en"), null)
})

test("heatmap uses adjacent published rates and leaves gaps blank", () => {
  const snapshot = {
    meta: { publish_bank_series: true },
    series: { median_by_period: [
      { period: "2024Q2" }, { period: "2024Q3" }, { period: "2024Q4" }, { period: "2025Q1" },
    ] },
    banks: [
      { code: "BID", series: [
        { period: "2024Q2", npl_pct: 2 }, { period: "2024Q3", npl_pct: 1.7 }, { period: "2025Q1", npl_pct: 2.1 },
      ] },
      { code: "VCB", series: [{ period: "2024Q4", npl_pct: 1 }] },
    ],
  } as Snapshot
  const model = heatmapModel(snapshot)
  assert.deepEqual(model.periods, ["2024Q2", "2024Q3", "2024Q4", "2025Q1"])
  assert.deepEqual(model.rows.map((row) => row.bank), ["BID", "VCB"])
  assert.deepEqual(model.rows[0].cells[0], { before: null, after: 2, change: null })
  assert.equal(model.rows[0].cells[1].change?.toFixed(2), "-0.30")
  assert.deepEqual(model.rows[0].cells[3], { before: null, after: 2.1, change: null })
  const decomposed = heatmapModel(snapshot, [{
    bank_code: "BID", period: "2024Q2", npl_pct: 2.4, d_npl_pp: .4,
    denominator_pp: -.1, numerator_pp: .5, d_g2_pp: null,
  }])
  assert.deepEqual(decomposed.rows[0].cells[0], { before: 2, after: 2.4, change: .4 })
  assert.deepEqual(decomposed.rows[0].cells[1], { before: null, after: null, change: null })
  assert.deepEqual(heatmapModel({ ...snapshot, meta: { ...snapshot.meta, publish_bank_series: false } }).rows, [])
})

test("waterfall bridges the two effects and leaves an unpublished Q1 blank", () => {
  const values: BankBreakdown = {
    bank: "TCB", year: "2025", before: 2, after: 1.8, next: null, denominator: -.4, numerator: .2,
    checks: [],
  }
  const steps = waterfallModel(values, "en")
  assert.deepEqual(steps.map((step) => [step.label, step.value]), [
    ["Q3", 2], ["Loan growth", -.4], ["Bad-debt change", .2], ["Q4", 1.8], ["Next Q1", null],
  ])
  assert.deepEqual(steps.map((step) => [step.start, step.end]), [[0, 2], [2, 1.6], [1.6, 1.8], [0, 1.8], [null, null]])
})

test("the breakdown uses the published split and the exact next quarter", () => {
  const snapshot = { meta: { publish_bank_series: true }, decoder: [] } as unknown as Snapshot
  const q4 = { bank_code: "TCB", period: "2025Q4", npl_pct: 1.5, d_npl_pp: -.5,
    denominator_pp: -.4, numerator_pp: -.1, d_g2_pp: .2 }
  const rows = breakdownModel(snapshot, [q4, { ...q4, period: "2026Q1", npl_pct: 1.8 },
    { ...q4, bank_code: "BID", d_npl_pp: .2 }], "en")
  assert.equal(rows.length, 1)
  assert.deepEqual([rows[0].before, rows[0].after, rows[0].next], [2, 1.5, 1.8])
  assert.deepEqual(rows[0].checks.map((check) => [check.label, check.flagged]), [
    ["Group 2", true], ["Write-offs (proxy)", false], ["Coverage", false], ["Year-end range", false],
  ])
})

test("the market chart preserves measured prices, absent predictions and the test window", () => {
  const price = marketPriceModel({
    series: [
      { month: "2025-01", actual_price: 100, predicted_price: null, in_test: false },
      { month: "2025-02", actual_price: 104, predicted_price: 101, in_test: true },
    ],
    mae_price: 3,
    mae_price_random_walk: 2,
  })
  assert.deepEqual(price, {
    points: [
      { month: "2025-01", actual: 100, predicted: null, test: false },
      { month: "2025-02", actual: 104, predicted: 101, test: true },
    ],
    modelMae: 3, baselineMae: 2, lowerError: false,
  })
})
