import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"
import { detectLang } from "../lang.ts"

const cases = JSON.parse(readFileSync(new URL("cases.json", import.meta.url), "utf8")) as {
  id: string
  lang: "vi" | "en"
  question: string
  adversarial?: string
  mixed?: boolean
}[]

test("live eval covers 15 cases per language and six adversarial cases", () => {
  assert.equal(cases.length, 30)
  assert.equal(new Set(cases.map((item) => item.id)).size, 30)
  assert.equal(cases.filter((item) => item.lang === "vi").length, 15)
  assert.equal(cases.filter((item) => item.lang === "en").length, 15)
  assert.equal(cases.filter((item) => item.adversarial).length, 6)
})

test("language detection follows the main question in six mixed-language cases", () => {
  const mixed = cases.filter((item) => item.mixed)
  assert.equal(mixed.filter((item) => item.lang === "vi").length, 3)
  assert.equal(mixed.filter((item) => item.lang === "en").length, 3)
  for (const item of mixed) assert.equal(detectLang(item.question), item.lang, item.id)
})
