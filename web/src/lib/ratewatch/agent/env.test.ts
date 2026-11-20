// Run: node --test src/lib/ratewatch/agent/env.test.ts
import assert from "node:assert/strict"
import { mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { test } from "node:test"

import { loadDotenvFile } from "./env.ts"

test("loadDotenvFile sets unset keys and never overrides existing ones", () => {
  const dir = mkdtempSync(join(tmpdir(), "rw-env-"))
  try {
    const file = join(dir, ".env.local")
    writeFileSync(file, 'OPENAI_MODEL=gpt-6-luna\nQUOTED_KEY="giá trị có khoảng trắng"\nEMPTY_KEY=\n# comment\n\n', "utf8")
    process.env.OPENAI_MODEL = "already-set"
    const before = process.env.OPENAI_MODEL
    loadDotenvFile(file)
    assert.equal(process.env.OPENAI_MODEL, before) // not overridden
    assert.equal(process.env.QUOTED_KEY, "giá trị có khoảng trắng")
    assert.equal(process.env.EMPTY_KEY, "")
    delete process.env.QUOTED_KEY
    delete process.env.EMPTY_KEY
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test("loadDotenvFile is silent on a missing file", () => {
  loadDotenvFile(join(tmpdir(), "khong-ton-tai-" + Date.now() + ".env"))
})

test("loadDotenvFile never stores a key name with an empty value over an existing value", () => {
  process.env.RW_ENV_PROBE = "keep"
  const dir = mkdtempSync(join(tmpdir(), "rw-env-"))
  try {
    const file = join(dir, ".env.local")
    writeFileSync(file, "RW_ENV_PROBE=\n", "utf8")
    loadDotenvFile(file)
    assert.equal(process.env.RW_ENV_PROBE, "keep")
  } finally {
    rmSync(dir, { recursive: true, force: true })
    delete process.env.RW_ENV_PROBE
  }
})
