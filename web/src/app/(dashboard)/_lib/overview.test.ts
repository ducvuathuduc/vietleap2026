import assert from "node:assert/strict"
import { test } from "node:test"

import fixture from "../../../lib/monitor/__fixtures__/synthetic.monitor.json" with { type: "json" }
import type { Monitor } from "../../../lib/monitor/types.ts"
import { overviewHeadline, overviewPage } from "./overview.ts"

const monitor = fixture as Monitor

test("overview renders the payload title, lead, one card and the overview chart", () => {
  const page = overviewPage(monitor)
  assert.equal(page.level, "overview")
  assert.equal(page.headline, "Tiêu đề tổng quan")
  assert.deepEqual(page.lead, ["Câu dẫn một."])
  assert.equal(page.cards.length, 1)
  const card = page.cards[0]
  assert.equal(card.value, "1")
  assert.equal(card.unit, "%")
  assert.equal(card.period, "10/2026")
  assert.equal(card.source, "Nguồn NSO")
  assert.equal(card.eyebrow, "Ngân hàng")
  assert.equal(card.action?.href, "/khuyen-nghi#rec_credit")
  assert.equal(page.figure?.id, "credit_gap")
  assert.equal(page.figure?.number, 1)
  assert.equal(page.figure?.pointCount, 0)
  assert.equal(page.figure?.body, null)
  assert.deepEqual(page.actions, [{ label: "Xem dữ liệu", href: "/phuong-phap" }])
  assert.equal(page.recommendations[0]?.href, "/khuyen-nghi#rec_credit")
  assert.equal(page.recommendations[0]?.meta, "SBV · Quý tới")
})

test("overview drops cards that miss unit, period or a registered source", () => {
  const noUnit = structuredClone(monitor) as Monitor
  const card = noUnit.sectors.banking?.cards[0]
  assert.ok(card)
  card.unit = ""
  assert.equal(overviewPage(noUnit).cards.length, 0)

  const noPeriod = structuredClone(monitor) as Monitor
  const periodCard = noPeriod.sectors.banking?.cards[0]
  assert.ok(periodCard)
  periodCard.period = " "
  assert.equal(overviewPage(noPeriod).cards.length, 0)

  const noSource = structuredClone(monitor) as Monitor
  const sourceCard = noSource.sectors.banking?.cards[0]
  assert.ok(sourceCard)
  sourceCard.source_id = "missing"
  assert.equal(overviewPage(noSource).cards.length, 0)
})

test("overview never renders a KPI without unit, period or source", () => {
  const page = overviewPage(monitor)
  assert.deepEqual(page.kpis, [])
  assert.equal(page.kpiTrust, null)

  const noValue = structuredClone(monitor) as Monitor
  noValue.meta.kpi_ids = ["credit_ytd"]
  assert.equal(overviewPage(noValue).kpis.length, 0)

  const noUnit = structuredClone(monitor) as Monitor
  const indicator = noUnit.indicators[0]
  assert.ok(indicator)
  noUnit.meta.kpi_ids = [indicator.id]
  indicator.latest = { period: "2026-10", value: 3.5 }
  indicator.unit = ""
  assert.equal(overviewPage(noUnit).kpis.length, 0)

  const ok = structuredClone(monitor) as Monitor
  const usable = ok.indicators[0]
  assert.ok(usable)
  ok.meta.kpi_ids = [usable.id]
  usable.latest = { period: "2026-10", value: 3.5 }
  usable.sparkline = [
    { period: "2026-08", value: 1 },
    { period: "2026-09", value: 2 },
    { period: "2026-10", value: 3.5 },
  ]
  const strip = overviewPage(ok)
  assert.equal(strip.kpis.length, 1)
  assert.equal(strip.kpis[0]?.value, "3,5")
  assert.equal(strip.kpis[0]?.period, "10/2026")
  assert.deepEqual(strip.kpis[0]?.sparkline, [1, 2, 3.5])
  assert.equal(strip.kpiTrust?.sourceName, "NSO")
})

test("overview caps the KPI strip at six and the card grid at three", () => {
  const many = structuredClone(monitor) as Monitor
  const base = many.indicators[0]
  assert.ok(base)
  many.indicators = Array.from({ length: 8 }, (_, index) => ({
    ...base,
    id: `ind_${index}`,
    latest: { period: "2026-10", value: index + 1 },
    sparkline: [],
  }))
  many.meta.kpi_ids = many.indicators.map((item) => item.id)
  assert.equal(overviewPage(many).kpis.length, 6)

  const crowded = structuredClone(monitor) as Monitor
  const sector = crowded.sectors.banking
  assert.ok(sector)
  const card = sector.cards[0]
  assert.ok(card)
  sector.cards = Array.from({ length: 5 }, (_, index) => ({ ...card, rule_id: `BR-BK${index}` }))
  assert.equal(overviewPage(crowded).cards.length, 3)
})

test("the headline prefers a title with a number and the duplicate card sentence is removed", () => {
  const numericTitle = structuredClone(monitor) as Monitor
  numericTitle.meta.title_vi = "Tín dụng tăng 11,8% trong 10 tháng 2026, chậm 1,2 điểm % so với kế hoạch."
  assert.equal(overviewHeadline(numericTitle.meta, []), numericTitle.meta.title_vi)

  const numericCard = structuredClone(monitor) as Monitor
  const sector = numericCard.sectors.banking
  assert.ok(sector)
  const card = sector.cards[0]
  assert.ok(card)
  sector.cards = [{ ...card, sentence_vi: "Tín dụng tăng 11,8% trong tháng 10/2026, thấp hơn kế hoạch." }]
  const page = overviewPage(numericCard)
  assert.equal(page.headline, "Tín dụng tăng 11,8% trong tháng 10/2026, thấp hơn kế hoạch.")
  assert.equal(page.cards.length, 0)
  assert.equal(page.lead.length, 1)
})

test("the lead never repeats a card sentence", () => {
  const repeated = structuredClone(monitor) as Monitor
  const card = repeated.sectors.banking?.cards[0]
  assert.ok(card)
  repeated.meta.lead_vi = ["Câu thẻ.", "Điều mới nhất."]
  assert.deepEqual(overviewPage(repeated).lead, ["Điều mới nhất."])

  const onlyRepeat = structuredClone(monitor) as Monitor
  onlyRepeat.meta.lead_vi = ["Câu thẻ."]
  assert.deepEqual(overviewPage(onlyRepeat).lead, ["Câu thẻ."])
})
