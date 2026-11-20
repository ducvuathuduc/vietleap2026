// Guards for the NPL assistant.
// Input: reject prompts that carry personal data (Vietnamese citizen ID, phone
// numbers, bank account numbers, emails) with a polite VI/EN notice — private
// data must never enter a prompt, a trace or a log (JUDGE.md section 4).
// Output: every number in the final text must match a value a tool returned;
// anything else is replaced by "[chưa kiểm chứng]" and the answer is flagged.
// Tolerant to VI/EN formatting: "6,3" and "6.3" are the same value, "1,2 tỷ"
// matches 1 200 000 000, "350 triệu" matches 350000000.

export type PiiKind = "email" | "phone" | "id" | "account"

export interface PiiHit {
  kind: PiiKind
  match: string
}

const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g
const DIGIT_RUN_RE = /\+84\d{8,11}|\d{8,19}/g

function classifyDigitRun(run: string): PiiKind | null {
  if (run.startsWith("+84")) return "phone"
  if (run.startsWith("0") && (run.length === 10 || run.length === 11)) return "phone"
  if (run.length === 9 || run.length === 12) return "id"
  return "account"
}

/** Personal-data hits in free text: emails, phones, citizen IDs, account numbers. */
export function findPii(text: string): PiiHit[] {
  const hits: PiiHit[] = []
  for (const match of text.matchAll(EMAIL_RE)) hits.push({ kind: "email", match: match[0] })
  for (const match of text.matchAll(DIGIT_RUN_RE)) {
    const kind = classifyDigitRun(match[0])
    if (kind) hits.push({ kind, match: match[0] })
  }
  return hits
}

export interface FilterResult {
  ok: boolean
  kinds: PiiKind[]
  notice_vi: string
  notice_en: string
}

const KIND_VI: Record<PiiKind, string> = {
  email: "email",
  phone: "số điện thoại",
  id: "số CCCD/CMND",
  account: "số tài khoản",
}

/** Reject a user prompt that carries personal data; the notice names kinds, never values. */
export function filterInput(text: string): FilterResult {
  const kinds = [...new Set(findPii(text).map((hit) => hit.kind))]
  if (kinds.length === 0) return { ok: true, kinds: [], notice_vi: "", notice_en: "" }
  const listVi = kinds.map((kind) => KIND_VI[kind]).join(", ")
  return {
    ok: false,
    kinds,
    notice_vi: `Bạn vui lòng xoá thông tin cá nhân (${listVi}) rồi hỏi lại. Trợ lý chỉ cần số tiền, kỳ hạn và ngân hàng — không cần và không lưu bất kỳ thông tin cá nhân nào.`,
    notice_en: `Please remove the personal data (${kinds.join(", ")}) and ask again. The assistant only needs the amount, the term and the bank — it never asks for or stores personal information.`,
  }
}

/** Numeric values a token like "1.234,5" / "60,3" / "2.104" could mean (VN and EN separators). */
export function numberCandidates(token: string): number[] {
  const out = new Set<number>()
  const plain = token.replace(/[.,\u00A0\u202F]/g, "")
  out.add(Number(plain))
  if (/^\d+([.,]\d+)$/.test(token)) out.add(Number(token.replace(",", ".")))
  const lastSep = Math.max(token.lastIndexOf("."), token.lastIndexOf(","))
  if (lastSep > 0) out.add(Number(token.slice(0, lastSep).replace(/[.,]/g, "") + "." + token.slice(lastSep + 1)))
  return [...out].filter((x) => Number.isFinite(x))
}

// Grouping separators: ".", "," and the NBSP/narrow-NBSP some models emit
// ("332 068 311"). An ASCII space stays a boundary between two numbers.
const NUM_RE = /\d+(?:[.,\u00A0\u202F]\d+)*/g

export function numbersIn(text: string): string[] {
  return text.match(NUM_RE) ?? []
}

function close(a: number, b: number): boolean {
  if (a === b) return true
  const scale = Math.max(Math.abs(a), Math.abs(b))
  return Math.abs(a - b) <= Math.max(0.006, scale * 0.006)
}

// \b after a non-ASCII letter ("tỷ") never matches in JS, so the Vietnamese
// units use no word boundary; tr/k end in ASCII and keep it.
const UNIT_SCALE: [RegExp, number][] = [
  [/\s*tỷ/i, 1e9],
  [/\s*triệu/i, 1e6],
  [/\s*nghìn/i, 1e3],
  [/\s*tr\b/i, 1e6],
  [/\s*k\b/i, 1e3],
  [/\s*billion\b/i, 1e9],
  [/\s*million\b/i, 1e6],
  [/\s*thousand\b/i, 1e3],
]

function tokenGrounded(token: string, suffix: string, truth: number[]): boolean {
  const cands = numberCandidates(token)
  if (cands.some((c) => Number.isInteger(c) && c >= 0 && c <= 10)) return true
  for (const [unit, scale] of UNIT_SCALE) {
    if (!suffix.match(unit)) continue
    if (cands.some((c) => truth.some((t) => close(c * scale, t)))) return true
  }
  return cands.some((c) => truth.some((t) => close(c, t)))
}

export interface GuardResult {
  text: string
  flagged: string[]
}

/** Replace every number that matches no tool value with "[chưa kiểm chứng]" and list them. */
export function guardNumbers(text: string, truth: number[]): GuardResult {
  const negatedTruth = truth.map((t) => -t)
  const flagged: string[] = []
  const out = text.replace(NUM_RE, (token, offset: number) => {
    const rest = text.slice(offset + token.length, offset + token.length + 12)
    // A token right after a minus/dash may be a negative value: test both signs.
    const pool = offset > 0 && /[-−–]/.test(text[offset - 1] ?? "") ? [...truth, ...negatedTruth] : truth
    if (tokenGrounded(token, rest, pool)) return token
    flagged.push(token)
    return "[chưa kiểm chứng]"
  })
  return { text: out, flagged }
}

/** Every numeric value in tool outputs (numbers, and numbers inside strings such as dates). */
export function collectTruthNumbers(toolOutputs: unknown[]): number[] {
  const vals: number[] = []
  let hasCi = false
  const walk = (v: unknown, depth: number) => {
    if (depth > 6 || v === null || v === undefined) return
    if (typeof v === "number" && Number.isFinite(v)) vals.push(v)
    else if (typeof v === "string") numbersIn(v).forEach((token) => vals.push(...numberCandidates(token)))
    else if (Array.isArray(v)) v.slice(0, 250).forEach((x) => walk(x, depth + 1))
    else if (typeof v === "object") {
      if ("ci95" in v || "lo80" in v) hasCi = true
      Object.values(v as Record<string, unknown>).forEach((x) => walk(x, depth + 1))
    }
  }
  walk(toolOutputs, 0)
  // A tool that returns an interval lets the answer state the interval level.
  if (hasCi) vals.push(95, 80)
  return vals
}

export const UNGROUNDED_MARK = "[chưa kiểm chứng]"

/** Deep-copy a span payload with every PII-looking substring replaced by "[redacted]". */
export function redactPii(value: unknown, depth = 0): unknown {
  if (depth > 6 || value === null || value === undefined) return value
  if (typeof value === "string") {
    let out = value.replace(EMAIL_RE, "[redacted]")
    out = out.replace(DIGIT_RUN_RE, (run) => (classifyDigitRun(run) ? "[redacted]" : run))
    return out
  }
  // 8-19 digit numbers are account/ID-sized: amounts and identifiers never export.
  if (typeof value === "number" && Number.isFinite(value) && Math.abs(value) >= 1e7 && Math.abs(value) < 1e19) {
    return "[redacted]"
  }
  if (Array.isArray(value)) return value.slice(0, 250).map((item) => redactPii(item, depth + 1))
  if (typeof value === "object") {
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) out[key] = redactPii(item, depth + 1)
    return out
  }
  return value
}

/**
 * UI-message-stream transform for the chat route: tool-output parts are passed
 * through and their values join the truth set; text parts are buffered and
 * emitted guarded at text-end; a data-guard part follows the finish when
 * anything was replaced.
 */
export function guardTextStream(): TransformStream<Record<string, unknown>, Record<string, unknown>> {
  type Buffer = { start: Record<string, unknown>; deltas: string[] }
  let buffer: Buffer | null = null
  let truth: number[] = []
  const flagged: string[] = []
  return new TransformStream({
    transform(chunk, controller) {
      const type = chunk.type
      if (type === "tool-output-available") {
        truth = truth.concat(collectTruthNumbers([chunk.output]))
        controller.enqueue(chunk)
        return
      }
      if (type === "text-start") {
        buffer = { start: chunk, deltas: [] }
        return
      }
      if (type === "text-delta") {
        if (buffer) buffer.deltas.push(String(chunk.delta ?? ""))
        else controller.enqueue(chunk)
        return
      }
      if (type === "text-end") {
        if (!buffer) {
          controller.enqueue(chunk)
          return
        }
        const guarded = guardNumbers(buffer.deltas.join(""), truth)
        flagged.push(...guarded.flagged)
        controller.enqueue(buffer.start)
        const id = (buffer.start as { id?: string }).id ?? "text"
        controller.enqueue({ type: "text-delta", id, delta: guarded.text })
        controller.enqueue(chunk)
        buffer = null
        return
      }
      if (type === "finish") {
        if (flagged.length > 0) {
          controller.enqueue({ type: "data-guard", id: "guard", data: { flagged: [...new Set(flagged)] } })
        }
        controller.enqueue(chunk)
        return
      }
      controller.enqueue(chunk)
    },
    flush(controller) {
      if (buffer) {
        const guarded = guardNumbers(buffer.deltas.join(""), truth)
        flagged.push(...guarded.flagged)
        controller.enqueue(buffer.start)
        const id = (buffer.start as { id?: string }).id ?? "text"
        controller.enqueue({ type: "text-delta", id, delta: guarded.text })
        controller.enqueue({ type: "text-end", id })
        buffer = null
      }
      if (flagged.length > 0) {
        controller.enqueue({ type: "data-guard", id: "guard", data: { flagged: [...new Set(flagged)] } })
      }
    },
  })
}
