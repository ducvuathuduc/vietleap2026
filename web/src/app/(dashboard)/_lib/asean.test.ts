import assert from "node:assert/strict"
import { test } from "node:test"

import fixture from "../../../lib/monitor/__fixtures__/synthetic.monitor.json" with { type: "json" }
import type { Monitor } from "../../../lib/monitor/types.ts"
import { aseanPage } from "./asean.ts"
import { gapUnit } from "./common.ts"

const monitor = fixture as Monitor

/** Small multi-country payload: ranking, median and an annual series for three countries. */
function withRegion(): Monitor {
  const copy = structuredClone(monitor) as Monitor
  copy.asean.credit_ytd = {
    year: 2024,
    rows: [
      { iso3: "VNM", name_vi: "Việt Nam", value: 11.8, rank: 2 },
      { iso3: "THA", name_vi: "Thái Lan", value: 13.4, rank: 1 },
      { iso3: "IDN", name_vi: "Indonesia", value: 8.2, rank: 3 },
    ],
    vn_rank: 2,
    n: 3,
    median: 11.8,
    higher_is_better: true,
    source_id: "nso",
  }
  copy.series.credit_ytd = [
    { period: "2023", value: 10.2, geo: "VNM" },
    { period: "2024", value: 11.8, geo: "VNM" },
    { period: "2023", value: 12.9, geo: "THA" },
    { period: "2024", value: 13.4, geo: "THA" },
    { period: "2023", value: 7.4, geo: "IDN" },
    { period: "2024", value: 8.2, geo: "IDN" },
  ]
  return copy
}

test("asean ranks a single country and always keeps the same indicator selected", () => {
  const page = aseanPage(monitor, null)
  assert.ok(page)
  assert.equal(page.selectedId, "credit_ytd")
  assert.equal(page.headline, "Việt Nam thứ 1/1 về Tăng tín dụng năm 2024, cách trung vị 0 điểm %.")
  assert.equal(page.selector.length, 1)
  assert.equal(page.selector[0]?.active, true)
  assert.equal(page.figures.length, 1)
  assert.equal(page.figures[0]?.number, 1)
  assert.equal(page.figures[0]?.body?.kind, "bar")
  assert.equal(page.yearNote, "Năm chung gần nhất: 2024.")
})

test("asean falls back to the first named indicator for an unknown query value", () => {
  const page = aseanPage(monitor, "khong_ton_tai")
  assert.ok(page)
  assert.equal(page.selectedId, "credit_ytd")
  assert.equal(page.selector[0]?.href, "/asean?indicator=credit_ytd")
})

test("asean draws ranking, spread and timeline with a highlighted Vietnam", () => {
  const page = aseanPage(withRegion(), null)
  assert.ok(page)
  assert.equal(page.headline, "Việt Nam thứ 2/3 về Tăng tín dụng năm 2024, cách trung vị 0 điểm %.")
  assert.deepEqual(
    page.figures.map((figure) => figure.body?.kind),
    ["bar", "range", "line"],
  )
  const rank = page.figures[0]?.body
  assert.equal(rank?.kind, "bar")
  if (rank?.kind === "bar") {
    assert.equal(rank.rows.filter((row) => row.highlight).length, 1)
    assert.equal(rank.rows.find((row) => row.id === "VNM")?.highlight, true)
    assert.equal(rank.rows.find((row) => row.id === "THA")?.highlight, false)
  }
  const range = page.figures[1]?.body
  assert.equal(range?.kind, "range")
  if (range?.kind === "range") {
    assert.equal(range.items[0]?.min, 8.2)
    assert.equal(range.items[0]?.median, 11.8)
    assert.equal(range.items[0]?.max, 13.4)
    assert.equal(range.reference, 11.8)
    assert.equal(range.referenceLabel, "Việt Nam")
  }
  const timeline = page.figures[2]?.body
  assert.equal(timeline?.kind, "line")
  if (timeline?.kind === "line") {
    assert.deepEqual(
      timeline.series.map((item) => item.name),
      ["Việt Nam", "Trung vị ASEAN", "Thái Lan"],
    )
    assert.equal(timeline.series[0]?.context, false)
    assert.equal(timeline.series[1]?.context, true)
    assert.equal(timeline.series[0]?.points.length, 2)
  }
  assert.equal(page.figures[2]?.number, 3)
  assert.equal(page.table?.rows.length, 3)
  assert.deepEqual(
    page.table?.columns.map((column) => column.label),
    ["Hạng", "Nước", "Giá trị", "Chênh trung vị"],
  )
  assert.deepEqual(
    page.table?.rows.map((row) => row.name),
    ["Thái Lan", "Việt Nam", "Indonesia"],
  )
  assert.equal(page.table?.rows[1]?.gap, 0)
  assert.equal(page.yearNote, "Năm chung gần nhất: 2024. Chuỗi số liệu: 2023–2024.")
})

test("a gap in a percentage unit is written in percentage points", () => {
  assert.equal(gapUnit("%"), "điểm %")
  assert.equal(gapUnit("% GDP"), "điểm % GDP")
  assert.equal(gapUnit("tỷ đồng"), "tỷ đồng")
})

test("asean renders nothing numeric without a registered source", () => {
  const broken = withRegion()
  const entry = broken.asean.credit_ytd
  assert.ok(entry)
  entry.source_id = "missing"
  const page = aseanPage(broken, null)
  assert.ok(page)
  assert.deepEqual(page.figures, [])
  assert.equal(page.table, null)
})

test("asean returns null when the payload has no regional comparison", () => {
  const empty = structuredClone(monitor) as Monitor
  empty.asean = {}
  assert.equal(aseanPage(empty, null), null)
})
