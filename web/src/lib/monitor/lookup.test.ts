import assert from "node:assert/strict"
import { test } from "node:test"

import fixture from "./__fixtures__/synthetic.monitor.json" with { type: "json" }
import { cardsBySector, indicatorById, sourceById } from "./lookup.ts"
import type { Monitor } from "./types.ts"

const monitor = fixture as Monitor

test("indicator lookup returns the catalog row or null", () => {
  assert.equal(indicatorById(monitor, "credit_ytd")?.name_vi, "Tăng tín dụng")
  assert.equal(indicatorById(monitor, "khong_co"), null)
})

test("source lookup returns the catalog row or null", () => {
  assert.equal(sourceById(monitor, "nso")?.title_vi, "Báo cáo KT-XH")
  assert.equal(sourceById(monitor, "khong_co"), null)
})

test("cards by sector are empty when that sector is absent", () => {
  assert.equal(cardsBySector(monitor, "banking")[0]?.sentence_vi, "Câu thẻ.")
  assert.deepEqual(cardsBySector(monitor, "fdi"), [])
  assert.deepEqual(cardsBySector(monitor, "public_finance"), [])
})
