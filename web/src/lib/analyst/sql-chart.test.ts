// Run: npm test
import { test } from "node:test"
import assert from "node:assert/strict"

import { chartFromResult } from "./sql-chart.ts"

test("returns null on empty rows or empty columns", () => {
  assert.equal(chartFromResult(["a", "b"], []), null)
  assert.equal(chartFromResult([], []), null)
})

test("1 short text column + 1 numeric column <= 30 rows -> bar without mutating order", () => {
  const rows = [
    ["HN", 120],
    ["HCM", 95],
    ["DN", 60],
  ]
  const c = chartFromResult(["province", "median_price"], rows)
  assert.equal(c?.kind, "bar")
  assert.deepEqual(c?.x, ["HN", "HCM", "DN"])
  assert.deepEqual(c?.series[0].data, [120, 95, 60])
})

test("1 long text column (>12 chars) + numeric -> hbar", () => {
  const rows = [
    ["Thành phố Hồ Chí Minh", 120],
    ["Hà Nội", 95],
  ]
  const c = chartFromResult(["province", "value"], rows)
  assert.equal(c?.kind, "hbar")
  assert.deepEqual(c?.x, ["Thành phố Hồ Chí Minh", "Hà Nội"])
})

test("1 category column with > 30 rows returns null (table only)", () => {
  const rows = Array.from({ length: 31 }, (_, i) => [`Cat ${i}`, i * 10])
  assert.equal(chartFromResult(["cat", "val"], rows), null)
})

test("1 time/year column + 1..2 numeric columns -> line sorted ascending", () => {
  const rows = [
    [2024, 15.2, 10.1],
    [2022, 12.8, 9.4],
    [2023, 14.0, 9.8],
  ]
  const c = chartFromResult(["year", "revenue", "tax"], rows)
  assert.equal(c?.kind, "line")
  assert.deepEqual(c?.x, ["2022", "2023", "2024"])
  assert.deepEqual(c?.series.map((s) => s.name), ["revenue", "tax"])
  assert.deepEqual(c?.series[0].data, [12.8, 14.0, 15.2])
})

test("2 numeric columns with >= 10 rows -> scatter; < 10 rows -> null", () => {
  const small = Array.from({ length: 9 }, (_, i) => [i + 1, (i + 1) * 2])
  assert.equal(chartFromResult(["area", "price"], small), null)

  const big = Array.from({ length: 12 }, (_, i) => [i + 1, (i + 1) * 2])
  const sc = chartFromResult(["area", "price"], big)
  assert.equal(sc?.kind, "scatter")
  assert.equal(sc?.x.length, 12)
  assert.equal(sc?.series[0].data.length, 12)
})

test("wide results (> 10 columns or > 3 numeric series) return null", () => {
  const cols = ["cat", "n1", "n2", "n3", "n4"]
  assert.equal(chartFromResult(cols, [["a", 1, 2, 3, 4]]), null)
  const manyCols = Array.from({ length: 11 }, (_, i) => `c${i}`)
  assert.equal(chartFromResult(manyCols, [Array(11).fill(1)]), null)
})
