import fixture from "../../../seed/ratewatch/snapshot.fixture.json"

import type { Snapshot, SnapshotBank } from "./types.ts"

export function loadSnapshot(): Snapshot {
  return fixture as unknown as Snapshot
}

export function bankByCode(snapshot: Snapshot, code: string): SnapshotBank | null {
  const key = code.toUpperCase()
  return snapshot.banks.find((bank) => bank.code === key) ?? null
}
