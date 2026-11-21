// Proxy (Next 16; the middleware.ts convention is deprecated): security
// headers the route handlers cannot set themselves, plus production gates for
// internal endpoints. CSP, X-Content-Type-Options, Referrer-Policy,
// Permissions-Policy and frame-ancestors ship from next.config.ts headers()
// (covered by src/lib/security-headers.test.ts); this file adds HSTS and the
// production 404s for legacy pages and APIs unless explicitly enabled.
import { NextResponse, type NextRequest } from "next/server"
import { LANGUAGE_COOKIE, LANGUAGE_HEADER, parseLanguage } from "./lib/npl/language.ts"

const LEGACY_PATHS = [
  "/lab", "/print", "/ban-do", "/chinh-sach", "/lai-suat", "/tai-lieu/lai-suat",
  "/api/brief", "/api/chat", "/api/datasets", "/api/export", "/api/hoi-dap",
  "/api/ingest", "/api/jobs", "/api/sources", "/api/sql", "/api/story", "/api/warehouse",
]
const PUBLIC_API_PATHS = new Set(["/api/health", "/api/npl/chat"])

function atOrBelow(pathname: string, prefix: string) {
  return pathname === prefix || pathname.startsWith(`${prefix}/`)
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const production = process.env.NODE_ENV === "production"

  if (production) {
    const legacy = LEGACY_PATHS.some((prefix) => atOrBelow(pathname, prefix))
    const legacyBlocked = legacy && process.env.ENABLE_LAB !== "1"
    const unknownApi = !legacy && atOrBelow(pathname, "/api") && !PUBLIC_API_PATHS.has(pathname)
    if (legacyBlocked || unknownApi) {
      return new NextResponse(null, { status: 404 })
    }
  }

  const explicit = parseLanguage(request.nextUrl.searchParams.get("lang"))
  const remembered = parseLanguage(request.cookies.get(LANGUAGE_COOKIE)?.value)
  const headers = new Headers(request.headers)
  headers.set(LANGUAGE_HEADER, explicit ?? remembered ?? "en")
  const response = NextResponse.next({ request: { headers } })
  const prefetch = headers.has("next-router-prefetch") || headers.get("sec-purpose")?.includes("prefetch")
  if (explicit && explicit !== remembered && request.method === "GET" && !prefetch && !atOrBelow(pathname, "/api")) {
    response.cookies.set(LANGUAGE_COOKIE, explicit, {
      path: "/",
      httpOnly: true,
      sameSite: "lax",
      secure: request.nextUrl.protocol === "https:",
      maxAge: 365 * 24 * 60 * 60,
    })
  }
  response.headers.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
  return response
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}
