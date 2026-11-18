// Run: npm test
import { test } from "node:test"
import assert from "node:assert/strict"

import { canonicalProvince34, isRatioMetric, OLD_63_TO_34, PROVINCES_34 } from "./geo-names.ts"

test("all 34 canonical provinces resolve cleanly 1-to-1 (SC-801)", () => {
  assert.equal(PROVINCES_34.length, 34)
  const resolved = new Set(PROVINCES_34.map((p) => canonicalProvince34(p).province))
  assert.equal(resolved.size, 34)
  for (const p of PROVINCES_34) {
    assert.ok(resolved.has(p), `Missing canonical resolution for ${p}`)
  }
})

test("all 63 pre-2025 provinces resolve into the 34 canonical units", () => {
  const olds = Object.keys(OLD_63_TO_34)
  assert.equal(olds.length, 63)
  for (const old of olds) {
    const out = canonicalProvince34(old)
    assert.equal(out.province, OLD_63_TO_34[old])
    assert.ok(out.region, `Missing region for ${old}`)
  }
  assert.equal(canonicalProvince34("Bình Dương").convertedFrom63, true)
  assert.equal(canonicalProvince34("Thừa Thiên Huế").province, "Huế")
})

test("aliases like TP. Hồ Chí Minh, HCMC, Bà Rịa - Vũng Tàu resolve without mismatch", () => {
  assert.equal(canonicalProvince34("TP. Hồ Chí Minh").province, "Hồ Chí Minh")
  assert.equal(canonicalProvince34("Ho Chi Minh City").province, "Hồ Chí Minh")
  assert.equal(canonicalProvince34("HCMC").province, "Hồ Chí Minh")
  assert.equal(canonicalProvince34("Tỉnh Bà Rịa - Vũng Tàu").province, "Hồ Chí Minh")
  assert.equal(canonicalProvince34("Hanoi").province, "Hà Nội")
  assert.equal(canonicalProvince34("Không rõ").province, null)
})

test("isRatioMetric flags ratios/percentages to block sum aggregation", () => {
  assert.equal(isRatioMetric("tax_revenue_pct_gdp"), true)
  assert.equal(isRatioMetric("price_per_m2"), true)
  assert.equal(isRatioMetric("earmarked_transfers"), false)
})
