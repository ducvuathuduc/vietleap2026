import { expect, test } from "@playwright/test"

const title = "Hỏi về dữ liệu"

test("the desktop assistant is narrow, scrolls independently, and closes on Escape", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 900 })
  await page.goto("/")
  const trigger = page.getByRole("button", { name: title, exact: true })
  await trigger.click()
  const panel = page.getByRole("dialog", { name: title })
  await expect(panel).toBeVisible()
  const box = (await panel.boundingBox())!
  const input = (await panel.getByRole("textbox").boundingBox())!
  expect(box.width).toBeLessThanOrEqual(440)
  expect(box.width - input.width).toBeLessThanOrEqual(34)
  await expect(page.locator('[data-slot="sheet-overlay"]')).toHaveCount(0)
  await page.mouse.move(400, 500)
  await page.mouse.wheel(0, 700)
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0)
  await page.keyboard.press("Escape")
  await expect(panel).toBeHidden()
  await expect(trigger).toBeFocused()
})

test("the phone assistant covers the viewport and has a local close control", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/")
  await page.getByRole("button", { name: title, exact: true }).click()
  const panel = page.getByRole("dialog", { name: title })
  await expect(panel).toBeVisible()
  const box = (await panel.boundingBox())!
  expect(Math.round(box.width)).toBe(390)
  expect(Math.round(box.height)).toBe(844)
  await panel.getByRole("button", { name: "Đóng", exact: true }).click()
  await expect(panel).toBeHidden()
})

test("the Group 2 answer shows one sortable table and opens the matching waterfall", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("button", { name: title, exact: true }).click()
  const panel = page.getByRole("dialog", { name: title })
  const question = "Ngân hàng nào có NPL giảm quý 4/2025 nhưng nợ nhóm 2 tăng?"
  await panel.getByRole("textbox", { name: "Câu hỏi về dữ liệu" }).fill(question)
  await panel.getByRole("button", { name: "Gửi", exact: true }).click()
  const answer = panel.getByRole("article")
  await expect(answer.getByText(/6 ngân hàng.*BVB, LPB, NAB, NVB, SGB, SHB/)).toBeVisible()
  await expect(answer.getByRole("figure")).toHaveCount(1)
  const table = answer.getByRole("table", { name: "Ngân hàng phù hợp" })
  await expect(table.getByRole("rowheader")).toHaveText(["BVB", "LPB", "NAB", "NVB", "SGB", "SHB"])
  const group2 = table.getByRole("columnheader", { name: "Nhóm 2", exact: true })
  await group2.getByRole("button").click()
  await group2.getByRole("button").click()
  await expect(group2).toHaveAttribute("aria-sort", "descending")
  await expect(table.getByRole("rowheader").first()).toHaveText("SGB")
  await expect(answer.getByText("Nguồn FiinQuant (FiinGroup) (2025Q4)")).toHaveCount(1)
  await expect(answer).not.toContainText(/\btool\b|\bfocus\b|\b[a-z]+_[a-z]+\b|Đầu vào & nguồn/i)
  await table.getByRole("link", { name: "BVB", exact: true }).click()
  await expect(page).toHaveURL(/[?&]bank=BVB&year=2025#q4-breakdown$/)
  const breakdown = page.getByRole("region", { name: "Mổ xẻ một lần NPL giảm" })
  await expect(breakdown.getByRole("combobox", { name: "Ngân hàng" }).locator('[data-slot="select-value"]')).toHaveText("BVB")
  await expect(breakdown.getByRole("combobox", { name: "Năm" }).locator('[data-slot="select-value"]')).toHaveText("2025")
})

test("the rank-gap question shows a single table with the published ranks", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("button", { name: title, exact: true }).click()
  const panel = page.getByRole("dialog", { name: title })
  await panel.getByRole("textbox", { name: "Câu hỏi về dữ liệu" }).fill("Ngân hàng nào NPL đẹp nhưng chất lượng tổng thể kém?")
  await panel.getByRole("button", { name: "Gửi", exact: true }).click()
  const answer = panel.getByRole("article")
  const table = answer.getByRole("table", { name: "Chênh lệch thứ hạng tín dụng" })
  await expect(table.getByRole("row", { name: "BID 8 14" })).toBeVisible()
  await expect(answer.getByRole("table")).toHaveCount(1)
  await expect(answer.getByRole("figure")).toHaveCount(1)
})

test("the English early-warning answer compares three models in one table", async ({ page }) => {
  await page.goto("/phuong-phap?lang=en")
  await page.getByRole("button", { name: "Ask the data", exact: true }).click()
  const panel = page.getByRole("dialog", { name: "Ask the data" })
  await panel.getByRole("button", { name: "Does Group 2 improve early warning?" }).click()
  const answer = panel.getByRole("article")
  await expect(answer).toContainText("shows no clear improvement over NPL alone")
  const table = answer.getByRole("table", { name: "Early warning comparison" })
  await expect(table.getByRole("rowheader")).toHaveText(["NPL only", "Add Group 2", "Full indicators"])
  await expect(answer.getByRole("table")).toHaveCount(1)
  await expect(answer.getByRole("link", { name: "See on the page" })).toHaveAttribute("href", "/phuong-phap?lang=en#early-warning")
})

test("home metadata follows the new title and subtitle in both languages", async ({ page }) => {
  await page.goto("/")
  await expect(page).toHaveTitle("Vượt ra ngoài tỷ lệ nợ xấu")
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /Khung đánh giá chất lượng tín dụng và cảnh báo rủi ro, 27 ngân hàng niêm yết, 2021–2026/)
  await page.goto("/?lang=en")
  await expect(page).toHaveTitle("Beyond the NPL Ratio")
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /A credit quality assessment framework, 27 listed banks, 2021–2026/)
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("When the reported NPL ratio falls, what else should we check before concluding that credit quality has improved?")
})

test("an unknown English bank keeps its 404 and offers a localized way back", async ({ page }) => {
  const response = await page.goto("/ngan-hang/ZZZ?lang=en")
  expect(response?.status()).toBe(404)
  await expect(page.getByRole("heading", { name: "Bank not found" })).toBeVisible()
  await expect(page.getByRole("link", { name: "Browse listed banks" })).toHaveAttribute("href", "/ngan-hang?lang=en")
})
