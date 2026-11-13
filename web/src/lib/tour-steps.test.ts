// Run: npm test
import { test } from "node:test"
import assert from "node:assert/strict"

import { targetSelector, tourSteps } from "./tour-steps.ts"

const all = () => true
const none = () => false

test("known page keeps only present elements and appends the header steps", () => {
  const present = new Set(['[data-insight-target="pipeline-stage:ingestion"]', '[data-tour="inspect-toggle"]', '[data-tour="story-button"]'])
  const steps = tourSteps("/pipeline", (s) => present.has(s))
  assert.deepEqual(steps.map((s) => s.title), ["1 · Ingestion", "Hỏi AI về bất kỳ phần tử nào", "Câu chuyện insight"])
})

test("page without hand-written steps uses discovered targets (deduped, capped at 5)", () => {
  const found = Array.from({ length: 8 }, (_, k) => ({ selector: `[data-insight-target="kpi:${k % 7}"]`, label: `KPI ${k % 7}` }))
  const steps = tourSteps("/sql", all, found)
  assert.equal(steps.length, 5 + 2)
  assert.equal(steps[0].title, "KPI 0")
})

test("empty page falls back to dataset picker; nothing present → no steps (no crash)", () => {
  assert.equal(tourSteps("/sources", (s) => s.includes("dataset-select"))[0].title, "Chọn dataset")
  assert.deepEqual(tourSteps("/unknown", none), [])
})

test("targetSelector escapes quotes", () => {
  assert.equal(targetSelector('kpi:a"b'), '[data-insight-target="kpi:a\\"b"]')
})
