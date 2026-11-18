import fs from "node:fs"
import path from "node:path"

export interface StaticDatasetEntry {
  id: string
  sampleCsvPath: string | null
  target?: string
  domain: string
  briefRaw?: unknown
}

export function discoverStaticOutputs(outRoot: string): StaticDatasetEntry[] {
  if (!fs.existsSync(/*turbopackIgnore: true*/ outRoot)) return []
  const items: StaticDatasetEntry[] = []
  try {
    for (const entry of fs.readdirSync(/*turbopackIgnore: true*/ outRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue
      const dsId = entry.name
      const dir = path.join(/*turbopackIgnore: true*/ outRoot, dsId)
      const briefPath = path.join(/*turbopackIgnore: true*/ dir, "brief.json")
      let briefRaw: unknown
      if (fs.existsSync(/*turbopackIgnore: true*/ briefPath)) {
        try {
          briefRaw = JSON.parse(fs.readFileSync(/*turbopackIgnore: true*/ briefPath, "utf-8"))
        } catch {
          /* ignore malformed brief.json */
        }
      }
      const sampleCsv = path.join(/*turbopackIgnore: true*/ dir, "clean_sample.csv")
      const hasSample = fs.existsSync(/*turbopackIgnore: true*/ sampleCsv)
      let target: string | undefined
      let domain = "auto"
      const resJson = path.join(/*turbopackIgnore: true*/ dir, "results.json")
      if (fs.existsSync(/*turbopackIgnore: true*/ resJson)) {
        try {
          const r = JSON.parse(fs.readFileSync(/*turbopackIgnore: true*/ resJson, "utf-8")) as {
            meta?: { target?: string; domain?: string }
          }
          target = r.meta?.target
          domain = r.meta?.domain ?? "auto"
        } catch {
          /* ignore malformed results.json */
        }
      }
      if (hasSample || briefRaw !== undefined) {
        items.push({
          id: dsId,
          sampleCsvPath: hasSample ? sampleCsv : null,
          target,
          domain,
          briefRaw,
        })
      }
    }
  } catch {
    /* ignore unreadable out/ */
  }
  return items
}

export class FallbackBackendError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function fetchBackendOrFallback<T>(
  apiUrl: string,
  reqPath: string,
  init: RequestInit | undefined,
  fallbackDispatch: (p: string, i?: RequestInit) => Promise<T>,
  fetcher: typeof fetch = fetch
): Promise<T> {
  if (!apiUrl) {
    try {
      return await fallbackDispatch(reqPath, init)
    } catch (e) {
      const err = e as Error & { status?: number }
      throw new FallbackBackendError(err.status ?? 500, err.message)
    }
  }

  let res: Response
  try {
    res = await fetcher(`${apiUrl}${reqPath}`, { ...init, cache: "no-store", signal: AbortSignal.timeout(60_000) })
  } catch (e) {
    const cause = (e as Error & { cause?: { code?: string; message?: string } }).cause
    const why = cause?.code ?? cause?.message ?? (e as Error).message
    console.warn(`[offline-fallback] API ${apiUrl} unreachable (${why}); falling back to in-process engine for ${reqPath}`)
    try {
      return await fallbackDispatch(reqPath, init)
    } catch (fallbackErr) {
      const fe = fallbackErr as Error & { status?: number }
      throw new FallbackBackendError(fe.status ?? 0, `Không kết nối được API ${apiUrl} (${why}); fallback lỗi: ${fe.message}`)
    }
  }

  if (res.status >= 502 && res.status <= 504) {
    console.warn(`[offline-fallback] API ${apiUrl} returned ${res.status}; falling back to in-process engine for ${reqPath}`)
    try {
      return await fallbackDispatch(reqPath, init)
    } catch {
      /* fall through to HTTP error */
    }
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new FallbackBackendError(res.status, detail)
  }

  return (await res.json()) as T
}
