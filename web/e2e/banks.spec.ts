import { expect, test } from "@playwright/test"

import { LANGS, withLang } from "./helpers"

const ATTRIBUTION = "Nguồn: FiinQuant (FiinGroup)"
const CHART_HEADINGS = {
  vi: {
    effects: "Trung bình theo quý của ngân hàng này, chấm là hệ số cả nhóm",
    series: "NPL, bao phủ, LDR, NIM và tăng trưởng dư nợ",
  },
  en: {
    effects: "This bank's quarterly mean, dots are the panel coefficients",
    series: "NPL, coverage, LDR, NIM and loan growth",
  },
} as const

for (const code of ["VCB", "TCB", "STB"]) {
  for (const lang of LANGS) {
    test(`bank page ${code} [${lang}]: renders charts and the attribution line`, async ({ page }) => {
      await page.goto(withLang(`/ngan-hang/${code}`, lang), { waitUntil: "load" })

      await expect(page.getByRole("heading", { level: 1, name: new RegExp(`\\b${code}\\b`) })).toBeVisible()

      const effects = page.locator("section").filter({ has: page.getByRole("heading", { name: CHART_HEADINGS[lang].effects, exact: true }) })
      const effectsChart = effects.getByRole("application")
      await expect(effectsChart).toBeVisible()
      await expect(effectsChart).toContainText(/Q2.*Q3.*Q4/)
      await expect(effectsChart).toContainText(lang === "vi" ? "0,00" : "0.00")

      const series = page.locator("section").filter({ has: page.getByRole("heading", { name: CHART_HEADINGS[lang].series, exact: true }) })
      await expect(series.getByRole("application")).toHaveCount(3)
      const nplChart = series.getByRole("application").first()
      await expect(nplChart).toBeVisible()
      await expect(nplChart).toContainText(/20\d{2}Q[1-4]/)

      await expect(series.getByText(ATTRIBUTION, { exact: true })).toBeVisible()
    })
  }
}
