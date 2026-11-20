import { expect, test } from "@playwright/test"

import { withLang } from "./helpers"

const ATTRIBUTION = "Nguồn: FiinQuant (FiinGroup)"

for (const code of ["VCB", "TCB", "STB"]) {
  for (const lang of ["vi", "en"] as const) {
    test(`bank page ${code} [${lang}]: renders charts and the attribution line`, async ({ page }) => {
      await page.goto(withLang(`/ngan-hang/${code}`, lang), { waitUntil: "load" })

      await expect(page.locator("h1")).toBeVisible()

      // Recharts surfaces: the quarterly compare chart and the per-metric lines.
      const charts = page.locator(".recharts-surface")
      await expect(charts.first(), `${code} (${lang}) must render at least one chart`).toBeVisible()
      expect(await charts.count(), `${code} (${lang}) chart count`).toBeGreaterThanOrEqual(1)

      await expect(page.getByText(ATTRIBUTION).first(), `${code} (${lang}) must show the attribution line`).toBeVisible()
    })
  }
}
