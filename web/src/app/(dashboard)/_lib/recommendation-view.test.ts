import assert from "node:assert/strict"
import { test } from "node:test"

import fixture from "../../../lib/monitor/__fixtures__/synthetic.monitor.json" with { type: "json" }
import type { Monitor, Rule } from "../../../lib/monitor/types.ts"
import { recommendationPage } from "./recommendation-view.ts"

const monitor = fixture as Monitor

function withRules(): Monitor {
  const next = structuredClone(monitor) as Monitor
  const fired: Rule = {
    id: "BR-BK1",
    name_vi: "Bộ đệm vốn",
    formula_vi: "Vốn trừ dư nợ.",
    threshold_vi: "Dưới 8%.",
    fired: true,
    agency_vi: "Ngân hàng Nhà nước",
  }
  const idle: Rule = {
    id: "BR-BK2",
    name_vi: "Nợ xấu",
    formula_vi: "Nợ nhóm 3 trở lên chia tổng dư nợ.",
    threshold_vi: "Trên 3%.",
    fired: false,
  }
  next.rules = [idle, fired]
  return next
}

test("recommendation page numbers the work and points evidence at the sector chart", () => {
  const page = recommendationPage(withRules())
  assert.equal(page.level, "detail")
  assert.equal(page.headline, "1 việc cần làm trong Quý tới.")
  assert.equal(page.items.length, 1)
  const item = page.items[0]
  assert.ok(item)
  assert.equal(item.title, "1. Siết bộ đệm vốn.")
  assert.equal(item.agency, "SBV")
  assert.equal(item.horizon, "Quý tới")
  assert.equal(item.evidence.length, 1)
  assert.equal(item.evidence[0]?.fact, "Một sự kiện.")
  assert.equal(item.evidence[0]?.formula, "Vốn trừ dư nợ.")
  assert.equal(item.evidence[0]?.threshold, "Dưới 8%.")
  assert.equal(item.evidence[0]?.chartHref, "/nganh/ngan-hang#credit_gap")
  assert.equal(item.figures[0]?.id, "credit_gap")
})

test("recommendation page lists every rule as fired or not yet evaluated", () => {
  const page = recommendationPage(withRules())
  assert.deepEqual(
    page.rules.map((rule) => ({ name: rule.name, status: rule.status })),
    [
      { name: "Bộ đệm vốn", status: "Đã kích hoạt" },
      { name: "Nợ xấu", status: "Chưa đánh giá" },
    ],
  )
  assert.equal(page.rules[0]?.formula, "Vốn trừ dư nợ.")
  assert.equal(page.rules[1]?.threshold, "Trên 3%.")
  assert.equal(page.rules[0]?.agency, "Ngân hàng Nhà nước")
})

test("central agencies appear only when a recommendation compares disbursement by unit", () => {
  const next = withRules()
  next.sources.push({
    id: "bcp_mof_dtc_2026_10",
    publisher: "BCP_MOF_DTC_2026_10",
    title_vi: "Báo cáo ngành và công bố chuyên đề",
    url: "https://bcp.cdnchinhphu.vn/report",
    method: "file",
    license: "Nguồn công bố",
    fetched_at: "2026-11-19T07:05:00.000Z",
    data_cutoff: "2026-10",
  })
  const national = structuredClone(next.indicators[0])
  national.id = "dtc_giai_ngan_pct_plan"
  national.name_vi = "Giải ngân đầu tư công so với dự toán hoặc kế hoạch"
  national.unit = "%"
  national.latest = { period: "2026-10", value: 70 }
  next.indicators.push(national)
  const agencies = [
    ["Bộ Công Thương", 10, 100],
    ["Bộ Công an", 20, 200],
    ["Bộ Giáo dục", 30, 300],
    ["Bộ Y tế", 40, 400],
    ["Liên minh Hợp tác xã Việt Nam", 50, null],
  ] as const
  next.reconciliation = agencies.flatMap(([name, rate, amount]) => {
    const rows = [
      {
        indicator_id: "dtc_ministry_disbursed",
        period: "2026-10",
        values: { bcp_mof_dtc_2026_10: rate },
        diff_pct: 0,
        tolerance_pct: 1,
        verdict: "single_source" as const,
        note_vi: `${name} · pct_plan · %`,
      },
    ]
    if (amount !== null) {
      rows.push({
        indicator_id: "dtc_ministry_disbursed",
        period: "2026-10",
        values: { bcp_mof_dtc_2026_10: amount },
        diff_pct: 0,
        tolerance_pct: 1,
        verdict: "single_source",
        note_vi: `${name} · level · triệu đồng`,
      })
    }
    return rows
  })

  assert.equal(recommendationPage(next).agencies, null)

  const disbursement = next.rules?.find((rule) => rule.id === "BR-BK1")
  assert.ok(disbursement)
  disbursement.formula_vi = "Tỷ lệ giải ngân từng đơn vị so với trung ương và địa phương."
  disbursement.name_vi = "Tiến độ giải ngân đầu tư công"
  const page = recommendationPage(next)
  assert.equal(page.agencies?.rows.length, 5)
  assert.equal(page.agencies?.national, "70%")
  assert.equal(page.agencies?.rows[0]?.name, "Bộ Công an")
  assert.equal(page.agencies?.rows[0]?.rate, "20%")
  assert.equal(page.agencies?.rows[0]?.gap, "-50 điểm %")
  assert.equal(page.agencies?.rows.find((row) => row.name === "Liên minh Hợp tác xã Việt Nam")?.amount, "–")
  assert.equal(page.agencies?.rows.some((row) => row.name.includes("_") || row.rate.includes("pct_plan")), false)
  assert.deepEqual(
    page.agencies?.groups.map((group) => group.range),
    ["10–18", "18–26", "26–34", "34–42", "42–50"],
  )
  assert.equal(page.agencies?.sourceName.includes("BCP_MOF"), false)
})

test("recommendation page has no items when the payload has no recommendations", () => {
  const next = structuredClone(monitor) as Monitor
  next.recommendations = []
  const page = recommendationPage(next)
  assert.equal(page.items.length, 0)
  assert.equal(page.headline, "")
})
