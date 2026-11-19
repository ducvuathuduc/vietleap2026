// Server-only reader. Do not import from a Client Component (uses node:fs).
import fs from "node:fs"
import path from "node:path"

import type { Monitor } from "./types.ts"

export class MonitorSchemaError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "MonitorSchemaError"
  }
}

type CacheEntry = { mtimeMs: number; payload: Monitor }

const cache = new Map<string, CacheEntry>()

export function defaultMonitorPaths(): { primary: string; seed: string } {
  // The Next server bundle leaves import.meta.dirname undefined, so resolve from the app root (`web/`).
  const here = process.cwd()
  return {
    primary: path.resolve(here, "../out/vn_monitor/monitor.json"),
    seed: path.resolve(here, "seed/vn_monitor/monitor.json"),
  }
}

export function resolveMonitorPaths(env?: { MONITOR_PATH?: string }): { primary: string; seed: string } {
  const defaults = defaultMonitorPaths()
  const configured = (env ? env.MONITOR_PATH : process.env.MONITOR_PATH)?.trim()
  return { primary: configured || defaults.primary, seed: defaults.seed }
}

/**
 * Cached read for judge pages. Cache Components prerenders the result into the
 * static shell, so the HTML carries the content instead of a streamed-in div.
 * The file mtime is part of the cache key, so a re-published payload is a new entry.
 */
export async function loadPublishedMonitor(): Promise<Monitor | null> {
  const paths = resolveMonitorPaths()
  const file = [paths.primary, paths.seed].find((candidate) => fs.existsSync(candidate))
  if (!file) return null
  return readPublished({ file, mtimeMs: fs.statSync(file).mtimeMs })
}

// `mtimeMs` is not read here: it sits in the argument object only to make a
// re-published payload a separate cache entry.
async function readPublished(source: { file: string; mtimeMs: number }): Promise<Monitor | null> {
  "use cache"
  return readCached(source.file)
}

/** Read the published payload. Null when neither the primary file nor the seed exists. */
export function loadMonitor(options?: { primary: string; seed: string }): Monitor | null {
  const paths = options ?? resolveMonitorPaths()
  // These paths come from the caller or the environment, so the tracer cannot scope them;
  // the ignore comments keep it from pulling the whole project into the server output.
  if (fs.existsSync(/*turbopackIgnore: true*/ paths.primary)) return readCached(paths.primary)
  if (fs.existsSync(/*turbopackIgnore: true*/ paths.seed)) return readCached(paths.seed)
  return null
}

function readCached(file: string): Monitor {
  const stat = fs.statSync(file)
  const hit = cache.get(file)
  if (hit && hit.mtimeMs === stat.mtimeMs) return hit.payload
  let parsed: unknown
  try {
    parsed = JSON.parse(fs.readFileSync(file, "utf8"))
  } catch (error) {
    throw new MonitorSchemaError(error instanceof Error ? error.message : "JSON không đọc được")
  }
  const version = parsed && typeof parsed === "object" ? (parsed as { schema_version?: unknown }).schema_version : undefined
  if (version !== 1) throw new MonitorSchemaError(`schema_version phải là 1 (nhận ${String(version)})`)
  const payload = parsed as Monitor
  cache.set(file, { mtimeMs: stat.mtimeMs, payload })
  return payload
}
