import { expect, test, type Page } from "@playwright/test"

import {
  FORBIDDEN_TEXT, LANGS, NPL_BANK_CODES, NPL_ROUTES, monitor, switchTo, withLang, type Lang,
} from "./helpers"

const NPL_PAGES = [...NPL_ROUTES, ...NPL_BANK_CODES.map((code) => `/ngan-hang/${code}`)]

async function expectHealthyPage(page: Page, route: string, lang: Lang) {
  const failures = monitor(page)
  await page.setViewportSize({ width: 390, height: 844 })
  const response = await page.goto(withLang(route, lang), { waitUntil: "networkidle" })
  expect(response?.status()).toBe(200)
  expect(new URL(page.url()).pathname).toBe(route)

  const headline = page.getByRole("heading", { level: 1, includeHidden: true })
  await expect.soft(headline).toHaveCount(1)
  if (await headline.count() === 1) await expect.soft(headline).toBeVisible()

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect.soft(overflow, "root horizontal overflow in px at a 390px viewport").toBeLessThanOrEqual(0)
  expect.soft((await page.locator("body").innerText()).match(FORBIDDEN_TEXT)?.[0], "forbidden text on the page").toBeUndefined()
  expect.soft(failures.consoleErrors, "console and page errors").toEqual([])
  expect.soft(failures.failedRequests, "failed or unsuccessful requests").toEqual([])
}

for (const route of NPL_PAGES) {
  for (const lang of LANGS) {
    test(`public route ${route} [${lang}] is healthy at 390px`, async ({ page }) => {
      await expectHealthyPage(page, route, lang)
    })
  }
}

const NAV = {
  vi: ["Tổng quan", "Ngân hàng", "Thị trường", "Phương pháp", "Dữ liệu"],
  en: ["Overview", "Banks", "Market", "Method", "Data"],
  brand: { vi: "Vượt ra ngoài tỷ lệ nợ xấu", en: "Beyond the NPL Ratio" },
}

test("a first visit serves English HTML and metadata", async ({ request }) => {
  const response = await request.get("/")
  expect(response.status()).toBe(200)
  const html = await response.text()
  expect(html.match(/<html[^>]*\blang="([^"]+)"/)?.[1]).toBe("en")
  expect(html.match(/<title>([^<]+)<\/title>/)?.[1]).toBe("Beyond the NPL Ratio")
  expect(html.match(/<meta property="og:title" content="([^"]+)"/)?.[1]).toBe("Beyond the NPL Ratio")
  expect(html.match(/<meta property="og:locale" content="([^"]+)"/)?.[1]).toBe("en_US")
})

test("an explicit language takes precedence and persists for URLs without a language", async ({ page }) => {
  await page.goto("/?bank=BID&period=2025Q4")
  await switchTo(page, "vi")
  const query = new URL(page.url()).searchParams
  expect(query.get("bank")).toBe("BID")
  expect(query.get("period")).toBe("2025Q4")
  await expect(page).toHaveTitle(NAV.brand.vi)
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", NAV.brand.vi)
  await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute("content", "vi_VN")

  await page.goto("/thi-truong")
  await expect(page.locator("html")).toHaveAttribute("lang", "vi")
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Biết nợ xấu chưa giúp dự báo giá tốt hơn")
  await expect(page).toHaveTitle("Thị trường")
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", "Thị trường")

  await page.goto("/thi-truong?lang=en")
  await expect(page.locator("html")).toHaveAttribute("lang", "en")
  await expect(page).toHaveTitle("Market")
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", "Market")

  await page.goto("/")
  await expect(page.locator("html")).toHaveAttribute("lang", "en")
  await expect(page).toHaveTitle(NAV.brand.en)
})

async function expectLocalizedHeader(page: Page, lang: Lang) {
  const nav = page.getByRole("navigation", { name: lang === "vi" ? "Mục" : "Sections", exact: true })
  const header = page.getByRole("banner").filter({ has: nav })
  await expect(nav).toBeVisible()
  expect.soft(await nav.getByRole("link").allInnerTexts()).toEqual(NAV[lang])
  await expect.soft(header.getByText(NAV.brand[lang], { exact: true }).first()).toBeVisible()
  const language = page.getByRole("group", { name: lang === "vi" ? "Ngôn ngữ" : "Language", exact: true })
  await expect.soft(language.getByRole("link", { name: lang.toUpperCase(), exact: true })).toHaveAttribute("aria-current", "true")
}

const LABEL_ROLES = [
  "heading", "columnheader", "caption", "link", "button", "tab", "combobox", "checkbox", "slider", "textbox", "switch",
] as const

async function visiblePageLabels(page: Page) {
  return Promise.all(LABEL_ROLES.map(async (role) => {
    const labels = await page.getByRole(role).evaluateAll((elements) => elements.map((element) => {
      const labelledBy = element.getAttribute("aria-labelledby")?.split(/\s+/)
        .map((id) => element.ownerDocument.getElementById(id)?.textContent)
        .filter(Boolean).join(" ")
      const associatedLabels = "labels" in element
        ? Array.from((element as HTMLInputElement).labels ?? [], (label) => label.textContent).join(" ")
        : ""
      const label = labelledBy || element.getAttribute("aria-label") || associatedLabels || (element as HTMLElement).innerText
      return label?.replace(/\s+/g, " ").trim() ?? ""
    }))
    return { role, labels: [...new Set(labels.filter(Boolean))] }
  }))
}

const INVARIANT_LABELS = new Set([
  ...NPL_BANK_CODES,
  "VI", "EN", "NPL", "NIM", "LDR", "ROA", "P/B", "VNINDEX",
  "Agribank", "Eximbank", "HDBank", "PVcomBank", "Sacombank", "Techcombank", "VCBNeo", "VietBank",
  "Open Next.js Dev Tools",
])

function isInvariant(label: string) {
  // Figures without captions, reporting periods, and source URLs remain the same.
  return INVARIANT_LABELS.has(label) || /^(?:https?:\/\/\S+|[\d.,%+−\-\s]+|20\d{2}Q[1-4]|—)$/.test(label)
}

for (const route of NPL_PAGES) {
  test(`VI/EN toggle on ${route} translates the navigation, headings and visible controls`, async ({ page }) => {
    const response = await page.goto(withLang(route, "vi"))
    expect(response?.status()).toBe(200)
    await expect(page.locator("html")).toHaveAttribute("lang", "vi")
    await expectLocalizedHeader(page, "vi")
    const vi = await visiblePageLabels(page)
    expect(vi[0].labels.length).toBeGreaterThan(0)

    await switchTo(page, "en")
    await expectLocalizedHeader(page, "en")
    const en = await visiblePageLabels(page)
    for (const [index, { role, labels }] of vi.entries()) {
      const englishLabels = en[index].labels
      const unchanged = labels.filter((label) => !isInvariant(label) && englishLabels.includes(label))
      expect.soft(unchanged, `${role} labels unchanged across locales`).toEqual([])
      if (role === "heading" || role === "columnheader") {
        expect.soft(englishLabels, `number of distinct ${role} labels after changing language`).toHaveLength(labels.length)
      }
    }

    await switchTo(page, "vi")
    await expectLocalizedHeader(page, "vi")
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(vi[0].labels[0])
  })
}
