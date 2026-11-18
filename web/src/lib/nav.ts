import { fold } from "./analyst/explain.ts"

export const NAV = [
  { title: "Tổng quan", url: "/", group: "Phân tích", keywords: ["overview", "dashboard"] },
  { title: "Đề bài", url: "/brief", group: "Phân tích", keywords: ["brief", "question"] },
  { title: "Nguồn dữ liệu", url: "/sources", group: "Dữ liệu", keywords: ["upload", "sources", "ingestion"] },
  { title: "Pipeline", url: "/pipeline", group: "Dữ liệu", keywords: ["lineage", "etl"] },
  { title: "Chất lượng dữ liệu", url: "/quality", group: "Dữ liệu", keywords: ["quality", "missing"] },
  { title: "Mô hình dữ liệu", url: "/model", group: "Dữ liệu", keywords: ["model", "star", "schema"] },
  { title: "SQL Explorer", url: "/sql", group: "Dữ liệu", keywords: ["query", "truy van"] },
  { title: "Hồ sơ dữ liệu", url: "/profile", group: "Dữ liệu", keywords: ["profile", "eda"] },
  { title: "Insight", url: "/insights", group: "Phân tích", keywords: ["finding", "bang chung"] },
  { title: "Drivers & What-if", url: "/drivers", group: "Phân tích", keywords: ["what-if", "scenario", "kich ban"] },
  { title: "Kịch bản what-if", url: "/whatif", group: "Phân tích", keywords: ["whatif", "scenario", "kich ban nhieu bien", "multi-driver"] },
  { title: "Phân khúc", url: "/segments", group: "Phân tích", keywords: ["segments", "groups"] },
  { title: "Quyết định", url: "/decision", group: "Kết quả", keywords: ["decision", "recommendation"] },
  { title: "AI Analyst", url: "/analyst", group: "Phân tích", keywords: ["chat", "hoi ai"] },
  { title: "Xuất báo cáo", url: "/report", group: "Kết quả", keywords: ["export", "zip", "deck", "pitch"] },
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
