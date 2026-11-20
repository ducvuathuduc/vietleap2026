import decoderFile from "../../../seed/npl/decoder.fixture.json"
import fixture from "../../../seed/npl/snapshot.fixture.json"

import { applyPublishFlag, type DecoderCell, type Snapshot } from "./view.ts"

export function loadSnapshot(): Snapshot {
  const snapshot = applyPublishFlag(fixture as Snapshot)
  if (snapshot.decoder?.length) return snapshot
  return { ...snapshot, decoder: (decoderFile as { decoder: DecoderCell[] }).decoder }
}

export function bankByCode(snapshot: Snapshot, code: string) {
  const key = code.toUpperCase()
  return snapshot.banks.find((bank) => bank.code === key) ?? null
}
