import { defineConfig } from "@playwright/test"

// Target an already-running server: E2E_BASE_URL (production URL from Kiro) or
// the local dev server on 3109. This config never starts a server itself.
const baseURL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:3109"

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  forbidOnly: true,
  fullyParallel: false,
  workers: process.env.E2E_WORKERS ? Number(process.env.E2E_WORKERS) : 2,
  reporter: [["list"]],
  outputDir: process.env.E2E_OUTPUT_DIR ?? "test-results",
  use: {
    baseURL,
    headless: true,
    ignoreHTTPSErrors: true,
    viewport: { width: 1280, height: 800 },
  },
})
