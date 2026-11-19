/**
 * Page 4 (`/tinh`, `/tinh/[code]`): choropleth, group chips, national range and the
 * province table. Display strings are formatted here so the pages render text only.
 */
import { formatNumber, formatWithUnit } from "../../../lib/monitor/format.ts"
import { indicatorById, sourceById } from "../../../lib/monitor/lookup.ts"
import type { Monitor, ProvinceGroup, ProvinceRow, ProvinceStats } from "../../../lib/monitor/types.ts"
import {
  formatGap,
  hasNumber,
  medianOf,
  trustFor,
  type FooterModel,
  type TrustModel,
} from "./common.ts"
import { publicFooter, publicPublisher } from "./method-view.ts"

export interface ProvinceGroupChip {
  id: string
  label: string
  range: string
  count: string
  href: string
}

export interface ProvinceTableRow {
  name: string
  href: string
  region: string
  group: string
  value: number | null
  gap: number | null
  valueText: string
  gapText: string
}

export interface ProvinceMapModel {
  title: string
  ariaLabel: string
  rows: { name: string; value: number | null; group: number | null }[]
  groups: ProvinceGroup[]
  unit?: string
  sourceIds: string[]
  pointCount: number
  frequency: string | null
  trust: TrustModel
}

export interface ProvinceRangeModel {
  title: string
  ariaLabel: string
  items: { id: string; label: string; min: number; median: number; max: number }[]
  unit?: string
  sourceIds: string[]
  pointCount: number
  frequency: string | null
  trust: TrustModel
}

export interface ProvincePageModel {
  level: "detail"
  headline: string
  lead: string[]
  generatedAt: string
  unit: string
  metricName: string
  period: string
  activeGroup: string | null
  groups: ProvinceGroupChip[]
  map: ProvinceMapModel | null
  range: ProvinceRangeModel | null
  table: ProvinceTableRow[]
  disbursement: ProvinceDisbursementModel | null
  footer: FooterModel
}

export interface ProvinceDisbursementModel {
  headline: string
  name: string
  period: string
  activeGroup: string | null
  groups: ProvinceGroupChip[]
  map: ProvinceMapModel | null
  range: ProvinceRangeModel | null
  table: ProvinceTableRow[]
  trust: TrustModel | null
}

export interface ProvinceMetricModel {
  id: string
  name: string
  valueText: string
  medianText: string
  gapText: string
  period: string
}

export interface ProvinceDetailModel {
  level: "detail"
  headline: string
  lead: string[]
  generatedAt: string
  name: string
  group: string
  backHref: string
  metrics: ProvinceMetricModel[]
  trust: TrustModel | null
  know: { definition: string; note: string | null; unit: string | null; frequency: string | null } | null
  footer: FooterModel
}

interface MetricFacts {
  id: string
  name: string
  unit: string
  period: string
  frequency: string | null
  stats: { median: number; min: number; max: number } | null
}

function prosePeriod(period: string | null | undefined): string {
  if (!period) return ""
  const month = /^(\d{4})-(\d{2})$/.exec(period)
  if (month) return `tháng ${Number(month[2])}/${month[1]}`
  const quarter = /^(\d{4})-Q([1-4])$/.exec(period)
  if (quarter) {
    const roman = ["I", "II", "III", "IV"][Number(quarter[2]) - 1]
    return `quý ${roman}/${quarter[1]}`
  }
  if (/^\d{4}$/.test(period)) return `năm ${period}`
  return period
}

function finiteMetric(row: ProvinceRow, id: string): number | null {
  const value = row.metrics[id]
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function primaryId(monitor: Monitor): string | null {
  const preferred = monitor.province.primary_metric
  if (preferred) return preferred
  return monitor.province.metric_ids[0] ?? null
}

function metricFacts(monitor: Monitor, id: string): MetricFacts {
  const indicator = indicatorById(monitor, id)
  const values = monitor.province.rows
    .map((row) => finiteMetric(row, id))
    .filter((value): value is number => value !== null)
  const given: ProvinceStats | undefined = monitor.province.stats?.[id]
  let stats: MetricFacts["stats"] = null
  if (
    given &&
    typeof given.median === "number" &&
    Number.isFinite(given.median) &&
    typeof given.min === "number" &&
    Number.isFinite(given.min) &&
    typeof given.max === "number" &&
    Number.isFinite(given.max)
  ) {
    stats = { median: given.median, min: given.min, max: given.max }
  } else if (values.length) {
    const median = medianOf(values)
    if (median !== null) stats = { median, min: Math.min(...values), max: Math.max(...values) }
  }
  return {
    id,
    name: indicator?.name_vi?.trim() || "Chỉ số",
    unit: indicator?.unit?.trim() || "",
    period: indicator?.latest?.period || "",
    frequency: indicator?.frequency ?? null,
    stats,
  }
}

function sourceIds(monitor: Monitor, metric: string | null): string[] {
  const listed = (monitor.province.source_ids ?? []).filter((id) => monitor.sources.some((source) => source.id === id))
  if (listed.length) return listed
  const sourceId = metric ? indicatorById(monitor, metric)?.source_id : undefined
  if (sourceId && monitor.sources.some((source) => source.id === sourceId)) return [sourceId]
  return []
}

function groupLabel(groups: ProvinceGroup[], group: number | null): string {
  if (group === null) return "–"
  return groups.find((item) => item.group === group)?.label_vi?.trim() || "–"
}

function valueText(value: number | null, unit: string): string {
  if (value === null) return "–"
  return formatWithUnit(value, unit) || "–"
}

function gapText(value: number | null, median: number | null, unit: string): string {
  if (value === null || median === null) return "–"
  return formatGap(value - median, unit) || "–"
}

function composedHeadline(facts: MetricFacts, rows: ProvinceRow[]): string | null {
  if (!facts.stats) return null
  const finite = rows
    .map((row) => ({ name: row.name, value: finiteMetric(row, facts.id) }))
    .filter((row): row is { name: string; value: number } => row.value !== null)
  if (!finite.length) return null
  const below = finite.filter((row) => row.value < facts.stats!.median).length
  const lowest = finite.reduce((best, row) => (row.value < best.value ? row : best))
  const period = prosePeriod(facts.period)
  const core = `${formatNumber(below)}/${formatNumber(finite.length)} tỉnh dưới trung vị về ${facts.name}, thấp nhất ${lowest.name} ${valueText(lowest.value, facts.unit)}`
  return period ? `${core}, ${period}` : core
}

function pageHeadline(monitor: Monitor, facts: MetricFacts): string {
  const given = monitor.province.headline_vi?.trim() ?? ""
  if (hasNumber(given)) return given
  return composedHeadline(facts, monitor.province.rows) || given || monitor.province.question_vi?.trim() || "Tỉnh thành"
}

const RATE_NAME = "Giải ngân đầu tư công so với kế hoạch"
const AMOUNT_NAME = "Giải ngân đầu tư công"

interface DisbursementObservation {
  rate: number | null
  amount: number | null
  period: string
  sourceId: string
}

function quantile(sorted: number[], q: number): number {
  if (sorted.length === 1) return sorted[0]
  const position = (sorted.length - 1) * q
  const lower = Math.floor(position)
  const upper = Math.ceil(position)
  if (lower === upper) return sorted[lower]
  const weight = position - lower
  return sorted[lower] * (1 - weight) + sorted[upper] * weight
}

function bisectLeft(cuts: number[], value: number): number {
  let lower = 0
  let upper = cuts.length
  while (lower < upper) {
    const mid = (lower + upper) >> 1
    if (cuts[mid] < value) lower = mid + 1
    else upper = mid
  }
  return lower
}

export function assignQuintiles(entries: { key: string; value: number }[]): { groups: ProvinceGroup[]; byKey: Map<string, number> } {
  const sorted = entries.map((entry) => entry.value).sort((left, right) => left - right)
  const cuts = [sorted[0], quantile(sorted, 0.2), quantile(sorted, 0.4), quantile(sorted, 0.6), quantile(sorted, 0.8), sorted[sorted.length - 1]]
  const inner = cuts.slice(1, -1)
  const byKey = new Map<string, number>()
  const counts = [0, 0, 0, 0, 0]
  for (const entry of entries) {
    const group = Math.min(5, bisectLeft(inner, entry.value) + 1)
    byKey.set(entry.key, group)
    counts[group - 1] += 1
  }
  return {
    byKey,
    groups: cuts.slice(0, 5).map((lower, index) => ({
      group: index + 1,
      label_vi: `Nhóm ${index + 1}`,
      min: lower,
      max: cuts[index + 1],
      count: counts[index],
    })),
  }
}

function disbursementObservations(monitor: Monitor): Map<string, DisbursementObservation> {
  const out = new Map<string, DisbursementObservation>()
  for (const row of monitor.reconciliation) {
    if (row.indicator_id !== "dtc_province_disbursed" || !row.note_vi) continue
    const [code, measure, unit] = row.note_vi.split(" · ").map((part) => part.trim())
    if (!code) continue
    const entry = Object.entries(row.values).find(([, value]) => typeof value === "number" && Number.isFinite(value))
    if (!entry) continue
    const current = out.get(code) ?? { rate: null, amount: null, period: row.period, sourceId: entry[0] }
    if (measure === "pct_plan" && unit === "%") current.rate = entry[1]
    if (measure === "level" && unit === "triệu đồng") current.amount = entry[1]
    if (row.period > current.period) current.period = row.period
    current.sourceId = entry[0]
    out.set(code, current)
  }
  return out
}

function citedTrust(monitor: Monitor, sourceIds: string[]): TrustModel | null {
  const trust = trustFor(monitor, { sourceIds })
  if (!trust) return null
  const names = sourceIds
    .map((id) => sourceById(monitor, id))
    .filter((source): source is NonNullable<typeof source> => Boolean(source))
    .map((source) => publicPublisher(source))
  if (names.length) trust.sourceName = [...new Set(names)].join(", ")
  return trust
}

function disbursementModel(monitor: Monitor, activeGroup: string | null): ProvinceDisbursementModel | null {
  const observed = disbursementObservations(monitor)
  const joined = monitor.province.rows.flatMap((row) => {
    const item = observed.get(row.code)
    if (!item || item.rate === null) return []
    return [{ row, rate: item.rate, amount: item.amount, period: item.period, sourceId: item.sourceId }]
  })
  if (!joined.length) return null
  const ranked = assignQuintiles(joined.map((item) => ({ key: item.row.code, value: item.rate })))
  const active = activeGroup && ranked.groups.some((group) => String(group.group) === activeGroup) ? activeGroup : null
  const rates = joined.map((item) => item.rate)
  const median = medianOf(rates)
  const sourceIds = [...new Set(joined.map((item) => item.sourceId))].filter((id) => sourceById(monitor, id))
  const trust = citedTrust(monitor, sourceIds)
  if (median === null || !trust) return null
  const lowest = joined.reduce((best, item) => (item.rate < best.rate ? item : best))
  const below = joined.filter((item) => item.rate < median).length
  const period = prosePeriod(joined.reduce((latest, item) => (item.period > latest ? item.period : latest), joined[0].period))
  const core = `${formatNumber(below)}/${formatNumber(joined.length)} tỉnh dưới trung vị về ${RATE_NAME}, thấp nhất ${lowest.row.name} ${valueText(lowest.rate, "%")}`
  const headline = period ? `${core}, ${period}` : core
  const distribution = `${RATE_NAME} từ ${valueText(Math.min(...rates), "%")} đến ${valueText(Math.max(...rates), "%")}, trung vị ${valueText(median, "%")}${period ? `, ${period}` : ""}`
  const visible = joined.filter((item) => (active ? String(ranked.byKey.get(item.row.code)) === active : true))
  return {
    headline,
    name: RATE_NAME,
    period,
    activeGroup: active,
    groups: ranked.groups.map((group) => ({
      id: String(group.group),
      label: group.label_vi,
      range: `${formatNumber(group.min)}–${formatNumber(group.max)}`,
      count: formatNumber(group.count),
      href: `/tinh?giai-ngan=${group.group}`,
    })),
    map: {
      title: distribution,
      ariaLabel: distribution,
      rows: joined.map((item) => ({
        name: item.row.name,
        value: item.rate,
        group: ranked.byKey.get(item.row.code) ?? null,
      })),
      groups: ranked.groups,
      unit: "%",
      sourceIds,
      pointCount: joined.length,
      frequency: null,
      trust,
    },
    range: {
      title: distribution,
      ariaLabel: distribution,
      items: [{ id: "dtc-province-rate", label: RATE_NAME, min: Math.min(...rates), median, max: Math.max(...rates) }],
      unit: "%",
      sourceIds,
      pointCount: joined.length,
      frequency: null,
      trust,
    },
    table: visible.map((item) => ({
      name: item.row.name,
      href: `/tinh/${encodeURIComponent(item.row.code)}`,
      region: item.row.region,
      group: groupLabel(ranked.groups, ranked.byKey.get(item.row.code) ?? null),
      value: item.rate,
      gap: item.rate - median,
      valueText: valueText(item.rate, "%"),
      gapText: gapText(item.rate, median, "%"),
    })),
    trust,
  }
}

function disbursementMetrics(monitor: Monitor, code: string): ProvinceMetricModel[] {
  const item = disbursementObservations(monitor).get(code)
  if (!item) return []
  const observed = [...disbursementObservations(monitor).values()]
  const rates = observed.map((entry) => entry.rate).filter((value): value is number => value !== null)
  const amounts = observed.map((entry) => entry.amount).filter((value): value is number => value !== null)
  const rateMedian = medianOf(rates)
  const amountMedian = medianOf(amounts)
  const period = prosePeriod(item.period)
  const metrics: ProvinceMetricModel[] = []
  if (item.rate !== null) {
    metrics.push({
      id: "dtc-province-rate",
      name: RATE_NAME,
      valueText: valueText(item.rate, "%"),
      medianText: rateMedian === null ? "–" : valueText(rateMedian, "%"),
      gapText: gapText(item.rate, rateMedian, "%"),
      period,
    })
  }
  metrics.push({
    id: "dtc-province-amount",
    name: AMOUNT_NAME,
    valueText: valueText(item.amount, "triệu đồng"),
    medianText: amountMedian === null ? "–" : valueText(amountMedian, "triệu đồng"),
    gapText: gapText(item.amount, amountMedian, "triệu đồng"),
    period,
  })
  return metrics
}

export function provincePage(monitor: Monitor, group: string | null, disbursementGroup: string | null = null): ProvincePageModel {
  const id = primaryId(monitor)
  const facts = id ? metricFacts(monitor, id) : metricFacts(monitor, "")
  const groups = [...monitor.province.groups].sort((left, right) => left.group - right.group)
  const active = group && groups.some((item) => String(item.group) === group) ? group : null
  const sources = sourceIds(monitor, id)
  const trust = trustFor(monitor, { sourceIds: sources, indicatorIds: id ? [id] : [] })
  const finiteCount = monitor.province.rows.filter((row) => finiteMetric(row, facts.id) !== null).length
  const question = monitor.province.question_vi?.trim() ?? ""
  const headline = pageHeadline(monitor, facts)
  const period = prosePeriod(facts.period)
  const distribution =
    facts.stats && facts.name
      ? `${facts.name} từ ${valueText(facts.stats.min, facts.unit)} đến ${valueText(facts.stats.max, facts.unit)}, trung vị ${valueText(facts.stats.median, facts.unit)}${period ? `, ${period}` : ""}`
      : facts.name

  const table = monitor.province.rows
    .filter((row) => (active ? String(row.group) === active : true))
    .map((row) => {
      const value = finiteMetric(row, facts.id)
      return {
        name: row.name,
        href: `/tinh/${encodeURIComponent(row.code)}`,
        region: row.region,
        group: groupLabel(groups, row.group),
        value,
        gap: value === null || !facts.stats ? null : value - facts.stats.median,
        valueText: valueText(value, facts.unit),
        gapText: gapText(value, facts.stats?.median ?? null, facts.unit),
      }
    })

  const figureBase = trust
    ? {
        unit: facts.unit || undefined,
        sourceIds: sources,
        frequency: facts.frequency,
        trust,
      }
    : null

  return {
    level: "detail",
    headline,
    lead: question && question !== headline ? [question] : [],
    generatedAt: monitor.meta.generated_at,
    unit: facts.unit,
    metricName: facts.name,
    period: prosePeriod(facts.period),
    activeGroup: active,
    groups: groups.map((item) => ({
      id: String(item.group),
      label: item.label_vi,
      range: `${formatNumber(item.min)}–${formatNumber(item.max)}`,
      count: formatNumber(item.count),
      href: `/tinh?nhom=${item.group}`,
    })),
    map: figureBase
      ? {
          ...figureBase,
          title: distribution,
          ariaLabel: distribution,
          rows: monitor.province.rows.map((row) => ({
            name: row.name,
            value: finiteMetric(row, facts.id),
            group: row.group,
          })),
          groups,
          pointCount: finiteCount,
        }
      : null,
    range:
      figureBase && facts.stats
        ? {
            ...figureBase,
            title: distribution,
            ariaLabel: distribution,
            items: [{ id: facts.id || "primary", label: facts.name, ...facts.stats }],
            pointCount: finiteCount || 1,
          }
        : null,
    table,
    disbursement: disbursementModel(monitor, disbursementGroup),
    footer: publicFooter(monitor),
  }
}

export function provinceDetail(monitor: Monitor, code: string): ProvinceDetailModel | null {
  const wanted = code.trim().toLowerCase()
  if (!wanted) return null
  const row = monitor.province.rows.find((item) => item.code.toLowerCase() === wanted)
  if (!row) return null

  const groups = monitor.province.groups
  const primary = primaryId(monitor)
  const ids = monitor.province.metric_ids.length ? monitor.province.metric_ids : primary ? [primary] : []
  const metrics = ids.map((id) => {
    const facts = metricFacts(monitor, id)
    const value = finiteMetric(row, id)
    return {
      id,
      name: facts.name,
      valueText: valueText(value, facts.unit),
      medianText: facts.stats ? valueText(facts.stats.median, facts.unit) : "–",
      gapText: gapText(value, facts.stats?.median ?? null, facts.unit),
      period: prosePeriod(facts.period),
    }
  })
  const main = (primary ? metrics.find((metric) => metric.id === primary) : metrics[0]) ?? null
  const label = groupLabel(groups, row.group)
  const place = row.group === null || label === "–" ? "chưa xếp nhóm" : `đứng ${label}`
  const comparison = main
    ? main.valueText === "–"
      ? `chưa có số so với trung vị ${main.medianText}`
      : `${main.valueText} so với trung vị ${main.gapText}`
    : "chưa có chỉ số"
  const headlineCore = `${row.name} ${place} về ${main?.name ?? "chỉ số"}: ${comparison}`
  const headline = main?.period ? `${headlineCore}, ${main.period}` : headlineCore
  const sources = sourceIds(monitor, primary)
  const indicator = primary ? indicatorById(monitor, primary) : null
  const question = monitor.province.question_vi?.trim() ?? ""

  return {
    level: "detail",
    headline,
    lead: question && question !== headline ? [question] : [],
    generatedAt: monitor.meta.generated_at,
    name: row.name,
    group: label,
    backHref: "/tinh",
    metrics: [...metrics, ...disbursementMetrics(monitor, row.code)],
    trust: trustFor(monitor, { sourceIds: sources, indicatorIds: ids }),
    know: indicator?.definition_vi
      ? {
          definition: indicator.definition_vi,
          note: indicator.note_vi?.trim() ? indicator.note_vi : null,
          unit: indicator.unit || null,
          frequency: indicator.frequency,
        }
      : null,
    footer: publicFooter(monitor),
  }
}
