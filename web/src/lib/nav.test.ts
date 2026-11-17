import assert from "node:assert/strict"
import { test } from "node:test"

import { NAV, filterCommands, whatIfLink } from "./nav.ts"

test("commands find Vietnamese page names without accents", () => {
  assert.equal(filterCommands("chat luong")[0]?.url, "/quality")
  assert.equal(filterCommands("quality")[0]?.url, "/quality")
  assert.equal(filterCommands("what-if")[0]?.url, "/drivers")
  assert.equal(new Set(NAV.map((page) => page.url)).size, NAV.length)
})

test("what-if shortcut encodes the selected feature and bounds the percentage", () => {
  assert.equal(whatIfLink("what-if GDP/người +50%"), "/drivers?feature=GDP%2Fng%C6%B0%E1%BB%9Di&pct=30")
  assert.equal(whatIfLink("what-if"), null)
})
