import type { NextConfig } from "next";

import { legacyRedirects } from "./src/lib/nav.ts";

// Static CSP (no nonce): Next 16 inline scripts and Recharts style attributes need 'unsafe-inline'.
// React's dev overlay needs 'unsafe-eval' only outside production. Nobody may frame the site.
function securityHeaders() {
  const isDev = process.env.NODE_ENV !== "production"
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self'${isDev ? " ws: wss: http://localhost:* http://127.0.0.1:*" : ""}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ")
  return [
    { key: "Content-Security-Policy", value: csp },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  ]
}

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async redirects() {
    return legacyRedirects(process.env.ENABLE_LAB === "1")
  },
  async rewrites() {
    const backend = process.env.EXTERNAL_API_URL
    if (!backend) return []
    // Keep chat and story in Next.js. Serve engine results from the same store used by the analyst.
    const resources = ["datasets", "health", "sql", "brief", "sources", "warehouse", "jobs", "ingest", "export"]
    return {
      beforeFiles: resources.map((resource) => ({
        source: `/api/${resource}/:path*`,
        destination: `${backend}/api/${resource}/:path*`,
      })),
      afterFiles: [],
      fallback: [],
    }
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders() }]
  },
  cacheComponents: true,
  partialPrefetching: true,
  // The published payload is read with node:fs from outside the bundle, so tell the tracer
  // which folder ships with the server instead of tracing the whole project. Turbopack rejects
  // globs that leave the project root (`../out/vn_monitor/**` panics the build), and `next start`
  // reads that payload from disk anyway, so only the in-project seed is declared here.
  outputFileTracingIncludes: {
    "/*": ["./seed/vn_monitor/**"],
  },
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
