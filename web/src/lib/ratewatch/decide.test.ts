import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

import { saverModel } from "./decide.ts"
import type { Snapshot } from "./types.ts"

const snapshot = JSON.parse(
  readFileSync(new URL("../../../seed/ratewatch/snapshot.fixture.json", import.meta.url), "utf8"),
) as Snapshot

test("the OCB online fixture screen states 4,75, 6,00, 6,30 and the 6,41 renewal calculation", () => {
  const model = saverModel(snapshot, {
    amount: 500_000_000,
    need: "2027-05-20",
    online: true,
    bank: "OCB",
    compare: [],
    lang: "vi",
    asOf: "2026-11-20",
  })
  assert.match(model.headline, /06\/11\/2026/)
  assert.match(model.headline, /4,75%/)
  assert.match(model.headline, /6,00%/)
  assert.match(model.headline, /6,30%/)
  assert.match(model.headline, /6,41%/)
  assert.equal(model.numbers.yourRate, 6)
  assert.equal(model.figures.interestVnd, 15_000_000)
  assert.equal(model.figures.insuredVnd, 350_000_000)
  assert.equal(model.figures.excessVnd, 150_000_000)
  assert.equal(model.chartTitle, "OCB trả 6,00% từ kỳ 6 tháng; kỳ 1–5 tháng bị giới hạn ở 4,75%")
  assert.equal(model.numbers.breakEvenLabel, "phép tính, không phải dự báo")
  assert.equal(model.chart.rows.some((row) => row.term === 1 && row.OCB === 4.75), true)
  assert.equal(model.chart.rows.some((row) => row.term === 6), true)
  assert.ok(model.plans.length >= 1)
  assert.ok(model.split.allocations.length >= 1)
  assert.ok(model.split.allocations.every((row) => row.total_vnd <= snapshot.policy.cap.vnd + 1e-6))
})
