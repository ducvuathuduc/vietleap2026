import fs from "node:fs"
import path from "node:path"
import type { Brief, BriefPack } from "@/lib/api/types"
import { asciiKey, repoRoot } from "./vn"

interface RawPack extends BriefPack {
  domain: string
  keywords: string[]
}

function unquote(s: string): string {
  const t = s.trim()
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1).replace(/\\"/g, '"')
  }
  return t
}

/** Lightweight parser for scenarios/packs/*.yaml without adding external yaml deps. */
function parsePackYaml(text: string): RawPack {
  const lines = text.split(/\r?\n/)
  const out: Record<string, unknown> = {
    kpis: [],
    recipe: [],
    deck_storyline: [],
    expected_columns: [],
    keywords: [],
    decision_template: { who: "", what: "", where: "", kpi: "", caveat: "" },
  }
  let curKey: string | null = null
  let inDecision = false

  for (const raw of lines) {
    if (!raw.trim() || raw.trim().startsWith("#")) continue
    const indent = raw.search(/\S/)
    const trimmed = raw.trim()

    if (indent === 0) {
      inDecision = false
      const colon = trimmed.indexOf(":")
      if (colon < 0) continue
      const k = trimmed.slice(0, colon).trim()
      const rest = trimmed.slice(colon + 1).trim()
      curKey = k
      if (k === "decision_template") {
        inDecision = true
      } else if (rest.startsWith("[") && rest.endsWith("]")) {
        out[k] = rest
          .slice(1, -1)
          .split(",")
          .map((x) => unquote(x))
          .filter(Boolean)
      } else if (rest) {
        out[k] = unquote(rest)
      } else if (!out[k]) {
        out[k] = []
      }
    } else if (inDecision && trimmed.includes(":")) {
      const colon = trimmed.indexOf(":")
      const subk = trimmed.slice(0, colon).trim()
      const subv = unquote(trimmed.slice(colon + 1))
      ;(out.decision_template as Record<string, string>)[subk] = subv
    } else if (trimmed.startsWith("- ") && curKey && Array.isArray(out[curKey])) {
      ;(out[curKey] as string[]).push(unquote(trimmed.slice(2)))
    }
  }

  return {
    id: String(out.id ?? ""),
    title: String(out.title ?? ""),
    sponsor: String(out.sponsor ?? ""),
    domain: String(out.domain ?? "generic"),
    keywords: (out.keywords as string[]) ?? [],
    kpis: (out.kpis as string[]) ?? [],
    recipe: (out.recipe as string[]) ?? [],
    decision_template: out.decision_template as BriefPack["decision_template"],
    deck_storyline: (out.deck_storyline as string[]) ?? [],
    expected_columns: (out.expected_columns as string[]) ?? [],
  }
}

let _packsCache: RawPack[] | null = null

export function loadPacks(): RawPack[] {
  if (_packsCache) return _packsCache
  const dir = path.join(repoRoot(), "scenarios", "packs")
  if (!fs.existsSync(dir)) return []
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".yaml")).sort()
  _packsCache = files.map((f) => parsePackYaml(fs.readFileSync(path.join(dir, f), "utf-8")))
  return _packsCache
}

export function loadBriefSamples(): { name: string; text: string }[] {
  const dir = path.join(repoRoot(), "scenarios", "briefs")
  if (!fs.existsSync(dir)) return []
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md") && f !== "README.md")
    .sort()
    .map((f) => ({
      name: f.replace(/\.md$/, ""),
      text: fs
        .readFileSync(path.join(dir, f), "utf-8")
        .replace(/<!--[\s\S]*?-->\s*/g, "")
        .trim(),
    }))
}

interface ConceptDef {
  id: string
  label: string
  phrases: string[]
  domain: string
  columns: string[]
  derived?: string
}

const CONCEPTS: ConceptDef[] = [
  { id: "price_per_m2", label: "Giá/m²", phrases: ["gia m2", "gia tren m2", "gia moi m2", "don gia", "price per m2", "price m2"], domain: "property", columns: ["price_per_m2"], derived: "price_per_m2" },
  { id: "rent", label: "Giá thuê", phrases: ["gia thue", "tien thue", "rent", "rental"], domain: "property", columns: ["gia_thue", "rent"] },
  { id: "house_price", label: "Giá bán", phrases: ["gia ban", "gia nha", "house price", "sale price"], domain: "property", columns: ["gia_ban", "price"] },
  { id: "household_income", label: "Thu nhập hộ", phrases: ["thu nhap ho", "household income"], domain: "property", columns: ["thu_nhap_ho", "income"] },
  { id: "roe", label: "ROE", phrases: ["roe", "loi nhuan tren von chu", "return on equity"], domain: "firm", columns: ["roe_pct", "roe"], derived: "roe_pct" },
  { id: "tax_revenue", label: "Thu thuế (% GDP)", phrases: ["thu thue", "nguon thu thue", "tax revenue", "tax to gdp"], domain: "public_finance", columns: ["tax_revenue_pct_gdp", "tax_revenue", "tax"] },
  { id: "gov_revenue", label: "Thu ngân sách", phrases: ["thu ngan sach", "thu nsnn", "government revenue", "revenue pct gdp"], domain: "public_finance", columns: ["revenue_pct_gdp", "budget_revenue", "revenue"] },
  { id: "budget_transfers", label: "Bổ sung có mục tiêu", phrases: ["bo sung", "ngan sach bo sung", "earmarked", "transfer"], domain: "public_finance", columns: ["earmarked_transfers", "budget_transfers"] },
  { id: "public_debt", label: "Nợ công", phrases: ["no cong", "no chinh phu", "public debt", "government debt"], domain: "public_finance", columns: ["central_gov_debt_pct_gdp", "debt"] },
  { id: "gdp_per_capita", label: "GDP/người", phrases: ["gdp binh quan", "gdp dau nguoi", "gdp per capita"], domain: "public_finance", columns: ["gdp_per_capita_usd", "gdp_per_capita"] },
  { id: "gdp_growth", label: "Tăng trưởng GDP", phrases: ["tang truong gdp", "tang truong kinh te", "gdp growth"], domain: "public_finance", columns: ["gdp_growth_pct", "gdp_growth"] },
  { id: "inflation", label: "Lạm phát", phrases: ["lam phat", "cpi", "inflation"], domain: "public_finance", columns: ["inflation_pct", "inflation"] },
  { id: "fdi", label: "FDI", phrases: ["fdi", "von dau tu nuoc ngoai", "foreign direct investment"], domain: "public_finance", columns: ["fdi_inflow_pct_gdp", "fdi"] },
]

const UNITS: Record<string, string[]> = {
  province: ["tinh", "tinh thanh", "dia phuong", "province"],
  district: ["quan huyen", "cap huyen", "district"],
  region: ["vung", "region"],
  year: ["nam", "hang nam", "year", "annual"],
  quarter: ["quy", "quarter"],
  month: ["thang", "month"],
  firm: ["doanh nghiep", "cong ty", "ma ck", "firm", "company"],
  sector: ["nganh", "sector", "industry"],
  country: ["quoc gia", "country", "countries"],
  household: ["ho gia dinh", "household"],
}

const DECISIONS: Record<string, { label: string; cues: string[] }> = {
  budget_allocation: { label: "Phân bổ ngân sách / nguồn lực", cues: ["phan bo", "ngan sach", "nguon luc", "allocate", "budget"] },
  regional_priority: { label: "Ưu tiên khu vực / nhóm đối tượng", cues: ["uu tien", "khu vuc", "vung", "prioriti", "target"] },
  pricing_policy: { label: "Chính sách giá / thuế / phí", cues: ["chinh sach gia", "gia", "thue suat", "pricing", "tax"] },
  investment: { label: "Quyết định đầu tư", cues: ["dau tu", "danh muc", "invest"] },
  regulation: { label: "Quy định / giám sát", cues: ["quy dinh", "giam sat", "quan ly", "regulat", "monitor"] },
  forecast_planning: { label: "Dự báo & kế hoạch", cues: ["du bao", "ke hoach", "forecast", "plan"] },
}

const DELIVERABLES: Record<string, string[]> = {
  dashboard: ["dashboard", "bang dieu khien", "truc quan"],
  data_pipeline: ["pipeline", "luong du lieu", "etl", "ingestion"],
  recommendation: ["khuyen nghi", "de xuat", "recommend", "propose"],
  presentation: ["thuyet trinh", "pitch", "slide", "presentation"],
  report: ["bao cao", "report"],
  model: ["du bao", "mo hinh", "forecast", "predict", "model"],
}

function hasPhrase(textKey: string, phrase: string): number {
  const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const re = new RegExp(`(?<![a-z0-9])${escaped}(?![a-z0-9])`, "g")
  return (textKey.match(re) ?? []).length
}

export function parseBrief(text: string, columns?: string[] | null): Brief {
  const clean = text.trim()
  if (clean.length < 10) throw new Error("Đề bài quá ngắn (tối thiểu 10 ký tự).")

  const viCount = (clean.match(/[ăâđêôơưàáạảãèéẹẻẽìíịỉĩòóọỏõùúụủũỳýỵỷỹ]/gi) ?? []).length
  const letters = (clean.match(/[a-zA-ZÀ-ỹ]/g) ?? []).length || 1
  const language: "vi" | "en" = viCount / letters > 0.02 ? "vi" : "en"

  const lines = clean.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  const title = (lines[0] ?? clean.slice(0, 80)).replace(/^#+\s*(?:đề bài\s*:\s*)?/i, "").slice(0, 120)

  const sentences = clean
    .replace(/^\s*#+\s*/gm, "")
    .split(/(?<=[.?!;:])\s+|\n+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 6)

  const questionCues = ["hay", "phan tich", "de xuat", "danh gia", "xac dinh", "so sanh", "du bao", "analy", "propose", "recommend", "which", "what", "how", "why"]
  const questions = sentences.filter((s) => {
    const k = asciiKey(s)
    return s.includes("?") || questionCues.some((c) => hasPhrase(k, c) > 0)
  }).slice(0, 6)

  const textKey = asciiKey(clean)
  const qKeys = questions.map(asciiKey)

  const colList = columns ?? []
  const resolveCol = (c: ConceptDef): { column: string | null; resolved: string } => {
    if (!columns) return { column: null, resolved: "chưa đối chiếu cột (chưa chọn dataset)" }
    for (const pat of c.columns) {
      const hit = colList.find((col) => col === pat || asciiKey(col).includes(asciiKey(pat)))
      if (hit) return { column: hit, resolved: `khớp cột '${hit}' trong dataset` }
    }
    return { column: null, resolved: "không tìm thấy cột tương ứng trong dataset đang chọn" }
  }

  const scoredConcepts = CONCEPTS.map((c) => {
    const baseHits = c.phrases.reduce((s, p) => s + hasPhrase(textKey, p), 0)
    const qHits = qKeys.reduce((s, qk) => s + c.phrases.reduce((ss, p) => ss + hasPhrase(qk, p), 0), 0)
    return { concept: c, score: baseHits + qHits * 2 }
  })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)

  const targets = scoredConcepts.map(({ concept, score }) => {
    const r = resolveCol(concept)
    return {
      concept: concept.id,
      label: concept.label,
      column: r.column,
      resolved: r.resolved,
      domain: concept.domain,
      score,
    }
  })

  const target = targets[0] ?? null
  const alternatives = targets.slice(1, 4)

  const units = Object.entries(UNITS)
    .filter(([, cues]) => cues.some((p) => hasPhrase(textKey, p) > 0))
    .map(([u]) => u)

  const years = Array.from(new Set((clean.match(/\b(?:19|20)\d{2}\b/g) ?? []).map(Number))).sort((a, b) => a - b)
  const range: [number, number] | null = years.length >= 2 ? [years[0], years[years.length - 1]] : null

  const decision_types = Object.entries(DECISIONS)
    .map(([id, d]) => ({ id, label: d.label, hits: d.cues.reduce((s, p) => s + hasPhrase(textKey, p), 0) }))
    .filter((d) => d.hits > 0)
    .sort((a, b) => b.hits - a.hits)

  const deliverables = Object.entries(DELIVERABLES)
    .filter(([, cues]) => cues.some((p) => hasPhrase(textKey, p) > 0))
    .map(([d]) => d)

  const data_sources_mentioned: string[] = []
  if (/api/.test(textKey)) data_sources_mentioned.push("api")
  if (/scrap|website/.test(textKey)) data_sources_mentioned.push("web_scraping")
  if (/database|sql/.test(textKey)) data_sources_mentioned.push("database")
  if (/du lieu mo|open data|cong khai/.test(textKey)) data_sources_mentioned.push("open_data")

  const packs = loadPacks()
  const pack_scores: Record<string, number> = {}
  for (const p of packs) {
    pack_scores[p.id] = p.keywords.reduce((s, kw) => s + hasPhrase(textKey, asciiKey(kw)), 0)
  }
  const bestPack = packs
    .slice()
    .sort((a, b) => (pack_scores[b.id] ?? 0) - (pack_scores[a.id] ?? 0))
    .find((p) => (pack_scores[p.id] ?? 0) > 0) ?? null

  const segments: string[] = []
  if (units.includes("province")) segments.push("tỉnh/thành")
  if (units.includes("region")) segments.push("vùng")
  if (units.includes("sector")) segments.push("ngành")
  if (units.includes("country")) segments.push("quốc gia")

  const domain = target?.domain ?? bestPack?.domain ?? "auto"
  const plan = [
    `1. Thu thập & làm sạch dữ liệu (chuẩn hoá ngày, số kiểu Việt Nam, gắn cờ ngoại lai 3×IQR).`,
    `2. Xác nhận biến mục tiêu: ${target ? `${target.label}${target.column ? ` (${target.column})` : ""}` : "chọn cột số chính"}.`,
    `3. So sánh theo ${segments.join(", ") || "nhóm phân khúc chính"} bằng Kruskal–Wallis + Mann–Whitney.`,
    `4. Mô hình yếu tố tác động (Ridge chuẩn hoá + bootstrap 90% CI) và kiểm tra kịch bản What-If.`,
    `5. Tổng hợp quyết định & hạn chế dữ liệu trước khi xuất deck/báo cáo.`,
  ]

  const warnings: string[] = []
  if (!target) warnings.push("Chưa nhận diện được biến mục tiêu rõ ràng từ đề bài.")
  else if (columns && !target.column) warnings.push(`Biến mục tiêu '${target.label}' chưa khớp trực tiếp với cột nào trong dataset đang chọn.`)

  return {
    language,
    title,
    questions,
    target,
    alternatives,
    units,
    segments,
    time: { years, range },
    decision_types,
    deliverables,
    data_sources_mentioned,
    pack: bestPack,
    pack_scores,
    run_config: { target: target?.column ?? null, domain, segment_by: segments },
    plan,
    warnings,
    dataset: null,
  }
}
