import assert from "node:assert/strict"
import { test } from "node:test"

import { promptsFor, visibleText } from "./question-lang.ts"

test("provides three distinct quick questions per language for the current page", () => {
  const routes = ["/", "/ngan-hang/acb/", "/giai-ma", "/thi-truong", "/phuong-phap"]
  const sets = routes.map(promptsFor)
  for (const { vi, en } of sets) {
    assert.equal(new Set(vi).size, 3)
    assert.equal(new Set(en).size, 3)
  }
  assert.equal(new Set(sets.map((prompts) => JSON.stringify(prompts))).size, routes.length)
})

test("uses the bank in the current route in both languages", () => {
  const { vi, en } = promptsFor("/ngan-hang/acb/")
  for (const prompt of [...vi, ...en]) {
    assert.match(prompt, /\bACB\b/)
    assert.doesNotMatch(prompt, /\bVCB\b/)
  }
})

test("the plain-text transcript preserves emphasized findings without showing markup", () => {
  assert.equal(visibleText("The latest decoder status is **no fall**."), "The latest decoder status is no fall.")
})
