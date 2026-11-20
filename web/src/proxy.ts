// Proxy (Next 16; the middleware.ts convention is deprecated): security
// headers the route handlers cannot set themselves, plus production gates for
// internal endpoints. CSP, X-Content-Type-Options, Referrer-Policy,
// Permissions-Policy and frame-ancestors ship from next.config.ts headers()
// (covered by src/lib/security-headers.test.ts); this file adds HSTS and the
// production 404s for legacy pages and APIs unless explicitly enabled.
import { NextResponse, type NextRequest } from "next/server"

const LEGACY_PATHS = [
  "/lab", "/print", "/ban-do", "/chinh-sach", "/lai-suat", "/tai-lieu/lai-suat",
  "/api/brief", "/api/chat", "/api/datasets", "/api/export", "/api/hoi-dap",
  "/api/ingest", "/api/jobs", "/api/sources", "/api/sql", "/api/story", "/api/warehouse",
]

function atOrBelow(pathname: string, prefix: string) {
  return pathname === prefix || pathname.startsWith(`${prefix}/`)
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const production = process.env.NODE_ENV === "production"

  if (production) {
    const legacyBlocked = process.env.ENABLE_LAB !== "1" && LEGACY_PATHS.some((prefix) => atOrBelow(pathname, prefix))
    const ratewatchBlocked = process.env.ENABLE_RATEWATCH !== "1" && atOrBelow(pathname, "/api/ratewatch")
    if (legacyBlocked || ratewatchBlocked) {
      return new NextResponse(null, { status: 404 })
    }
  }

  const response = NextResponse.next()
  response.headers.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
  return response
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}
