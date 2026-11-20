import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"

import { LARGE_BANKS, decoderModel, type DecoderCell, type Snapshot } from "./view.ts"

type Point = { period: string; npl_pct: number | null; coverage_pct: number | null; ldr_pct: number | null; nim_pct: number | null; loan_growth_pct: number | null }
type Bank = { code: string; years: number; down_then_up_years: number; series?: Point[] }
type Fixture = {
  _fixture_note: string
  meta: { publish_bank_series: boolean }
  headline: { vi: string; en: string }
  kpis: { level: { period: string; npl_median_pct: number }; benchmark: { coef_pp: number } }
  quarter_effects: { quarter: number; coef_pp: number }[]
  banks: Bank[]
}

test("the fixture publishes per-bank FiinQuant series by default", () => {
  const path = join(dirname(fileURLToPath(import.meta.url)), "../../../seed/npl/snapshot.fixture.json")
  const snapshot = JSON.parse(readFileSync(path, "utf8")) as Fixture
  assert.match(snapshot._fixture_note, /results\.json/)
  assert.equal(snapshot.meta.publish_bank_series, true)
  assert.equal(snapshot.kpis.level.period, "2026Q3")
  assert.ok(snapshot.headline.vi.includes(snapshot.kpis.benchmark.coef_pp.toFixed(3)))
  assert.ok(snapshot.headline.en.includes("Do not treat the Q4 NPL decline as a lasting improvement"))
  assert.deepEqual(snapshot.quarter_effects.map((row) => row.quarter), [2, 3, 4])
  assert.equal(snapshot.quarter_effects[2]?.coef_pp, snapshot.kpis.benchmark.coef_pp)
  assert.ok(snapshot.banks.length > 0)
  assert.ok(snapshot.banks.every((bank) => Array.isArray(bank.series) && bank.series.length > 0))
  const point = snapshot.banks.find((bank) => bank.code === "VCB")?.series?.find((row) => row.period === "2026Q3")
  assert.equal(point?.npl_pct, 0.71)
  assert.equal(point?.coverage_pct, 243.17)
  assert.equal(point?.ldr_pct, 81.93)
  assert.equal(point?.nim_pct, 2.87)
  assert.equal(point?.loan_growth_pct, 11.84)
  const repeat = snapshot.banks.filter((bank) => bank.years > 0 && bank.down_then_up_years === bank.years).map((bank) => bank.code)
  assert.deepEqual(repeat, ["OCB", "SGB", "TPB", "VCB"])
  assert.equal(repeat.includes("SSB"), false)
})

test("the decoder fixture uses FiinQuant coverage and Q4 flags from snapshot.json", () => {
  const path = join(dirname(fileURLToPath(import.meta.url)), "../../../seed/npl/decoder.fixture.json")
  const file = JSON.parse(readFileSync(path, "utf8")) as { _fixture_note: string; decoder: DecoderCell[] }
  assert.match(file._fixture_note, /FiinQuant/)
  assert.match(file._fixture_note, /S3/)
  assert.match(file._fixture_note, /S4/)
  assert.ok(file.decoder.every((cell) => cell.signals.every((signal) => signal.id === "S3" || signal.id === "S4")))
  const vcb = Object.fromEntries(file.decoder.filter((cell) => cell.bank === "VCB").map((cell) => [cell.period, cell]))
  assert.equal(vcb["2025Q2"]?.d_npl_pp, -0.03)
  assert.equal(vcb["2025Q2"]?.status, "coverage")
  assert.equal(vcb["2025Q4"]?.d_npl_pp, -0.45)
  assert.equal(vcb["2025Q4"]?.status, "seasonal")
  assert.equal(vcb["2026Q2"]?.d_npl_pp, -0.01)
  assert.equal(vcb["2026Q2"]?.status, "missing")
  assert.equal(vcb["2026Q3"]?.d_npl_pp, 0.1)
  assert.equal(vcb["2026Q3"]?.status, "no_fall")
  const ctg = file.decoder.find((cell) => cell.bank === "CTG" && cell.period === "2025Q2")
  assert.equal(ctg?.d_npl_pp, -0.24)
  assert.equal(ctg?.status, "coverage")
  const table = decoderModel({ decoder: file.decoder } as Snapshot, "vi")
  assert.deepEqual(table.rows.map((row) => row.bank), [...LARGE_BANKS])
  assert.deepEqual(table.periods, ["2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"])
  assert.equal(table.rows[0]?.cells[0]?.label, "Cờ vàng: bao phủ giảm")
  assert.equal(table.rows[0]?.cells[2]?.label, "Nhịp mùa vụ cuối năm")
  const full = decoderModel({ decoder: file.decoder } as Snapshot, "vi", "all")
  assert.equal(full.rows.length, 27)
  assert.deepEqual(full.rows.slice(0, 8).map((row) => row.bank), [...LARGE_BANKS])
  assert.equal(full.rows.some((row) => row.bank === "ABB"), true)
  assert.equal(full.periods[0], "2021Q1")
  assert.equal(full.periods.at(-1), "2026Q3")
  assert.ok(full.periods.length > 6)
})
