// Deterministic offline NL->SQL template planner (feature 006 FR-605).
// Matches Vietnamese questions (diacritic-free via `fold`) onto allowlisted columns in `column_plan`.
import type { ColumnPlan } from "@/lib/api/types"
import { fold } from "./explain.ts"
import { quoteIdent } from "./sql-guard.ts"

export interface OfflineSqlPlan {
  intent: "topN" | "byTime" | "compare"
  sql: string
  explanation: string
}

const METRIC_SYNONYMS: Record<string, string[]> = {
  gia: ["price_per_m2", "gia_ban", "gia", "price", "gia_m2", "gia_thue_thang"],
  price: ["price_per_m2", "gia_ban", "price"],
  thue: ["gia_thue_thang", "tax_revenue_pct_gdp", "tax"],
  tax: ["tax_revenue_pct_gdp", "revenue_pct_gdp"],
  revenue: ["revenue_pct_gdp", "tax_revenue_pct_gdp"],
  thu: ["revenue_pct_gdp", "tax_revenue_pct_gdp", "thu_nhap_ho_thang", "earmarked_transfers"],
  no: ["central_gov_debt_pct_gdp", "debt"],
  debt: ["central_gov_debt_pct_gdp", "debt"],
  gdp: ["gdp_per_capita_usd", "gdp_growth_pct"],
  dien: ["dien_tich", "area"],
  area: ["dien_tich", "area"],
  roe: ["roe"],
  bo: ["earmarked_transfers", "earmarked_capex"],
}

const GROUP_SYNONYMS: Record<string, string[]> = {
  quan: ["district", "quan", "tinh_tp", "province", "region"],
  district: ["district", "tinh_tp", "province"],
  tinh: ["tinh_tp", "province", "province_2025", "region"],
  province: ["province", "tinh_tp", "province_2025"],
  vung: ["region", "vung", "province", "tinh_tp"],
  region: ["region", "tinh_tp", "province"],
  quoc: ["country", "iso3"],
  nuoc: ["country", "iso3"],
  country: ["country"],
  loai: ["loai_bds", "type", "category", "sector", "nganh"],
  type: ["loai_bds", "type", "category"],
  nganh: ["nganh", "sector", "industry", "loai_bds"],
  phap: ["phap_ly", "legal"],
}

function matchColumn(queryFold: string, candidates: string[], synonyms: Record<string, string[]>): string | null {
  if (candidates.length === 0) return null
  const tokens = queryFold.split(" ").filter(Boolean)

  // 1. Direct exact or full-phrase match on column name (with or without underscores)
  for (const col of candidates) {
    const rawFold = fold(col)
    const cf = fold(col.replace(/_/g, " "))
    if (!cf) continue
    if (
      queryFold.includes(rawFold) ||
      queryFold.includes(cf) ||
      cf.split(" ").every((w) => w.length >= 3 && tokens.includes(w))
    ) {
      return col
    }
  }
  // 2. Domain synonym map against allowlisted candidates (exact target before substring)
  for (const tok of tokens) {
    const targets = synonyms[tok]
    if (!targets) continue
    for (const t of targets) {
      const ft = fold(t)
      const exact = candidates.find((c) => fold(c) === ft)
      if (exact) return exact
      const partial = candidates.find((c) => fold(c).includes(ft))
      if (partial) return partial
    }
  }
  // 3. Partial token overlap (>= 3 chars) against column tokens
  for (const col of candidates) {
    const colTokens = fold(col.replace(/_/g, " ")).split(" ").filter((t) => t.length >= 3)
    if (colTokens.some((ct) => tokens.includes(ct))) return col
  }
  return null
}

function formatTableRef(tableName: string): string {
  const clean = tableName.replace(/"/g, "").trim()
  const dot = clean.indexOf(".")
  if (dot > 0) {
    const schema = clean.slice(0, dot)
    const tbl = clean.slice(dot + 1)
    return `${schema}.${quoteIdent(tbl)}`
  }
  return `gold.${quoteIdent(clean)}`
}

export function isSqlLikeQuestion(question: string): boolean {
  const f = fold(question)
  if (!f) return false
  return /\b(top|xep hang|cao nhat|thap nhat|theo nam|theo thang|theo tinh|theo quan|theo vung|theo loai|theo|so sanh|truy van|sql|select|trung vi|trung binh|tong)\b/.test(f)
}

export function planOfflineSql(
  question: string,
  plan: ColumnPlan,
  tableName: string,
  extraMeasures: string[] = [],
  extraCats: string[] = []
): OfflineSqlPlan | null {
  const f = fold(question)
  if (!f) return null

  const measures = Array.from(new Set([...(plan.measures ?? []), ...extraMeasures])).filter(Boolean)
  const cats = Array.from(
    new Set([plan.province, ...(plan.cats ?? []), ...extraCats].filter((x): x is string => Boolean(x)))
  )
  const tblRef = formatTableRef(tableName)

  const topMatch = f.match(/\btop\s+(\d+)/)
  const wantsExtreme = /\b(cao nhat|thap nhat|lon nhat|nho nhat|xep hang|top)\b/.test(f)
  const wantsTime = /\btheo\s+(nam|thang|ngay|quy|thoi gian|year|month)\b/.test(f) || (/\b(xu huong|dien bien)\b/.test(f) && Boolean(plan.time))
  const wantsCompare = /\b(so sanh|khac biet|giua cac)\b/.test(f)

  // Split around "theo" if present to disambiguate metric vs group
  const theoParts = f.split(/\btheo\b/)
  const metricText = theoParts[0] ?? f
  const groupText = theoParts.slice(1).join(" ") || f

  const metric = matchColumn(metricText, measures, METRIC_SYNONYMS) ?? matchColumn(f, measures, METRIC_SYNONYMS)
  const group = matchColumn(groupText, cats, GROUP_SYNONYMS) ?? matchColumn(f, cats, GROUP_SYNONYMS)

  // 1. byTime intent
  if (wantsTime && plan.time) {
    const m = metric ?? measures[0]
    if (!m) return null
    const tCol = plan.time
    const sql = `SELECT ${quoteIdent(tCol)}, median(${quoteIdent(m)}) AS median_value, COUNT(*) AS n\nFROM ${tblRef}\nGROUP BY 1\nORDER BY 1 ASC\nLIMIT 50`
    return {
      intent: "byTime",
      sql,
      explanation: `Diễn biến trung vị ${m} theo ${tCol} từ bảng ${tableName}.`,
    }
  }

  // 2. topN / rank intent
  if (topMatch || wantsExtreme || (theoParts.length > 1 && metric && group)) {
    const rawN = topMatch ? Number(topMatch[1]) : 10
    const n = Math.max(1, Math.min(50, Number.isFinite(rawN) ? rawN : 10))
    const asc = /\b(thap nhat|nho nhat|re nhat)\b/.test(f)
    if (!metric || !group) return null
    const sql = `SELECT ${quoteIdent(group)}, median(${quoteIdent(metric)}) AS median_value, COUNT(*) AS n\nFROM ${tblRef}\nGROUP BY 1\nORDER BY 2 ${asc ? "ASC" : "DESC"}\nLIMIT ${n}`
    return {
      intent: "topN",
      sql,
      explanation: `Top ${n} ${group} theo trung vị ${metric} (${asc ? "thấp → cao" : "cao → thấp"}).`,
    }
  }

  // 3. compare intent
  if (wantsCompare) {
    if (!group) return null
    const m = metric ?? measures[0]
    if (!m) return null
    const sql = `SELECT ${quoteIdent(group)}, median(${quoteIdent(m)}) AS median_value, COUNT(*) AS n\nFROM ${tblRef}\nGROUP BY 1\nORDER BY 2 DESC\nLIMIT 20`
    return {
      intent: "compare",
      sql,
      explanation: `So sánh trung vị ${m} giữa các nhóm ${group}.`,
    }
  }

  return null
}
