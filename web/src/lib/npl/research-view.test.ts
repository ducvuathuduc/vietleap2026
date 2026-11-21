import assert from "node:assert/strict"
import { test } from "node:test"

import seed from "../../../seed/npl/snapshot.json" with { type: "json" }
import { bankCheck, scorecardRanks } from "./research-view.ts"
import { applyPublishFlag, type Snapshot } from "./view.ts"

const publication = seed as unknown as Snapshot

test("the bank check uses five distinct measures and treats the seasonal range as context", () => {
  const model = bankCheck(publication, "MBB", "2025Q4", "en")
  assert.deepEqual(model.checks.map(({ id }) => id), ["season", "loans", "writeoffs", "group2", "coverage"])
  assert.equal(model.checks[0].tone, "context")
  assert.match(model.checks[1].value, /-0\.26 pp/)
  assert.match(model.checks[2].value, /0\.31%/)
  assert.match(model.checks[3].value, /-0\.42 pp/)
  assert.ok(model.ranks && model.ranks.count > 0)
  assert.ok(typeof model.adjustedChange === "number")
})

test("ranks both series on the comparable cohort and preserves competition ties", () => {
  const row = (bank_code: string, npl: number | null, composite: number | null) => ({
    bank_code, period: "2025Q4", values: { npl }, percentiles: {}, composite, n_asset: 8,
  })
  const scorecard = { ...publication.scorecard!, rows: [
    row("A", .01, .2), row("B", .01, .5), row("C", .03, .8), row("D", .002, null),
  ] }
  assert.deepEqual(scorecardRanks(scorecard.rows, "B", "2025Q4"), { npl: 1, composite: 2, count: 3 })
  assert.equal(scorecardRanks(scorecard.rows, "D", "2025Q4"), null)
})

test("reads quarter-four timing from actual and historical changes even without a decline flag", () => {
  const row = {
    bank_code: "MBB", period: "2025Q4", delta_npl_ratio: .001,
    expected_change_pp: -.2, lo80_pp: -.4, hi80_pp: .4,
    layers: { data_quality: "đủ", accounting: [], context: [] },
  }
  const result = bankCheck({ ...publication, decoder: { rows: [row] } }, "MBB", "2025Q4", "en")
  assert.equal(result.checks[0].verdict, "Inside year-end range")
  assert.match(result.checks[0].value, /-0\.60 to \+0\.20 pp/)
})

test("the publication flag hides new individual-bank values and rank gaps", () => {
  const hidden = applyPublishFlag(publication, "0")
  assert.deepEqual(hidden.scorecard?.rows, [])
  assert.deepEqual(hidden.scorecard?.rank_gaps, {})
  assert.deepEqual(hidden.context?.seasonal_adjustment?.series, [])
  assert.deepEqual(hidden.context?.seasonal_adjustment?.latest, [])
  assert.equal(bankCheck(hidden, "MBB", "2025Q4", "en").ranks, null)
})
