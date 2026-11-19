import assert from "node:assert/strict"
import { test } from "node:test"

import fixture from "./__fixtures__/synthetic.monitor.json" with { type: "json" }
import { MONITOR_EMPTY_VI, aseanView, methodView, overviewView, provinceDetailView, provinceView, recommendationView, sectorView } from "./sections.ts"
import type { Monitor } from "./types.ts"

const monitor = fixture as Monitor

test("missing monitor copy is the published empty state", () => {
  assert.equal(
    MONITOR_EMPTY_VI,
    "Chưa có dữ liệu đã xuất bản. Chạy pipeline vn_monitor để tạo out/vn_monitor/monitor.json.",
  )
  assert.equal(/\d/.test(MONITOR_EMPTY_VI), false)
})

test("overview reads the payload headline and question", () => {
  const view = overviewView(monitor)
  assert.equal(view.headline, "Tiêu đề tổng quan")
  assert.equal(view.question, "Vốn đang kẹt ở đâu?")
  assert.ok(view.sections.length > 0)
  assert.ok(view.sections.every((section) => !/\d/.test(section.label)))
})

test("sector view prefers payload titles over a typed figure", () => {
  const view = sectorView(monitor, "banking", "Ngân hàng")
  assert.equal(view.headline, "Bộ đệm ngân hàng đang mỏng.")
  assert.equal(view.question, "Tín dụng tăng nhanh hơn huy động?")
  assert.deepEqual(view.sections.map((section) => section.label), [
    "Thẻ kết luận",
    "Cần theo dõi",
    "Tín dụng lệch huy động.",
    "Bảng dư nợ.",
  ])
})

test("a known sector missing from the payload still has a placeholder list", () => {
  const view = sectorView(monitor, "fdi", "FDI")
  assert.equal(view.headline, "FDI")
  assert.equal(view.question, "")
  assert.deepEqual(view.sections.map((section) => section.label), ["Thẻ kết luận", "Cần theo dõi", "Biểu đồ", "Bảng"])
})

test("asean sections use indicator names", () => {
  const view = aseanView(monitor)
  assert.equal(view.headline, "Chỉ số & ASEAN")
  assert.deepEqual(view.sections.map((section) => section.label), ["Tăng tín dụng"])
  assert.ok(view.sections.every((section) => section.label !== "credit_ytd"))
})

test("province detail resolves a code and rejects an unknown one", () => {
  assert.equal(provinceView(monitor).headline, "Nhóm tỉnh.")
  assert.equal(provinceView(monitor).question, "Tỉnh nào lệch trung vị?")
  assert.equal(provinceDetailView(monitor, "HN")?.headline, "Hà Nội")
  assert.equal(provinceDetailView(monitor, "ZZ"), null)
  assert.deepEqual(provinceDetailView(monitor, "HN")?.sections.map((section) => section.label), ["Tăng tín dụng"])
})

test("recommendation and method views list payload titles", () => {
  assert.deepEqual(recommendationView(monitor).sections.map((section) => section.label), ["Siết bộ đệm vốn."])
  assert.equal(recommendationView(monitor).headline, "Phân tích & Khuyến nghị")
  assert.ok(methodView(monitor).sections.some((section) => section.label === "Báo cáo KT-XH"))
  assert.ok(methodView(monitor).sections.every((section) => !section.label.includes("nso")))
})
