// Run: npm test
import assert from "node:assert/strict"
import { test } from "node:test"

import {
  LEVEL_LABELS,
  canRenderChart,
  emptyPeriodText,
  figureLabel,
  formatDay,
  frequencyLabel,
  groupToStep,
  levelLabel,
  loadErrorText,
  nextReleaseText,
  partialPeriodText,
  pctileToStep,
  stepFill,
  stepTextClass,
  trustText,
  updateBadge,
} from "./labels.ts"
import { enterClass } from "./motion.ts"

test("level labels follow the mentor vocabulary and cover exactly three levels", () => {
  assert.equal(levelLabel("overview"), "Tổng quan · Overview")
  assert.equal(levelLabel("drilldown"), "Đào sâu · Drill-down")
  assert.equal(levelLabel("detail"), "Chi tiết · Detail")
  assert.equal(Object.keys(LEVEL_LABELS).length, 3)
})

test("formatDay renders dd/mm/yyyy in Asia/Saigon and keeps period shapes", () => {
  assert.equal(formatDay("2026-11-19T07:05:00.000Z"), "19/11/2026")
  // 18:30 UTC is already 01:30 of the next day in Saigon.
  assert.equal(formatDay("2026-11-18T18:30:00.000Z"), "19/11/2026")
  assert.equal(formatDay("2026-03-15"), "15/03/2026")
  assert.equal(formatDay("2026-10"), "10/2026")
  assert.equal(formatDay("2026-Q3"), "Quý 3/2026")
  assert.equal(formatDay(""), "")
  assert.equal(formatDay(null), "")
  assert.equal(formatDay(undefined), "")
  assert.equal(formatDay("khong-phai-ngay"), "")
})

test("pctileToStep maps a 12m percentile onto 5 grey steps and keeps null blank", () => {
  assert.equal(pctileToStep(0), 0)
  assert.equal(pctileToStep(19.9), 0)
  assert.equal(pctileToStep(20), 1)
  assert.equal(pctileToStep(55), 2)
  assert.equal(pctileToStep(99), 4)
  assert.equal(pctileToStep(100), 4)
  assert.equal(pctileToStep(-5), 0)
  assert.equal(pctileToStep(null), null)
  assert.equal(pctileToStep(undefined), null)
  assert.equal(pctileToStep(Number.NaN), null)
})

test("groupToStep ranks province groups onto the same 5 steps", () => {
  const groups = [{ group: 1 }, { group: 2 }, { group: 3 }, { group: 4 }, { group: 5 }]
  assert.equal(groupToStep(1, groups), 0)
  assert.equal(groupToStep(3, groups), 2)
  assert.equal(groupToStep(5, groups), 4)
  assert.equal(groupToStep(2, [{ group: 1 }]), null)
  assert.equal(groupToStep(null, groups), null)
  assert.equal(groupToStep(1, [{ group: 1 }, { group: 2 }, { group: 3 }]), 0)
})

test("stepFill and stepTextClass only fill cells that have a step", () => {
  assert.equal(stepFill(null), "")
  assert.equal(stepFill(undefined), "")
  assert.equal(stepFill(0), "var(--chart-1)")
  assert.equal(stepFill(4), "var(--chart-5)")
  assert.equal(stepFill(9), "var(--chart-5)")
  assert.equal(stepTextClass(null), "")
  assert.equal(stepTextClass(0), "text-foreground")
  assert.equal(stepTextClass(4), "text-background")
})

test("trust copy states source, update date and next release", () => {
  assert.equal(
    trustText({ sourceName: "World Bank WDI", lastUpdated: "2026-03-15", nextRelease: "2027-03" }),
    "Nguồn World Bank WDI · Cập nhật 15/03/2026 · Kỳ tới 03/2027"
  )
  assert.equal(
    trustText({ sourceName: "NSO", lastUpdated: "2026-10", nextRelease: null }),
    "Nguồn NSO · Cập nhật 10/2026 · Chưa có lịch kỳ tới"
  )
  assert.equal(nextReleaseText(undefined), "Chưa có lịch kỳ tới")
  // Fail closed: no source means no line at all.
  assert.equal(trustText({ sourceName: "", lastUpdated: "2026-10" }), "")
  assert.equal(trustText({}), "")
})

test("update badge and empty states use the spec copy", () => {
  assert.equal(updateBadge("2026-11-19T07:05:00.000Z"), "Cập nhật 19/11/2026")
  assert.equal(updateBadge(null), "")
  assert.equal(emptyPeriodText("monthly"), "Chưa có số liệu kỳ này. Nguồn công bố: hàng tháng.")
  assert.equal(emptyPeriodText(undefined), "Chưa có số liệu kỳ này.")
  assert.equal(frequencyLabel("quarterly"), "hàng quý")
  assert.equal(frequencyLabel("unknown"), "")
  assert.equal(partialPeriodText(9), "Số liệu 9 tháng, chưa gồm ước tính tháng 10.")
  assert.equal(loadErrorText("biểu đồ tín dụng"), "Không tải được biểu đồ tín dụng. Thử lại.")
})

test("charts fail closed without a source or without points", () => {
  assert.equal(canRenderChart({ sourceIds: ["nso"], pointCount: 2 }), true)
  assert.equal(canRenderChart({ sourceIds: [], pointCount: 2 }), false)
  assert.equal(canRenderChart({ sourceIds: ["nso"], pointCount: 0 }), false)
  assert.equal(canRenderChart({}), false)
})

test("figure caption carries the chart number when the payload has one", () => {
  assert.equal(figureLabel(1, "Tín dụng lệch huy động"), "Hình 1 · Tín dụng lệch huy động")
  assert.equal(figureLabel(null, "Tín dụng lệch huy động"), "Tín dụng lệch huy động")
})

test("no builder emits placeholder text instead of a number", () => {
  const outputs = [
    trustText({ sourceName: "NSO", lastUpdated: null, nextRelease: null }),
    nextReleaseText(null),
    updateBadge(null),
    emptyPeriodText("monthly"),
    partialPeriodText(3),
    loadErrorText("biểu đồ"),
    figureLabel(2, "Tiêu đề"),
    stepFill(null),
    levelLabel("detail"),
  ]
  for (const text of outputs) {
    assert.doesNotMatch(text, /N\/A|\bnull\b|\bundefined\b|NaN/, text)
  }
})

test("motion helper is CSS-only and respects reduced motion", () => {
  const base = enterClass()
  assert.match(base, /duration-\[180ms\]/)
  assert.match(base, /starting:opacity-0/)
  assert.match(base, /starting:translate-y-1/)
  assert.match(base, /motion-reduce:transition-none/)
  assert.match(enterClass(40), /\[transition-delay:40ms\]/)
  assert.doesNotMatch(enterClass(0), /transition-delay/)
})
