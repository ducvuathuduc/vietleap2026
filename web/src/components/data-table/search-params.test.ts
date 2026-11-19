import assert from "node:assert/strict"
import { test } from "node:test"

import { clampPageSize, parseSortParam, rowMatchesQuery, serializeSortParam } from "./search-params.ts"

test("sort param round-trips the Kiranism id.direction form", () => {
  assert.deepEqual(parseSortParam("value.desc,name.asc"), [
    { id: "value", desc: true },
    { id: "name", desc: false },
  ])
  assert.equal(serializeSortParam([{ id: "value", desc: true }]), "value.desc")
  assert.equal(parseSortParam("value"), null)
  assert.deepEqual(parseSortParam(""), [])
})

test("page size stays on the supported set", () => {
  assert.equal(clampPageSize(20), 20)
  assert.equal(clampPageSize(15), 10)
  assert.equal(clampPageSize(Number.NaN), 10)
})

test("row filter matches folded Vietnamese text and ignores an empty query", () => {
  assert.equal(rowMatchesQuery({ name: "Ngân hàng" }, ""), true)
  assert.equal(rowMatchesQuery({ name: "Ngân hàng" }, "ngan hang"), true)
  assert.equal(rowMatchesQuery({ name: "Ngân hàng" }, "fdi"), false)
})
