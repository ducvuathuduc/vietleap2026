// Loads KEY=VALUE lines from a dotenv file into process.env without overriding
// values that are already set. The repo keeps its model/Langfuse keys in the
// repo-root .env.local, which Next.js does not read (the app root is web/).
// Never logs names together with values.
import { readFileSync } from "node:fs"

export function parseDotenv(text: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith("#")) continue
    const eq = line.indexOf("=")
    if (eq <= 0) continue
    const key = line.slice(0, eq).trim()
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue
    let value = line.slice(eq + 1).trim()
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1)
    }
    out[key] = value
  }
  return out
}

export function loadDotenvFile(path: string): void {
  let text: string
  try {
    text = readFileSync(path, "utf8")
  } catch {
    return
  }
  for (const [key, value] of Object.entries(parseDotenv(text))) {
    if (process.env[key] === undefined) process.env[key] = value
  }
}

/** web/.env.local first, then the repo root .env.local; existing env always wins. */
export function loadRepoEnv(cwd = process.cwd()): void {
  loadDotenvFile(`${cwd}/.env.local`)
  loadDotenvFile(`${cwd}/../.env.local`)
}
