// Run: npm test  (node --test with built-in TypeScript type stripping)
import { test } from "node:test"
import assert from "node:assert/strict"

import { contextTerms, explainOffline, fold, matchInsights, sourcesFor } from "./explain.ts"

const ins = (id: string, rank: number, columns: string[], extra: Record<string, unknown> = {}) => ({
  id, rank, type: "segment_gap", title_en: id, title_vi: `tiêu đề ${id}`, sentence_en: "", sentence_vi: `câu ${id}`,
  value: null, test: "Kruskal–Wallis", effect: 0.5, p_value: 0.0001, relevance: 1, score: 1, chart: null,
  evidence: extra, columns, caveat: null,
})

const insights = [
  ins("gap_type", 1, ["Loại BĐS", "price_per_m2"], { by: "Loại BĐS", metric: "price_per_m2" }),
  ins("gap_region", 2, ["_region", "price_per_m2"], { by: "_region" }),
  ins("corr_area", 3, ["Diện tích", "Giá bán"]),
]

test("fold removes Vietnamese diacritics and đ", () => {
  assert.equal(fold("Loại BĐS"), "loai bds")
  assert.equal(fold("Đồng bằng sông Hồng"), "dong bang song hong")
})

test("contextTerms collects id, label and data strings", () => {
  const t = contextTerms({ kind: "segment", id: "Loại BĐS", label: "Phân khúc", data: { groups: [{ "Loại BĐS": "Biệt thự" }] } })
  assert.ok(t.includes("loai bds") && t.includes("biet thu"))
})

test("exact insight id wins", () => {
  const m = matchInsights(insights as never, { kind: "insight", id: "corr_area", label: "x" })
  assert.equal(m[0].id, "corr_area")
})

test("column overlap matches, ordered by score then rank", () => {
  const m = matchInsights(insights as never, { kind: "segment", id: "Loại BĐS", label: "Giá theo loại" })
  assert.equal(m[0].id, "gap_type")
  assert.ok(!m.some((x) => x.id === "corr_area"))
})

test("no match falls back to top insight without inventing numbers", () => {
  const out = explainOffline({ kind: "kpi", id: "zzz", label: "zzz" }, { insights: { insights: insights as never, recommendations: [] } })
  assert.match(out.text, /Insight mạnh nhất/)
  assert.match(out.text, /tiêu đề gap_type/)
})

test("pipeline stage explanation uses pipeline numbers", () => {
  const p = { timings: { ingest: 4.33 }, provenance: [{ kind: "file" }, { kind: "api" }], bronze: ["a"], silver: ["b"], gold: ["c"], quality: {}, models: {}, recommended: { serving: "obt", semantic: "star" } }
  const out = explainOffline({ kind: "pipeline-stage", id: "ingestion", label: "Ingestion" }, { pipeline: p as never })
  assert.match(out.text, /2 nguồn \(file, api\), thời gian 4.33 giây/)
})

test("sourcesFor maps kinds to engine resources", () => {
  assert.deepEqual(sourcesFor("quality"), ["quality"])
  assert.deepEqual(sourcesFor("kpi"), ["insights"])
})
