import { readSnapshot } from "./snapshot-source.ts"
import { applyPublishFlag, type Snapshot } from "./view.ts"

export async function loadSnapshot(): Promise<Snapshot> {
  return applyPublishFlag(await readSnapshot())
}

export function bankByCode(snapshot: Snapshot, code: string) {
  const key = code.toUpperCase()
  return snapshot.banks.find((bank) => bank.code === key) ?? null
}
