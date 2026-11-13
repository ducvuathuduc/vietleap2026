// Deterministic (no-LLM) explanation of an inspected dashboard element from engine output.
// Pure functions only: no fetch, no framework imports — unit-tested with `node --test`.
import type { Insight, ModelsResponse, PipelineSummary, QualityResponse, Recommendation } from "@/lib/api/types"
import type { InsightContext } from "@/lib/insight-target"

/** Lower-case, diacritic-free, alnum tokens joined by single spaces (đ → d). */
export function fold(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
}

/** Column / group names an element refers to: its id, label and the string values in its data. */
export function contextTerms(ctx: InsightContext): string[] {
  const out = new Set<string>()
  const add = (v: unknown) => {
    if (typeof v === "string" && v.length >= 2 && v.length <= 80) out.add(fold(v))
  }
  add(ctx.id)
  add(ctx.label)
  const walk = (v: unknown, depth: number) => {
    if (depth > 4 || v === null || v === undefined) return
    if (typeof v === "string") add(v)
    else if (Array.isArray(v)) v.slice(0, 30).forEach((x) => walk(x, depth + 1))
    else if (typeof v === "object") Object.entries(v as Record<string, unknown>).forEach(([k, x]) => {
      add(k)
      walk(x, depth + 1)
    })
  }
  walk(ctx.data, 0)
  out.delete("")
  return [...out]
}

function insightKeys(i: Insight): string[] {
  const ev = i.evidence ?? {}
  const keys = [...(i.columns ?? []), ev.by, ev.metric, ev.feature, ev.x, ev.y]
  return keys.filter((k): k is string => typeof k === "string").map(fold)
}

/** Insights related to the element, best first. Exact id match wins; then column overlap; ties keep engine rank. */
export function matchInsights(insights: Insight[], ctx: InsightContext, limit = 3): Insight[] {
  const terms = contextTerms(ctx)
  const scored = insights.map((ins) => {
    if (ins.id === ctx.id || String(ins.rank) === ctx.id) return { ins, score: 100 }
    const keys = insightKeys(ins)
    let score = 0
    for (const k of keys) for (const t of terms) if (k && t && (k === t || (k.length >= 4 && t.includes(k)) || (t.length >= 4 && k.includes(t)))) score += k === t ? 2 : 1
    return { ins, score }
  })
  return scored
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score || a.ins.rank - b.ins.rank)
    .slice(0, limit)
    .map((s) => s.ins)
}

export function fmtP(p: number | null): string {
  if (p === null) return "n/a"
  return p < 0.001 ? "p<0,001" : `p=${p.toFixed(3).replace(".", ",")}`
}

function insightLine(i: Insight): string {
  const stats = [i.test, i.p_value !== null ? fmtP(i.p_value) : null, i.effect !== null ? `effect size ${i.effect.toFixed(2)}` : null].filter(Boolean).join(" · ")
  return `• **${i.title_vi}** — ${i.sentence_vi}\n  Kiểm định: ${stats}${i.caveat ? `\n  Lưu ý: ${i.caveat}` : ""}`
}

export interface OfflineSources {
  insights?: { insights: Insight[]; recommendations: Recommendation[] }
  pipeline?: PipelineSummary
  quality?: QualityResponse
  models?: ModelsResponse
}

/** Which engine resources an element kind needs. */
export function sourcesFor(kind: InsightContext["kind"]): (keyof OfflineSources)[] {
  if (kind === "pipeline-stage") return ["pipeline"]
  if (kind === "quality") return ["quality"]
  if (kind === "model") return ["models"]
  return ["insights"]
}

const STAGE_TEXT: Record<string, (p: PipelineSummary) => string> = {
  ingestion: (p) => `Ingestion: ${p.provenance.length} nguồn (${[...new Set(p.provenance.map((s) => s.kind))].join(", ")}), thời gian ${p.timings.ingest ?? "–"} giây. Mỗi nguồn có provenance: thời điểm tải, giấy phép, fingerprint.`,
  storage: (p) => `Storage: ${p.bronze.length} bảng bronze trong DuckDB + Parquet, giữ nguyên dữ liệu thô kèm _src, _ingested_at, _row_hash để audit.`,
  transform: (p) => {
    const q = Object.entries(p.quality).map(([t, s]) => `${t}: ${s.score_before} → ${s.score_after}`).join("; ")
    return `Transform: ${p.silver.length} bảng silver đã làm sạch (missing, duplicate, outlier gắn cờ). Điểm chất lượng trước → sau: ${q}.`
  },
  serving: (p) => `Serving: ${p.gold.length} bảng gold (mô hình ${Object.keys(p.models).join(", ")}). Dashboard dùng ${p.recommended.serving}, trình bày ngữ nghĩa bằng ${p.recommended.semantic}.`,
}

export interface OfflineExplanation {
  output: unknown
  text: string
}

/** Build the deterministic answer. Every number in `text` is copied from the engine output passed in. */
export function explainOffline(ctx: InsightContext, src: OfflineSources): OfflineExplanation {
  const head = `Giải thích “${ctx.label}” (chế độ offline — số liệu lấy nguyên văn từ engine):`
  if (ctx.kind === "pipeline-stage" && src.pipeline) {
    const fn = STAGE_TEXT[ctx.id]
    const p = src.pipeline
    return {
      output: { timings: p.timings, bronze: p.bronze.length, silver: p.silver.length, gold: p.gold.length, quality: p.quality },
      text: `${head}\n\n${fn ? fn(p) : "Không có mô tả cho giai đoạn này."}`,
    }
  }
  if (ctx.kind === "quality" && src.quality) {
    const entries = Object.entries(src.quality).filter(([t]) => ctx.id === "score" || fold(t).includes(fold(ctx.id)) || fold(ctx.id).includes(fold(t)))
    const rows = (entries.length ? entries : Object.entries(src.quality)).slice(0, 5)
    const lines = rows.map(([t, q]) =>
      `• ${t}: điểm ${q.score_before} → ${q.score_after}; ô thiếu ${q.before.missing_cells} → ${q.after.missing_cells}; dòng trùng ${q.before.duplicate_rows} → ${q.after.duplicate_rows}; ${q.cleaning_log.length} bước làm sạch.`
    )
    return {
      output: Object.fromEntries(rows.map(([t, q]) => [t, { score_before: q.score_before, score_after: q.score_after }])),
      text: `${head}\n\n${lines.join("\n")}\n\nOutlier chỉ được gắn cờ (3×IQR), không xoá.`,
    }
  }
  if (ctx.kind === "model" && src.models) {
    const key = ctx.id as keyof ModelsResponse["models"]
    const info = src.models.models[key]
    const rationale = src.models.rationale[key]
    return {
      output: { tables: info?.tables ?? [], rationale, recommended: src.models.recommended },
      text: info
        ? `${head}\n\n${rationale ?? ""}\n\nBảng gold: ${info.tables.join(", ")}.${src.models.recommended.serving === key ? " Đây là mô hình khuyến nghị cho dashboard." : ""}${src.models.recommended.semantic === key ? " Đây là mô hình khuyến nghị để trình bày mô hình dữ liệu." : ""}`
        : `${head}\n\nMô hình “${ctx.id}” chưa được dựng cho dataset này.`,
    }
  }
  const all = src.insights?.insights ?? []
  const matched = matchInsights(all, ctx)
  const recs = src.insights?.recommendations ?? []
  const rec = matched.length ? recs.find((r) => r.from_insight === matched[0].id) : undefined
  const body = matched.length
    ? matched.map(insightLine).join("\n")
    : all.length
      ? `Không có insight nào gắn trực tiếp với phần tử này. Insight mạnh nhất của dataset:\n${insightLine(all[0])}`
      : "Engine chưa tạo insight nào cho dataset này."
  return {
    output: { matched: matched.map((i) => ({ id: i.id, rank: i.rank, test: i.test, p_value: i.p_value, effect: i.effect })) },
    text: `${head}\n\n${body}${rec ? `\n\nKhuyến nghị liên quan (${rec.confidence === "high" ? "tin cậy cao" : "tin cậy trung bình"}): ${rec.now_what_vi}` : ""}\n\nĐây là quan hệ liên đới, không chứng minh nhân quả.`,
  }
}
