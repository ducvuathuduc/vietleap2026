// Server-side helpers for the AI analyst: use in-process TypeScript engine unless EXTERNAL_API_URL is explicitly configured.
import { dispatchBackend } from "@/lib/engine/store"

const API = process.env.EXTERNAL_API_URL || ""

export class BackendError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export async function backend<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API) {
    try {
      return await dispatchBackend<T>(path, init)
    } catch (e) {
      const err = e as Error & { status?: number }
      throw new BackendError(err.status ?? 500, err.message)
    }
  }
  let res: Response
  try {
    res = await fetch(`${API}${path}`, { ...init, cache: "no-store", signal: AbortSignal.timeout(60_000) })
  } catch (e) {
    const cause = (e as Error & { cause?: { code?: string; message?: string } }).cause
    const why = cause?.code ?? cause?.message ?? (e as Error).message
    throw new BackendError(0, `Không kết nối được API phân tích ${API} (${why}). Backend có chạy không?`)
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new BackendError(res.status, detail)
  }
  return (await res.json()) as T
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
