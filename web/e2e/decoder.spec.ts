import { expect, test, type Locator, type Page } from "@playwright/test"

import { decoderCell, LANGS, switchTo, withLang, type Lang } from "./helpers"

const PANEL = {
  vi: {
    inputs: "5 đầu vào",
    inputLabels: ["Dư nợ khách hàng (L)", "Nợ nhóm 2 (G2)", "Nợ nhóm 3–5 (N)", "Dự phòng cuối kỳ (P)", "Xóa nợ trong kỳ (W)"],
    ratios: "Bốn tỷ lệ",
    ratioLabels: ["Tỷ lệ nợ xấu N/L", "Tỷ lệ nhóm 2 G2/L", "Bao phủ P/N", "Tỷ lệ xóa nợ W/L quý trước"],
    source: "Nguồn:",
    disclaimer: "Tool chỉ nêu cờ cần xem xét, không kết luận ngân hàng che giấu nợ xấu",
  },
  en: {
    inputs: "Five inputs",
    inputLabels: ["Customer loans (L)", "Group 2 loans (G2)", "NPL groups 3–5 (N)", "Provision balance (P)", "Write-offs (W)"],
    ratios: "Four ratios",
    ratioLabels: ["NPL ratio N/L", "Group 2 ratio G2/L", "Coverage P/N", "Write-off ratio W/L prior quarter"],
    source: "Source:",
    disclaimer: "The tool only raises a flag to review. It does not conclude that a bank is hiding bad debt.",
  },
} as const

async function expectItems(list: Locator, labels: readonly string[]) {
  const items = list.getByRole("listitem")
  await expect(items).toHaveCount(labels.length)
  for (const [index, label] of labels.entries()) {
    await expect(items.nth(index)).toContainText(label)
  }
}

async function expectPanel(page: Page, lang: Lang) {
  const copy = PANEL[lang]
  const dialog = page.getByRole("dialog", { name: /^[A-Z0-9]+ 20\d{2}Q[1-4]$/ })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole("heading", { name: copy.inputs, exact: true })).toBeVisible()
  await expect(dialog.getByRole("heading", { name: copy.ratios, exact: true })).toBeVisible()
  const lists = dialog.getByRole("list")
  await expectItems(lists.nth(0), copy.inputLabels)
  const ratios = lists.nth(1)
  await expectItems(ratios, copy.ratioLabels)
  for (const item of await ratios.getByRole("listitem").all()) {
    await expect(item).toContainText(copy.source)
  }
  await expect(dialog.getByText(/FiinQuant \(FiinGroup\)/).last()).toBeVisible()
  await expect(dialog.getByText(copy.disclaimer, { exact: true })).toBeVisible()
  return dialog
}

for (const lang of LANGS) {
  test(`decoder cell [${lang}] opens the inputs, ratios, sources and disclaimer`, async ({ page }) => {
    await page.goto(withLang("/giai-ma", lang))
    await decoderCell(page, lang).click()
    const dialog = await expectPanel(page, lang)

    await page.keyboard.press("Escape")
    await expect(dialog).toBeHidden()
  })

  test(`decoder cell [${lang}] supports Tab, Enter and Escape`, async ({ page }) => {
    await page.goto(withLang("/giai-ma", lang))
    const cell = decoderCell(page, lang)
    await cell.focus()
    await page.keyboard.press("Shift+Tab")
    await expect(cell).not.toBeFocused()
    await page.keyboard.press("Tab")
    await expect(cell).toBeFocused()

    await page.keyboard.press("Enter")
    const dialog = await expectPanel(page, lang)
    await page.keyboard.press("Escape")
    await expect(dialog).toBeHidden()
    await expect(cell).toBeFocused()
  })
}

test("VI/EN toggle changes the decoder filters, legend and decimal separator in the same cell", async ({ page }) => {
  await page.goto("/giai-ma")

  const viCell = decoderCell(page, "vi")
  await expect(viCell).toBeVisible()
  const viText = (await viCell.innerText()).match(/^-?\d+,\d{2}/)?.[0] ?? ""
  expect(viText, "the Vietnamese cell should display a comma decimal").toBeTruthy()
  await expect(page.getByRole("combobox", { name: "Quý", exact: true })).toHaveText(/Mọi quý/)
  await expect(page.getByRole("combobox", { name: "Trạng thái", exact: true })).toHaveText(/Mọi trạng thái/)
  await expect(page.getByRole("heading", { name: "Chú giải", exact: true })).toBeVisible()
  await expect(page.getByRole("columnheader", { name: "Ngân hàng", exact: true })).toBeVisible()

  await switchTo(page, "en")
  const enCell = decoderCell(page, "en")
  await expect(enCell).toBeVisible()
  const enText = (await enCell.innerText()).match(/^-?\d+\.\d{2}/)?.[0]
  expect(enText, "the same English cell should display a dot decimal").toBe(viText.replace(",", "."))
  await expect(page.getByRole("combobox", { name: "Quarter", exact: true })).toHaveText(/All quarters/)
  await expect(page.getByRole("combobox", { name: "Status", exact: true })).toHaveText(/All statuses/)
  await expect(page.getByRole("heading", { name: "Legend", exact: true })).toBeVisible()
  await expect(page.getByRole("columnheader", { name: "Bank", exact: true })).toBeVisible()

  await switchTo(page, "vi")
  await expect(viCell).toContainText(viText)
})
