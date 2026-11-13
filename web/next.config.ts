import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
