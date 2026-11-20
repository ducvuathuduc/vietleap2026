// Run: node --test src/lib/ratewatch/agent/guards.test.ts
import assert from "node:assert/strict"
import { test } from "node:test"

import { collectTruthNumbers, filterInput, findPii, guardNumbers, guardTextStream, redactPii } from "./guards.ts"

test("findPii detects Vietnamese citizen IDs (9 and 12 digits)", () => {
  const kinds = findPii("Tôi là Nguyễn Văn A, số 012345678901").map((h) => h.kind)
  assert.ok(kinds.includes("id"))
  const kinds9 = findPii("CMND 123456789 của tôi").map((h) => h.kind)
  assert.ok(kinds9.includes("id"))
})

test("findPii detects phone numbers (0-prefix and +84)", () => {
  const hits = findPii("gọi tôi 0912345678 hoặc +84912345678")
  assert.deepEqual([...new Set(hits.map((h) => h.kind))], ["phone"])
})

test("findPii detects bank account numbers (8-19 digits)", () => {
  const kinds = findPii("tài khoản 12345678 tại Vietcombank").map((h) => h.kind)
  assert.ok(kinds.includes("account"))
})

test("findPii detects emails", () => {
  const kinds = findPii("email me at someone@example.com").map((h) => h.kind)
  assert.ok(kinds.includes("email"))
})

test("findPii ignores normal amounts, terms and dates", () => {
  const text = "Tôi có 1,2 tỷ cần gửi 6 tháng, lãi 4,75%/năm, ngày 20/11/2026"
  assert.deepEqual(findPii(text), [])
})

test("filterInput rejects with a polite VI/EN notice naming the kinds only", () => {
  const res = filterInput("số CCCD 012345678901, email a@b.com")
  assert.equal(res.ok, false)
  assert.ok(res.notice_vi.includes("CCCD") || res.notice_vi.includes("cá nhân"))
  assert.ok(res.notice_en.length > 0)
  assert.ok(!res.notice_vi.includes("012345678901")) // never echoes the value
})

test("filterInput passes clean questions", () => {
  assert.equal(filterInput("1,2 tỷ cần sau 5 tháng, gửi đâu tốt?").ok, true)
})

// Models what real tool outputs contain: rates, money, a break-even, and the
// term/date numbers carried by rows and citations (12 tháng, ngày 06/11/2026).
const TRUTH = [4.75, 6.0, 6.3, 5.7, 5.4, 350_000_000, 1_200_000_000, 0.5660377358490566, 2026, 2025, 800_000_000, 12, 11]

test("guardNumbers keeps space-grouped thousands (NBSP/narrow NBSP, as some models format VND)", () => {
  // gpt-oss models write "332 068 311" with U+202F/U+00A0 between groups.
  const res = guardNumbers(
    "AGRIBANK 12\u202Ftháng: 332\u202F068\u202F311\u202FVND, tổng 800\u00A0000\u00A0000\u00A0VND",
    [332_068_311.1954459, 800_000_000, 12],
  )
  assert.deepEqual(res.flagged, [])
  assert.ok(res.text.includes("332\u202F068\u202F311"))
  assert.ok(!res.text.includes("chưa kiểm chứng"))
})

test("guardNumbers scales EN unit words (million/billion/thousand)", () => {
  const res = guardNumbers("The insured cap is 350 million VND, not 1.2 billion VND; minimum 350 thousand VND", [
    350_000_000,
    1_200_000_000,
    350_000,
  ])
  assert.deepEqual(res.flagged, [])
})

test("guardNumbers still treats an ASCII space as a boundary between numbers", () => {
  const res = guardNumbers("kỳ 12 tháng 6 lãi 7,1%", [12])
  assert.ok(res.flagged.length > 0)
})

test("guardNumbers keeps numbers the tools returned (VI and EN formatting)", () => {
  const res = guardNumbers("OCB online 12 tháng là 6,3%/năm, STB quầy 6 tháng 5.7%/năm", TRUTH)
  assert.deepEqual(res.flagged, [])
  assert.ok(res.text.includes("6,3%"))
})

test("guardNumbers accepts tỷ/triệu scaling and small counts", () => {
  const res = guardNumbers("Gửi 1,2 tỷ thành 350 triệu mỗi ngân hàng, 3 ngân hàng", TRUTH)
  assert.deepEqual(res.flagged, [])
})

test("guardNumbers replaces unknown numbers with [chưa kiểm chứng] and flags them", () => {
  const res = guardNumbers("Lãi kỳ 6 tháng tới sẽ là 7,1%/năm", TRUTH)
  assert.deepEqual(res.flagged, ["7,1"])
  assert.ok(res.text.includes("[chưa kiểm chứng]"))
  assert.ok(!res.text.includes("7,1"))
})

test("guardNumbers keeps dates that appear in tool outputs", () => {
  const res = guardNumbers("Biểu đề ngày 06/11/2026", TRUTH)
  assert.deepEqual(res.flagged, [])
})

test("collectTruthNumbers walks nested tool outputs including strings", () => {
  const truth = collectTruthNumbers([{ points: [{ rate_pct: 6.3 }], sheet_date: "2026-11-06" }])
  assert.ok(truth.includes(6.3))
  assert.ok(truth.includes(2026))
  assert.ok(truth.includes(11))
})

test("redactPii replaces personal data inside span payloads, keeps the rest", () => {
  const span = {
    input: { question: "gọi 0912345678 nhé", amount: 1_200_000_000 },
    messages: [{ role: "user", content: "email a@b.com, CCCD 012345678901" }],
    nested: { url: "https://ocb.com.vn/bieu", id: 12345678 },
  }
  const out = redactPii(span) as typeof span
  assert.equal(out.input.question, "gọi [redacted] nhé")
  assert.equal(out.input.amount, "[redacted]") // account-sized amounts never export
  assert.equal(out.messages[0]!.content, "email [redacted], CCCD [redacted]")
  assert.equal(out.nested.url, "https://ocb.com.vn/bieu")
  assert.equal(out.nested.id, "[redacted]")
})

async function readAll(stream: ReadableStream<Record<string, unknown>>): Promise<Record<string, unknown>[]> {
  const out: Record<string, unknown>[] = []
  for await (const chunk of stream) out.push(chunk)
  return out
}

test("guardTextStream passes tool parts through, learns truth from them, and guards text at text-end", async () => {
  const input: Record<string, unknown>[] = [
    { type: "tool-input-available", toolCallId: "t1", toolName: "get_curve", input: { bank: "OCB" } },
    { type: "tool-output-available", toolCallId: "t1", output: { rate_pct: 6.3 } },
    { type: "text-start", id: "a" },
    { type: "text-delta", id: "a", delta: "OCB 6 tháng 6,3% và " },
    { type: "text-delta", id: "a", delta: "7,5% năm sau" },
    { type: "text-end", id: "a" },
    { type: "finish" },
  ]
  const stream = ReadableStream.from(input).pipeThrough(guardTextStream())
  const chunks = await readAll(stream)
  const text = chunks
    .filter((c) => c.type === "text-delta")
    .map((c) => (c as { delta: string }).delta)
    .join("")
  assert.ok(text.includes("6,3%"))
  assert.ok(text.includes("[chưa kiểm chứng]"))
  assert.ok(!text.includes("7,5%"))
  const flag = chunks.find((c) => c.type === "data-guard") as { data?: { flagged: string[] } } | undefined
  assert.ok(flag && flag.data && flag.data.flagged.includes("7,5"))
  // tool parts untouched
  assert.ok(chunks.some((c) => c.type === "tool-output-available"))
  assert.ok(chunks.some((c) => c.type === "finish"))
})
