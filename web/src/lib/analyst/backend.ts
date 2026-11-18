// Server-side helpers for the AI analyst: use in-process TypeScript engine unless EXTERNAL_API_URL is explicitly configured.
import { dispatchBackend } from "@/lib/engine/store"
import { FallbackBackendError, fetchBackendOrFallback } from "@/lib/engine/offline-fallback"

const API = process.env.EXTERNAL_API_URL || ""

export class BackendError extends FallbackBackendError {}

export async function backend<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await fetchBackendOrFallback<T>(API, path, init, dispatchBackend)
  } catch (e) {
    if (e instanceof FallbackBackendError) {
      throw new BackendError(e.status, e.message)
    }
    throw e
  }
}

export const post = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
})

export const dsPath = (id: string) => `/api/datasets/${encodeURIComponent(id)}`

/** Round floats so tool outputs stay readable and cheap in tokens (values are not altered beyond 4 significant digits). */
export function compact<T>(v: T): T {
  return JSON.parse(
    JSON.stringify(v, (_k, x) => (typeof x === "number" && !Number.isInteger(x) ? Number(x.toPrecision(4)) : x))
  ) as T
}
