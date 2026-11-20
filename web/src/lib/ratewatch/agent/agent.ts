// The RateWatch assistant: an AI SDK v7 ToolLoopAgent that may only speak
// numbers returned by the deterministic snapshot tools. Six steps maximum;
// the system prompt is the judge contract (tools only, sheet dates, break-even
// is a calculation, no investment advice, no personal data).
import { isStepCount, ToolLoopAgent, type LanguageModel } from "ai"

import type { Snapshot } from "../types.ts"
import { makeRatewatchTools, TOOL_NAMES } from "./tools.ts"
import { ratewatchModel } from "./model.ts"

export { TOOL_NAMES }

export function ratewatchSystemPrompt(): string {
  return [
    "Bạn là trợ lý lãi suất tiền gửi cho một hộ gia đình (RateWatch VN).",
    "Quy tắc số: chỉ trả lời bằng các số do tool trả về. Không tự nghĩ ra, không ước lượng, không dự báo.",
    "Mỗi con số phải kèm tên ngân hàng, kỳ hạn (tháng), kênh (quầy/online) và ngày biểu (sheet date).",
    "Break-even là phép tính, không phải dự báo — luôn ghi rõ điều đó. The break-even is a calculation, not a forecast.",
    "Chỉ so sánh lãi suất tiền gửi; không dùng từ ngữ tư vấn đầu tư (mua/bán/chứng khoán). Không khuyên mua hay bán bất kỳ sản phẩm nào.",
    "Không bao giờ hỏi hay nhắc lại họ tên, số CCCD/CMND, số điện thoại, số tài khoản, email. Nếu người dùng đưa vào, bỏ qua và không nhắc lại.",
    "Trả lời tiếng Việt có dấu, ngắn gọn; nếu người dùng hỏi bằng tiếng Anh thì trả lời tiếng Anh.",
    "Khi tool trả lỗi (ngân hàng không có trong snapshot, dòng contested, thiếu dữ liệu) thì nói đúng điều đó, không bịa số thay thế.",
    "Answer only with numbers returned by tools; name the bank, term, channel and sheet date; no investment advice; never repeat personal data.",
  ].join("\n")
}

export function makeRatewatchAgent(input: {
  snapshot: Snapshot
  /** Defaults to the provider chosen from env; an explicit null forces offline. */
  model?: LanguageModel | null
  env?: NodeJS.ProcessEnv
  /** Chat session id: sent as the gateway langfuse-session-id header. */
  sessionId?: string | null
}): ToolLoopAgent | null {
  const model =
    input.model === undefined ? ratewatchModel(input.env, input.sessionId)?.model ?? null : input.model
  if (!model) return null
  return new ToolLoopAgent({
    model,
    instructions: ratewatchSystemPrompt(),
    tools: makeRatewatchTools(input.snapshot),
    stopWhen: isStepCount(6),
  })
}
