import assert from "node:assert/strict"
import { test } from "node:test"

import fixture from "../../../lib/monitor/__fixtures__/synthetic.monitor.json" with { type: "json" }
import type { Monitor } from "../../../lib/monitor/types.ts"
import { sectorIdFromSlug } from "./common.ts"
import { sectorPage } from "./sector.ts"

const monitor = fixture as Monitor

test("unknown sector slugs stay null so the route can call notFound", () => {
  assert.equal(sectorIdFromSlug("ngan-hang"), "banking")
  assert.equal(sectorIdFromSlug("bat-dong-san"), "real_estate")
  assert.equal(sectorIdFromSlug("khong-co"), null)
})

test("a sector page always shows the five tabs and marks the active one", () => {
  const page = sectorPage(monitor, "banking")
  assert.equal(page.level, "drilldown")
  assert.equal(page.tabs.length, 5)
  assert.deepEqual(
    page.tabs.map((tab) => tab.href),
    ["/nganh/tai-chinh-cong", "/nganh/fdi", "/nganh/ngan-hang", "/nganh/thi-truong-von", "/nganh/bat-dong-san"],
  )
  assert.equal(page.tabs.filter((tab) => tab.active).length, 1)
  assert.equal(page.tabs.find((tab) => tab.active)?.id, "banking")
})

test("a sector page maps the headline, cards, chart, watch list and empty table", () => {
  const page = sectorPage(monitor, "banking")
  assert.equal(page.headline, "Câu thẻ.")
  assert.equal(page.hasData, true)
  assert.equal(page.cards.length, 1)
  assert.equal(page.cards[0]?.source, "Nguồn NSO")
  assert.equal(page.figures.length, 1)
  assert.equal(page.figures[0]?.id, "credit_gap")
  assert.equal(page.figures[0]?.number, 1)
  assert.equal(page.figures[0]?.pointCount, 0)
  assert.equal(page.figures[0]?.body, null)
  assert.equal(page.heatmap, null)
  assert.deepEqual(page.tables, [])
  assert.deepEqual(page.watch, [{ text: "Theo dõi chất lượng tài sản." }])
})

test("a sector with only a watch item still counts as having no data", () => {
  const watchOnly = structuredClone(monitor) as Monitor
  const sector = watchOnly.sectors.banking
  assert.ok(sector)
  sector.cards = []
  sector.charts = []
  sector.tables = []
  sector.heatmap = []
  const page = sectorPage(watchOnly, "banking")
  assert.equal(page.hasData, false)
  assert.equal(page.watch.length, 1)
})

test("a sector missing from the payload shows a factual empty state", () => {
  const page = sectorPage(monitor, "fdi")
  assert.equal(page.hasData, false)
  assert.equal(page.headline, "Chưa có số liệu đã xuất bản cho ngành FDI.")
  assert.deepEqual(page.cards, [])
  assert.deepEqual(page.figures, [])
  assert.deepEqual(page.tables, [])
  assert.equal(page.heatmap, null)
})

test("sector cards stay at three and keep unit, period and source", () => {
  const crowded = structuredClone(monitor) as Monitor
  const sector = crowded.sectors.banking
  assert.ok(sector)
  const card = sector.cards[0]
  assert.ok(card)
  sector.cards = Array.from({ length: 5 }, (_, index) => ({ ...card, rule_id: `BR-BK${index}` }))
  assert.equal(sectorPage(crowded, "banking").cards.length, 3)

  const noUnit = structuredClone(monitor) as Monitor
  const brokenCard = noUnit.sectors.banking?.cards[0]
  assert.ok(brokenCard)
  brokenCard.unit = ""
  assert.deepEqual(sectorPage(noUnit, "banking").cards, [])

  const noSource = structuredClone(monitor) as Monitor
  const orphan = noSource.sectors.banking?.cards[0]
  assert.ok(orphan)
  orphan.source_id = "missing"
  assert.deepEqual(sectorPage(noSource, "banking").cards, [])
})

test("a chart without a registered source is not rendered", () => {
  const broken = structuredClone(monitor) as Monitor
  const chart = broken.sectors.banking?.charts[0]
  assert.ok(chart)
  chart.source_ids = ["missing"]
  assert.deepEqual(sectorPage(broken, "banking").figures, [])
})

test("tables only render rows with a registered source and two-way sorting data", () => {
  const withTable = structuredClone(monitor) as Monitor
  const sector = withTable.sectors.banking
  assert.ok(sector)
  const table = sector.tables[0]
  assert.ok(table)
  table.columns = [
    { key: "ten", label_vi: "Tên" },
    { key: "no", label_vi: "Dư nợ", unit: "%", kind: "number" },
  ]
  table.rows = [
    { ten: "A", no: 1.5 },
    { ten: "B", no: 2.5 },
  ]
  const page = sectorPage(withTable, "banking")
  assert.equal(page.tables.length, 1)
  assert.equal(page.tables[0]?.columns[1]?.unit, "%")
  assert.equal(page.tables[0]?.pointCount, 2)
  assert.equal(page.tables[0]?.trust.sourceName, "NSO")

  const noSource = structuredClone(withTable) as Monitor
  const orphan = noSource.sectors.banking?.tables[0]
  assert.ok(orphan)
  orphan.source_ids = ["missing"]
  assert.deepEqual(sectorPage(noSource, "banking").tables, [])
})

test("the heatmap keeps percentile cells and one know-box per KPI indicator", () => {
  const withHeat = structuredClone(monitor) as Monitor
  const sector = withHeat.sectors.banking
  assert.ok(sector)
  sector.heatmap = [
    {
      indicator_id: "credit_ytd",
      cells: [
        { period: "2026-09", value: 10.2, pctile: 65 },
        { period: "2026-10", value: 11.8, pctile: null },
      ],
    },
  ]
  sector.kpi_ids = ["credit_ytd"]
  const page = sectorPage(withHeat, "banking")
  assert.ok(page.heatmap)
  assert.equal(page.heatmap.body?.kind, "heatmap")
  assert.equal(page.heatmap.title, "Phân vị 12 tháng của 1 chỉ số, 09/2026–10/2026.")
  if (page.heatmap.body?.kind === "heatmap") {
    assert.equal(page.heatmap.body.rows[0]?.label, "Tăng tín dụng")
    assert.deepEqual(
      page.heatmap.body.rows[0]?.cells.map((cell) => cell.pctile),
      [65, null],
    )
  }
  assert.equal(page.heatmap.pointCount, 2)
  assert.equal(page.heatmap.number, 2)
  assert.equal(page.knowBoxes.length, 1)
  assert.equal(page.knowBoxes[0]?.definition, "Dư nợ tín dụng so với đầu năm.")
  assert.equal(page.knowBoxes[0]?.frequency, "monthly")
})
