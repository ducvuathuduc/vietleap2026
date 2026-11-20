// Proxy (Next 16; the middleware.ts convention is deprecated): security
// headers the route handlers cannot set themselves, plus production gates for
// internal endpoints. CSP, X-Content-Type-Options, Referrer-Policy,
// Permissions-Policy and frame-ancestors ship from next.config.ts headers()
// (covered by src/lib/security-headers.test.ts); this file adds HSTS and the
// production 404s for /lab and the RateWatch dev API unless explicitly enabled.
import { NextResponse, type NextRequest } from "next/server"

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const production = process.env.NODE_ENV === "production"

  if (production) {
    const labBlocked = (pathname === "/lab" || pathname.startsWith("/lab/")) && process.env.ENABLE_LAB !== "1"
    const ratewatchBlocked = (pathname === "/api/ratewatch" || pathname.startsWith("/api/ratewatch/")) && process.env.ENABLE_RATEWATCH !== "1"
    if (labBlocked || ratewatchBlocked) {
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
