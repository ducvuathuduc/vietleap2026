import { readSnapshot } from "../snapshot-source.ts"
import { applyPublishFlag, type Snapshot } from "../view.ts"

/** Use the same normalized data and publication settings as the study pages. */
export async function loadNplSnapshot(): Promise<Snapshot> {
  return applyPublishFlag(await readSnapshot())
}
