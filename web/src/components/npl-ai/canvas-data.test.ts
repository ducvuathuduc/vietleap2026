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
