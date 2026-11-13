// Run: npm test
import { test } from "node:test"
import assert from "node:assert/strict"

import { escapeHtml, groundTruthNumbers, mergeDraft, numberCandidates, offlineStory, parseDraft, pickInsights, stepSelector, ungroundedNumbers } from "./story.ts"

// Shapes mirror engine results.json (values copied from the bds_practice run).
const ins = (id: string, rank: number, sentence: string, extra: Record<string, unknown> = {}) => ({
  id, rank, type: "segment_gap", title_en: id, title_vi: `tiêu đề ${id}`, sentence_en: "", sentence_vi: sentence,
  value: null, test: "Kruskal–Wallis", effect: 0.218, p_value: 5.3e-115, relevance: 1, score: 1, chart: null,
  evidence: { n: 2427 }, columns: [], caveat: null, ...extra,
}) as never
const rec = (from: string) => ({
  so_what_en: "", now_what_en: "", impact_en: "", so_what_vi: "gấp 2.104 lần", now_what_vi: `làm ${from}`, impact_vi: "≈ +35.9%",
  from_insight: from, type: "segment_gap", confidence: "high",
}) as never

const A = ins("a", 1, "Trung vị cao nhất ở Biệt thự (127 triệu đồng, n=567), thấp nhất ở Đất nền (60,3 triệu đồng), chênh 2,10 lần.", { value: { top_median: 126840491 } })
const B = ins("b", 2, "Diện tích tương quan với giá (ρ=0,41).")
const C = ins("c", 3, "Câu c.")

test("pickInsights keeps engine rank order and size", () => {
  assert.deepEqual(pickInsights([C, A, B] as never, 2).map((i: { id: string }) => i.id), ["a", "b"])
})

test("offlineStory copies engine sentences and actions verbatim", () => {
  const s = offlineStory([A, B, C] as never, [rec("a")], "bds", 5)
  assert.equal(s.mode, "offline")
  assert.equal(s.steps.length, 3)
  assert.equal(s.steps[0].narration, (A as { sentence_vi: string }).sentence_vi)
  assert.equal(s.steps[0].action, "làm a")
  assert.equal(s.steps[1].action, null)
  assert.match(s.steps[0].stats, /p<0,001/)
  assert.match(s.steps[0].stats, /n=2\.427/)
  assert.match(s.closing, /không chứng minh nhân quả/)
})

test("offlineStory with no insights says so", () => {
  const s = offlineStory([], [], "x")
  assert.equal(s.steps.length, 0)
  assert.match(s.headline, /chưa tìm thấy/)
})

test("numberCandidates reads VN and EN separators", () => {
  assert.ok(numberCandidates("60,3").includes(60.3))
  assert.ok(numberCandidates("1.234").includes(1234))
  assert.ok(numberCandidates("2.104").includes(2.104))
  assert.ok(numberCandidates("1.234,5").includes(1234.5))
})

test("ungroundedNumbers accepts engine numbers, scaled units and small counts; rejects invented ones", () => {
  const truth = groundTruthNumbers(A as never, rec("a"))
  assert.deepEqual(ungroundedNumbers("Biệt thự 127 triệu, Đất nền 60,3 triệu, gấp 2,10 lần, 3 nhóm, n=567", truth), [])
  assert.deepEqual(ungroundedNumbers("khoảng 126,8 triệu đồng", truth), [])
  assert.deepEqual(ungroundedNumbers("giá tăng 48% trong 2 năm", truth), ["48"])
})

test("parseDraft tolerates fences/chatter and drops malformed steps", () => {
  const d = parseDraft('Đây:\n```json\n{"headline":"H","steps":[{"id":"a","narration":"N"},{"id":1}],"closing":"C"}\n```')
  assert.deepEqual(d, { headline: "H", steps: [{ id: "a", narration: "N" }], closing: "C" })
  assert.equal(parseDraft("không có json"), null)
  assert.equal(parseDraft("{hỏng"), null)
})

test("mergeDraft keeps grounded LLM narration and falls back to engine text for invented numbers", () => {
  const base = offlineStory([A, B] as never, [rec("a")], "bds")
  const merged = mergeDraft(base, {
    headline: "Hai phát hiện về giá nhà",
    steps: [
      { id: "a", narration: "Biệt thự đắt gấp 2,10 lần đất nền (127 so với 60,3 triệu/m²)." },
      { id: "b", narration: "Diện tích giải thích 87% biến động giá." },
    ],
    closing: "Ưu tiên hỗ trợ nhóm thấp nhất.",
  }, [A, B] as never, [rec("a")], "Groq · test")
  assert.equal(merged.mode, "llm")
  assert.equal(merged.model, "Groq · test")
  assert.equal(merged.steps[0].source, "llm")
  assert.equal(merged.steps[1].source, "engine")
  assert.equal(merged.steps[1].narration, (B as { sentence_vi: string }).sentence_vi)
  assert.equal(merged.headline, "Hai phát hiện về giá nhà")
  assert.match(merged.closing, /^Ưu tiên hỗ trợ nhóm thấp nhất\. .*nhân quả/)
  assert.equal(merged.steps[0].stats, base.steps[0].stats)
})

test("mergeDraft with no usable draft returns the offline story", () => {
  const base = offlineStory([A] as never, [], "bds")
  assert.deepEqual(mergeDraft(base, null, [A] as never, [], "m"), base)
  const bad = mergeDraft(base, { steps: [{ id: "a", narration: "999 tỷ" }] }, [A] as never, [], "m")
  assert.equal(bad.mode, "offline")
  assert.equal(bad.model, null)
})

test("escapeHtml and stepSelector are injection-safe", () => {
  assert.equal(escapeHtml(`<img src=x onerror="a">&'`), "&lt;img src=x onerror=&quot;a&quot;&gt;&amp;&#39;")
  assert.equal(stepSelector('a"b'), '[data-insight-target="insight:a\\"b"]')
  assert.equal(stepSelector("x", "table-row"), '[data-insight-target="table-row:x"]')
})
