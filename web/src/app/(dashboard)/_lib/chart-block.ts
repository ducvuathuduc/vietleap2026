/**
 * Chart records → figure props. Every figure carries a numbered conclusion caption,
 * its source ids and a citation line; a chart without a registered source is dropped.
 */
import { indicatorById } from "../../../lib/monitor/lookup.ts"
import type { Chart, HeatRow, Monitor, SectorId } from "../../../lib/monitor/types.ts"
import {
  SECTOR_IDS,
  finitePoints,
  indicatorName,
  medianOf,
  nationalPoints,
  seriesPoints,
  trustFor,
  type TrustModel,
} from "./common.ts"

export interface LineSeriesModel {
  id: string
  name: string
  points: { period: string; value: number | null }[]
  context?: boolean
}

export type ChartBodyModel =
  | { kind: "line"; series: LineSeriesModel[]; unit?: string; sourceName?: string }
  | { kind: "bar"; rows: { id: string; label: string; value: number; highlight?: boolean }[]; unit?: string; period?: string; sourceName?: string }
  | {
      kind: "range"
      items: { id: string; label: string; min: number; median: number; max: number }[]
      unit?: string
      reference?: number | null
      referenceLabel?: string
    }
  | {
      kind: "heatmap"
      rows: { indicatorId: string; label: string; cells: { period: string; value: number | null; pctile: number | null }[] }[]
      unit?: string
    }

export interface FigureModel {
  id: string
  number: number | null
  title: string
  ariaLabel: string
  body: ChartBodyModel | null
  sourceIds: string[]
  pointCount: number
  frequency: string | null
  note: string | null
  trust: TrustModel
}

function lineBody(monitor: Monitor, chart: Chart, sourceName: string, unit?: string): { body: ChartBodyModel | null; pointCount: number } {
  const series: LineSeriesModel[] = []
  for (const id of chart.indicator_ids) {
    const name = indicatorName(monitor, id)
    if (!name) continue
    const points = nationalPoints(seriesPoints(monitor, id))
    if (!finitePoints(points).length) continue
    series.push({ id, name, points: points.map((point) => ({ period: point.period, value: point.value })), context: series.length > 0 })
  }
  if (!series.length) return { body: null, pointCount: 0 }
  const pointCount = series.reduce((total, item) => total + finitePoints(item.points).length, 0)
  return { body: { kind: "line", series, unit, sourceName }, pointCount }
}

function barBody(monitor: Monitor, chart: Chart, sourceName: string, unit?: string): { body: ChartBodyModel | null; pointCount: number } {
  const rows: { id: string; label: string; value: number; highlight?: boolean }[] = []
  let period: string | undefined
  for (const id of chart.indicator_ids) {
    const indicator = indicatorById(monitor, id)
    const value = indicator?.latest?.value
    if (!indicator || typeof value !== "number" || !Number.isFinite(value)) continue
    if (!indicator.name_vi?.trim()) continue
    period ??= indicator.latest.period
    rows.push({ id, label: indicator.name_vi, value, highlight: chart.highlight === id })
  }
  if (!rows.length) return { body: null, pointCount: 0 }
  return { body: { kind: "bar", rows, unit, period, sourceName }, pointCount: rows.length }
}

function rangeBody(monitor: Monitor, chart: Chart, unit?: string): { body: ChartBodyModel | null; pointCount: number } {
  const items: { id: string; label: string; min: number; median: number; max: number }[] = []
  for (const id of chart.indicator_ids) {
    const name = indicatorName(monitor, id)
    if (!name) continue
    const values = finitePoints(nationalPoints(seriesPoints(monitor, id))).map((point) => point.value)
    const median = medianOf(values)
    if (median === null) continue
    items.push({ id, label: name, min: Math.min(...values), median, max: Math.max(...values) })
  }
  if (!items.length) return { body: null, pointCount: 0 }
  return { body: { kind: "range", items, unit }, pointCount: items.length }
}

function heatBody(monitor: Monitor, chart: Chart, heatmap: HeatRow[], unit?: string): { body: ChartBodyModel | null; pointCount: number } {
  const wanted = new Set(chart.indicator_ids)
  const rows = heatmap
    .filter((row) => !wanted.size || wanted.has(row.indicator_id))
    .map((row) => ({ row, label: indicatorName(monitor, row.indicator_id) }))
    .filter((entry): entry is { row: HeatRow; label: string } => Boolean(entry.label))
    .map(({ row, label }) => ({
      indicatorId: row.indicator_id,
      label,
      cells: row.cells.map((cell) => ({ period: cell.period, value: cell.value, pctile: cell.pctile })),
    }))
  if (!rows.length) return { body: null, pointCount: 0 }
  const pointCount = rows.reduce(
    (total, row) => total + row.cells.filter((cell) => typeof cell.value === "number").length,
    0,
  )
  return { body: { kind: "heatmap", rows, unit }, pointCount }
}

/**
 * Build the figure for one `charts[]` record. Kinds the judge pages do not draw
 * (map, scatter, stacked bars) and table records return null so the page can skip
 * them instead of showing an empty frame.
 */
export function figureFromChart(monitor: Monitor, chart: Chart, options?: { heatmap?: HeatRow[] }): FigureModel | null {
  if (!["line", "bar", "range", "heatmap"].includes(chart.kind)) return null
  const sourceIds = chart.source_ids.filter((id) => monitor.sources.some((source) => source.id === id))
  if (!sourceIds.length) return null
  const trust = trustFor(monitor, { sourceIds, indicatorIds: chart.indicator_ids })
  if (!trust) return null
  if (!chart.title_vi?.trim()) return null

  const unit = indicatorById(monitor, chart.indicator_ids[0] ?? "")?.unit
  const frequency = indicatorById(monitor, chart.indicator_ids[0] ?? "")?.frequency ?? null
  const sourceName = trust.sourceName
  const built =
    chart.kind === "line"
      ? lineBody(monitor, chart, sourceName, unit)
      : chart.kind === "bar"
        ? barBody(monitor, chart, sourceName, unit)
        : chart.kind === "range"
          ? rangeBody(monitor, chart, unit)
          : heatBody(monitor, chart, options?.heatmap ?? [], unit)

  return {
    id: chart.id,
    number: typeof chart.number === "number" ? chart.number : null,
    title: chart.title_vi,
    ariaLabel: chart.title_vi,
    body: built.body,
    sourceIds,
    pointCount: built.pointCount,
    frequency,
    note: chart.note_vi?.trim() ? chart.note_vi : null,
    trust,
  }
}

/** The one overview-level line chart for the front page. */
export function overviewFigure(monitor: Monitor, sectorOrder: readonly SectorId[] = SECTOR_IDS): FigureModel | null {
  const charts = sectorOrder.flatMap((id) => monitor.sectors[id]?.charts ?? [])
  const chart =
    charts.find((item) => item.kind === "line" && item.level === "overview") ??
    charts.find((item) => item.kind === "line")
  return chart ? figureFromChart(monitor, chart) : null
}
