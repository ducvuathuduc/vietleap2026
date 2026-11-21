import type { UIMessage, UIMessageChunk } from "ai"

import { filterInput, numberCandidates, UNGROUNDED_MARK, type GuardResult } from "../../llm/guards.ts"
import type { Lang } from "./lang.ts"

const INVESTMENT_REQUEST = /\b(?:should (?:i|we|one) (?:buy|sell|invest)|would you (?:buy|sell|invest)|(?:recommend|suggest)\b.{0,35}\b(?:buy(?:ing)?|sell(?:ing)?|invest(?:ing)?)|(?:buy|sell) or (?:buy|sell)|(?:buy|sell|invest)\b.{0,40}\b(?:stock|shares?)|co nen (?:mua|ban|dau tu)|nen (?:mua|ban|dau tu)|khuyen nghi (?:mua|ban|dau tu)|(?:mua|ban) co phieu)\b/i
const DIRECT_TRADE = /^(?:please |hãy |hay )?(?:[Bb]uy|[Ss]ell|[Mm]ua|[Bb]án|[Bb]an)\s+[A-Z]{2,5}\b/

export function investmentAdviceNotice(question: string, lang: Lang): string | null {
  const plain = question.normalize("NFD").replace(/\p{M}/gu, "").replace(/[đĐ]/g, "d").trim()
  if (!INVESTMENT_REQUEST.test(plain) && !DIRECT_TRADE.test(question.trim())) return null
  return lang === "vi"
    ? "Tôi không thể đưa ra khuyến nghị đầu tư. Tôi có thể dùng bộ giải mã để kiểm tra mức giảm nợ xấu có cơ sở hay không. Bạn muốn xem ngân hàng và quý nào?"
    : "I can’t provide investment advice. I can run the decoder check to see whether an NPL decline is supported. Which bank and quarter would you like to examine?"
}

interface HistoryMessage {
  id: string
  role: "user" | "assistant"
  parts: readonly unknown[]
}

export function nplMessageText(parts: readonly unknown[]): string {
  return parts.flatMap((part) => {
    if (typeof part !== "object" || part === null || !("type" in part) || part.type !== "text") return []
    return "text" in part && typeof part.text === "string" ? [part.text] : []
  }).join(" ").trim()
}

export function messagesForNplModel(messages: readonly HistoryMessage[]): UIMessage[] {
  return messages.flatMap(({ id, role, parts }) => {
    const text = nplMessageText(parts)
    return text && filterInput(text).ok ? [{ id, role, parts: [{ type: "text", text }] }] : []
  })
}

const NUMBER = /(?:((?<![\dQ])[-+−]))?(\d+(?:[.,\u00A0\u202F]\d+)*)/gu
const FALL_BEFORE = /(?:\b(?:fell|falls?|declin(?:e|ed)|dropp?ed|drop|decreas(?:e|ed)|lower|down)\s+(?:(?:by|of)\s+)?(?:(?:about|around)\s+)?|(?:giảm|thấp hơn|ít hơn)\s+(?:(?:quý\s+[1-4]|NPL|tỷ lệ nợ xấu)\s+)?(?:(?:khoảng|là)\s+)?)$/iu
const FALL_AFTER = /^(?:\s*(?:percentage points?|pp|điểm (?:phần trăm|%)|%))?\s+(?:lower|less|below|thấp hơn|ít hơn)\b/iu

function numericSign(sign: string | undefined): number {
  return sign === "-" || sign === "−" ? -1 : 1
}

function candidates(magnitude: string): number[] {
  const values = numberCandidates(magnitude)
  const grouping = /^[1-9]\d{0,2}(?:[.,\u00A0\u202F]\d{3})+$/.test(magnitude)
  if (grouping || !/[.,]/.test(magnitude)) return values
  const withoutSeparators = Number(magnitude.replace(/[.,\u00A0\u202F]/g, ""))
  return values.filter((value) => value !== withoutSeparators)
}

function collectNplTruth(outputs: unknown[]): number[] {
  const values = new Set<number>()
  function visit(value: unknown): void {
    if (typeof value === "number" && Number.isFinite(value)) values.add(value)
    else if (typeof value === "string") {
      for (const [, sign, magnitude] of value.matchAll(NUMBER)) {
        candidates(magnitude).forEach((candidate) => values.add(numericSign(sign) * candidate))
      }
    } else if (Array.isArray(value)) value.forEach(visit)
    else if (value !== null && typeof value === "object") {
      const record = value as Record<string, unknown>
      const ci95 = record.ci95
      if (Array.isArray(ci95) && ci95.length === 2 && ci95.every((bound) => typeof bound === "number")) values.add(95)
      if (typeof record.lo80 === "number" && typeof record.hi80 === "number") values.add(80)
      Object.values(record).forEach(visit)
    }
  }
  outputs.forEach(visit)
  return [...values]
}

export function guardNplAnswer(text: string, outputs: unknown[]): GuardResult {
  const truth = collectNplTruth(outputs)
  const flagged: string[] = []
  const result = text.replace(NUMBER, (token: string, sign: string | undefined, magnitude: string, offset: number) => {
    const direction = numericSign(sign)
    const lastSeparator = Math.max(magnitude.lastIndexOf("."), magnitude.lastIndexOf(","))
    const falling = sign === undefined && (
      FALL_BEFORE.test(text.slice(Math.max(0, offset - 32), offset).replace(/(?:\*\*|__)+$/, ""))
      || FALL_AFTER.test(text.slice(offset + token.length).replace(/^(?:\*\*|__)+/, ""))
    )
    const grounded = candidates(magnitude).some((candidate) => {
      const signed = direction * candidate
      const digits = lastSeparator >= 0 ? magnitude.length - lastSeparator - 1 : 0
      const tolerance = digits > 0 ? 0.5 * 10 ** -digits : 0
      return truth.some((value) => Math.abs(signed - value) <= tolerance || (falling && Math.abs(signed + value) <= tolerance))
    })
    if (grounded) return token
    flagged.push(token)
    return UNGROUNDED_MARK
  })
  return { text: result, flagged }
}

/** Buffer each text part until its signed numbers can be checked against this turn's tool results. */
export function guardNplStream(lang: Lang = "vi"): TransformStream<UIMessageChunk, UIMessageChunk> {
  const outputs: unknown[] = []
  const buffered = new Map<string, string>()
  const flagged = new Set<string>()
  return new TransformStream({
    transform(chunk, controller) {
      switch (chunk.type) {
        case "tool-output-available":
          outputs.push(chunk.output)
          break
        case "text-start":
          buffered.set(chunk.id, "")
          break
        case "text-delta":
          buffered.set(chunk.id, (buffered.get(chunk.id) ?? "") + chunk.delta)
          return
        case "text-end": {
          const guarded = guardNplAnswer(buffered.get(chunk.id) ?? "", outputs)
          guarded.flagged.forEach((token) => flagged.add(token))
          const delta = lang === "vi" ? guarded.text : guarded.text.replaceAll(UNGROUNDED_MARK, "[unverified]")
          controller.enqueue({ type: "text-delta", id: chunk.id, delta })
          buffered.delete(chunk.id)
          break
        }
        case "finish":
          if (flagged.size) controller.enqueue({ type: "data-guard", id: "guard", data: { flagged: [...flagged] } })
          break
      }
      controller.enqueue(chunk)
    },
  })
}
