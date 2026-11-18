import { NextResponse } from "next/server"
import { EngineBadRequestError, EngineNotFoundError } from "./store"

export function jsonError(err: unknown, fallbackStatus = 500) {
  if (err instanceof EngineNotFoundError) {
    return NextResponse.json({ detail: err.message }, { status: 404 })
  }
  if (err instanceof EngineBadRequestError) {
    return NextResponse.json({ detail: err.message }, { status: 422 })
  }
  const e = err as Error & { status?: number }
  const status = typeof e?.status === "number" ? e.status : fallbackStatus
  return NextResponse.json({ detail: e?.message ?? String(err) }, { status })
}
