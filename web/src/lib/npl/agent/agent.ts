// The NPL study assistant: a ToolLoopAgent over the published snapshot only.
// The system prompt is the judge contract: snapshot numbers only, association
// not causation for M4–M6, forecasts are calculations, never investment advice.
import { isStepCount, tool, ToolLoopAgent, type LanguageModel, type Tool } from "ai"
import { z } from "zod"

import type { Snapshot } from "../view.ts"
import { ratewatchModel } from "../../ratewatch/agent/model.ts"
import { detectLang, type Lang } from "./lang.ts"
import * as npl from "./tools.ts"

export { detectLang, type Lang }

export function nplSystemPrompt(lang: Lang): string {
  if (lang === "en") {
    return [
      "You are the assistant of the NPL study (Vietnamese bank panel 2021Q2–2026Q3).",
      "Answer ONLY with values returned by the tools; never invent or estimate a number.",
      "For M4–M6 results say 'association, not causation'; for forecasts say 'calculation, not a promise'.",
      "Cite source, period, n and the 95% interval whenever the tool returns one.",
      "If a tool returns found: false, say exactly that the bank or term is not in the snapshot.",
      "Answer in English when the user writes English, in Vietnamese when they write Vietnamese.",
      "Never ask for or repeat personal data (name, citizen ID, phone, account number).",
    ].join("\n")
  }
  return [
    "Bạn là trợ lý của nghiên cứu nợ xấu (bảng ngân hàng 2021Q2–2026Q3).",
    "Chỉ trả lời bằng các số do tool trả về; không tự nghĩ ra hay ước lượng con số nào.",
    "Với kết quả M4–M6 hãy nói 'liên hệ, không phải nhân quả'; với dự báo hãy nói 'phép tính, không phải lời hứa'.",
    "Mỗi con số phải kèm nguồn, kỳ (period), n và khoảng tin cận 95% khi tool trả về.",
    "Nếu tool trả found: false thì nói đúng điều đó — ngân hàng hoặc kỳ hạn không có trong snapshot.",
    "Trả lời bằng tiếng Việt khi người dùng viết tiếng Việt, bằng tiếng Anh khi họ viết tiếng Anh.",
    "Không bao giờ hỏi hay nhắc lại thông tin cá nhân (họ tên, CCCD, số điện thoại, số tài khoản).",
  ].join("\n")
}

const bankSchema = z.string().min(2).max(40).describe("Bank code, e.g. VCB, MBB")

/** Bind the deterministic snapshot tools for a ToolLoopAgent. */
export function makeNplTools(snapshot: Snapshot): Record<string, Tool> {
  return {
    overview: tool({
      description: "Study headline: NPL level, benchmark Q4-vs-Q1 coefficient, trend, sources.",
      inputSchema: z.object({}),
      execute: async () => npl.overview(snapshot),
    }),
    quarter_effects: tool({
      description: "Quarter effects (Q2/Q3/Q4 versus Q1) with 95% intervals and p-values.",
      inputSchema: z.object({}),
      execute: async () => npl.quarterEffects(snapshot),
    }),
    bank_profile: tool({
      description: "One bank from the snapshot: ownership, medians, latest quarter, signals.",
      inputSchema: z.object({ code: bankSchema }),
      execute: async (input) => npl.bankProfile(snapshot, input),
    }),
    adjusted_change: tool({
      description: "Raw and quarter-effect-adjusted NPL change for one bank and period (latest when omitted).",
      inputSchema: z.object({ code: bankSchema, period: z.string().regex(/^\d{4}Q[1-4]$/).optional() }),
      execute: async (input) => npl.adjustedChange(snapshot, input),
    }),
    compare_banks: tool({
      description: "Compare at most 4 banks on Q4 change, Q1 rebound and latest adjusted change.",
      inputSchema: z.object({ codes: z.array(bankSchema).min(1).max(4) }),
      execute: async (input) => npl.compareBanks(snapshot, input),
    }),
    forecast: tool({
      description: "Next-quarter NPL forecast for one bank with an 80% interval and forecast MAE.",
      inputSchema: z.object({ code: bankSchema }),
      execute: async (input) => npl.forecast(snapshot, input),
    }),
    market_reaction: tool({
      description: "Market reaction around disclosure events: CAR by day and event-study regressions.",
      inputSchema: z.object({}),
      execute: async () => npl.marketReaction(snapshot),
    }),
    method: tool({
      description: "One study method (M1–M7): spec, n, reading and what it does not show.",
      inputSchema: z.object({ model_id: z.string().min(2).max(4) }),
      execute: async (input) => npl.method(snapshot, input),
    }),
    limitations: tool({
      description: "Study limitations and the legal references of the snapshot.",
      inputSchema: z.object({}),
      execute: async () => npl.limitations(snapshot),
    }),
    glossary: tool({
      description: "Explain a study term (NPL, adjusted change, quarter effect, wild bootstrap, CAR, coverage, LDR, NIM).",
      inputSchema: z.object({ term: z.string().min(2).max(60) }),
      execute: async (input) => npl.glossary(snapshot, input),
    }),
  }
}

export function makeNplAgent(input: {
  snapshot: Snapshot
  /** Explicit model wins; otherwise resolved from env via the shared provider switch. */
  model?: LanguageModel | null
  env?: NodeJS.ProcessEnv
  /** Chat session id: sent as the gateway langfuse-session-id header. */
  sessionId?: string | null
  lang?: Lang
}): ToolLoopAgent | null {
  const model = input.model === undefined ? ratewatchModel(input.env, input.sessionId)?.model ?? null : input.model
  if (!model) return null
  return new ToolLoopAgent({
    model,
    instructions: nplSystemPrompt(input.lang ?? "vi"),
    tools: makeNplTools(input.snapshot),
    stopWhen: isStepCount(6),
  })
}
