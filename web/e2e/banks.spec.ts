import { expect, test } from "@playwright/test"

import { LANGS, withLang } from "./helpers"

const ATTRIBUTION = "Nguồn: FiinQuant (FiinGroup)"

for (const code of ["VCB", "TCB", "STB"]) {
  for (const lang of LANGS) {
    test(`bank page ${code} [${lang}]: renders charts and the attribution line`, async ({ page }) => {
      await page.goto(withLang(`/ngan-hang/${code}`, lang), { waitUntil: "load" })

      await expect(page.getByRole("heading", { level: 1, name: new RegExp(`\\b${code}\\b`) })).toBeVisible()

      const charts = page.getByRole("application")
      await expect(charts.first()).toBeVisible()
      await expect(charts.first()).toContainText("Q4")
      await expect(charts.nth(1)).toBeVisible()
      await expect(charts.nth(1)).toContainText(/20\d{2}Q[1-4]/)

      await expect(page.getByText(ATTRIBUTION, { exact: true }).first()).toBeVisible()
    })
  }
}
