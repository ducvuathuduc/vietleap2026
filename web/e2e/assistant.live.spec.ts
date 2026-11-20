import { expect, test } from "@playwright/test"

import { FORBIDDEN_TEXT, LANGS, withLang } from "./helpers"

interface Chunk {
  type: string
  delta?: string
  output?: { citations?: { source?: string }[] }
}

const COPY = {
  vi: {
    ask: "Hỏi về dữ liệu",
    question: "Mức nợ xấu trung vị mới nhất là bao nhiêu?",
    input: "Câu hỏi về dữ liệu",
    send: "Gửi",
    conversation: "Hội thoại",
    figures: "Số liệu đối chiếu",
    median: /trung vị nợ xấu|nợ xấu trung vị/i,
    open: "Xem trên trang",
  },
  en: {
    ask: "Ask the data",
    question: "What is the latest median NPL of the panel?",
    input: "Question about the data",
    send: "Send",
    conversation: "Conversation",
    figures: "Answer evidence",
    median: /median NPL|median non-performing loan/i,
    open: "See on the page",
  },
}

test.describe("assistant panel @live", () => {
  test.skip(process.env.LIVE_AI !== "1", "live AI checks require LIVE_AI=1")
  test.setTimeout(150_000)

  for (const lang of LANGS) {
    test(`streams a ${lang.toUpperCase()} answer with a canvas card and sources`, async ({ page }) => {
      const copy = COPY[lang]
      await page.goto(withLang("/", lang))
      await page.getByRole("button", { name: copy.ask, exact: true }).click()
      const panel = page.getByRole("dialog", { name: copy.ask, exact: true })
      await expect(panel).toBeVisible()
      await panel.getByRole("textbox", { name: copy.input, exact: true }).fill(copy.question)

      const pendingResponse = page.waitForResponse((res) => (
        new URL(res.url()).pathname === "/api/npl/chat" && res.request().method() === "POST"
      ), { timeout: 120_000 })
      await panel.getByRole("button", { name: copy.send, exact: true }).click()
      const response = await pendingResponse
      expect(response.status()).toBe(200)
      expect(response.headers()["content-type"]).toContain("text/event-stream")
      const chunks: Chunk[] = (await response.text()).split(/\r?\n/)
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim())
        .filter((line) => line && line !== "[DONE]")
        .map((line) => JSON.parse(line) as Chunk)
      expect(chunks.map((chunk) => chunk.type)).not.toContain("error")
      const answer = chunks.filter((chunk) => chunk.type === "text-delta").map((chunk) => chunk.delta).join("")
      expect(answer.trim()).toMatch(copy.median)

      const citations = chunks.filter((chunk) => chunk.type === "tool-output-available")
        .flatMap((chunk) => chunk.output?.citations ?? [])
        .map((citation) => citation.source ?? "")
      expect(citations.some((source) => source.trim().length > 0)).toBe(true)

      const conversation = panel.getByRole("region", { name: copy.conversation, exact: true })
      const reply = conversation.getByRole("paragraph").filter({ hasText: copy.median }).last()
      await expect(reply).toBeVisible()
      await expect(reply).not.toHaveText(copy.question)
      const figures = conversation.getByRole("figure", { name: copy.figures, exact: true })
      await expect(figures).toHaveCount(1)
      await expect(figures.getByRole("link", { name: copy.open, exact: true })).toBeVisible()
      await expect(figures.getByText(/FiinQuant \(FiinGroup\)/)).toBeVisible()
      expect((await panel.innerText()).match(FORBIDDEN_TEXT)?.[0]).toBeUndefined()
    })
  }
})
