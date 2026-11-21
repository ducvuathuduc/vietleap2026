import assert from "node:assert/strict"
import { test } from "node:test"

import * as canvas from "./canvas-data.ts"

test("comparison export contains latest changes with their quarters and original precision", () => {
  const result = canvas.readResult("compare_banks", {
    rows: [{ code: "VCB", latest_period: "2026Q3", d_npl_pp: -0.105812, adjusted_change_pp: 0.201157, q4_change_median_pp: -0.44, q1_rebound_median_pp: 0.26 }],
    missing: [],
  })
  assert.ok(result)
  assert.deepEqual(canvas.csvRows(result, "vi"), [
    ["bank", "period", "change_pp", "adjusted_change_pp"],
    ["VCB", "2026Q3", -0.105812, 0.201157],
  ])
})

test("a fixed-quarter comparison cannot substitute the available history for missing figures", () => {
  assert.equal(canvas.findAnswerCanvas([{
    id: "1",
    name: "compare_banks",
    input: { codes: ["VCB"], period: "2020Q1", trend: true },
    output: { requested_period: "2020Q1", rows: [{ code: "VCB", history: [{ period: "2025Q4", npl_pct: 1.05 }] }] },
  }]), null)
})

test("forecast chart joins the final observed value to the forecast interval", () => {
  const rows = canvas.forecastRows({
    series: [{ period: "2026Q2", npl_pct: 1.26 }, { period: "2026Q3", npl_pct: 1.10 }],
    forecast: { period: "2026Q4", npl_pct: 0.91, lo80: 0.68, hi80: 1.64 },
  })
  assert.deepEqual(rows, [
    { period: "2026Q2", observed: 1.26 },
    { period: "2026Q3", observed: 1.10, estimate: 1.10, band: [1.10, 1.10] },
    { period: "2026Q4", estimate: 0.91, band: [0.68, 1.64], error: [0.22999999999999998, 0.7299999999999999] },
  ])
})

test("text-only tools and results with no figures do not open a canvas", () => {
  assert.equal(canvas.findAnswerCanvas([
    { id: "1", name: "method", input: {}, output: { entry: {} } },
    { id: "2", name: "screen_declines", input: {}, output: { rows: [], citations: [] } },
    { id: "3", name: "bank_profile", input: {}, output: { found: false } },
    { id: "4", name: "adjusted_change", input: {}, output: { row: { d_npl_pp: null, adjusted_change_pp: null } } },
  ]), null)
})

test("a populated bank comparison keeps its canvas when a study returned no rows", () => {
  const selected = canvas.findAnswerCanvas([
    { id: "1", name: "rank_gap", input: {}, output: { rows: [], citations: [] } },
    { id: "2", name: "compare_banks", input: { codes: ["VCB"] }, output: { rows: [{ code: "VCB", npl_pct: 1.05 }] } },
  ])
  assert.equal(selected?.name, "compare_banks")
})

test("a bank profile for an unavailable quarter does not open an unrelated historical chart", () => {
  assert.equal(canvas.findAnswerCanvas([{
    id: "1",
    name: "bank_profile",
    input: { code: "MBB", period: "2010Q3" },
    output: { bank: { series: [{ period: "2025Q4", npl_pct: 1.5 }] }, selected: null },
  }]), null)
})

test("write-off rankings open a canvas when a bank has published quarterly figures", () => {
  const selected = canvas.findAnswerCanvas([{
    id: "1",
    name: "largest_writeoffs",
    input: { period: "2025Q4" },
    output: { data_period: "2025Q4", rows: [{ bank: "MBB", amount_vnd_bn: 2637, share_pct: 0.24 }] },
  }])
  assert.equal(selected?.name, "largest_writeoffs")
})

test("published decoder checks open a canvas even without a reported or adjusted change", () => {
  const selected = canvas.findAnswerCanvas([{
    id: "1",
    name: "decoder",
    input: { code: "MBB", period: "2025Q4" },
    output: {
      row: { d_npl_pp: null, adjusted_change_pp: null },
      selected: {
        decoder_row: { period: "2025Q4" },
        evidence: { en: { checks: [{ id: "group2", value: "0.12 pp" }] } },
      },
    },
  }])
  assert.equal(selected?.name, "decoder")
})

test("numeric table sorting preserves original rows and puts missing values last", () => {
  const rows = [
    { bank: "VCB", value: 12 },
    { bank: "BID", value: null },
    { bank: "MBB", value: 2 },
  ]
  assert.deepEqual(canvas.sortEvidenceRows(rows, (row) => row.value, false, "en").map((row) => row.bank),
    ["MBB", "VCB", "BID"])
  assert.deepEqual(canvas.sortEvidenceRows(rows, (row) => row.value, true, "vi").map((row) => row.bank),
    ["VCB", "MBB", "BID"])
  assert.deepEqual(rows.map((row) => row.bank), ["VCB", "BID", "MBB"])
})

test("quarterly comparison aligns bank values on a shared timeline without filling missing quarters", () => {
  assert.deepEqual(canvas.comparisonHistory([
    { code: "VCB", history: [{ period: "2025Q2", npl_pct: 1.2 }, { period: "2025Q3", npl_pct: null }] },
    { code: "MBB", history: [{ period: "2025Q1", npl_pct: 2 }, { period: "2025Q3", npl_pct: 1.9 }] },
  ]), [
    { period: "2025Q1", MBB: 2, VCB: null },
    { period: "2025Q2", MBB: null, VCB: 1.2 },
    { period: "2025Q3", MBB: 1.9, VCB: null },
  ])
})
