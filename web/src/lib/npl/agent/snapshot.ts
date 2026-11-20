// Snapshot loader for the NPL assistant: prefer the pipeline output
// (web/seed/npl/snapshot.json, written by python -m vlkit.npl.snapshot) and
// fall back to the bundled fixture when it is not on disk yet.
import { readFileSync } from "node:fs"
import path from "node:path"

import fixture from "../../../../seed/npl/snapshot.fixture.json" with { type: "json" }

import type { Snapshot } from "../view.ts"

let cached: Snapshot | null = null

export function loadNplSnapshot(): Snapshot {
  if (cached) return cached
  try {
    cached = JSON.parse(readFileSync(path.join(process.cwd(), "seed/npl/snapshot.json"), "utf8")) as Snapshot
  } catch {
    cached = fixture as unknown as Snapshot
  }
  return cached
}
