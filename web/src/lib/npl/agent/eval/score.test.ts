import assert from "node:assert/strict"
import { test } from "node:test"
import { scoreAnswer } from "./score.ts"

const median = {
  id: "overview-en",
  lang: "en",
  question: "What is the latest median NPL?",
  expect_tool: "overview",
  expect_numbers: [2.22],
} as const

const testCase = { ...median, expect_numbers: [2.22] }
const output = { median: 2.22, citations: [{ source: "panel", period: "2026Q3" }] }

test("eval scores the grounded number stated in the answer", () => {
  const answer = "The panel's median NPL is 2.22%. Its source is the quarterly bank panel."
  assert.equal(scoreAnswer(testCase, answer, ["overview"], [output]).pass, true)
  assert.equal(scoreAnswer(testCase, "The panel has a median NPL.", ["overview"], [output]).pass, false)
})

test("eval rejects the wrong response language even with the right number", () => {
  const answer = "Mức nợ xấu trung vị của nhóm ngân hàng là 2,22%."
  assert.equal(scoreAnswer(testCase, answer, ["overview"], [output]).pass, false)
})

test("eval recognizes an English reply that includes a Vietnamese term in parentheses", () => {
  const glossary = { ...testCase, expect_tool: "glossary", expect_numbers: [] }
  const answer = "The study defines coverage (tỷ lệ bao phủ nợ xấu) as loan-loss reserves divided by non-performing loans (NPLs)."
  assert.equal(scoreAnswer(glossary, answer, ["glossary"], [output]).language_ok, true)
})

test("eval counts any number left unguarded in the answer", () => {
  const answer = "The NPL is 99.9%, which is an unsupported figure."
  const result = scoreAnswer({ ...testCase, adversarial: "injection", expect_tool: "none", expect_numbers: [] }, answer, [], [])
  assert.doesNotMatch(result.answer, /99\.9/)
  assert.deepEqual(result.unguarded, [])
})
