/**
 * Page 5 (`/khuyen-nghi`): numbered recommendations and the full rule table.
 * Evidence links to the sector page that renders `chart_id`.
 */
import { formatNumber, formatWithUnit } from "../../../lib/monitor/format.ts"
import { indicatorById, sourceById } from "../../../lib/monitor/lookup.ts"
import type { Chart, Monitor, SectorId } from "../../../lib/monitor/types.ts"
import { figureFromChart, type FigureModel } from "./chart-block.ts"
import { SECTOR_IDS, formatGap, sectorHref, type FooterModel } from "./common.ts"
import { publicFooter, publicPublisher } from "./method-view.ts"
import { assignQuintiles } from "./province-view.ts"

export interface RecommendationEvidenceModel {
  ruleId: string
  fact: string
  formula: string
  threshold: string
  chartHref?: string
  chartId?: string
}

export interface RecommendationItemModel {
  id: string
  title: string
  evidence: RecommendationEvidenceModel[]
  implication: string
  action: string
  agency: string
  horizon: string
  caveat: string | null
  figures: FigureModel[]
}

export interface RuleRowModel {
  name: string
  formula: string
  threshold: string
  status: string
  agency: string
}

export interface AgencyRowModel {
  name: string
  rate: string
  gap: string
  amount: string
  group: string
}

export interface AgencyDisbursementModel {
  period: string
  national: string
  rows: AgencyRowModel[]
  groups: { label: string; range: string; count: string }[]
  sourceName: string
}

export interface RecommendationPageModel {
  level: "detail"
  headline: string
  lead: string[]
  generatedAt: string
  items: RecommendationItemModel[]
  rules: RuleRowModel[]
  agencies: AgencyDisbursementModel | null
  footer: FooterModel
}

function prosePeriod(period: string): string {
  const month = /^(\d{4})-(\d{2})$/.exec(period)
  if (month) return `tháng ${Number(month[2])}/${month[1]}`
  return period
}

function nationalDisbursementRate(monitor: Monitor): { value: number; period: string } | null {
  const latest = indicatorById(monitor, "dtc_giai_ngan_pct_plan")?.latest
  if (latest && typeof latest.value === "number" && Number.isFinite(latest.value)) {
    return { value: latest.value, period: latest.period }
  }
  for (const row of monitor.reconciliation) {
    if (row.indicator_id !== "dtc_disbursed" || !row.note_vi?.includes("pct_plan")) continue
    const value = Object.values(row.values).find((item) => typeof item === "number" && Number.isFinite(item))
    if (typeof value === "number") return { value, period: row.period }
  }
  return null
}

function centralAgencies(monitor: Monitor): AgencyDisbursementModel | null {
  const national = nationalDisbursementRate(monitor)
  if (!national) return null
  const observed = new Map<string, { rate: number | null; amount: number | null; period: string; sourceId: string }>()
  for (const row of monitor.reconciliation) {
    if (row.indicator_id !== "dtc_ministry_disbursed" || !row.note_vi) continue
    const [name, measure, unit] = row.note_vi.split(" · ").map((part) => part.trim())
    if (!name || name.includes("_")) continue
    const entry = Object.entries(row.values).find(([, value]) => typeof value === "number" && Number.isFinite(value))
    if (!entry || !sourceById(monitor, entry[0])) continue
    const current = observed.get(name) ?? { rate: null, amount: null, period: row.period, sourceId: entry[0] }
    if (measure === "pct_plan" && unit === "%") current.rate = entry[1]
    if (measure === "level" && unit === "triệu đồng") current.amount = entry[1]
    current.sourceId = entry[0]
    observed.set(name, current)
  }
  const rows = [...observed.entries()].flatMap(([name, item]) => (item.rate === null ? [] : [{ name, ...item, rate: item.rate }]))
  if (!rows.length) return null
  const ranked = assignQuintiles(rows.map((row) => ({ key: row.name, value: row.rate })))
  const sourceName = [...new Set(rows.map((row) => publicPublisher(sourceById(monitor, row.sourceId)!)))].join(", ")
  if (!sourceName) return null
  return {
    period: prosePeriod(national.period),
    national: formatWithUnit(national.value, "%"),
    sourceName,
    groups: ranked.groups.map((group) => ({
      label: group.label_vi,
      range: `${formatNumber(group.min)}–${formatNumber(group.max)}`,
      count: formatNumber(group.count),
    })),
    rows: rows
      .map((row) => ({
        name: row.name,
        rate: formatWithUnit(row.rate, "%"),
        gap: formatGap(row.rate - national.value, "%"),
        amount: row.amount === null ? "–" : formatWithUnit(row.amount, "triệu đồng"),
        group: ranked.groups.find((group) => group.group === ranked.byKey.get(row.name))?.label_vi ?? "–",
      }))
      .sort((left, right) => left.name.localeCompare(right.name, "vi")),
  }
}

function findChart(monitor: Monitor, chartId: string): { sector: SectorId; chart: Chart } | null {
  for (const sector of SECTOR_IDS) {
    const chart = monitor.sectors[sector]?.charts.find((item) => item.id === chartId)
    if (chart) return { sector, chart }
  }
  return null
}

export function recommendationPage(monitor: Monitor): RecommendationPageModel {
  const rules = new Map((monitor.rules ?? []).map((rule) => [rule.id, rule]))
  const seenCharts = new Set<string>()
  const items: RecommendationItemModel[] = []
  let agenciesSupported = false

  for (const item of monitor.recommendations) {
    const title = item.title_vi?.trim()
    const implication = item.so_what_vi?.trim()
    const action = item.action_vi?.trim()
    const agency = item.agency_vi?.trim()
    const horizon = item.horizon_vi?.trim()
    if (!title || !implication || !action || !agency || !horizon || !item.evidence.length) continue

    const evidence: RecommendationEvidenceModel[] = item.evidence.map((entry) => {
      const rule = rules.get(entry.rule_id)
      const located = findChart(monitor, entry.chart_id)
      const chartHref = located ? `${sectorHref(located.sector)}#${entry.chart_id}` : undefined
      return {
        ruleId: entry.rule_id,
        fact: entry.fact_vi,
        formula: rule?.formula_vi?.trim() ?? "",
        threshold: rule?.threshold_vi?.trim() ?? "",
        chartHref,
        chartId: chartHref ? entry.chart_id : undefined,
      }
    })

    const figures: FigureModel[] = []
    for (const entry of item.evidence) {
      const located = findChart(monitor, entry.chart_id)
      if (!located || seenCharts.has(located.chart.id)) continue
      seenCharts.add(located.chart.id)
      const figure = figureFromChart(monitor, located.chart)
      if (figure) figures.push(figure)
    }

    const ruleText = item.evidence
      .map((entry) => {
        const rule = rules.get(entry.rule_id)
        return `${rule?.name_vi ?? ""} ${rule?.formula_vi ?? ""}`
      })
      .join(" ")
    if (/giải ngân/i.test(ruleText) && /đơn vị|trung ương|địa phương/i.test(ruleText)) agenciesSupported = true

    items.push({
      id: item.id,
      title: `${formatNumber(items.length + 1)}. ${title}`,
      evidence,
      implication,
      action,
      agency,
      horizon,
      caveat: item.caveat_vi?.trim() ? item.caveat_vi : null,
      figures,
    })
  }

  const horizon = items[0]?.horizon ?? ""
  const headline = items.length
    ? horizon
      ? `${formatNumber(items.length)} việc cần làm trong ${horizon}.`
      : `${formatNumber(items.length)} việc cần làm.`
    : ""

  const ruleRows = (monitor.rules ?? [])
    .map((rule, index) => ({ rule, index }))
    .sort((left, right) => Number(right.rule.fired) - Number(left.rule.fired) || left.index - right.index)
    .map(({ rule }) => ({
      name: rule.name_vi?.trim() || "Quy tắc",
      formula: rule.formula_vi,
      threshold: rule.threshold_vi,
      status: rule.fired ? "Đã kích hoạt" : "Chưa đánh giá",
      agency: rule.agency_vi?.trim() ?? "",
    }))

  return {
    level: "detail",
    headline,
    lead: items.length ? ["Quý tới ai làm gì, dựa trên bằng chứng nào?"] : [],
    generatedAt: monitor.meta.generated_at,
    items,
    rules: ruleRows,
    agencies: agenciesSupported ? centralAgencies(monitor) : null,
    footer: publicFooter(monitor),
  }
}
