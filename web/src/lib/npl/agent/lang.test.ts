// Run: node --test src/lib/npl/agent/lang.test.ts
import assert from "node:assert/strict"
import { test } from "node:test"

import { detectLang } from "./lang.ts"

test("detectLang: Vietnamese diacritics win", () => {
  assert.equal(detectLang("Ngân hàng nào có nợ xấu thấp nhất?"), "vi")
  assert.equal(detectLang("Cho tôi biết tỷ lệ nợ xấu quý 4"), "vi")
  assert.equal(detectLang("Dự báo NPL của VCB"), "vi")
})

test("detectLang: unaccented Vietnamese words", () => {
  assert.equal(detectLang("ngan hang nao co no xau thap nhat"), "vi")
  assert.equal(detectLang("no xau quy 4 la bao nhieu"), "vi")
  assert.equal(detectLang("so sanh VCB va MBB"), "vi")
})

test("detectLang: English defaults to en", () => {
  assert.equal(detectLang("Which bank has the lowest NPL?"), "en")
  assert.equal(detectLang("Compare VCB and MBB for Q4"), "en")
  assert.equal(detectLang("What is the forecast for MBB?"), "en")
})
