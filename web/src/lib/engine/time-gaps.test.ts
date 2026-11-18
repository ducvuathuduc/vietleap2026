import test from "node:test"
import assert from "node:assert/strict"
import { computeMa3, detectTimeGaps } from "./time-gaps.ts"

test("detectTimeGaps finds missing monthly periods and caps samples at 5", () => {
  const gaps = detectTimeGaps(["2024-01", "2024-02", "2024-05", "2024-06"])
  assert.equal(gaps.count, 2)
  assert.deepEqual(gaps.samples, ["2024-03", "2024-04"])
  assert.equal(gaps.expected_periods, 6)
  assert.equal(gaps.pct_missing, 33.3)
})

test("detectTimeGaps handles contiguous yearly and quarterly series with 0 gaps", () => {
  const yearly = detectTimeGaps(["2020", "2021", "2022", "2023"], "Y")
  assert.equal(yearly.count, 0)
  assert.deepEqual(yearly.samples, [])
  assert.equal(yearly.expected_periods, 4)

  const quarterly = detectTimeGaps(["2024-Q1", "2024-Q2", "2024-Q4"], "Q")
  assert.equal(quarterly.count, 1)
  assert.deepEqual(quarterly.samples, ["2024-Q3"])
  assert.equal(quarterly.pct_missing, 25)
})

test("detectTimeGaps ignores degenerate single-point or unparseable grouped labels", () => {
  assert.equal(detectTimeGaps(["2024-01"]).count, 0)
  assert.equal(detectTimeGaps(["2024-01 (Hà Nội)", "2024-03 (Đà Nẵng)"]).count, 0)
})

test("computeMa3 computes trailing 3-period average and nulls first two / missing windows", () => {
  const out = computeMa3([
    { period: "2024-01", value: 10, n: 1 },
    { period: "2024-02", value: 20, n: 1 },
    { period: "2024-03", value: 30, n: 1 },
    { period: "2024-04", value: 40, n: 1 },
    { period: "2024-05", value: null, n: 0 },
    { period: "2024-06", value: 50, n: 1 },
  ])
  assert.deepEqual(
    out.map((p) => p.ma3),
    [null, null, 20, 30, null, null]
  )
})
