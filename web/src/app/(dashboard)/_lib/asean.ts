/**
 * Page 2 (`/asean`) mapping: indicator selector, ranking, spread around the median,
 * the VN-vs-ASEAN timeline and the sortable country table.
 */
import { formatNumber, formatPeriod } from "../../../lib/monitor/format.ts"
import { indicatorById } from "../../../lib/monitor/lookup.ts"
import type { AseanEntry, Monitor, Point } from "../../../lib/monitor/types.ts"
import type { ChartBodyModel, FigureModel } from "./chart-block.ts"
import {
  finitePoints,
  footerModel,
  formatGap,
  gapUnit,
  medianOf,
  nationalPoints,
  seriesPoints,
  trustFor,
  type FooterModel,
  type TrustModel,
} from "./common.ts"

export interface TableColumnModel {
  key: string
  label: string
  unit?: string
  kind?: "text" | "number" | "percent" | "date"
}

export interface TableModel {
  id: string
  title: string
  columns: TableColumnModel[]
  rows: Record<string, unknown>[]
  pointCount: number
  sourceIds: string[]
  trust: TrustModel
}

export interface AseanModel {
  level: "drilldown"
  selectedId: string
  indicatorName: string
  unit: string
  headline: string
  yearNote: string
  selector: { id: string; label: string; href: string; active: boolean }[]
  figures: FigureModel[]
  table: TableModel | null
  footer: FooterModel
}

function entryMedian(entry: AseanEntry): number | null {
  if (typeof entry.median === "number" && Number.isFinite(entry.median)) return entry.median
  return medianOf(entry.rows.map((row) => row.value))
}

function aseanMedianPoints(points: Point[], countries: Set<string>): { period: string; value: number }[] {
  const byPeriod = new Map<string, number[]>()
  for (const point of points) {
    if (!point.geo || !countries.has(point.geo)) continue
    if (typeof point.value !== "number" || !Number.isFinite(point.value)) continue
    const values = byPeriod.get(point.period) ?? []
    values.push(point.value)
    byPeriod.set(point.period, values)
  }
  const out: { period: string; value: number }[] = []
  for (const [period, values] of byPeriod) {
    const median = medianOf(values)
    if (median !== null) out.push({ period, value: median })
  }
  return out.sort((left, right) => left.period.localeCompare(right.period))
}

function spanLabel(periods: string[]): string {
  const sorted = [...periods].sort()
  const first = sorted[0]
  const last = sorted[sorted.length - 1]
  if (!first || !last) return ""
  if (first === last) return first
  const yearOnly = sorted.every((period) => /^\d{4}$/.test(period))
  return yearOnly ? `${first}–${last}` : `${formatPeriod(first)}–${formatPeriod(last)}`
}

function headlineFor(entry: AseanEntry, name: string, unit: string): string {
  const median = entryMedian(entry)
  const vietnam = entry.rows.find((row) => row.iso3 === "VNM")
  const n = entry.rows.length
  if (!vietnam || typeof entry.vn_rank !== "number" || median === null || !n) {
    return `Chưa đủ số liệu để xếp hạng Việt Nam về ${name} năm ${String(entry.year)}.`
  }
  const gap = formatGap(vietnam.value - median, gapUnit(unit))
  return `Việt Nam thứ ${formatNumber(entry.vn_rank)}/${formatNumber(n)} về ${name} năm ${String(entry.year)}, cách trung vị ${gap}.`
}

export function aseanPage(monitor: Monitor, requested: string | null): AseanModel | null {
  const known = Object.keys(monitor.asean).filter((id) => Boolean(indicatorById(monitor, id)?.name_vi?.trim()))
  if (!known.length) return null
  const selectedId = requested && known.includes(requested) ? requested : known[0]
  const indicator = indicatorById(monitor, selectedId)
  const entry = monitor.asean[selectedId]
  if (!indicator || !entry) return null

  const name = indicator.name_vi
  const unit = indicator.unit
  const median = entryMedian(entry)
  const vietnam = entry.rows.find((row) => row.iso3 === "VNM") ?? null
  const trust = trustFor(monitor, { sourceIds: [entry.source_id], indicatorIds: [selectedId] })
  const figures: FigureModel[] = []

  const rankedTitle =
    typeof entry.vn_rank === "number" && entry.rows.length
      ? `Xếp hạng ${name} năm ${String(entry.year)}: Việt Nam thứ ${formatNumber(entry.vn_rank)}/${formatNumber(entry.rows.length)}.`
      : `Xếp hạng ${name} năm ${String(entry.year)}.`
  const rankedRows = entry.rows.map((row) => ({
    id: row.iso3,
    label: row.name_vi,
    value: row.value,
    highlight: row.iso3 === "VNM",
  }))

  if (trust && rankedRows.length) {
    const body: ChartBodyModel = {
      kind: "bar",
      rows: rankedRows,
      unit,
      period: String(entry.year),
      sourceName: trust.sourceName,
    }
    figures.push({
      id: `${selectedId}-rank`,
      number: 1,
      title: rankedTitle,
      ariaLabel: rankedTitle,
      body,
      sourceIds: [entry.source_id],
      pointCount: rankedRows.length,
      frequency: indicator.frequency,
      note: null,
      trust,
    })
  }

  const values = entry.rows.map((row) => row.value).filter((value) => Number.isFinite(value))
  if (trust && median !== null && values.length >= 2) {
    const title = `Khoảng biến thiên ${name} năm ${String(entry.year)}: ${formatNumber(Math.min(...values))}–${formatNumber(Math.max(...values))} ${unit}.`
    figures.push({
      id: `${selectedId}-range`,
      number: figures.length + 1,
      title,
      ariaLabel: `${title} Khoảng giá trị từ ${formatNumber(Math.min(...values))} đến ${formatNumber(Math.max(...values))} ${unit}.`,
      body: {
        kind: "range",
        items: [{ id: "asean", label: "Toàn khối", min: Math.min(...values), median, max: Math.max(...values) }],
        unit,
        reference: vietnam ? vietnam.value : null,
        referenceLabel: vietnam ? "Việt Nam" : undefined,
      },
      sourceIds: [entry.source_id],
      pointCount: values.length,
      frequency: indicator.frequency,
      note: null,
      trust,
    })
  }

  const points = seriesPoints(monitor, selectedId)
  const countries = new Set(entry.rows.map((row) => row.iso3))
  const vietnamPoints = finitePoints(nationalPoints(points))
  const medianPoints = aseanMedianPoints(points, countries)
  const comparator = [...entry.rows].sort((left, right) => left.rank - right.rank).find((row) => row.iso3 !== "VNM")
  const years = spanLabel(points.map((point) => point.period))

  if (trust && vietnamPoints.length >= 2 && medianPoints.length >= 2) {
    const series = [
      {
        id: "vn",
        name: "Việt Nam",
        points: vietnamPoints.map((point) => ({ period: point.period, value: point.value })),
        context: false,
      },
      {
        id: "asean_median",
        name: "Trung vị ASEAN",
        points: medianPoints.map((point) => ({ period: point.period, value: point.value })),
        context: true,
      },
    ]
    if (comparator) {
      const comparatorPoints = finitePoints(points.filter((point) => point.geo === comparator.iso3))
      if (comparatorPoints.length >= 2) {
        series.push({
          id: comparator.iso3,
          name: comparator.name_vi,
          points: comparatorPoints.map((point) => ({ period: point.period, value: point.value })),
          context: true,
        })
      }
    }
    const common = [...new Set(medianPoints.map((point) => point.period))]
      .filter((period) => vietnamPoints.some((point) => point.period === period))
      .sort()
    const latest = common[common.length - 1]
    const vnLatest = vietnamPoints.find((point) => point.period === latest)
    const medianLatest = medianPoints.find((point) => point.period === latest)
    const title =
      vnLatest && medianLatest
        ? `Việt Nam ${formatGap(vnLatest.value - medianLatest.value, gapUnit(unit))} so với trung vị ASEAN về ${name} năm ${latest}.`
        : `Việt Nam và trung vị ASEAN về ${name}, ${years}.`
    figures.push({
      id: `${selectedId}-timeline`,
      number: figures.length + 1,
      title,
      ariaLabel: title,
      body: { kind: "line", series, unit, sourceName: trust.sourceName },
      sourceIds: [entry.source_id],
      pointCount: vietnamPoints.length,
      frequency: indicator.frequency,
      note: null,
      trust,
    })
  }

  const tableTrust = trust
  const table =
    tableTrust && entry.rows.length
      ? {
          id: `${selectedId}-table`,
          title: `${formatNumber(entry.rows.length)} nước ASEAN theo ${name} năm ${String(entry.year)}.`,
          columns: [
            { key: "rank", label: "Hạng", kind: "number" as const },
            { key: "name", label: "Nước", kind: "text" as const },
            { key: "value", label: "Giá trị", unit, kind: "number" as const },
            { key: "gap", label: "Chênh trung vị", unit: gapUnit(unit), kind: "number" as const },
          ],
          rows: [...entry.rows]
            .sort((left, right) => left.rank - right.rank)
            .map((row) => ({
              rank: row.rank,
              name: row.name_vi,
              value: row.value,
              gap: median === null ? null : row.value - median,
            })),
          pointCount: entry.rows.length,
          sourceIds: [entry.source_id],
          trust: tableTrust,
        }
      : null

  return {
    level: "drilldown",
    selectedId,
    indicatorName: name,
    unit,
    headline: headlineFor(entry, name, unit),
    yearNote: years
      ? `Năm chung gần nhất: ${String(entry.year)}. Chuỗi số liệu: ${years}.`
      : `Năm chung gần nhất: ${String(entry.year)}.`,
    selector: known.map((id) => ({
      id,
      label: indicatorById(monitor, id)?.name_vi ?? id,
      href: `/asean?indicator=${id}`,
      active: id === selectedId,
    })),
    figures,
    table,
    footer: footerModel(monitor),
  }
}
