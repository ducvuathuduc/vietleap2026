import assert from "node:assert/strict"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { dirname, join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"

const BANNED = [
  "Từ số liệu đến tiền gửi",
  "từ insight đến decision",
  "Data to decision",
  "thông minh",
  "đột phá",
  "toàn diện",
  "giải pháp",
]

function walk(dir: string): string[] {
  const files: string[] = []
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) files.push(...walk(path))
    else if (/\.(tsx|ts)$/.test(name) && !name.endsWith(".test.ts")) files.push(path)
  }
  return files
}

test("npl pages and components do not use slogan copy", () => {
  const root = join(dirname(fileURLToPath(import.meta.url)), "../..")
  const files = [...walk(join(root, "app/(npl)")), ...walk(join(root, "components/npl"))]
  const hits: string[] = []
  for (const file of files) {
    const text = readFileSync(file, "utf8").toLowerCase()
    for (const phrase of BANNED) {
      if (text.includes(phrase.toLowerCase())) hits.push(`${file}: ${phrase}`)
    }
  }
  assert.deepEqual(hits, [])
  assert.ok(files.length > 0)
})
