import { expect, test } from "@playwright/test"

import { FORBIDDEN_TEXT, PUBLIC_ROUTES, monitor, readLabels, withLang, type Lang } from "./helpers"

const LANGS: Lang[] = ["vi", "en"]

for (const route of PUBLIC_ROUTES) {
  for (const lang of LANGS) {
    test(`route ${route} [${lang}]: 200, one h1, clean console, no failed requests, no horizontal scroll at 390px, no forbidden text`, async ({ page }) => {
      const m = monitor(page)
      await page.setViewportSize({ width: 390, height: 844 })
      const response = await page.goto(withLang(route, lang), { waitUntil: "load" })
      expect(response?.status(), `HTTP status for ${route} (${lang})`).toBe(200)

      const h1 = page.locator("h1")
      await expect(h1).toHaveCount(1)
      await expect(h1).toBeVisible()

      // Let hydration finish so late console errors and client charts settle.
      await page.waitForTimeout(750)

      expect(m.consoleErrors, `console errors on ${route} (${lang})`).toEqual([])
      expect(m.failedRequests, `failed requests on ${route} (${lang})`).toEqual([])

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }))
      expect(overflow.scrollWidth, `horizontal overflow on ${route} (${lang}) at 390px`).toBeLessThanOrEqual(overflow.innerWidth)

      const bodyText = await page.locator("body").innerText()
      const leak = bodyText.match(FORBIDDEN_TEXT)
      expect(leak, `forbidden debug text "${leak?.[0]}" on ${route} (${lang})`).toBeNull()
    })
  }
}

test("VI/EN toggle on / switches every nav label, the brand line, h1 and html lang", async ({ page }) => {
  await page.goto("/", { waitUntil: "load" })
  const viLabels = await readLabels(page)
  expect(viLabels.nav).toEqual(["Tổng quan", "Ngân hàng", "Thị trường", "Phương pháp", "Dữ liệu"])
  await expect(page.locator("html")).toHaveAttribute("lang", "vi")

  await page.getByRole("button", { name: "EN", exact: true }).click()
  await page.waitForURL("?lang=en")
  await expect(page.locator("html")).toHaveAttribute("lang", "en")
  const enLabels = await readLabels(page)
  expect(enLabels.nav).toEqual(["Overview", "Banks", "Market", "Method", "Data"])
  expect(enLabels.h1, "h1 must change when toggling to EN").not.toBe(viLabels.h1)
  expect(enLabels.brand, "brand subtitle must change when toggling to EN").not.toBe(viLabels.brand)

  await page.getByRole("button", { name: "VI", exact: true }).click()
  await page.waitForURL((url) => !url.searchParams.has("lang"))
  await expect(page.locator("html")).toHaveAttribute("lang", "vi")
  const backLabels = await readLabels(page)
  expect(backLabels.nav).toEqual(viLabels.nav)
})

for (const route of PUBLIC_ROUTES) {
  test(`route ${route}: VI vs EN — every nav label, brand line and h1 change`, async ({ page }) => {
    await page.goto(withLang(route, "vi"), { waitUntil: "load" })
    const vi = await readLabels(page)
    await page.goto(withLang(route, "en"), { waitUntil: "load" })
    const en = await readLabels(page)

    expect(en.nav, `nav labels on ${route} must all change to EN`).not.toEqual(vi.nav)
    for (let i = 0; i < Math.min(vi.nav.length, en.nav.length); i++) {
      expect(en.nav[i], `nav label "${vi.nav[i]}" on ${route} must change to EN`).not.toBe(vi.nav[i])
    }
    expect(en.brand, `brand subtitle on ${route} must change to EN`).not.toBe(vi.brand)
    expect(en.h1, `h1 on ${route} must change to EN`).not.toBe(vi.h1)
    expect(en.h2, `section headings on ${route} must change to EN`).not.toBe(vi.h2)
  })
}
