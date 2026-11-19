/**
 * Pure helpers behind the judge pages. Each one turns a slice of monitor.json into
 * the props a kit component takes. No JSX and no framework imports, so `node --test`
 * can exercise them directly.
 */
import { formatNumber, formatPeriod, formatWithUnit } from "../../../lib/monitor/format.ts"
import { indicatorById, sourceById } from "../../../lib/monitor/lookup.ts"
import type {
  Card,
  Direction,
  Indicator,
  IndicatorChange,
  Monitor,
  Point,
  SectorId,
  Severity,
} from "../../../lib/monitor/types.ts"
import { SECTORS } from "../../../lib/nav.ts"

export const DEFINITIONS_HREF = "/phuong-phap"
export const RECOMMENDATIONS_HREF = "/khuyen-nghi"

export const SECTOR_IDS: SectorId[] = SECTORS.map((sector) => sector.id)

export interface TrustModel {
  sourceName: string
  lastUpdated: string | null
  nextRelease: string | null
  links: { data: string; definition: string }
}

export interface FooterModel {
  sources: { name: string; license: string }[]
  generatedAt: string
}

export interface KpiModel {
  id: string
  name: string
  value: string
  unit?: string
  period?: string
  change: { text: string; direction?: Direction; severity?: Severity } | null
  sparkline: number[]
}

export interface InsightCardModel {
  eyebrow?: string
  value: string
  unit?: string
  period?: string
  sentence: string
  action: { text: string; href?: string } | null
  source: string | null
  indicatorHref?: string
}

export interface SectorTab {
  id: SectorId
  label: string
  href: string
  active: boolean
}

export function indicatorHref(id: string): string {
  return `${DEFINITIONS_HREF}#indicator-${id}`
}

export function hasNumber(text: string | null | undefined): boolean {
  return typeof text === "string" && /\d/.test(text)
}

export function sectorMeta(id: SectorId) {
  return SECTORS.find((sector) => sector.id === id) ?? null
}

export function sectorHref(id: SectorId): string {
  const meta = sectorMeta(id)
  return meta ? `/nganh/${meta.slug}` : "/nganh"
}

export function sectorTitle(id: SectorId): string {
  return sectorMeta(id)?.title ?? id
}

/** Unknown slugs stay `null` so the route can call notFound(). */
export function sectorIdFromSlug(slug: string): SectorId | null {
  return SECTORS.find((sector) => sector.slug === slug)?.id ?? null
}

export function sectorTabs(active: SectorId | null): SectorTab[] {
  return SECTORS.map((sector) => ({
    id: sector.id,
    label: sector.title,
    href: `/nganh/${sector.slug}`,
    active: sector.id === active,
  }))
}

export function indicatorName(monitor: Monitor, id: string): string | null {
  const name = indicatorById(monitor, id)?.name_vi?.trim()
  return name ? name : null
}

export function seriesPoints(monitor: Monitor, id: string): Point[] {
  return monitor.series[id] ?? []
}

export function finitePoints(points: Point[]): { period: string; value: number }[] {
  const out: { period: string; value: number }[] = []
  for (const point of points) {
    if (typeof point.value === "number" && Number.isFinite(point.value)) {
      out.push({ period: point.period, value: point.value })
    }
  }
  return out
}

/**
 * A line chart on pages 1–3 only ever shows the national path. Country rows carry
 * `geo`, so prefer points without one, then VNM, then a single-geo series.
 */
export function nationalPoints(points: Point[]): Point[] {
  const national = points.filter((point) => !point.geo)
  if (national.length) return national
  const vietnam = points.filter((point) => point.geo === "VNM")
  if (vietnam.length) return vietnam
  const geos = new Set(points.map((point) => point.geo).filter((geo): geo is string => Boolean(geo)))
  return geos.size === 1 ? points : []
}

export function medianOf(values: number[]): number | null {
  const finite = values.filter((value) => Number.isFinite(value)).sort((left, right) => left - right)
  if (!finite.length) return null
  const middle = Math.floor(finite.length / 2)
  return finite.length % 2 === 1 ? finite[middle] : (finite[middle - 1] + finite[middle]) / 2
}

/** Percentage gaps are percentage points, never "pp", and keep any suffix ("% GDP" → "điểm % GDP"). */
export function gapUnit(unit: string): string {
  if (unit === "%") return "điểm %"
  if (unit.startsWith("% ")) return `điểm %${unit.slice(1)}`
  return unit
}

export function formatGap(value: number, unit: string): string {
  const sign = value > 0 ? "+" : ""
  return `${sign}${formatWithUnit(value, gapUnit(unit))}`
}

export function publisherList(monitor: Monitor, sourceIds: string[]): string {
  const names = sourceIds
    .map((id) => sourceById(monitor, id)?.publisher?.trim())
    .filter((name): name is string => Boolean(name))
  return [...new Set(names)].join(", ")
}

function latestStamp(values: (string | null | undefined)[]): string | null {
  const stamps = values.filter((value): value is string => Boolean(value && value.trim()))
  if (!stamps.length) return null
  return stamps.reduce((latest, value) => (value > latest ? value : latest))
}

/**
 * Citation line for a block: publishers plus the newest update stamp. Returns null
 * when no source resolves, which means the block must not render at all.
 */
export function trustFor(
  monitor: Monitor,
  input: { sourceIds: string[]; indicatorIds?: string[] },
): TrustModel | null {
  const sourceName = publisherList(monitor, input.sourceIds)
  if (!sourceName) return null
  const indicators = (input.indicatorIds ?? [])
    .map((id) => indicatorById(monitor, id))
    .filter((item): item is Indicator => Boolean(item))
  const sources = input.sourceIds.map((id) => sourceById(monitor, id)).filter((item) => Boolean(item))
  const lastUpdated =
    latestStamp(indicators.map((item) => item.last_updated)) ??
    latestStamp(sources.map((item) => item?.fetched_at))
  const nextRelease =
    indicators.find((item) => item.next_release)?.next_release ??
    sources.find((item) => item?.next_release)?.next_release ??
    null
  const definitionId = (input.indicatorIds ?? [])[0]
  return {
    sourceName,
    lastUpdated,
    nextRelease: nextRelease ?? null,
    links: {
      data: DEFINITIONS_HREF,
      definition: definitionId ? indicatorHref(definitionId) : DEFINITIONS_HREF,
    },
  }
}

export function footerModel(monitor: Monitor): FooterModel {
  return {
    sources: monitor.sources.map((source) => ({ name: source.publisher, license: source.license })),
    generatedAt: monitor.meta.generated_at,
  }
}

function changeModel(change: IndicatorChange | null | undefined): KpiModel["change"] {
  if (!change || !Number.isFinite(change.value)) return null
  if (!change.unit?.trim() || !change.vs_period?.trim()) return null
  const sign = change.value > 0 ? "+" : ""
  return { text: `${sign}${formatWithUnit(change.value, change.unit)} so với ${formatPeriod(change.vs_period)}` }
}

/**
 * One KPI tile. A value without unit, period or a registered source is dropped
 * instead of rendered half-cited.
 */
export function kpiModel(monitor: Monitor, id: string): KpiModel | null {
  const indicator = indicatorById(monitor, id)
  if (!indicator) return null
  const value = indicator.latest?.value
  if (typeof value !== "number" || !Number.isFinite(value)) return null
  if (!indicator.unit?.trim() || !indicator.latest.period?.trim()) return null
  if (!sourceById(monitor, indicator.source_id)) return null
  const name = indicator.name_vi?.trim()
  if (!name) return null
  return {
    id,
    name,
    value: formatNumber(value),
    unit: indicator.unit,
    period: formatPeriod(indicator.latest.period),
    change: changeModel(indicator.change),
    sparkline: indicator.sparkline
      .map((point) => point.value)
      .filter((point): point is number => typeof point === "number" && Number.isFinite(point)),
  }
}

/** rule_id → recommendation anchor, built from `recommendations[].evidence`. */
export function recommendationByRule(monitor: Monitor): Map<string, string> {
  const out = new Map<string, string>()
  for (const recommendation of monitor.recommendations) {
    for (const evidence of recommendation.evidence) {
      if (!out.has(evidence.rule_id)) out.set(evidence.rule_id, recommendation.id)
    }
  }
  return out
}

/**
 * One insight card: number, sentence, action and source. Cards missing any of the
 * four (or whose source is unregistered) are dropped.
 */
export function insightCard(monitor: Monitor, card: Card, fallbackEyebrow?: string): InsightCardModel | null {
  if (typeof card.value !== "number" || !Number.isFinite(card.value)) return null
  if (!card.unit?.trim() || !card.period?.trim() || !card.sentence_vi?.trim()) return null
  const source = sourceById(monitor, card.source_id)
  if (!source) return null
  const indicator = card.indicator_id ? indicatorById(monitor, card.indicator_id) : null
  const recommendation = recommendationByRule(monitor).get(card.rule_id)
  const action = card.action_vi?.trim()
  return {
    eyebrow: indicator?.name_vi ?? fallbackEyebrow,
    value: formatNumber(card.value),
    unit: card.unit,
    period: formatPeriod(card.period),
    sentence: card.sentence_vi,
    action: action ? { text: action, href: recommendation ? `${RECOMMENDATIONS_HREF}#${recommendation}` : undefined } : null,
    source: `Nguồn ${source.publisher}`,
    indicatorHref: indicator ? indicatorHref(indicator.id) : undefined,
  }
}
