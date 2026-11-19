import { indicatorById } from "./lookup.ts"
import type { Monitor, SectorId } from "./types.ts"

export const MONITOR_EMPTY_VI =
  "Chưa có dữ liệu đã xuất bản. Chạy pipeline vn_monitor để tạo out/vn_monitor/monitor.json."

export interface JudgeSection {
  id: string
  label: string
}

export interface JudgeView {
  headline: string
  question: string
  sections: JudgeSection[]
}

const SECTOR_PLACEHOLDERS: JudgeSection[] = [
  { id: "cards", label: "Thẻ kết luận" },
  { id: "watch", label: "Cần theo dõi" },
  { id: "charts", label: "Biểu đồ" },
  { id: "tables", label: "Bảng" },
]

export function overviewView(monitor: Monitor): JudgeView {
  return {
    headline: monitor.meta.title_vi,
    question: monitor.meta.question_vi,
    sections: [
      { id: "lead", label: "Điều mới nhất" },
      { id: "kpi", label: "Thẻ chỉ số" },
      { id: "watch", label: "Cần theo dõi" },
    ],
  }
}

export function sectorView(monitor: Monitor, sectorId: SectorId, title: string): JudgeView {
  const sector = monitor.sectors[sectorId]
  if (!sector) return { headline: title, question: "", sections: SECTOR_PLACEHOLDERS }
  const sections: JudgeSection[] = [
    { id: "cards", label: "Thẻ kết luận" },
    { id: "watch", label: "Cần theo dõi" },
  ]
  if (sector.charts.length) {
    for (const chart of sector.charts) sections.push({ id: chart.id, label: chart.title_vi })
  } else {
    sections.push({ id: "charts", label: "Biểu đồ" })
  }
  if (sector.tables.length) {
    for (const table of sector.tables) sections.push({ id: table.id, label: table.title_vi })
  } else {
    sections.push({ id: "tables", label: "Bảng" })
  }
  return { headline: sector.headline_vi, question: sector.question_vi, sections }
}

export function aseanView(monitor: Monitor): JudgeView {
  const named = Object.keys(monitor.asean).map((id) => ({
    id,
    label: indicatorById(monitor, id)?.name_vi ?? "Chỉ số",
  }))
  return {
    headline: "Chỉ số & ASEAN",
    question: "",
    sections: named.length
      ? named
      : [
          { id: "rank", label: "Xếp hạng" },
          { id: "gap", label: "Khoảng cách tới trung vị" },
        ],
  }
}

export function provinceView(monitor: Monitor): JudgeView {
  return {
    headline: monitor.province.headline_vi || "Tỉnh thành",
    question: monitor.province.question_vi ?? "",
    sections: [
      { id: "map", label: "Bản đồ" },
      { id: "groups", label: "Nhóm" },
      { id: "table", label: "Bảng tỉnh" },
    ],
  }
}

export function provinceDetailView(monitor: Monitor, code: string): JudgeView | null {
  const row = monitor.province.rows.find((item) => item.code === code)
  if (!row) return null
  const sections = monitor.province.metric_ids.map((id) => ({
    id,
    label: indicatorById(monitor, id)?.name_vi ?? "Chỉ số",
  }))
  return {
    headline: row.name,
    question: monitor.province.question_vi ?? "",
    sections: sections.length ? sections : [{ id: "metrics", label: "Chỉ số của tỉnh" }],
  }
}

export function recommendationView(monitor: Monitor): JudgeView {
  const sections = monitor.recommendations.map((item) => ({ id: item.id, label: item.title_vi }))
  return {
    headline: "Phân tích & Khuyến nghị",
    question: "",
    sections: sections.length ? sections : [{ id: "recs", label: "Khuyến nghị" }],
  }
}

export function methodView(monitor: Monitor): JudgeView {
  return {
    headline: "Dữ liệu & Phương pháp",
    question: "",
    sections: [
      ...monitor.sources.map((source) => ({ id: source.id, label: source.title_vi })),
      { id: "quality", label: "Chất lượng" },
      { id: "reconciliation", label: "Đối soát" },
    ],
  }
}
