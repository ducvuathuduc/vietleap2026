import { defineConfig } from "@playwright/test"

// Target an already-running server. BASE_URL works for dev and production.
const baseURL = process.env.BASE_URL ?? process.env.E2E_BASE_URL ?? "http://localhost:3112"

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
