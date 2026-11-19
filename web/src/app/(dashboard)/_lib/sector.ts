/**
 * Page 3 (`/nganh/[sector]`) mapping: headline, ≤3 cards, charts by kind, the
 * monthly percentile heatmap, sortable tables, the watch list and one "Điều cần
 * biết" box per KPI indicator.
 */
import { formatNumber, formatPeriod } from "../../../lib/monitor/format.ts"
import { indicatorById } from "../../../lib/monitor/lookup.ts"
import type { Indicator, Monitor, SectorId } from "../../../lib/monitor/types.ts"
import { figureFromChart, type FigureModel } from "./chart-block.ts"
import {
  footerModel,
  hasNumber,
  indicatorName,
  insightCard,
  sectorTabs,
  sectorTitle,
  trustFor,
  type FooterModel,
  type InsightCardModel,
  type SectorTab,
} from "./common.ts"
import type { TableModel } from "./asean.ts"

const MAX_CARDS = 3
const MAX_KNOW_BOXES = 6
const MAX_WATCH = 4

export interface KnowBoxModel {
  id: string
  name: string
  definition: string
  note: string | null
  unit: string | null
  frequency: string | null
}

export interface SectorModel {
  level: "drilldown"
  sector: SectorId
  title: string
  headline: string
  tabs: SectorTab[]
  hasData: boolean
  cards: InsightCardModel[]
  figures: FigureModel[]
  heatmap: FigureModel | null
  tables: TableModel[]
  watch: { text: string }[]
  knowBoxes: KnowBoxModel[]
  footer: FooterModel
}

function heatmapFigure(monitor: Monitor, sector: SectorId): FigureModel | null {
  const record = monitor.sectors[sector]
  const rows = record?.heatmap ?? []
  if (!record || !rows.length) return null
  const chart = record.charts.find((item) => item.kind === "heatmap")
  if (chart) {
    const figure = figureFromChart(monitor, chart, { heatmap: rows })
    if (figure) return figure
  }
  const labels = rows
    .map((row) => ({ row, label: indicatorName(monitor, row.indicator_id) }))
    .filter((entry): entry is { row: (typeof rows)[number]; label: string } => Boolean(entry.label))
  const periods = [...new Set(rows.flatMap((row) => row.cells.map((cell) => cell.period)))].sort()
  const span = periods.length ? `${formatPeriod(periods[0])}–${formatPeriod(periods[periods.length - 1])}` : null
  const sourceIds = [
    ...new Set(
      rows
        .map((row) => indicatorById(monitor, row.indicator_id)?.source_id)
        .filter((id): id is string => Boolean(id)),
    ),
  ]
  const trust = trustFor(monitor, { sourceIds, indicatorIds: rows.map((row) => row.indicator_id) })
  if (!trust || !labels.length) return null
  const title = span
    ? `Phân vị 12 tháng của ${formatNumber(labels.length)} chỉ số, ${span}.`
    : `Phân vị 12 tháng của ${formatNumber(labels.length)} chỉ số.`
  return {
    id: `${sector}-heatmap`,
    number: null,
    title,
    ariaLabel: title,
    body: {
      kind: "heatmap",
      rows: labels.map(({ row, label }) => ({
        indicatorId: row.indicator_id,
        label,
        cells: row.cells.map((cell) => ({ period: cell.period, value: cell.value, pctile: cell.pctile })),
      })),
      unit: indicatorById(monitor, rows[0].indicator_id)?.unit,
    },
    sourceIds,
    pointCount: rows.reduce((total, row) => total + row.cells.filter((cell) => typeof cell.value === "number").length, 0),
    frequency: "monthly",
    note: null,
    trust,
  }
}

export function sectorPage(monitor: Monitor, sector: SectorId): SectorModel {
  const title = sectorTitle(sector)
  const record = monitor.sectors[sector]
  const emptyHeadline = `Chưa có số liệu đã xuất bản cho ngành ${title}.`

  if (!record) {
    return {
      level: "drilldown",
      sector,
      title,
      headline: emptyHeadline,
      tabs: sectorTabs(sector),
      hasData: false,
      cards: [],
      figures: [],
      heatmap: null,
      tables: [],
      watch: [],
      knowBoxes: [],
      footer: footerModel(monitor),
    }
  }

  const cards = record.cards
    .slice(0, MAX_CARDS)
    .map((card) => insightCard(monitor, card, title))
    .filter((card): card is InsightCardModel => Boolean(card))
  const figures = record.charts
    .filter((chart) => chart.kind === "line" || chart.kind === "bar" || chart.kind === "range")
    .map((chart) => figureFromChart(monitor, chart, { heatmap: record.heatmap ?? [] }))
    .filter((figure): figure is FigureModel => Boolean(figure))
    .map((figure, index) => ({ ...figure, number: figure.number ?? index + 1 }))
  const heatmapFigureModel = heatmapFigure(monitor, sector)
  const heatmap = heatmapFigureModel
    ? { ...heatmapFigureModel, number: heatmapFigureModel.number ?? figures.length + 1 }
    : null
  const tables: TableModel[] = []
  for (const table of record.tables) {
    const trust = trustFor(monitor, { sourceIds: table.source_ids })
    if (!trust || !table.rows.length) continue
    tables.push({
      id: table.id,
      title: table.title_vi,
      columns: table.columns.map((column) => ({
        key: column.key,
        label: column.label_vi,
        unit: column.unit,
        kind: column.kind,
      })),
      rows: table.rows,
      pointCount: table.rows.length,
      sourceIds: table.source_ids,
      trust,
    })
  }

  const knowBoxes = (record.kpi_ids ?? [])
    .slice(0, MAX_KNOW_BOXES)
    .map((id) => ({ id, indicator: indicatorById(monitor, id) }))
    .filter((entry): entry is { id: string; indicator: Indicator } => Boolean(entry.indicator))
    .map(({ id, indicator }) => ({
      id,
      name: indicator.name_vi,
      definition: indicator.definition_vi,
      note: indicator.note_vi?.trim() ? indicator.note_vi : null,
      unit: indicator.unit || null,
      frequency: indicator.frequency,
    }))

  const headline = hasNumber(record.headline_vi)
    ? record.headline_vi
    : (cards[0]?.sentence ?? (record.headline_vi || emptyHeadline))

  return {
    level: "drilldown",
    sector,
    title,
    headline,
    tabs: sectorTabs(sector),
    hasData: Boolean(cards.length || figures.length || heatmap || tables.length),
    cards,
    figures,
    heatmap,
    tables,
    watch: record.watch
      .filter((sentence) => sentence.trim())
      .slice(0, MAX_WATCH)
      .map((text) => ({ text })),
    knowBoxes,
    footer: footerModel(monitor),
  }
}
