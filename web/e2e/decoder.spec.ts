import { expect, test } from "@playwright/test"

import { withLang } from "./helpers"

const DISCLAIMER = {
  vi: "Tool chỉ nêu cờ cần xem xét, không kết luận ngân hàng che giấu nợ xấu",
  en: "The tool only raises a flag to review. It does not conclude that a bank is hiding bad debt.",
}

for (const lang of ["vi", "en"] as const) {
  test(`decoder table [${lang}]: click a cell -> side panel with 5 inputs, 4 ratios, source, disclaimer; Escape closes`, async ({ page }) => {
    const vi = lang === "vi"
    await page.goto(withLang("/giai-ma", lang), { waitUntil: "load" })

    // Open a cell that has data (a real button cell, not the em-dash placeholder).
    const cell = page.locator("button[aria-pressed]").first()
    await expect(cell).toBeVisible()
    await cell.click()

    const dialog = page.getByRole("dialog")
    await expect(dialog).toBeVisible()

    const inputsHeading = dialog.getByRole("heading", { name: vi ? "5 đầu vào" : "Five inputs" })
    await expect(inputsHeading).toBeVisible()
    const inputItems = dialog.locator(
      `xpath=//h3[normalize-space()="${vi ? "5 đầu vào" : "Five inputs"}"]/following-sibling::ul[1]/li`,
    )
    await expect(inputItems).toHaveCount(5)

    const ratiosHeading = dialog.getByRole("heading", { name: vi ? "Bốn tỷ lệ" : "Four ratios" })
    await expect(ratiosHeading).toBeVisible()
    const ratioItems = dialog.locator(
      `xpath=//h3[normalize-space()="${vi ? "Bốn tỷ lệ" : "Four ratios"}"]/following-sibling::ul[1]/li`,
    )
    await expect(ratioItems).toHaveCount(4)
    await expect(ratioItems.first()).toContainText(vi ? "Nguồn:" : "Source:")

    await expect(dialog).toContainText(DISCLAIMER[lang])

    // Escape closes the side panel.
    await page.keyboard.press("Escape")
    await expect(dialog).not.toBeVisible()
  })

  test(`decoder table [${lang}]: keyboard reachable — Enter on a focused cell opens the panel`, async ({ page }) => {
    const vi = lang === "vi"
    await page.goto(withLang("/giai-ma", lang), { waitUntil: "load" })
    const cell = page.locator("button[aria-pressed]").first()
    await cell.focus()
    await page.keyboard.press("Enter")
    const dialog = page.getByRole("dialog")
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole("heading", { name: vi ? "5 đầu vào" : "Five inputs" })).toBeVisible()
    await page.keyboard.press("Escape")
    await expect(dialog).not.toBeVisible()
  })

  test(`decoder table [${lang}]: numbers use the ${lang === "vi" ? "comma" : "dot"} decimal separator`, async ({ page }) => {
    await page.goto(withLang("/giai-ma", lang), { waitUntil: "load" })
    const cellNumbers = await page.locator("button[aria-pressed] span.tabular-nums").allInnerTexts()
    const numeric = cellNumbers.filter((t) => /\d/.test(t))
    expect(numeric.length, "decoder table must show numeric cells").toBeGreaterThan(0)
    for (const text of numeric) {
      if (lang === "vi") {
        expect(text, `VI cell "${text}" must use a comma decimal separator`).toMatch(/\d,\d{2}$/)
      } else {
        expect(text, `EN cell "${text}" must use a dot decimal separator`).toMatch(/\d\.\d{2}$/)
      }
    }
  })
}
