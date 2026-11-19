import assert from "node:assert/strict"
import { test } from "node:test"

import fixture from "./__fixtures__/synthetic.monitor.json" with { type: "json" }
import {
  answerOffline,
  flaggedNumbers,
  getIndicator,
  getProvince,
  getRecommendations,
  getRules,
  getSector,
  listIndicators,
  monitorChatGate,
  qaSystemPrompt,
} from "./qa.ts"
import type { Monitor } from "./types.ts"

const monitor = fixture as Monitor

test("listIndicators reads names and latest values from the fixture", () => {
  const items = listIndicators(monitor)
  assert.equal(items.length, 1)
  assert.equal(items[0]?.id, "credit_ytd")
  assert.equal(items[0]?.name_vi, "Tăng tín dụng")
  assert.deepEqual(items[0]?.latest, { period: "2026-10", value: null })
  assert.equal(items[0]?.source_id, "nso")
  assert.equal(items[0]?.source_publisher, "NSO")
})

test("getIndicator returns latest, sparkline, definition and source", () => {
  const detail = getIndicator(monitor, "credit_ytd")
  assert.equal(detail?.definition_vi, "Dư nợ tín dụng so với đầu năm.")
  assert.deepEqual(detail?.latest, { period: "2026-10", value: null })
  assert.deepEqual(detail?.sparkline, [])
  assert.equal(detail?.source?.publisher, "NSO")
  assert.equal(detail?.source?.title_vi, "Báo cáo KT-XH")
  assert.equal(getIndicator(monitor, "khong_co"), null)
})

test("getSector returns cards and a table summary", () => {
  const sector = getSector(monitor, "banking")
  assert.equal(sector?.cards[0]?.sentence_vi, "Câu thẻ.")
  assert.equal(sector?.cards[0]?.value, 1)
  assert.equal(sector?.cards[0]?.period, "2026-10")
  assert.equal(sector?.tables[0]?.title_vi, "Bảng dư nợ.")
  assert.equal(sector?.tables[0]?.row_count, 0)
  assert.deepEqual(sector?.tables[0]?.columns, ["Tên"])
  assert.equal(getSector(monitor, "fdi"), null)
})

test("getProvince returns one province or a metric ranking", () => {
  const province = getProvince(monitor, { code: "hn" })
  assert.equal(province && "metrics" in province ? province.name : "", "Hà Nội")
  assert.equal(province && "metrics" in province ? province.metrics[0]?.value : 1, null)
  assert.equal(getProvince(monitor, { code: "khong_co" }), null)

  const ranked = getProvince(monitor, { metric: "credit_ytd" })
  assert.equal(ranked && "ranking" in ranked ? ranked.ranking[0]?.name : "", "Hà Nội")
  assert.equal(ranked && "ranking" in ranked ? ranked.ranking[0]?.value : 1, null)
  assert.equal(ranked && "ranking" in ranked ? ranked.ranking[0]?.rank : 1, null)
})

test("province ranking cites the published source and period", () => {
  const next = structuredClone(monitor)
  next.province.source_ids = ["nso"]
  const ranked = getProvince(next, { metric: "credit_ytd" })
  assert.equal(ranked && "sources" in ranked ? ranked.sources[0]?.publisher : "", "NSO")
  assert.equal(ranked && "period" in ranked ? ranked.period : "", "2026-10")
})

test("province ranking orders finite values and leaves gaps unranked", () => {
  const next = structuredClone(monitor)
  next.province.rows = [
    { code: "HN", name: "Hà Nội", region: "Đồng bằng sông Hồng", metrics: { credit_ytd: 5 }, group: 1 },
    { code: "SG", name: "TP. Hồ Chí Minh", region: "Đông Nam Bộ", metrics: { credit_ytd: 12.5 }, group: 1 },
    { code: "HP", name: "Hải Phòng", region: "Đồng bằng sông Hồng", metrics: { credit_ytd: null }, group: 1 },
  ]
  const ranked = getProvince(next, { metric: "credit_ytd" })
  assert.deepEqual(
    ranked && "ranking" in ranked ? ranked.ranking.map((row) => [row.code, row.rank, row.value]) : [],
    [
      ["SG", 1, 12.5],
      ["HN", 2, 5],
      ["HP", null, null],
    ]
  )
})

test("getRecommendations and getRules read the published lists", () => {
  assert.equal(getRecommendations(monitor)[0]?.title_vi, "Siết bộ đệm vốn.")
  assert.equal(getRecommendations(monitor)[0]?.agency_vi, "SBV")
  assert.equal(getRecommendations(monitor)[0]?.evidence[0]?.fact_vi, "Một sự kiện.")
  assert.deepEqual(getRules(monitor), [])
})

test("offline answer cites the indicator name, period and source", () => {
  const text = answerOffline(monitor, "Tăng tín dụng đang ở mức nào?")
  assert.match(text, /Tăng tín dụng/)
  assert.match(text, /chưa có số/)
  assert.match(text, /tháng 10\/2026/)
  assert.match(text, /NSO/)
  assert.doesNotMatch(text, /dataset/i)
  assert.doesNotMatch(text, /\bAI\b/)
  assert.deepEqual(flaggedNumbers(text, [getIndicator(monitor, "credit_ytd")]), [])
})

test("guard flags an invented number", () => {
  const detail = getIndicator(monitor, "credit_ytd")
  assert.deepEqual(flaggedNumbers("Tăng tín dụng đạt 48,2% trong tháng 10/2026.", [detail]), ["48,2"])
  assert.deepEqual(flaggedNumbers("Kỳ tháng 10/2026, nguồn NSO.", [detail]), [])
})

test("gate off returns 404", () => {
  const prev = process.env.ENABLE_CHAT
  try {
    delete process.env.ENABLE_CHAT
    assert.equal(monitorChatGate()?.status, 404)
    process.env.ENABLE_CHAT = "true"
    assert.equal(monitorChatGate()?.status, 404)
    process.env.ENABLE_CHAT = "1"
    assert.equal(monitorChatGate(), null)
  } finally {
    if (prev === undefined) delete process.env.ENABLE_CHAT
    else process.env.ENABLE_CHAT = prev
  }
})

test("system prompt asks for a Vietnamese citation and names no dataset", () => {
  const prompt = qaSystemPrompt()
  assert.match(prompt, /tiếng Việt/)
  assert.match(prompt, /nguồn/)
  assert.match(prompt, /kỳ/)
  assert.doesNotMatch(prompt, /\bAI\b/)
  assert.doesNotMatch(prompt, /dataset/i)
})
