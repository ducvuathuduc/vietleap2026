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
  published?: boolean
}[]

test("live eval preserves 30 fixture cases and adds five published-data cases per language", () => {
  assert.equal(cases.length, 40)
  assert.equal(new Set(cases.map((item) => item.id)).size, 40)
  assert.equal(cases.filter((item) => item.lang === "vi").length, 20)
  assert.equal(cases.filter((item) => item.lang === "en").length, 20)
  assert.equal(cases.filter((item) => item.lang === "vi" && item.published).length, 5)
  assert.equal(cases.filter((item) => item.lang === "en" && item.published).length, 5)
  assert.equal(cases.filter((item) => item.adversarial).length, 6)
})

test("language detection follows the main question in six mixed-language cases", () => {
  const mixed = cases.filter((item) => item.mixed)
  assert.equal(mixed.filter((item) => item.lang === "vi").length, 3)
  assert.equal(mixed.filter((item) => item.lang === "en").length, 3)
  for (const item of mixed) assert.equal(detectLang(item.question), item.lang, item.id)
})
