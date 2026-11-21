import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test, type TestContext } from "node:test"

import { S3Client } from "@aws-sdk/client-s3"
import Ajv2020 from "ajv/dist/2020.js"
import addFormats from "ajv-formats"

import seed from "../../../seed/npl/snapshot.json" with { type: "json" }

import { readSnapshot } from "./snapshot-source.ts"
import schema from "./snapshot.schema.json" with { type: "json" }
import { applyPublishFlag, bankModel, decoderModel, methodModel, overviewModel, publicCsv } from "./view.ts"

function setSource(t: TestContext, uri?: string) {
  const saved = process.env.NPL_SNAPSHOT_S3_URI
  if (uri) process.env.NPL_SNAPSHOT_S3_URI = uri
  else delete process.env.NPL_SNAPSHOT_S3_URI
  t.after(() => {
    if (saved === undefined) delete process.env.NPL_SNAPSHOT_S3_URI
    else process.env.NPL_SNAPSHOT_S3_URI = saved
  })
}

test("the web schema matches the pipeline contract", () => {
  const contract = new URL("../../../../engine/vlkit/npl/schema/snapshot.schema.json", import.meta.url)
  assert.deepEqual(schema, JSON.parse(readFileSync(contract, "utf8")))
})

test("the schema accepts a publication without the research additions", () => {
  const legacy = structuredClone(seed)
  for (const key of ["scorecard", "pdf_audit"]) Reflect.deleteProperty(legacy, key)
  for (const key of ["early_warning", "seasonal_adjustment"]) Reflect.deleteProperty(legacy.context, key)
  for (const fit of Object.values(legacy.decoder.regression).filter((value) => typeof value === "object" && !Array.isArray(value))) {
    for (const key of ["without_writeoff", "sample_banks"]) Reflect.deleteProperty(fit, key)
  }
  const validate = addFormats(new Ajv2020({ strict: false })).compile(schema)
  assert.equal(validate(legacy), true, JSON.stringify(validate.errors))
})

test("loads and adapts the bundled snapshot when S3 is unconfigured", async (t) => {
  setSource(t)
  const send = t.mock.method(S3Client.prototype, "send")
  const snapshot = await readSnapshot()

  assert.equal(snapshot.meta.snapshot_id, seed.meta.snapshot_id)
  assert.equal(overviewModel(snapshot, "en").benchmark.coef, seed.kpis.benchmark.q4_coef_pp)
  assert.ok(bankModel(snapshot, "VCB", "en")?.pairs.length)
  assert.equal(methodModel(snapshot, "en").edaSummary, seed.method.find((entry) => entry.id === "M1")?.reading_en)
  assert.match(publicCsv(snapshot), /VCB/)
  assert.equal(decoderModel(snapshot, "en", "all").rows.length, 27)
  assert.equal(Array.isArray(snapshot.decoder) ? undefined : snapshot.decoder?.regression?.fiinquant?.without_writeoff?.n,
    seed.decoder.regression.fiinquant.without_writeoff.n)
  assert.equal(send.mock.callCount(), 0)
})

test("the published decoder keeps its missing status and any available coverage signal", async (t) => {
  setSource(t, "s3://vietleap-test/snapshots/npl/partial-notes.json")
  const object = structuredClone(seed)
  const row = object.decoder.rows.find((row) => row.bank_code === "VCB" && row.period === "2025Q2")!
  Object.assign(row, {
    status: "missing", coverage_contested: false, group2_vnd_bn: 123,
    signals: [{ id: "S3", text_vi: "Đệm dự phòng mỏng đi", text_en: "Provision buffer thinner" }],
  })
  t.mock.method(S3Client.prototype, "send", async () => ({
    Body: { transformToString: async () => JSON.stringify(object) },
  }))
  const table = decoderModel(await readSnapshot(), "en", "all")
  const cell = table.rows.find((row) => row.bank === "VCB")?.cells.find((cell) => cell?.period === "2025Q2")
  assert.equal(cell?.status, "missing")
  assert.equal(cell?.dNpl, -0.03)
  assert.deepEqual(cell?.signals, ["Provision buffer thinner"])
  assert.match(cell?.reading ?? "", /Provision buffer thinner/)
  assert.equal(cell?.inputs.group2, 123)
})

test("runtime publish flag redacts vendor level fields and keeps the decoder's derived changes", async (t) => {
  setSource(t)
  const publicSnapshot = await readSnapshot()
  const privateSnapshot = applyPublishFlag(publicSnapshot, "0")

  assert.ok(publicSnapshot.banks.every((bank) => bank.series?.length))
  assert.ok(privateSnapshot.banks.every((bank) => !bank.series))
  if (publicSnapshot.decomposition) {
    assert.deepEqual(privateSnapshot.decomposition, { by_quarter: publicSnapshot.decomposition.by_quarter, rows: [] })
  }
  const { decoder } = privateSnapshot
  assert.ok(decoder && !Array.isArray(decoder))
  const row = decoder.rows?.find((item) => item.bank_code === "VCB" && item.period === "2025Q2")
  assert.ok(row)
  assert.deepEqual([row.npl_ratio, row.coverage, row.loan_growth, row.nim, row.lagged_coverage], Array(5).fill(null))
  assert.ok((row.delta_npl_ratio ?? 0) < 0)
})

test("reads S3 with the configured bucket and key, deduplicates requests and expires cache after ten minutes", async (t) => {
  setSource(t, "s3://vietleap-test/snapshots/npl/snapshot.json")
  let now = 1000
  t.mock.method(Date, "now", () => now)
  const object = { ...seed, meta: { ...seed.meta, snapshot_id: "cloud-test" } }
  const send = t.mock.method(S3Client.prototype, "send", async () => ({
    Body: { transformToString: async () => JSON.stringify(object) },
  }))
  const [first, second] = await Promise.all([readSnapshot(), readSnapshot()])
  assert.equal(first.meta.snapshot_id, "cloud-test")
  assert.equal(first, second)
  assert.equal(send.mock.callCount(), 1)
  assert.deepEqual(send.mock.calls[0].arguments[0].input, {
    Bucket: "vietleap-test",
    Key: "snapshots/npl/snapshot.json",
  })

  now += 599_999
  assert.equal(await readSnapshot(), first)
  now += 1
  assert.equal((await readSnapshot()).meta.snapshot_id, "cloud-test")
  assert.equal(send.mock.callCount(), 2)
})

test("serves the bundled snapshot when S3 is older and caches the decision", async (t) => {
  setSource(t, "s3://vietleap-test/snapshots/npl/older.json")
  const object = { ...seed, meta: { ...seed.meta, snapshot_id: "older-cloud",
    generated_at: new Date(Date.parse(seed.meta.generated_at) - 1_000).toISOString() } }
  const warn = t.mock.method(console, "warn", () => {})
  const send = t.mock.method(S3Client.prototype, "send", async () => ({
    Body: { transformToString: async () => JSON.stringify(object) },
  }))

  const [first, second] = await Promise.all([readSnapshot(), readSnapshot()])
  assert.equal(first.meta.snapshot_id, seed.meta.snapshot_id)
  assert.equal(first, second)
  assert.equal(await readSnapshot(), first)
  assert.equal(send.mock.callCount(), 1)
  assert.equal(warn.mock.callCount(), 1)
  assert.match(String(warn.mock.calls[0].arguments[0]), /older/)
})

test("fallback retains an explicit S3 restriction on bank series", async (t) => {
  setSource(t, "s3://vietleap-test/snapshots/npl/restricted-older.json")
  const object = { ...seed, meta: { ...seed.meta, publish_bank_series: false,
    generated_at: new Date(Date.parse(seed.meta.generated_at) - 1_000).toISOString() } }
  t.mock.method(console, "warn", () => {})
  t.mock.method(S3Client.prototype, "send", async () => ({
    Body: { transformToString: async () => JSON.stringify(object) },
  }))
  const snapshot = applyPublishFlag(await readSnapshot())
  assert.equal(snapshot.meta.snapshot_id, seed.meta.snapshot_id)
  assert.equal(snapshot.meta.publish_bank_series, false)
  assert.ok(snapshot.banks.every((bank) => !bank.series))
})

for (const section of ["decomposition", "market", "decision_rule", "scorecard", "context"]) {
  test(`serves the seed if a newer S3 snapshot lacks ${section}`, async (t) => {
    setSource(t, `s3://vietleap-test/snapshots/npl/no-${section}.json`)
    const object = structuredClone(seed)
    object.meta.snapshot_id = "incomplete-cloud"
    object.meta.generated_at = new Date(Date.parse(seed.meta.generated_at) + 1_000).toISOString()
    Reflect.deleteProperty(object, section)
    const warn = t.mock.method(console, "warn", () => {})
    t.mock.method(S3Client.prototype, "send", async () => ({
      Body: { transformToString: async () => JSON.stringify(object) },
    }))
    const snapshot = await readSnapshot()
    assert.equal(snapshot.meta.snapshot_id, seed.meta.snapshot_id)
    assert.ok(snapshot.decomposition?.rows.length && snapshot.market.m8 && snapshot.decision_rule?.q4_oos)
    assert.equal(warn.mock.callCount(), 1)
    assert.match(String(warn.mock.calls[0].arguments[0]), /incomplete/)
  })
}

test("serves the seed if S3 only has the legacy regressions", async (t) => {
  setSource(t, "s3://vietleap-test/snapshots/npl/legacy-regression.json")
  const object = structuredClone(seed)
  object.meta.snapshot_id = "legacy-regression"
  Reflect.deleteProperty(object.decoder.regression.fiinquant, "without_writeoff")
  const warn = t.mock.method(console, "warn", () => {})
  t.mock.method(S3Client.prototype, "send", async () => ({
    Body: { transformToString: async () => JSON.stringify(object) },
  }))
  assert.equal((await readSnapshot()).meta.snapshot_id, seed.meta.snapshot_id)
  assert.equal(warn.mock.callCount(), 1)
  assert.match(String(warn.mock.calls[0].arguments[0]), /incomplete/)
})

test("rejects an invalid S3 snapshot and retries the same key after correction", async (t) => {
  setSource(t, "s3://vietleap-test/snapshots/npl/corrected.json")
  let object: unknown = { ...seed, banks: [{ ...seed.banks[0], code: false }] }
  const send = t.mock.method(S3Client.prototype, "send", async () => ({
    Body: { transformToString: async () => JSON.stringify(object) },
  }))

  await assert.rejects(readSnapshot(), /snapshot schema/)
  object = seed
  assert.equal((await readSnapshot()).meta.snapshot_id, seed.meta.snapshot_id)
  assert.equal(send.mock.callCount(), 2)
})
