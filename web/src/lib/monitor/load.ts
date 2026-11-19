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
  const here = import.meta.dirname
  return {
    primary: path.resolve(here, "../../../../out/vn_monitor/monitor.json"),
    seed: path.resolve(here, "../../../seed/vn_monitor/monitor.json"),
  }
}

export function resolveMonitorPaths(env?: { MONITOR_PATH?: string }): { primary: string; seed: string } {
  const defaults = defaultMonitorPaths()
  const configured = (env ? env.MONITOR_PATH : process.env.MONITOR_PATH)?.trim()
  return { primary: configured || defaults.primary, seed: defaults.seed }
}

/** Read the published payload. Null when neither the primary file nor the seed exists. */
export function loadMonitor(options?: { primary: string; seed: string }): Monitor | null {
  const paths = options ?? resolveMonitorPaths()
  if (fs.existsSync(paths.primary)) return readCached(paths.primary)
  if (fs.existsSync(paths.seed)) return readCached(paths.seed)
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
