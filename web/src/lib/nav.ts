import { fold } from "./analyst/explain.ts"

export const NAV = [
  { title: "Tổng quan", url: "/", keywords: ["overview", "dashboard"] },
  { title: "Đề bài", url: "/brief", keywords: ["brief", "question"] },
  { title: "Nguồn dữ liệu", url: "/sources", keywords: ["upload", "sources", "ingestion"] },
  { title: "Pipeline", url: "/pipeline", keywords: ["lineage", "etl"] },
  { title: "Chất lượng dữ liệu", url: "/quality", keywords: ["quality", "missing"] },
  { title: "Mô hình dữ liệu", url: "/model", keywords: ["model", "star", "schema"] },
  { title: "SQL Explorer", url: "/sql", keywords: ["query", "truy van"] },
  { title: "Hồ sơ dữ liệu", url: "/profile", keywords: ["profile", "eda"] },
  { title: "Insight", url: "/insights", keywords: ["finding", "bang chung"] },
  { title: "Drivers & What-if", url: "/drivers", keywords: ["what-if", "scenario", "kich ban"] },
  { title: "Phân khúc", url: "/segments", keywords: ["segments", "groups"] },
  { title: "Quyết định", url: "/decision", keywords: ["decision", "recommendation"] },
  { title: "AI Analyst", url: "/analyst", keywords: ["chat", "hoi ai"] },
  { title: "Xuất báo cáo", url: "/report", keywords: ["export", "zip", "deck", "pitch"] },
] as const

export function filterCommands(query: string) {
  return NAV.filter((page) => commandScore(page.title, query, [...page.keywords]) > 0)
}

export function commandScore(value: string, query: string, keywords: string[] = []): number {
  const text = fold([value, ...keywords].join(" "))
  return fold(query).split(/\s+/).every((word) => text.includes(word)) ? 1 : 0
}

export function whatIfLink(query: string): string | null {
  const match = /^what-if\s+(.+?)\s+([+-]?\d+(?:[.,]\d+)?)%$/i.exec(query.trim())
  if (!match) return null
  const percent = Math.max(-30, Math.min(30, Number(match[2].replace(",", "."))))
  return `/drivers?feature=${encodeURIComponent(match[1])}&pct=${percent}`
}
