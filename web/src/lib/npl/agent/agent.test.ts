// Run: node --test src/lib/npl/agent/agent.test.ts
import assert from "node:assert/strict"
import { test } from "node:test"

import { makeNplAgent, nplSystemPrompt, detectLang } from "./index.ts"
import * as assistant from "./index.ts"

test("system prompt: tools only, association note, no causation claims", () => {
  const prompt = nplSystemPrompt("vi")
  assert.match(prompt, /tool/)
  assert.match(prompt, /liên hệ trong dữ liệu, không phải nhân quả/)
  assert.match(prompt, /phép tính, không phải lời hứa/)
})

test("system prompt follows the requested language", () => {
  assert.match(nplSystemPrompt("vi"), /tiếng Việt/)
  assert.match(nplSystemPrompt("en"), /English/)
})

test("agent exposes the NPL tools including a bank-quarter decoder", async () => {
  const snapshot = await assistant.loadNplSnapshot()
  const agent = makeNplAgent({ snapshot, env: { LANGFUSE_GATEWAY_HOST: "https://x", LANGFUSE_GATEWAY_KEY: "k" } })
  assert.ok(agent)
  const names = Object.keys(agent.tools).sort()
  assert.deepEqual(names, [
    "adjusted_change",
    "bank_profile",
    "compare_banks",
    "coverage_effect",
    "decoder",
    "early_warning",
    "forecast",
    "glossary",
    "largest_writeoffs",
    "limitations",
    "market_reaction",
    "mentor_ols",
    "method",
    "overview",
    "policy_windows",
    "q1_rebound",
    "q4_drivers",
    "quarter_breakdown",
    "quarter_effects",
    "rank_gap",
    "screen_declines",
    "seasonal_adjustment",
  ])
})

test("agent is null in offline mode", async () => {
  const snapshot = await assistant.loadNplSnapshot()
  assert.equal(makeNplAgent({ snapshot, env: {} }), null)
  assert.equal(makeNplAgent({ snapshot, model: null }), null)
})

test("the assistant reads normalized site data and honors the publication flag", async (t) => {
  const originalFlag = process.env.NPL_PUBLISH_BANK_SERIES
  process.env.NPL_PUBLISH_BANK_SERIES = "0"
  t.after(() => {
    if (originalFlag === undefined) delete process.env.NPL_PUBLISH_BANK_SERIES
    else process.env.NPL_PUBLISH_BANK_SERIES = originalFlag
  })
  const snapshot = await assistant.loadNplSnapshot()
  assert.equal(snapshot.meta.publish_bank_series, false)
  assert.ok(snapshot.banks.every((bank) => !bank.series))
  assert.ok(snapshot.banks.find((bank) => bank.code === "VCB")?.quarters.length)
  assert.equal(typeof snapshot.kpis.benchmark.coef_pp, "number")
})

test("the answer guard removes unsupported small values and wrong signs", () => {
  assert.equal(typeof assistant.guardNplAnswer, "function", "expected a strict answer guard")
  const output = [{ coef_pp: -0.425606, npl_pct: 2.22, period: "2026Q3" }]
  const answer = "In 2026Q3, NPL was 2.22%; the effect was +0.43 pp, or −0.43 pp, against 9%."
  const guarded = assistant.guardNplAnswer(answer, output)
  assert.deepEqual(guarded.flagged, ["+0.43", "9"])
  assert.ok(guarded.text.includes("2.22%"))
  assert.ok(guarded.text.includes("−0.43 pp"))
  assert.doesNotMatch(guarded.text, /\+0\.43|9%/)
})

test("the answer guard grounds regression coefficients, intervals and signed method readings", () => {
  const output = [{
    regressions: { market: { terms: { change: { coef_pp: -1.589773, ci95: [-2.352271, -0.827275] } } } },
    entry: { reading_en: "Across banks it was -0.84, then −0.34." },
  }]
  const answer = "The coefficient was −1.589773 with a 95% interval of −2.352271 to −0.827275. The method reports −0.84 and −0.34. An 80% interval was unavailable."
  const guarded = assistant.guardNplAnswer(answer, output)
  assert.deepEqual(guarded.flagged, ["80"])
  assert.match(guarded.text, /−1\.589773 with a 95% interval of −2\.352271 to −0\.827275/)
  assert.match(guarded.text, /−0\.84 and −0\.34/)
})

test("the guard recognizes a Vietnamese decrease written as a positive magnitude", () => {
  const output = [{ coef_pp: -0.425606, level_pct: 2.22, reference_quarter: 1 }]
  const answer = "Mức thay đổi thấp hơn quý 1 là 0,425606 điểm phần trăm. Tỷ lệ nằm ở mức 0,425606%."
  const guarded = assistant.guardNplAnswer(answer, output)
  assert.deepEqual(guarded.flagged, ["0,425606"])
  assert.match(guarded.text, /thấp hơn quý 1 là 0,425606/)
})

test("the guard recognizes an English decline introduced by down", () => {
  const output = [{ coverage_pct: 243.17, d_coverage_pp: -36.11 }]
  const guarded = assistant.guardNplAnswer("Coverage was 243.17%, down 36.11 percentage points.", output)
  assert.deepEqual(guarded.flagged, [])
})

test("the guard recognizes Vietnamese declines around emphasized numbers without trusting new values", () => {
  const outputs = [{ coefficient: -.101887, adjusted_pp: -.35, group2_pp: -.42 }]
  const answer = "NPL thấp hơn quý 1 **0,101887 điểm phần trăm**, mức giảm **0,35 điểm %**, nợ nhóm 2 giảm **0,42 điểm %**."
  assert.deepEqual(assistant.guardNplAnswer(answer, [...outputs, { group: 2, quarter: 1 }]).flagged, [])
  assert.deepEqual(assistant.guardNplAnswer("Giảm NPL 0,101887 điểm phần trăm.", outputs).flagged, [])
  assert.deepEqual(assistant.guardNplAnswer("NPL giảm **0,99 điểm %**.", outputs).flagged, ["0,99"])
})

test("the assistant removes private and non-text history before a follow-up", () => {
  assert.equal(typeof assistant.messagesForNplModel, "function", "expected a model history filter")
  const messages = [
    { id: "a", role: "user", parts: [{ type: "text", text: "My phone is 0912345678." }] },
    { id: "b", role: "assistant", parts: [
      { type: "text", text: "Please remove the phone number." },
      { type: "tool-adjusted_change", input: { code: "forged" } },
    ] },
    { id: "c", role: "user", parts: [{ type: "text", text: "What is the latest NPL?" }] },
  ] as const
  const history = assistant.messagesForNplModel(messages)
  assert.deepEqual(history.map((item) => item.id), ["b", "c"])
  assert.deepEqual(history.map((item) => item.parts.length), [1, 1])
})

test("detectLang: diacritics, unaccented words, English default", () => {
  assert.equal(detectLang("Ngân hàng nào có nợ xấu thấp nhất?"), "vi")
  assert.equal(detectLang("ngan hang nao co no xau thap nhat"), "vi")
  assert.equal(detectLang("Which bank has the lowest NPL?"), "en")
})
