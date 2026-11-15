// Sliding-window rate limit for LLM route handlers (/api/chat, /api/story): protects the LLM quota and the
// single-writer backend from request floods. In-memory, per client key — enough for a local single-process app.
// Env: CHAT_RATE_LIMIT_PER_MIN (default 20, 0 disables).

export function createRateLimiter(perMinute: number, windowMs = 60_000) {
  const hits = new Map<string, number[]>()
  return function allow(key: string, now = Date.now()): { ok: boolean; retryAfterS: number } {
    if (perMinute <= 0) return { ok: true, retryAfterS: 0 }
    const recent = (hits.get(key) ?? []).filter((t) => now - t < windowMs)
    if (recent.length >= perMinute) {
      hits.set(key, recent)
      return { ok: false, retryAfterS: Math.max(1, Math.ceil((windowMs - (now - recent[0])) / 1000)) }
    }
    recent.push(now)
    hits.set(key, recent)
    if (hits.size > 10_000) hits.clear() // bound memory under spoofed keys
    return { ok: true, retryAfterS: 0 }
  }
}

export function clientKey(req: Request): string {
  return req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || req.headers.get("x-real-ip") || "local"
}

const perMin = Number(process.env.CHAT_RATE_LIMIT_PER_MIN ?? 20)
export const llmLimiter = createRateLimiter(Number.isFinite(perMin) ? perMin : 20)

/** Returns a 429 Response when the caller is over the limit, otherwise null. */
export function rateLimited(req: Request): Response | null {
  const r = llmLimiter(clientKey(req))
  if (r.ok) return null
  return Response.json(
    { detail: "Quá nhiều yêu cầu tới AI — vui lòng đợi rồi thử lại." },
    { status: 429, headers: { "Retry-After": String(r.retryAfterS) } }
  )
}
