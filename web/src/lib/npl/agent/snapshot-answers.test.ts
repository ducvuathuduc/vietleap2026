import assert from "node:assert/strict"
import { test } from "node:test"

import { answerSnapshot, screenDeclines } from "./snapshot-answers.ts"
import { loadNplSnapshot } from "./snapshot.ts"
import { detectLang } from "./lang.ts"
import { guardNplAnswer } from "./answer-policy.ts"

test("2025Q4 screening returns the six published S1 banks outside the focus list", async () => {
  const snapshot = await loadNplSnapshot()
  const result = screenDeclines(snapshot, { period: "2025Q4" })
  assert.deepEqual(result.rows.map((row) => row.bank), ["BVB", "LPB", "NAB", "NVB", "SGB", "SHB"])
  assert.ok(result.rows.every((row) => row.flags.includes("S1") && row.group2_pp != null && row.group2_pp > 0))
  assert.ok(result.rows.find((row) => row.bank === "BVB")?.writeoff_pct != null)
  assert.equal(result.missing_group2, 0)
})

test("known questions use the published mechanism, rebound baseline, bank quarter and coverage", async () => {
  const snapshot = await loadNplSnapshot()
  const cases = [
    ["Vì sao NPL quý 4 giảm?", "q4_drivers", /71.*0,35/],
    ["Quý 1 có luôn tăng không?", "q1_rebound", /74,2.*98\/132/],
    ["Cho xem MBB 2025", "quarter_breakdown", /MBB.*1,87.*1,29/],
    ["Bao phủ tăng ở quý 4 có thật không?", "coverage_effect", /13,09.*6,21.*19,96/],
    ["Which banks had falling NPL and rising group 2 loans in Q4 2025?", "screen_declines", /6.*BVB, LPB, NAB, NVB, SGB, SHB/],
  ] as const
  for (const [question, tool, output] of cases) {
    const answer = answerSnapshot(snapshot, question, detectLang(question))
    assert.equal(answer?.name, tool, question)
    assert.match(answer?.text ?? "", output, question)
    assert.ok(answer?.output.citations.length, question)
    assert.deepEqual(guardNplAnswer(answer.text, [answer.output]).flagged, [], question)
  }
  assert.equal(detectLang("Cho xem MBB 2025"), "vi")
  assert.equal(answerSnapshot(snapshot, "What is the cost of capital?", "en"), null)
})

test("known definitions and the requested-quarter comparison return grounded answers", async () => {
  const snapshot = await loadNplSnapshot()
  const definition = answerSnapshot(snapshot, "What is the NPL ratio?", "en")
  assert.equal(definition?.name, "glossary")
  assert.match(definition.text, /Groups 3–5 divided by total loans/)
  const comparison = answerSnapshot(snapshot, "Compare MBB and VCB in 2025Q4", "en")
  assert.equal(comparison?.name, "compare_banks")
  assert.equal(comparison.output.requested_period, "2025Q4")
  assert.match(comparison.text, /MBB.*1\.29.*VCB.*0\.58/)
  assert.deepEqual(guardNplAnswer(comparison.text, [comparison.output]).flagged, [])
})

test("assistant grounds bilingual rank gaps and early-warning comparisons in the published results", async () => {
  const snapshot = await loadNplSnapshot()
  const cases = [
    ["Ngân hàng nào NPL đẹp nhưng chất lượng tổng thể kém?", "vi", "rank_gap"],
    ["Which banks look better on NPL than on composite asset quality?", "en", "rank_gap"],
    ["Mô hình cảnh báo sớm có tốt hơn chỉ dùng NPL không?", "vi", "early_warning"],
    ["Does Group 2 improve early warning?", "en", "early_warning"],
  ] as const
  for (const [question, lang, tool] of cases) {
    const answer = answerSnapshot(snapshot, question, lang)
    assert.equal(answer?.name, tool, question)
    assert.deepEqual(guardNplAnswer(answer.text, [answer.output]).flagged, [], question)
    if (answer.name === "rank_gap") {
      const expected = snapshot.scorecard?.rank_gaps.latest.filter((row) => row.npl_place < row.composite_place)
      assert.ok(expected?.length)
      assert.deepEqual(answer.output.rows.map((row) => row.bank_code), expected.map((row) => row.bank_code))
      assert.ok(expected.every((row) => answer.text.includes(row.bank_code)))
    } else if (answer.name === "early_warning") {
      const fits = snapshot.context?.early_warning?.backtests.rise_in_four.fits
      assert.ok(fits?.npl_only?.auc)
      assert.equal(answer.output.fits?.npl_only?.auc?.estimate, fits.npl_only.auc.estimate)
    }
  }
})
