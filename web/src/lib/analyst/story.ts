// "Auto-insight story": a narrated walkthrough of the top insights, one driver.js step per insight card.
// Pure functions only (no fetch / framework imports) — unit-tested with `node --test`.
// Numbers are never invented: the offline story copies engine sentences verbatim, and an LLM narration is kept
// only if every number in it also appears in that insight's engine output (`ungroundedNumbers`).
import type { Insight, Recommendation } from "@/lib/api/types"

export interface StoryStep {
  id: string
  rank: number
  title: string
  /** 1–3 sentences told to the audience */
  narration: string
  /** test · p · effect line, always from the engine */
  stats: string
  /** recommended action from the engine, if any */
  action: string | null
  /** "llm" when the narration came from the model and passed the number check, else "engine" */
  source: "llm" | "engine"
}

export interface Story {
  mode: "llm" | "offline"
  model: string | null
  headline: string
  steps: StoryStep[]
  closing: string
}

export const STORY_SIZE = 5

function fmtNum(x: number, digits = 2): string {
  return x.toFixed(digits).replace(".", ",")
}

export function statsLine(i: Insight): string {
  const p = i.p_value === null ? null : i.p_value < 0.001 ? "p<0,001" : `p=${fmtNum(i.p_value, 3)}`
  const n = typeof i.evidence?.n === "number" ? `n=${(i.evidence.n as number).toLocaleString("vi-VN")}` : null
  return [i.test, p, i.effect !== null ? `effect size ${fmtNum(i.effect)}` : null, n].filter(Boolean).join(" · ")
}

/** Top-n insights by engine rank (ties keep order). */
export function pickInsights(insights: Insight[], n = STORY_SIZE): Insight[] {
  return [...insights].sort((a, b) => a.rank - b.rank).slice(0, n)
}

const CAUSAL_NOTE = "Đây là quan hệ liên đới từ dữ liệu quan sát, không chứng minh nhân quả."

/** Deterministic story: every sentence is engine output. */
export function offlineStory(insights: Insight[], recs: Recommendation[], datasetName: string, n = STORY_SIZE): Story {
  const top = pickInsights(insights, n)
  const recBy = new Map(recs.map((r) => [r.from_insight, r]))
  const steps = top.map<StoryStep>((i) => ({
    id: i.id,
    rank: i.rank,
    title: i.title_vi,
    narration: i.sentence_vi,
    stats: statsLine(i),
    action: recBy.get(i.id)?.now_what_vi ?? null,
    source: "engine",
  }))
  const first = recs.find((r) => top.some((i) => i.id === r.from_insight))
  return {
    mode: "offline",
    model: null,
    headline: top.length
      ? `${top.length} phát hiện mạnh nhất trong dữ liệu “${datasetName}”, xếp theo độ lớn hiệu ứng × ý nghĩa thống kê × mức liên quan.`
      : `Engine chưa tìm thấy insight có ý nghĩa thống kê cho “${datasetName}”.`,
    steps,
    closing: `${first ? `Khuyến nghị ưu tiên: ${first.now_what_vi} ` : ""}${CAUSAL_NOTE}`,
  }
}

/** Numeric values a token like "1.234,5" / "60,3" / "2.104" could mean (VN and EN separators). */
export function numberCandidates(token: string): number[] {
  const out = new Set<number>()
  const plain = token.replace(/[.,]/g, "")
  out.add(Number(plain))
  if (/^\d+([.,]\d+)$/.test(token)) out.add(Number(token.replace(",", "."))) // single separator = decimal
  const lastSep = Math.max(token.lastIndexOf("."), token.lastIndexOf(","))
  if (lastSep > 0) out.add(Number(token.slice(0, lastSep).replace(/[.,]/g, "") + "." + token.slice(lastSep + 1)))
  return [...out].filter((x) => Number.isFinite(x))
}

const NUM_RE = /\d+(?:[.,]\d+)*/g

export function numbersIn(text: string): string[] {
  return text.match(NUM_RE) ?? []
}

/** All numbers an insight's engine output contains: its sentences, stats, evidence and recommendation. */
export function groundTruthNumbers(i: Insight, rec?: Recommendation | null): number[] {
  const vals: number[] = []
  const walk = (v: unknown, depth: number) => {
    if (depth > 5 || v === null || v === undefined) return
    if (typeof v === "number" && Number.isFinite(v)) vals.push(v)
    else if (typeof v === "string") numbersIn(v).forEach((t) => vals.push(...numberCandidates(t)))
    else if (Array.isArray(v)) v.slice(0, 50).forEach((x) => walk(x, depth + 1))
    else if (typeof v === "object") Object.entries(v as Record<string, unknown>).forEach(([k, x]) => {
      walk(k, depth + 1)
      walk(x, depth + 1)
    })
  }
  walk([i.sentence_vi, i.sentence_en, i.title_vi, i.title_en, i.test, i.p_value, i.effect, i.value, i.evidence, statsLine(i)], 0)
  if (rec) walk([rec.so_what_vi, rec.now_what_vi, rec.impact_vi, rec.so_what_en, rec.now_what_en, rec.impact_en], 0)
  return vals
}

function close(a: number, b: number): boolean {
  if (a === b) return true
  const scale = Math.max(Math.abs(a), Math.abs(b))
  return Math.abs(a - b) <= Math.max(0.006, scale * 0.006)
}

/** Number tokens in `text` that match no engine value (small counts ≤ 10 are allowed: "3 nhóm", "top 5"). */
export function ungroundedNumbers(text: string, truth: number[]): string[] {
  return numbersIn(text).filter((tok) => {
    const cands = numberCandidates(tok)
    if (cands.some((c) => Number.isInteger(c) && c >= 0 && c <= 10)) return false
    // "127 triệu" ↔ 126840491: also accept the value expressed in thousands / millions / billions
    return !cands.some((c) => truth.some((t) => close(c, t) || [1e3, 1e6, 1e9].some((u) => close(c, t / u) || close(c, Math.round(t / u)))))
  })
}

export interface LlmStoryDraft {
  headline?: string
  steps?: { id: string; narration: string }[]
  closing?: string
}

/** Parse the first JSON object in a model reply (tolerates ```json fences and chatter). */
export function parseDraft(text: string): LlmStoryDraft | null {
  const start = text.indexOf("{")
  const end = text.lastIndexOf("}")
  if (start < 0 || end <= start) return null
  try {
    const obj = JSON.parse(text.slice(start, end + 1)) as unknown
    if (typeof obj !== "object" || obj === null) return null
    const o = obj as Record<string, unknown>
    const steps = Array.isArray(o.steps)
      ? o.steps.filter((s): s is { id: string; narration: string } => typeof s === "object" && s !== null && typeof (s as { id?: unknown }).id === "string" && typeof (s as { narration?: unknown }).narration === "string")
      : undefined
    return {
      headline: typeof o.headline === "string" ? o.headline : undefined,
      steps,
      closing: typeof o.closing === "string" ? o.closing : undefined,
    }
  } catch {
    return null
  }
}

const MAX_NARRATION = 420

/**
 * Merge a model draft onto the offline story. A narration/headline/closing replaces the engine text only when
 * it is non-empty, not too long and every number in it is grounded in the engine output; otherwise the engine
 * text stays. The ordering, titles, stats and actions always come from the engine.
 */
export function mergeDraft(base: Story, draft: LlmStoryDraft | null, insights: Insight[], recs: Recommendation[], model: string): Story {
  if (!draft) return base
  const byId = new Map(insights.map((i) => [i.id, i]))
  const recBy = new Map(recs.map((r) => [r.from_insight, r]))
  const allTruth = base.steps.flatMap((s) => {
    const i = byId.get(s.id)
    return i ? groundTruthNumbers(i, recBy.get(s.id)) : []
  })
  const ok = (text: string | undefined, truth: number[]) =>
    typeof text === "string" && text.trim().length > 0 && text.length <= MAX_NARRATION && ungroundedNumbers(text, truth).length === 0
  const drafted = new Map((draft.steps ?? []).map((s) => [s.id, s.narration.trim()]))
  const steps = base.steps.map((s) => {
    const i = byId.get(s.id)
    const text = drafted.get(s.id)
    if (i && ok(text, groundTruthNumbers(i, recBy.get(s.id)))) return { ...s, narration: text as string, source: "llm" as const }
    return s
  })
  const used = steps.some((s) => s.source === "llm")
  return {
    ...base,
    mode: used ? "llm" : base.mode,
    model: used ? model : null,
    headline: ok(draft.headline, allTruth) ? (draft.headline as string).trim() : base.headline,
    closing: ok(draft.closing, allTruth) ? `${(draft.closing as string).trim()} ${CAUSAL_NOTE}` : base.closing,
    steps,
  }
}

/** Prompt for the model: only the engine facts it may use. */
export function storyPrompt(insights: Insight[], recs: Recommendation[], datasetName: string): string {
  const recBy = new Map(recs.map((r) => [r.from_insight, r]))
  const facts = insights.map((i) => ({
    id: i.id,
    rank: i.rank,
    title: i.title_vi,
    finding: i.sentence_vi,
    stats: statsLine(i),
    action: recBy.get(i.id)?.now_what_vi ?? null,
    impact: recBy.get(i.id)?.impact_vi ?? null,
  }))
  return [
    `Bạn là người dẫn chuyện dữ liệu cho bài pitch hackathon "From Data to Decision". Dataset: "${datasetName}".`,
    "Viết một câu chuyện ngắn bằng tiếng Việt có dấu cho các insight dưới đây, theo đúng thứ tự.",
    "Quy tắc bắt buộc:",
    "- Chỉ dùng con số xuất hiện nguyên văn trong FACTS; không làm tròn khác đi, không thêm số mới.",
    "- Mỗi narration 1–3 câu, ≤ 350 ký tự: nói phát hiện + vì sao người ra quyết định nên quan tâm. Nối mạch giữa các insight.",
    "- Không khẳng định nhân quả; dùng 'liên quan', 'đi kèm'.",
    '- Trả về DUY NHẤT một JSON: {"headline": string, "steps": [{"id": string, "narration": string}], "closing": string}.',
    "",
    `FACTS = ${JSON.stringify(facts)}`,
  ].join("\n")
}

/** Escape text for driver.js popovers (they render description as HTML). */
export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string)
}

/** CSS selector of the element a story step highlights. */
export function stepSelector(id: string, kind: "insight" | "table-row" = "insight"): string {
  return `[data-insight-target="${kind}:${id.replace(/["\\]/g, "\\$&")}"]`
}
