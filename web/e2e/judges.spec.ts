import { expect, test } from "@playwright/test"

import { NPL_BANK_CODES } from "./helpers"

test("home explains the Q4 pattern and links the heatmap to banks", async ({ page }) => {
  await page.goto("/?lang=vi")
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Khi tỷ lệ nợ xấu được báo cáo giảm, cần xem thêm bằng chứng gì trước khi kết luận chất lượng tín dụng thực sự cải thiện?")
  const chart = page.getByRole("table", { name: "Thay đổi tỷ lệ nợ xấu theo quý và ngân hàng" })
  await expect(chart.getByRole("rowheader")).toHaveCount(NPL_BANK_CODES.length)
  const first = chart.getByRole("link").first()
  await first.focus()
  await page.keyboard.press("ArrowRight")
  const next = chart.getByRole("link").nth(1)
  await expect(next).toBeFocused()
  await expect(next).toHaveAccessibleName(/ABB, .*Nợ xấu .* đến .* Thay đổi/)
  await next.click()
  await expect(page).toHaveURL(/\/ngan-hang\/ABB\?lang=vi$/)
})

test("the home bank check updates the five rows and preserves the selected quarter", async ({ page }) => {
  await page.goto("/?lang=vi")
  const check = page.getByRole("region", { name: "Kiểm tra một ngân hàng" })
  await expect(check.locator("dl dt")).toHaveText([
    "Thời điểm và mùa vụ", "Mẫu số dư nợ", "Xóa nợ", "Nợ nhóm 2", "Bao phủ và dự phòng",
  ])
  await check.getByRole("combobox", { name: "Ngân hàng", exact: true }).selectOption("BID")
  await check.getByRole("combobox", { name: "Quý", exact: true }).selectOption("2025Q4")
  await check.getByRole("button", { name: "Xem kết quả" }).click()
  await expect(page).toHaveURL(/[?]lang=vi&bank=BID&period=2025Q4#bank-check$/)
  await expect(check.getByRole("combobox", { name: "Ngân hàng", exact: true })).toHaveValue("BID")
  await expect(check).toContainText("Sau điều chỉnh mùa vụ")
  await expect(check).toContainText(/Hạng theo nợ xấu \d+\/\d+/)
  await expect(check.getByRole("link", { name: "Xem hồ sơ BID" })).toHaveAttribute("href", "/ngan-hang/BID?lang=vi")
})

test("home lets a judge pick a bank and year for the Q4 breakdown", async ({ page }) => {
  await page.goto("/?lang=vi")
  await page.getByRole("link", { name: "Thử một ngân hàng" }).click()
  const breakdown = page.getByRole("region", { name: "Mổ xẻ một lần NPL giảm" })
  await expect(breakdown).toBeVisible()
  const bank = breakdown.getByRole("combobox", { name: "Ngân hàng", exact: true })
  await bank.click()
  await page.getByRole("listbox").getByRole("option", { name: "BID", exact: true }).click()
  await expect(page.getByRole("link", { name: "Xem ngân hàng BID" })).toBeVisible()
  const year = breakdown.getByRole("combobox", { name: "Năm", exact: true })
  await year.click()
  const choice = page.getByRole("listbox").getByRole("option").last()
  const label = await choice.innerText()
  await choice.click()
  await expect(year).toContainText(label)
  await expect(page.getByRole("list", { name: "Các bước thay đổi tỷ lệ nợ xấu" }).getByRole("listitem")).toHaveCount(5)
  await expect(page.getByText("Cờ vàng cần xem xét", { exact: true })).toBeVisible()
  await page.goto("/phuong-phap#seasonal-models")
  const reading = page.getByRole("region", { name: "Điều chỉnh mùa vụ theo từng ngân hàng" })
  await expect(reading.getByRole("heading", { name: "Thử với dữ liệu chưa dùng để đặt quy tắc" })).toBeVisible()
  await expect(reading).toContainText("chưa đủ để phân biệt hai nhóm")
})

test("the bank and method pages use the published scorecard and model results", async ({ page }) => {
  await page.goto("/ngan-hang/MBB?lang=en")
  const scorecard = page.getByRole("region", { name: "Credit scorecard" })
  await expect(scorecard).toContainText(/NPL rank \d+\/\d+, composite rank \d+\/\d+/)
  await expect(scorecard.getByRole("columnheader", { name: "Percentile" })).toBeVisible()
  await expect(page.getByRole("region", { name: "Seasonally adjusted NPL" }).getByText("Seasonally adjusted", { exact: true })).toBeVisible()

  await page.goto("/phuong-phap?lang=en")
  const model = page.getByRole("region", { name: "Within-bank regression" })
  await expect(model).toContainText("253 observations")
  await expect(model).toContainText("559 observations")
  await expect(page.getByRole("region", { name: "Early warning on held-out quarters" })).toContainText("AUC 0.658")
  await expect(page.getByRole("region", { name: "Bank-specific seasonal adjustment" })).toContainText("21 of 65 adjustable Q4 declines")
})

test("market switches the price comparison to VNINDEX", async ({ page }) => {
  await page.goto("/thi-truong?lang=vi")
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Biết nợ xấu chưa giúp dự báo giá tốt hơn")
  const group = page.getByRole("group", { name: "Chọn nhóm cổ phiếu" })
  await expect(group.getByRole("button", { name: "Rổ cổ phiếu ngân hàng" })).toHaveAttribute("aria-pressed", "true")
  await group.getByRole("button", { name: "VNINDEX" }).click()
  await expect(group.getByRole("button", { name: "VNINDEX" })).toHaveAttribute("aria-pressed", "true")
  await expect(page.getByText("Sai số giá trung bình", { exact: false })).toBeVisible()
  await expect(page.getByRole("heading", { name: "P/B theo nhóm nợ xấu" })).toBeVisible()
})
