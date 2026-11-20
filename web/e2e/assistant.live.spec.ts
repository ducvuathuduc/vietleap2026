import { expect, test, type APIRequestContext } from "@playwright/test"

// Live AI assistant checks against /api/npl/chat. Skipped unless LIVE_AI=1 —
// they call the real LLM. The assistant panel component (NplAssistant) is not
// mounted on any page (defect, see REPORT.md), so these drive the API the
// panel would use: same transport, same UIMessage payload.
test.describe("@live assistant", () => {
  test.skip(!process.env.LIVE_AI, "live AI checks: run with LIVE_AI=1")

  interface Chunk {
    type: string
    delta?: string
    output?: { citations?: unknown }
  }

  async function ask(request: APIRequestContext, question: string): Promise<{ text: string; citations: unknown[] }> {
    const res = await request.post("/api/npl/chat", {
      data: {
        messages: [{ id: "m1", role: "user", parts: [{ type: "text", text: question }] }],
      },
      headers: { "content-type": "application/json" },
    })
    expect(res.status()).toBe(200)
    expect(res.headers()["content-type"] ?? "", "answer must stream as SSE").toContain("text/event-stream")

    const raw = await res.text()
    const chunks: Chunk[] = raw
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .filter(Boolean)
      .map((line) => JSON.parse(line) as Chunk)

    const deltas = chunks.filter((c) => c.type === "text-delta" && typeof c.delta === "string")
    expect(deltas.length, "answer must arrive as streamed text deltas").toBeGreaterThan(0)
    const text = deltas.map((c) => c.delta ?? "").join("")
    expect(text.trim().length, "streamed answer must not be empty").toBeGreaterThan(0)

    const citations = chunks
      .filter((c) => c.type === "tool-output-available")
      .flatMap((c) => (Array.isArray(c.output?.citations) ? (c.output?.citations as unknown[]) : []))
    expect(citations.length, "answer must cite sources via tool outputs").toBeGreaterThan(0)
    return { text, citations }
  }

  test("EN question gets a streamed answer with citations", async ({ request }) => {
    const { text, citations } = await ask(request, "What is the latest median NPL?")
    expect(text).not.toMatch(/undefined|\bNaN\b/)
    expect(String((citations[0] as { source?: string }).source ?? "")).toBeTruthy()
  })

  test("VI question gets a streamed answer with citations", async ({ request }) => {
    const { text, citations } = await ask(request, "Mức nợ xấu trung vị mới nhất là bao nhiêu?")
    expect(text).not.toMatch(/undefined|\bNaN\b/)
    expect(String((citations[0] as { source?: string }).source ?? "")).toBeTruthy()
  })
})
