// Run: npm test
import { test } from "node:test"
import assert from "node:assert/strict"

import { planOfflineSql } from "./nl2sql-offline.ts"

const BDS_PLAN = {
  time: "ngay_dang",
  time_is_date: true,
  province: "tinh_tp",
  cats: ["loai_bds", "phap_ly"],
  measures: ["price_per_m2", "gia_ban", "dien_tich"],
  ids: ["ma_tin"],
}

test("topN matches diacritic-free Vietnamese synonyms and quotes identifiers", () => {
  const res = planOfflineSql("top 5 giá theo quận", BDS_PLAN, "gold.obt_bds")
  assert.ok(res)
  assert.equal(res.intent, "topN")
  assert.match(res.sql, /SELECT "tinh_tp", median\("price_per_m2"\)/)
  assert.match(res.sql, /ORDER BY 2 DESC\s+LIMIT 5$/)
})

test("topN clamps N to [1, 50] and defaults ASC on 'thấp nhất'", () => {
  const hi = planOfflineSql("top 999 price_per_m2 theo tinh_tp", BDS_PLAN, "gold.obt_bds")
  assert.match(hi!.sql, /LIMIT 50$/)
  const lo = planOfflineSql("top 0 dien_tich thap nhat theo loai_bds", BDS_PLAN, "gold.obt_bds")
  assert.match(lo!.sql, /ORDER BY 2 ASC\s+LIMIT 1$/)
})

test("byTime generates ASC time-series aggregation query", () => {
  const res = planOfflineSql("giá theo năm", BDS_PLAN, "gold.obt_bds")
  assert.ok(res)
  assert.equal(res.intent, "byTime")
  assert.match(res.sql, /SELECT "ngay_dang", median\("price_per_m2"\)/)
  assert.match(res.sql, /ORDER BY 1 ASC/)
})

test("compare matches group column and falls back to primary measure", () => {
  const res = planOfflineSql("so sánh loại bất động sản", BDS_PLAN, "gold.obt_bds")
  assert.ok(res)
  assert.equal(res.intent, "compare")
  assert.match(res.sql, /SELECT "loai_bds", median\("price_per_m2"\)/)
})

test("returns null when question matches no allowlisted column", () => {
  const res = planOfflineSql("top 5 phi hanh gia theo sao hoa", BDS_PLAN, "gold.obt_bds")
  assert.equal(res, null)
})
