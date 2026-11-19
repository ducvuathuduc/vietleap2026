// Run: npm test
// Static copy/style checks that apply to the component kit.
import assert from "node:assert/strict"
import { readdirSync, readFileSync } from "node:fs"
import { join } from "node:path"
import { test } from "node:test"

const DIR = join(process.cwd(), "src", "components", "judge")
const files = readdirSync(DIR)
  .filter((name) => name.endsWith(".tsx"))
  .map((name) => ({ name, source: readFileSync(join(DIR, name), "utf8") }))

const PALETTE =
  /\b(?:bg|text|border|ring|fill|stroke|from|via|to)-(?:emerald|amber|green|blue|indigo|violet|purple|rose|red|orange|lime|cyan|sky|teal|yellow|fuchsia|pink|slate|gray|grey|zinc|neutral|stone)(?:-\d{2,3})?\b/

test("the kit is non-empty", () => {
  assert.ok(files.length >= 15, `found ${files.length} components`)
})

test("no emoji or decorative glyphs in component copy", () => {
  for (const file of files) {
    assert.doesNotMatch(file.source, /\p{Extended_Pictographic}/u, file.name)
  }
})

test("no gradients, glows, backdrop blur or palette classes", () => {
  for (const file of files) {
    assert.doesNotMatch(file.source, /gradient|backdrop-blur|drop-shadow|animate-bounce/, file.name)
    assert.doesNotMatch(file.source, PALETTE, file.name)
  }
})

test("no pie, donut, gauge or radial charts and no raster images", () => {
  for (const file of files) {
    assert.doesNotMatch(file.source, /\b(?:Pie|PieChart|RadialBar|RadialBarChart|Gauge)\b/, file.name)
    assert.doesNotMatch(file.source, /<img\b|<Image\b/, file.name)
  }
})

test("missing data is never rendered as N/A or a fake zero", () => {
  for (const file of files) {
    assert.doesNotMatch(file.source, /N\/A/, file.name)
    assert.doesNotMatch(file.source, /"(?:NaN|null|undefined)"/, file.name)
  }
})

test("every chart island is opt-in and named, not a generic series", () => {
  for (const file of files) {
    assert.doesNotMatch(file.source, /Series 1|series 1/, file.name)
  }
})
