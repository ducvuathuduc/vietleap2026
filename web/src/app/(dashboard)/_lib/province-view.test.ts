import assert from "node:assert/strict"
import { test } from "node:test"

import fixture from "../../../lib/monitor/__fixtures__/synthetic.monitor.json" with { type: "json" }
import type { Monitor } from "../../../lib/monitor/types.ts"
import { provinceDetail, provincePage } from "./province-view.ts"

const monitor = fixture as Monitor

function withValues(): Monitor {
  const next = structuredClone(monitor) as Monitor
  next.province.headline_vi = "Nhóm tỉnh."
  next.province.primary_metric = "credit_ytd"
  next.province.source_ids = ["nso"]
  next.province.groups = [
    { group: 1, label_vi: "Nhóm 1", min: 1, max: 4, count: 1 },
    { group: 2, label_vi: "Nhóm 2", min: 10, max: 10, count: 1 },
  ]
  next.province.stats = { credit_ytd: { median: 4, min: 1, max: 10, n: 2 } }
  next.province.rows = [
    { code: "HN", name: "Hà Nội", region: "Đồng bằng sông Hồng", metrics: { credit_ytd: 1 }, group: 1 },
    { code: "SG", name: "Thành phố Hồ Chí Minh", region: "Đông Nam Bộ", metrics: { credit_ytd: 10 }, group: 2 },
  ]
  return next
}

test("province page keeps a headline that already states a number", () => {
  const next = withValues()
  next.province.headline_vi = "Trung vị năm 2025 là 4 tỷ đồng mỗi tỉnh có số liệu."
  const page = provincePage(next, null)
  assert.equal(page.headline, "Trung vị năm 2025 là 4 tỷ đồng mỗi tỉnh có số liệu.")
})

test("province page builds the headline from the median gap when the payload title has no number", () => {
  const page = provincePage(withValues(), null)
  assert.equal(
    page.headline,
    "1/2 tỉnh dưới trung vị về Tăng tín dụng, thấp nhất Hà Nội 1%, tháng 10/2026",
  )
  assert.equal(page.level, "detail")
  assert.equal(page.lead[0], "Tỉnh nào lệch trung vị?")
})

test("province page lists group chips, a national range and one table row per province", () => {
  const page = provincePage(withValues(), null)
  assert.deepEqual(
    page.groups.map((group) => ({ label: group.label, range: group.range, count: group.count })),
    [
      { label: "Nhóm 1", range: "1–4", count: "1" },
      { label: "Nhóm 2", range: "10–10", count: "1" },
    ],
  )
  assert.equal(page.range?.items.length, 1)
  assert.deepEqual(page.range?.items[0], {
    id: "credit_ytd",
    label: "Tăng tín dụng",
    min: 1,
    median: 4,
    max: 10,
  })
  assert.equal(page.range?.unit, "%")
  assert.equal(page.map?.rows.length, 2)
  assert.equal(page.map?.rows[0]?.value, 1)
  assert.equal(page.table.length, 2)
  assert.equal(page.table[0]?.name, "Hà Nội")
  assert.equal(page.table[0]?.href, "/tinh/HN")
  assert.equal(page.table[0]?.group, "Nhóm 1")
  assert.equal(page.table[0]?.valueText, "1%")
  assert.equal(page.table[0]?.gapText, "-3 điểm %")
  assert.equal(page.table[1]?.gapText, "+6 điểm %")
  assert.equal(page.unit, "%")
})

test("province page keeps a missing metric as a dash and can filter rows by group", () => {
  const next = withValues()
  next.province.rows[1].metrics = { credit_ytd: null }
  const page = provincePage(next, "2")
  assert.equal(page.table.length, 1)
  assert.equal(page.table[0]?.name, "Thành phố Hồ Chí Minh")
  assert.equal(page.table[0]?.valueText, "–")
  assert.equal(page.table[0]?.gapText, "–")
  assert.equal(page.activeGroup, "2")
  assert.equal(provincePage(next, "9").table.length, 2)
})

test("province page adds public-investment disbursement as five groups and hides province codes", () => {
  const next = withValues()
  next.sources.push({
    id: "bcp_mof_dtc_2026_10",
    publisher: "BCP_MOF_DTC_2026_10",
    title_vi: "Báo cáo ngành và công bố chuyên đề",
    url: "https://bcp.cdnchinhphu.vn/report",
    method: "file",
    license: "Nguồn công bố",
    fetched_at: "2026-11-19T14:05:00+07:00",
    data_cutoff: "2026-10",
  })
  const places = [
    ["ha_noi", "Hà Nội", 10, 1000],
    ["hai_phong", "Hải Phòng", 20, 2000],
    ["da_nang", "Đà Nẵng", 30, 3000],
    ["can_tho", "Cần Thơ", 40, 4000],
    ["hue", "Huế", 50, 5000],
  ] as const
  next.province.rows = places.map(([code, name], index) => ({
    code,
    name,
    region: "Thử",
    metrics: { credit_ytd: index + 1 },
    group: 1,
  }))
  next.reconciliation = places.flatMap(([code, , rate, amount]) => [
    {
      indicator_id: "dtc_province_disbursed",
      period: "2026-10",
      values: { bcp_mof_dtc_2026_10: rate },
      diff_pct: 0,
      tolerance_pct: 1,
      verdict: "single_source" as const,
      note_vi: `${code} · pct_plan · %`,
    },
    {
      indicator_id: "dtc_province_disbursed",
      period: "2026-10",
      values: { bcp_mof_dtc_2026_10: amount },
      diff_pct: 0,
      tolerance_pct: 1,
      verdict: "single_source" as const,
      note_vi: `${code} · level · triệu đồng`,
    },
  ])

  assert.equal(provincePage(withValues(), null).disbursement, null)

  const page = provincePage(next, null, null)
  assert.equal(
    page.disbursement?.headline,
    "2/5 tỉnh dưới trung vị về Giải ngân đầu tư công so với kế hoạch, thấp nhất Hà Nội 10%, tháng 10/2026",
  )
  assert.deepEqual(
    page.disbursement?.groups.map((group) => ({ label: group.label, range: group.range, count: group.count })),
    [
      { label: "Nhóm 1", range: "10–18", count: "1" },
      { label: "Nhóm 2", range: "18–26", count: "1" },
      { label: "Nhóm 3", range: "26–34", count: "1" },
      { label: "Nhóm 4", range: "34–42", count: "1" },
      { label: "Nhóm 5", range: "42–50", count: "1" },
    ],
  )
  assert.equal(page.disbursement?.table[0]?.name, "Hà Nội")
  assert.equal(page.disbursement?.table[0]?.valueText, "10%")
  assert.equal(page.disbursement?.table[0]?.gapText, "-20 điểm %")
  assert.equal(page.disbursement?.table.some((row) => row.name.includes("_")), false)
  assert.equal(page.disbursement?.map?.rows.length, 5)
  assert.equal(page.disbursement?.range?.items[0]?.median, 30)
  assert.equal(page.disbursement?.trust?.sourceName.includes("BCP_MOF"), false)
  assert.equal(page.disbursement?.trust?.sourceName.includes("bcp.cdnchinhphu.vn"), true)

  const filtered = provincePage(next, null, "1")
  assert.equal(filtered.disbursement?.table.length, 1)
  assert.equal(filtered.disbursement?.table[0]?.name, "Hà Nội")

  const detail = provinceDetail(next, "ha_noi")
  assert.equal(detail?.metrics.some((metric) => metric.name === "Giải ngân đầu tư công so với kế hoạch" && metric.valueText === "10%" && metric.medianText === "30%" && metric.gapText === "-20 điểm %"), true)
  assert.equal(detail?.metrics.some((metric) => metric.name === "Giải ngân đầu tư công" && metric.valueText === "1.000 triệu đồng" && metric.gapText === "-2.000 triệu đồng"), true)
})

test("province detail compares every metric with the national median and rejects an unknown code", () => {
  const next = withValues()
  next.province.metric_ids = ["credit_ytd"]
  assert.equal(provinceDetail(next, "missing"), null)
  const detail = provinceDetail(next, "hn")
  assert.ok(detail)
  assert.equal(
    detail.headline,
    "Hà Nội đứng Nhóm 1 về Tăng tín dụng: 1% so với trung vị -3 điểm %, tháng 10/2026",
  )
  assert.equal(detail.backHref, "/tinh")
  assert.equal(detail.metrics.length, 1)
  assert.equal(detail.metrics[0]?.name, "Tăng tín dụng")
  assert.equal(detail.metrics[0]?.valueText, "1%")
  assert.equal(detail.metrics[0]?.medianText, "4%")
  assert.equal(detail.metrics[0]?.gapText, "-3 điểm %")
  assert.equal(detail.trust?.sourceName, "NSO")
})
