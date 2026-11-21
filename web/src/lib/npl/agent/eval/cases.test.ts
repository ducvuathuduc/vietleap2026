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

test("live eval preserves the fixture and published cases and adds five harder questions in both languages", () => {
  assert.equal(cases.length, 50)
  assert.equal(new Set(cases.map((item) => item.id)).size, 50)
  for (const lang of ["vi", "en"] as const) {
    const localized = cases.filter((item) => item.lang === lang)
    assert.equal(localized.filter((item) => !item.published).length, 15)
    assert.equal(localized.filter((item) => item.published).length, 10)
    const hard = localized.filter((item) => item.id.startsWith("b26-"))
    assert.equal(hard.length, 5)
    assert.ok(hard.every((item) => item.published && detectLang(item.question) === lang))
  }
  assert.equal(cases.filter((item) => item.adversarial).length, 6)
})

test("language detection follows the main question in six mixed-language cases", () => {
  const mixed = cases.filter((item) => item.mixed)
  assert.equal(mixed.filter((item) => item.lang === "vi").length, 3)
  assert.equal(mixed.filter((item) => item.lang === "en").length, 3)
  for (const item of mixed) assert.equal(detectLang(item.question), item.lang, item.id)
})
