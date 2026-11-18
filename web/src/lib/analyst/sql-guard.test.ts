// Run: npm test
import { test } from "node:test"
import assert from "node:assert/strict"

import { isReadOnlySql, quoteIdent } from "./sql-guard.ts"

test("accepts SELECT and WITH queries with trailing semicolon and comments", () => {
  assert.equal(isReadOnlySql("SELECT * FROM gold.obt_demo LIMIT 10;  ").ok, true)
  assert.equal(isReadOnlySql("-- comment\n/* block */ WITH x AS (SELECT 1) SELECT * FROM x").ok, true)
  assert.equal(isReadOnlySql("DESCRIBE gold.t").ok, true)
  assert.equal(isReadOnlySql("SELECT 'drop table; delete' AS txt FROM gold.t").ok, true)
})

test("rejects empty and comment-only queries", () => {
  assert.equal(isReadOnlySql("").ok, false)
  assert.equal(isReadOnlySql("   -- only comment\n;  ").ok, false)
})

test("rejects mutating statements, multiple statements, and DuckDB file access functions", () => {
  for (const q of [
    "DELETE FROM gold.t",
    "DROP TABLE gold.t",
    "SELECT 1; DROP TABLE gold.t",
    "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT * FROM read_parquet('a.parquet')",
    "COPY gold.t TO '/tmp/out.csv'",
    "PRAGMA database_list",
    "INSTALL httpfs; LOAD httpfs",
    "WITH x AS (SELECT 1) DELETE FROM gold.t",
  ]) {
    assert.equal(isReadOnlySql(q).ok, false, `Expected reject: ${q}`)
  }
})

test("quoteIdent safely escapes double quotes", () => {
  assert.equal(quoteIdent("price_per_m2"), '"price_per_m2"')
  assert.equal(quoteIdent('a"b'), '"a""b"')
})
