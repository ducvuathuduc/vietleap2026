// Run: npm test — feature 003 (US2): EN/VI toggle for the deck/pitch exports in the sidebar.
import { test } from "node:test"
import assert from "node:assert/strict"

import { availableLangs, exportKinds, isExportLang, pickLang } from "./export-lang.ts"

const both = { deck: "deck.pptx", deck_vi: "deck.vi.pptx", pitch_md: "pitch.md", pitch_en: "pitch.en.md", charts: 4 }
const viOnly = { deck_vi: "deck.vi.pptx", pitch_md: "pitch.md", charts: 4 }
const enOnly = { deck: "deck.pptx", pitch_en: "pitch.en.md" }

test("each language maps to its own deck and pitch export kinds", () => {
  assert.deepEqual(exportKinds(both, "vi"), ["deck_vi", "pitch_md"])
  assert.deepEqual(exportKinds(both, "en"), ["deck", "pitch_en"])
})

test("only files that were generated are offered", () => {
  assert.deepEqual(availableLangs(both), ["vi", "en"])
  assert.deepEqual(availableLangs(viOnly), ["vi"])
  assert.deepEqual(availableLangs(enOnly), ["en"])
  assert.deepEqual(availableLangs(undefined), [])
  assert.deepEqual(availableLangs({ deck: null, deck_vi: "" }), [])
  // results.json written before feature 003: English deck + Vietnamese pitch
  const legacy = { deck: "deck.pptx", pitch_md: "pitch.md" }
  assert.deepEqual(exportKinds(legacy, "vi"), ["pitch_md"])
  assert.deepEqual(exportKinds(legacy, "en"), ["deck"])
})

test("the stored preference wins when available, else the first available language", () => {
  assert.equal(pickLang(both, "en"), "en")
  assert.equal(pickLang(both, null), "vi")
  assert.equal(pickLang(viOnly, "en"), "vi")
  assert.equal(pickLang(enOnly, "vi"), "en")
  assert.equal(pickLang(undefined, "vi"), null)
  assert.equal(pickLang(both, "fr"), "vi")
})

test("only en and vi are languages", () => {
  assert.ok(isExportLang("vi") && isExportLang("en"))
  assert.ok(!isExportLang("both") && !isExportLang(undefined) && !isExportLang("../deck"))
})
