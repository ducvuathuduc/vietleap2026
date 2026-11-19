import assert from "node:assert/strict"
import { test } from "node:test"

import { formatDateTime, formatNumber, formatPercent, formatPeriod, formatWithUnit } from "./format.ts"

test("formatNumber uses vi-VN grouping and a comma decimal", () => {
  assert.equal(formatNumber(1234.5), "1.234,5")
  assert.equal(formatNumber(1000), "1.000")
  assert.equal(formatNumber(null), "")
})

test("formatPercent keeps the stored percent and does not scale it", () => {
  assert.equal(formatPercent(11.5), "11,5%")
  assert.equal(formatPercent(null), "")
})

test("formatWithUnit appends the payload unit", () => {
  assert.equal(formatWithUnit(11.5, "%"), "11,5%")
  assert.equal(formatWithUnit(1200, "tỷ đồng"), "1.200 tỷ đồng")
  assert.equal(formatWithUnit(null, "%"), "")
})

test("formatDateTime renders the Asia/Saigon clock", () => {
  const text = formatDateTime("2026-11-19T07:05:00.000Z")
  assert.match(text, /14:05/)
  assert.match(text, /19\/11\/2026/)
  assert.equal(formatDateTime("khong-phai-ngay"), "")
  assert.equal(formatDateTime(null), "")
})

test("formatPeriod spells quarter, month and day without changing the year", () => {
  assert.equal(formatPeriod("2026-Q3"), "Quý 3/2026")
  assert.equal(formatPeriod("2026-10"), "10/2026")
  assert.equal(formatPeriod("2026-10-14"), "14/10/2026")
  assert.equal(formatPeriod("2026"), "2026")
})
