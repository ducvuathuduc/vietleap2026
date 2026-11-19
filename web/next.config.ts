import type { NextConfig } from "next";

import { legacyRedirects } from "./src/lib/nav.ts";

const isDev = process.env.NODE_ENV !== "production"

// Security headers: allow same-origin and Google AI Studio preview/share iframe hosts while keeping strict CSP.
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
  "frame-ancestors 'self' https://aistudio.google.com https://*.google.com https://*.googleusercontent.com https://*.usercontent.goog",
].join("; ")

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
]

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
    return [{ source: "/:path*", headers: securityHeaders }]
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
