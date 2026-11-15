import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production"

// Security headers (docs/security/threat-model.md T3): no framing, no sniffing, CSP limited to this origin.
// 'unsafe-inline' is required by Next's inline bootstrap scripts (no nonce middleware) and by mermaid/driver.js inline
// styles; 'unsafe-eval' only in dev (React Refresh). All data calls go through same-origin /api/* rewrites.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self'${isDev ? " ws: http://localhost:* http://127.0.0.1:*" : ""}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ")

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
]

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }]
  },
  // Browser calls /api/* on the Next.js origin; anything that is not a Next route handler
  // (e.g. /api/chat) is proxied to FastAPI, so there is no CORS in the browser.
  async rewrites() {
    const api = process.env.API_URL ?? "http://127.0.0.1:8000"
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }]
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
