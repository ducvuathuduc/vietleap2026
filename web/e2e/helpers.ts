import { expect, type Page } from "@playwright/test"

export type Lang = "vi" | "en"

export const NPL_ROUTES = [
  "/",
  "/ngan-hang",
  "/thi-truong",
  "/phuong-phap",
  "/du-lieu",
  "/giai-ma",
] as const

// Canonical tickers in the published NPL panel.
export const NPL_BANK_CODES = [
  "ABB", "ACB", "BAB", "BID", "BVB", "CTG", "EIB", "HDB", "KLB", "LPB", "MBB", "MSB", "NAB", "NVB",
  "OCB", "PGB", "SGB", "SHB", "SSB", "STB", "TCB", "TPB", "VAB", "VBB", "VCB", "VIB", "VPB",
] as const

/** Debug/internal leaks that must never appear as rendered page text. */
export const FORBIDDEN_TEXT = /\b(?:get_ratios|fixture|run_id|undefined|NaN|stack|console)\b|\bError:/i

export function isProductionTarget(baseURL: string | undefined) {
  if (process.env.E2E_PROD !== undefined) return process.env.E2E_PROD === "1"
  return !!baseURL && !["localhost", "127.0.0.1", "[::1]"].includes(new URL(baseURL).hostname)
}

export const LANGS = ["vi", "en"] as const

export function withLang(path: string, lang: Lang): string {
  if (lang === "vi") return path
  return path.includes("?") ? `${path}&lang=en` : `${path}?lang=en`
}

/** Collect console errors (incl. uncaught page errors) and failed network requests. */
export function monitor(page: Page) {
  const consoleErrors: string[] = []
  const failedRequests: string[] = []
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text())
  })
  page.on("pageerror", (err) => consoleErrors.push(`pageerror: ${err.message}`))
  page.on("requestfailed", (req) => {
    failedRequests.push(`${req.method()} ${req.url()} :: ${req.failure()?.errorText ?? "failed"}`)
  })
  page.on("response", (res) => {
    if (res.status() >= 400) failedRequests.push(`${res.request().method()} ${res.url()} -> ${res.status()}`)
  })
  return { consoleErrors, failedRequests }
}

export function decoderCell(page: Page, lang: Lang) {
  const number = lang === "vi" ? /^-?\d+,\d{2}(?:\s|$)/ : /^-?\d+\.\d{2}(?:\s|$)/
  return page.getByRole("table").getByRole("button", { name: number, pressed: false }).first()
}

export async function switchTo(page: Page, lang: Lang) {
  const current = lang === "en" ? "Ngôn ngữ" : "Language"
  const group = page.getByRole("group", { name: current, exact: true })
  await group.getByRole("link", { name: lang.toUpperCase(), exact: true }).click()
  await page.waitForURL((url) => lang === "en" ? url.searchParams.get("lang") === "en" : !url.searchParams.has("lang"))
  await expect(page.locator("html")).toHaveAttribute("lang", lang)
}
