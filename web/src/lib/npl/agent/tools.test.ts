// Run: node --test src/lib/npl/agent/tools.test.ts
// Every tool is deterministic on the fixture snapshot (web/seed/npl/snapshot.fixture.json).
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

import type { Snapshot } from "../view.ts"
import {
  adjustedChange,
  bankProfile,
  compareBanks,
  forecast,
  glossary,
  limitations,
  marketReaction,
  method,
  overview,
  quarterEffects,
  type NplCitation,
} from "./tools.ts"
import * as tools from "./tools.ts"

// The fixture is read directly (load.ts uses a bundler-only JSON import).
const snapshot = JSON.parse(
  readFileSync(new URL("../../../../seed/npl/snapshot.fixture.json", import.meta.url), "utf8"),
) as Snapshot

function assertCitations(citations: NplCitation[], min = 1) {
  assert.ok(citations.length >= min, `expected >= ${min} citations`)
  for (const c of citations) {
    assert.equal(typeof c.source, "string")
    assert.ok(c.source.length > 0, "citation source must be named")
    assert.ok("period" in c && "n" in c && "ci95" in c)
  }
}

test("overview: headline, level and benchmark with citations", () => {
  const res = overview(snapshot)
  assert.equal(res.level.npl_median_pct, 2.22)
  assert.equal(res.level.period, "2026Q3")
  assert.equal(res.benchmark.coef_pp, -0.425606)
  assert.equal(res.benchmark.n, 576)
  assert.equal(res.data_period, "2021Q1–2026Q3")
  assert.match(res.note_vi, /liên hệ, không phải nhân quả/)
  assert.match(res.note_en, /association, not causation/)
  assertCitations(res.citations)
})

test("quarter_effects: Q2/Q3/Q4 with CI and the association note", () => {
  const res = quarterEffects(snapshot)
  assert.deepEqual(res.effects.map((e) => e.quarter), [2, 3, 4])
  const q4 = res.effects.find((e) => e.quarter === 4)!
  assert.equal(q4.coef_pp, -0.425606)
  assert.deepEqual(q4.ci95, [-0.576508, -0.274704])
  assert.equal(q4.n, 576)
  assert.equal(res.data_period, "2021Q1–2026Q3")
  assert.match(res.note_vi, /liên hệ trong dữ liệu, không phải nhân quả/)
  assertCitations(res.citations)
})

test("bank_profile: VCB with latest and signals", () => {
  const res = bankProfile(snapshot, { code: "vcb" })
  assert.equal(res.found, true)
  assert.equal(res.bank!.code, "VCB")
  assert.equal(res.bank!.q4_change_median_pp, -0.26)
  assert.equal(res.bank!.latest!.period, "2026Q3")
  assertCitations(res.citations)
})

test("bank_profile: unknown bank returns found: false and no numbers", () => {
  const res = bankProfile(snapshot, { code: "SCB" })
  assert.equal(res.found, false)
  assert.equal(res.bank, undefined)
  assertCitations(res.citations, 0)
})

test("adjusted_change: explicit period and latest fallback", () => {
  const latest = adjustedChange(snapshot, { code: "VCB" })
  assert.equal(latest.found, true)
  assert.equal(latest.row!.period, "2026Q3")
  assert.equal(latest.row!.adjusted_change_pp, 0.234139)
  const early = adjustedChange(snapshot, { code: "VCB", period: "2021Q2" })
  assert.equal(early.found, true)
  assert.equal(early.row!.d_npl_pp, -0.14)
  assertCitations(latest.citations)
})

test("adjusted_change: unknown period returns found: false", () => {
  const res = adjustedChange(snapshot, { code: "VCB", period: "2020Q1" })
  assert.equal(res.found, false)
})

test("compare_banks: up to 4 banks, missing listed", () => {
  const res = compareBanks(snapshot, { codes: ["VCB", "MBB", "VPB", "SCB"] })
  assert.equal(res.rows.length, 3)
  assert.deepEqual(res.missing, ["SCB"])
  const vcb = res.rows.find((r) => r.code === "VCB")!
  assert.equal(vcb.q4_change_median_pp, -0.26)
  assert.equal(vcb.d_npl_pp, 0.1)
  assert.equal(vcb.adjusted_change_pp, 0.234139)
  assert.equal(vcb.forecast_next!.npl_pct, 0.3989)
  assertCitations(res.citations, 3)
})

test("compare_banks: more than 4 codes throws", () => {
  assert.throws(() => compareBanks(snapshot, { codes: ["VCB", "MBB", "VPB", "STB", "ACB"] }), /at most 4/)
})

test("forecast: VCB next-quarter interval plus MAE and the not-a-promise note", () => {
  const res = forecast(snapshot, { code: "VCB" })
  assert.equal(res.found, true)
  assert.equal(res.forecast!.period, "2026Q4")
  assert.equal(res.forecast!.npl_pct, 0.3989)
  assert.equal(res.mae.model, 0.403182)
  assert.equal(res.mae.seasonal_naive, 0.894094)
  assert.deepEqual(res.backtest_period, ["2025Q1", "2026Q3"])
  assert.match(res.backtest_note_en!, /2025Q1 to 2026Q3.*MAE.*0\.40.*0\.34.*0\.89/)
  assert.match(res.note_vi, /phép tính, không phải lời hứa/)
  assert.match(res.note_en, /calculation, not a promise/)
  assertCitations(res.citations)
})

test("forecast: unknown bank returns found: false", () => {
  const res = forecast(snapshot, { code: "SCB" })
  assert.equal(res.found, false)
})

test("market_reaction: CAR window and regression readings with citations", () => {
  const res = marketReaction(snapshot)
  assert.ok(res.events_with_car >= 1)
  assert.ok(res.car_all.length > 0)
  assert.ok(res.reading_vi.length > 0)
  assert.ok(res.reading_en.length > 0)
  assertCitations(res.citations)
})

test("method: M4 returns spec, reading and does_not_show in both languages", () => {
  const res = method(snapshot, { model_id: "M4" })
  assert.equal(res.found, true)
  assert.equal(res.entry!.id, "M4")
  assert.ok(res.entry!.n > 0)
  assert.match(res.entry!.does_not_show_vi, /./)
  assertCitations(res.citations)
})

test("method: unknown id returns found: false with the valid ids", () => {
  const res = method(snapshot, { model_id: "M9" })
  assert.equal(res.found, false)
  assert.deepEqual(res.valid_ids, ["M1", "M2", "M3", "M4", "M5", "M6", "M7"])
})

test("limitations: the snapshot limitation list with legal references", () => {
  const res = limitations(snapshot)
  assert.ok(res.items.length >= 5)
  assert.ok(res.legal.length >= 1)
  assertCitations(res.citations)
})

test("glossary: known terms in both languages, unknown lists the vocabulary", () => {
  const npl = glossary(snapshot, { term: "nợ xấu" })
  assert.equal(npl.found, true)
  assert.match(npl.entry!.vi, /./)
  assert.match(npl.entry!.en, /./)
  const adjusted = glossary(snapshot, { term: "adjusted change" })
  assert.equal(adjusted.found, true)
  const unknown = glossary(snapshot, { term: "bitcoin" })
  assert.equal(unknown.found, false)
  assert.ok(unknown.terms!.length >= 8)
})

test("every tool output stays inside the snapshot (no invented fields)", () => {
  const res = overview(snapshot)
  assert.ok(res.last_median && res.last_median.period <= snapshot.meta.period_end)
})

test("decoder and adjustments return the selected public bank-quarter checks", () => {
  const published = {
    ...snapshot,
    decoder: { rows: [{
      bank_code: "VCB",
      period: "2026Q3",
      delta_npl_ratio: -0.01,
      delta_coverage: -0.15,
      coverage: 1.04,
      status: "missing",
      signals: [{ id: "S3", text_vi: "Bao phủ giảm", text_en: "Coverage fell" }],
    }] },
  }
  const result = tools.decoder(published, { code: " vcb ", period: "2026q3" })
  assert.ok(result.found)
  assert.equal(result.code, "VCB")
  assert.equal(result.data_period, "2026Q3")
  assert.equal(result.decoder?.status, "missing")
  assert.equal(result.decoder?.inputs.ratios.coverage.value, 104)
  assert.equal(result.decoder?.inputs.ratios.coverage.source, "FiinQuant (FiinGroup)")
  assert.equal(result.decoder?.checks.S3, "flagged")
  assert.equal(result.decoder?.checks.S1, "missing")
  assert.deepEqual(bankProfile(published, { code: "VCB" }).decoder, result.decoder)
  assert.deepEqual(adjustedChange(published, { code: "VCB" }).decoder, result.decoder)
  assert.equal(tools.decoder(published, { code: "VCB", period: "2020Q1" }).found, false)
})
