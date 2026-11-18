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
  assert.deepEqual(sourcesFor("join"), ["pipeline"])
})

test("join explanation copies coverage numbers from pipeline.conformed", () => {
  const conformed = {
    shared_keys: ["geo", "year"], dims: { geo: "dim_geo" }, facts: {}, integrated: "obt_integrated", integrated_rows: 63, row_explosion: false,
    sources: [{ table: "a", source: "gso", rows: 70, geo_level: "province", keys: { geo: { column: "tinh", matched_rows: 63, unmatched_rows: 7, null_key_rows: 0, match_pct: 90 } } }],
    joins: [{ source: "wb", keys: ["year"], status: "joined", matched_rows: 60, unmatched_rows: 3, match_pct: 95.2, unmatched_samples: ["2019"] }],
    overlap: [],
  }
  const p = { conformed } as never
  const a = explainOffline({ kind: "join", id: "gso:geo", label: "x" }, { pipeline: p })
  assert.match(a.text, /gso \(70 dòng\) theo khoá geo \(cột tinh\): 63 dòng khớp dimension chung, 7 không khớp, 0 khoá trống — tỉ lệ khớp 90%/)
  const b = explainOffline({ kind: "join", id: "integration:wb", label: "y" }, { pipeline: p })
  assert.match(b.text, /60 dòng khớp, 3 dòng không khớp \(95.2%\)/)
  assert.match(b.text, /Mẫu khoá chưa khớp: 2019/)
  const none = explainOffline({ kind: "join", id: "gso:geo", label: "z" }, { pipeline: { conformed: null } as never })
  assert.match(none.text, /không có lớp conformed/)
})

test("segment province explanation reports rank, national gap, small sample note, and zero causal claim", () => {
  const out = explainOffline(
    {
      kind: "segment",
      id: "Đà Nẵng",
      label: "Tỉnh Đà Nẵng",
      data: {
        province: "Đà Nẵng",
        region: "Bắc Trung Bộ và Duyên hải miền Trung",
        metric: "price_per_m2",
        agg: "median",
        value: 120,
        n: 4,
        rank: 2,
        total_provinces: 34,
        national_value: 80,
      },
    },
    {}
  )
  assert.match(out.text, /xếp hạng 2\/34 tỉnh thành/)
  assert.match(out.text, /cao hơn 50,0% so với mức toàn quốc/)
  assert.match(out.text, /cỡ mẫu nhỏ: n=4/)
  assert.match(out.text, /không chứng minh nhân quả/)
})

