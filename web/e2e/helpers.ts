import type { Page } from "@playwright/test"

export type Lang = "vi" | "en"

/** Public page routes of the judge flows (NPL product + RateWatch pages). */
export const PUBLIC_ROUTES = [
  "/",
  "/ngan-hang",
  "/ngan-hang/VCB",
  "/ngan-hang/TCB",
  "/ngan-hang/STB",
  "/thi-truong",
  "/phuong-phap",
  "/du-lieu",
  "/giai-ma",
  "/ban-do",
  "/chinh-sach",
  "/lai-suat",
  "/lai-suat/phuong-phap",
  "/lai-suat/ngan-hang/TCB",
] as const

/** Debug/internal leaks that must never appear as rendered page text. */
export const FORBIDDEN_TEXT = /get_ratios|fixture|run_id|undefined|\bNaN\b|Error:|stack/i

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

export interface PageLabels {
  nav: string[]
  brand: string
  h1: string
  h2: string
}

/** Visible UI labels: header nav links, brand subtitle, h1, joined h2 headings. */
export async function readLabels(page: Page): Promise<PageLabels> {
  const nav = await page.locator("header nav a").allInnerTexts()
  const brand = await page.locator("header p span").nth(1).innerText()
  const h1 = (await page.locator("h1").innerText()).trim()
  const h2 = (await page.locator("h2").allInnerTexts()).join(" | ")
  return { nav, brand, h1, h2 }
}
