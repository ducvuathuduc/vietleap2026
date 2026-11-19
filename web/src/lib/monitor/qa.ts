import { sqlTruthNumbers, ungroundedNumbers } from "../analyst/story.ts"
import { formatPeriod, formatWithUnit } from "./format.ts"
import { indicatorById, sourceById } from "./lookup.ts"
import type { Indicator, Monitor, ProvinceRow, SectorId } from "./types.ts"

const SECTORS: readonly SectorId[] = ["public_finance", "fdi", "banking", "capital_market", "real_estate"]

export interface IndicatorListItem {
  id: string
  name_vi: string
  sector: string
  unit: string
  latest: { period: string; value: number | null }
  source_id: string
  source_publisher: string
}

export interface IndicatorDetail {
  id: string
  name_vi: string
  definition_vi: string
  unit: string
  latest: { period: string; value: number | null }
  sparkline: { period: string; value: number | null }[]
  source: { id: string; publisher: string; title_vi: string; url: string; data_cutoff: string } | null
}

export interface SectorDetail {
  key: SectorId
  question_vi: string
  headline_vi: string
  cards: {
    value: number
    unit: string
    period: string
    sentence_vi: string
    source_id: string
    indicator_id: string | null
  }[]
  tables: { id: string; title_vi: string; row_count: number; columns: string[]; source_ids: string[] }[]
}

export interface ProvinceRecord {
  code: string
  name: string
  region: string
  metrics: { id: string; name_vi: string; unit: string; value: number | null }[]
}

export interface ProvinceRanking {
  metric: string
  name_vi: string | null
  unit: string | null
  period: string | null
  sources: { publisher: string; title_vi: string }[]
  ranking: { code: string; name: string; value: number | null; rank: number | null }[]
}

export interface RecommendationView {
  id: string
  title_vi: string
  evidence: { rule_id: string; chart_id: string; fact_vi: string }[]
  so_what_vi: string
  action_vi: string
  agency_vi: string
  horizon_vi: string
  caveat_vi: string | null
}

export interface RuleView {
  id: string
  name_vi: string
  formula_vi: string
  threshold_vi: string
  fired: boolean
  agency_vi: string | null
}

function fold(value: string): string {
  return value.trim().toLocaleLowerCase("vi")
}

function finite(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

export function listIndicators(monitor: Monitor): IndicatorListItem[] {
  return monitor.indicators.map((indicator) => ({
    id: indicator.id,
    name_vi: indicator.name_vi,
    sector: indicator.sector,
    unit: indicator.unit,
    latest: { period: indicator.latest.period, value: finite(indicator.latest.value) },
    source_id: indicator.source_id,
    source_publisher: sourceById(monitor, indicator.source_id)?.publisher ?? indicator.source_id,
  }))
}

export function getIndicator(monitor: Monitor, id: string): IndicatorDetail | null {
  const needle = fold(id)
  const indicator = monitor.indicators.find((item) => item.id === id || fold(item.id) === needle)
  if (!indicator) return null
  const source = sourceById(monitor, indicator.source_id)
  return {
    id: indicator.id,
    name_vi: indicator.name_vi,
    definition_vi: indicator.definition_vi,
    unit: indicator.unit,
    latest: { period: indicator.latest.period, value: finite(indicator.latest.value) },
    sparkline: indicator.sparkline.slice(-36).map((point) => ({ period: point.period, value: finite(point.value) })),
    source: source
      ? {
          id: source.id,
          publisher: source.publisher,
          title_vi: source.title_vi,
          url: source.url,
          data_cutoff: source.data_cutoff,
        }
      : null,
  }
}

export function getSector(monitor: Monitor, key: string): SectorDetail | null {
  const sectorId = SECTORS.find((id) => id === fold(key))
  if (!sectorId) return null
  const sector = monitor.sectors[sectorId]
  if (!sector) return null
  return {
    key: sectorId,
    question_vi: sector.question_vi,
    headline_vi: sector.headline_vi,
    cards: sector.cards.map((card) => ({
      value: card.value,
      unit: card.unit,
      period: card.period,
      sentence_vi: card.sentence_vi,
      source_id: card.source_id,
      indicator_id: card.indicator_id ?? null,
    })),
    tables: sector.tables.map((table) => ({
      id: table.id,
      title_vi: table.title_vi,
      row_count: table.rows.length,
      columns: table.columns.map((column) => column.label_vi),
      source_ids: table.source_ids,
    })),
  }
}

function resolveMetric(monitor: Monitor, metric: string): string | null {
  const needle = fold(metric)
  if (!needle) return null
  const indicator = monitor.indicators.find((item) => fold(item.id) === needle || fold(item.name_vi) === needle)
  if (indicator) return indicator.id
  return monitor.province.metric_ids.find((id) => fold(id) === needle) ?? null
}

function provinceRecord(monitor: Monitor, row: ProvinceRow): ProvinceRecord {
  const ids = monitor.province.metric_ids.length ? monitor.province.metric_ids : Object.keys(row.metrics)
  return {
    code: row.code,
    name: row.name,
    region: row.region,
    metrics: ids.map((id) => {
      const indicator = indicatorById(monitor, id)
      return { id, name_vi: indicator?.name_vi ?? id, unit: indicator?.unit ?? "", value: finite(row.metrics[id]) }
    }),
  }
}

export function getProvince(monitor: Monitor, query: { code?: string; metric?: string }): ProvinceRecord | ProvinceRanking | null {
  const metric = query.metric?.trim() ? resolveMetric(monitor, query.metric) : null
  if (query.metric?.trim()) {
    if (!metric) return null
    const known = monitor.province.metric_ids.includes(metric) || monitor.province.rows.some((row) => metric in row.metrics)
    if (!known) return null
    const indicator = indicatorById(monitor, metric)
    const rows = monitor.province.rows
      .map((row) => ({ code: row.code, name: row.name, value: finite(row.metrics[metric]) }))
      .sort((a, b) => {
        if (a.value === null && b.value === null) return a.name.localeCompare(b.name, "vi")
        if (a.value === null) return 1
        if (b.value === null) return -1
        return b.value - a.value || a.name.localeCompare(b.name, "vi")
      })
    let next = 0
    return {
      metric,
      name_vi: indicator?.name_vi ?? null,
      unit: indicator?.unit ?? null,
      period: indicator?.latest.period ?? null,
      sources: (monitor.province.source_ids ?? []).flatMap((id) => {
        const source = sourceById(monitor, id)
        return source ? [{ publisher: source.publisher, title_vi: source.title_vi }] : []
      }),
      ranking: rows.map((row) => ({
        code: row.code,
        name: row.name,
        value: row.value,
        rank: row.value === null ? null : ++next,
      })),
    }
  }
  const code = query.code?.trim()
  if (!code) return null
  const needle = fold(code)
  const row = monitor.province.rows.find((item) => fold(item.code) === needle || fold(item.name) === needle)
  return row ? provinceRecord(monitor, row) : null
}

export function getRecommendations(monitor: Monitor): RecommendationView[] {
  return monitor.recommendations.map((item) => ({
    id: item.id,
    title_vi: item.title_vi,
    evidence: item.evidence.map((evidence) => ({
      rule_id: evidence.rule_id,
      chart_id: evidence.chart_id,
      fact_vi: evidence.fact_vi,
    })),
    so_what_vi: item.so_what_vi,
    action_vi: item.action_vi,
    agency_vi: item.agency_vi,
    horizon_vi: item.horizon_vi,
    caveat_vi: item.caveat_vi ?? null,
  }))
}

export function getRules(monitor: Monitor): RuleView[] {
  return (monitor.rules ?? []).map((rule) => ({
    id: rule.id,
    name_vi: rule.name_vi,
    formula_vi: rule.formula_vi,
    threshold_vi: rule.threshold_vi,
    fired: rule.fired,
    agency_vi: rule.agency_vi ?? null,
  }))
}

function prosePeriod(period: string): string {
  if (/^\d{4}-\d{2}$/.test(period)) return `tháng ${formatPeriod(period)}`
  const quarter = /^(\d{4})-Q([1-4])$/.exec(period)
  if (quarter) return `quý ${["I", "II", "III", "IV"][Number(quarter[2]) - 1]}/${quarter[1]}`
  return formatPeriod(period)
}

function sourceLabel(monitor: Monitor, sourceId: string): string {
  const source = sourceById(monitor, sourceId)
  if (!source) return sourceId
  const publisher = source.publisher.trim()
  const title = source.title_vi.trim()
  if (publisher && title) return `${publisher} — ${title}`
  return publisher || title || sourceId
}

function indicatorSentence(monitor: Monitor, indicator: Indicator): string {
  const period = prosePeriod(indicator.latest.period)
  const source = sourceLabel(monitor, indicator.source_id)
  const value = formatWithUnit(indicator.latest.value, indicator.unit)
  if (!value) return `${indicator.name_vi} chưa có số mới nhất (kỳ ${period}). Nguồn: ${source}.`
  return `${indicator.name_vi} ${value} trong ${period}. Nguồn: ${source}.`
}

export function answerOffline(monitor: Monitor, question: string): string {
  const q = fold(question)
  const named = monitor.indicators.filter((indicator) => indicator.name_vi.trim() && q.includes(fold(indicator.name_vi)))
  const picked = named.length ? named : monitor.indicators.slice(0, 8)
  if (!picked.length) return "Chưa có chỉ số đã xuất bản."
  const lines = picked.map((indicator) => indicatorSentence(monitor, indicator))
  return named.length ? lines.join("\n") : `Không khớp tên chỉ số trong câu hỏi.\n${lines.join("\n")}`
}

/** Number tokens in an answer that do not appear in tool outputs. */
export function flaggedNumbers(answer: string, toolOutputs: unknown[]): string[] {
  return ungroundedNumbers(answer, sqlTruthNumbers(toolOutputs))
}

/** 404 unless ENABLE_CHAT is exactly "1". */
export function monitorChatGate(): Response | null {
  if (process.env.ENABLE_CHAT === "1") return null
  return Response.json({ detail: "Not found" }, { status: 404 })
}

export function qaSystemPrompt(): string {
  return [
    "Bạn trả lời câu hỏi về bản số liệu đã xuất bản.",
    "Chỉ dùng tool listIndicators, getIndicator, getSector, getProvince, getRecommendations, getRules.",
    "Trả lời bằng tiếng Việt có dấu, ngắn, một ý một câu.",
    "Mỗi số phải có trong kết quả tool. Kèm publisher và kỳ sau mỗi số, ví dụ 12,3% (NSO, kỳ tháng 10/2026). Chép publisher, không viết tắt và không dùng mã nguồn.",
    "Gọi tool trước khi viết câu trả lời.",
    "Không có số thì viết chưa có số và ghi kỳ cùng nguồn. Không ước lượng.",
    "Trong câu trả lời, dùng tên chỉ số, tên cơ quan và tên tỉnh. Không nêu mã nội bộ.",
    "Không nhắc tên mô hình.",
  ].join("\n")
}
