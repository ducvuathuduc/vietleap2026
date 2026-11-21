import { join } from "node:path"
import { expect, test, type Locator, type Page } from "@playwright/test"

const title = "Hỏi về dữ liệu"
const screenshotDir = process.env.ASSISTANT_QA_DIR

async function expectPanelWidth(panel: Locator, width: number) {
  await expect.poll(async () => (await panel.boundingBox())?.width ?? 0).toBeCloseTo(width, 0)
}

async function captureAssistant(page: Page, name: string) {
  if (!screenshotDir) return
  await page.screenshot({
    path: join(screenshotDir, `assistant-${name}.png`),
    animations: "disabled",
    style: "nextjs-portal { display: none !important; }",
  })
}

const panelCases = [
  {
    lang: "en",
    url: "/",
    title: "Ask the data",
    send: "Send",
    resize: "Resize assistant panel",
    collapse: "Collapse panel",
    canvasQuestion: "Which banks look better on NPL than on composite asset quality?",
    canvasTable: "Credit-quality rank gaps",
    chartQuestion: "Why does NPL fall in Q4?",
    chartTitle: "Drivers of Q4 NPL change",
    chartUnit: "Contribution to NPL change (pp)",
    chartCategory: "Loan growth",
    textQuestion: "What is the NPL ratio?",
  },
  {
    lang: "vi",
    url: "/?lang=vi",
    title,
    send: "Gửi",
    resize: "Đổi kích thước khung hỏi đáp",
    collapse: "Thu gọn",
    canvasQuestion: "Ngân hàng nào NPL đẹp nhưng chất lượng tổng thể kém?",
    canvasTable: "Chênh lệch thứ hạng tín dụng",
    chartQuestion: "Vì sao NPL quý 4 giảm?",
    chartTitle: "Yếu tố làm thay đổi nợ xấu quý 4",
    chartUnit: "Đóng góp vào thay đổi (điểm %)",
    chartCategory: "Dư nợ",
    textQuestion: "Tỷ lệ nợ xấu là gì?",
  },
] as const

for (const labels of panelCases) {
  test(`desktop ${labels.lang} assistant widens for canvases and remembers manual resizing`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(labels.url)
    const trigger = page.getByRole("button", { name: labels.title, exact: true })
    await trigger.click()
    const panel = page.getByRole("dialog", { name: labels.title })
    await expectPanelWidth(panel, 400)
    await captureAssistant(page, `1440-${labels.lang}-narrow`)

    const input = panel.getByRole("textbox")
    const send = panel.getByRole("button", { name: labels.send, exact: true })
    await input.fill(labels.canvasQuestion)
    await send.click()
    await expect(panel.getByRole("table", { name: labels.canvasTable })).toBeVisible()
    await expectPanelWidth(panel, 760)
    await captureAssistant(page, `1440-${labels.lang}-canvas`)
    await page.setViewportSize({ width: 1000, height: 900 })
    await expectPanelWidth(panel, 600)
    await page.setViewportSize({ width: 1440, height: 900 })
    await expectPanelWidth(panel, 760)

    const handle = panel.getByRole("separator", { name: labels.resize })
    const box = (await handle.boundingBox())!
    const x = box.x + box.width / 2
    const y = box.y + box.height / 2
    await page.mouse.move(x, y)
    await page.mouse.down()
    await page.mouse.move(x - 120, y, { steps: 8 })
    await page.mouse.up()
    await expectPanelWidth(panel, 880)
    await expect(handle).toHaveAttribute("aria-valuenow", "880")
    await captureAssistant(page, `1440-${labels.lang}-resized`)

    await handle.focus()
    await handle.press("Home")
    await expectPanelWidth(panel, 360)
    await handle.press("End")
    await expectPanelWidth(panel, 1080)
    await handle.press("ArrowRight")
    await expectPanelWidth(panel, 1056)

    await input.fill(labels.textQuestion)
    await send.click()
    const answer = panel.getByRole("article").last()
    await expect(panel.getByRole("article")).toHaveCount(2)
    await expect(answer.getByRole("table")).toHaveCount(0)
    await expectPanelWidth(panel, 400)

    await page.reload()
    await trigger.click()
    await expectPanelWidth(panel, 1056)
    await input.fill(labels.canvasQuestion)
    await send.click()
    await expect(panel.getByRole("table", { name: labels.canvasTable })).toBeVisible()
    await expectPanelWidth(panel, 760)
    await panel.getByRole("button", { name: labels.collapse, exact: true }).click()
    await expectPanelWidth(panel, 400)
    await expect(handle).toBeFocused()
  })

  test(`mobile ${labels.lang} assistant keeps canvas answers in the full-screen sheet`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(labels.url)
    await page.getByRole("button", { name: labels.title, exact: true }).click()
    const panel = page.getByRole("dialog", { name: labels.title })
    await expectPanelWidth(panel, 390)
    await panel.getByRole("textbox").fill(labels.canvasQuestion)
    await panel.getByRole("button", { name: labels.send, exact: true }).click()
    await expect(panel.getByRole("table", { name: labels.canvasTable })).toBeVisible()
    await expectPanelWidth(panel, 390)
    expect((await panel.boundingBox())?.height).toBe(844)
    await expect(panel.getByRole("separator", { name: labels.resize })).toHaveCount(0)
    await captureAssistant(page, `390-${labels.lang}-canvas`)
  })

  test(`${labels.lang} Q4 canvas keeps its chart labels at desktop and mobile widths`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(labels.url)
    await page.getByRole("button", { name: labels.title, exact: true }).click()
    const panel = page.getByRole("dialog", { name: labels.title })
    await panel.getByRole("textbox").fill(labels.chartQuestion)
    await panel.getByRole("button", { name: labels.send, exact: true }).click()
    const chart = panel.getByRole("figure", { name: labels.chartTitle })
    await expect(chart.getByText(labels.chartUnit, { exact: true })).toBeVisible()
    await expect(chart.getByText(labels.chartCategory, { exact: true })).toBeVisible()
    await expect(chart.getByText("0", { exact: true })).toBeVisible()
    await expectPanelWidth(panel, 760)
    await captureAssistant(page, `1440-${labels.lang}-chart`)

    await page.setViewportSize({ width: 390, height: 844 })
    await expectPanelWidth(panel, 390)
    await expect(chart.getByText(labels.chartCategory, { exact: true })).toBeVisible()
    await expect(chart.getByText("0", { exact: true })).toBeVisible()
    await captureAssistant(page, `390-${labels.lang}-chart`)
  })
}

test("the desktop assistant is narrow, scrolls independently, and closes on Escape", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 900 })
  await page.goto("/?lang=vi")
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
  await page.goto("/?lang=vi")
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
  await page.goto("/?lang=vi")
  await page.getByRole("button", { name: title, exact: true }).click()
  const panel = page.getByRole("dialog", { name: title })
  const question = "Ngân hàng nào có NPL giảm quý 4/2025 nhưng nợ nhóm 2 tăng?"
  await panel.getByRole("textbox", { name: "Câu hỏi về dữ liệu" }).fill(question)
  await panel.getByRole("button", { name: "Gửi", exact: true }).click()
  const answer = panel.getByRole("article")
  await expect(answer.getByText(/6 ngân hàng.*BVB, LPB, NAB, NVB, SGB, SHB/)).toBeVisible()
  await expect(answer.getByRole("figure")).toHaveCount(1)
  const figure = answer.getByRole("figure")
  const table = answer.getByRole("table", { name: "Nợ xấu giảm, nợ nhóm 2 tăng" })
  await expect(figure.getByText("2025Q4", { exact: true })).toBeVisible()
  await expect(table.getByRole("rowheader")).toHaveText(["BVB", "LPB", "NAB", "NVB", "SGB", "SHB"])
  const group2 = table.getByRole("columnheader", { name: "Δ Nợ nhóm 2 (điểm %)", exact: true })
  await group2.getByRole("button").click()
  await group2.getByRole("button").click()
  await expect(group2).toHaveAttribute("aria-sort", "descending")
  await expect(table.getByRole("rowheader").first()).toHaveText("SGB")
  await expect(figure.getByText("Nguồn: FiinQuant (FiinGroup)")).toHaveCount(1)
  await expect(answer).not.toContainText(/\btool\b|\bfocus\b|\b[a-z]+_[a-z]+\b|Đầu vào & nguồn/i)
  await table.getByRole("link", { name: "BVB", exact: true }).click()
  await expect(page).toHaveURL(/[?&]bank=BVB&year=2025#q4-breakdown$/)
  const breakdown = page.getByRole("region", { name: "Mổ xẻ một lần NPL giảm" })
  await expect(breakdown.getByRole("combobox", { name: "Ngân hàng" }).locator('[data-slot="select-value"]')).toHaveText("BVB")
  await expect(breakdown.getByRole("combobox", { name: "Năm" }).locator('[data-slot="select-value"]')).toHaveText("2025")
})

test("the rank-gap question shows a single table with the published ranks", async ({ page }) => {
  await page.goto("/?lang=vi")
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

test("home metadata follows the title and subtitle in both languages", async ({ page }) => {
  await page.goto("/?lang=vi")
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
