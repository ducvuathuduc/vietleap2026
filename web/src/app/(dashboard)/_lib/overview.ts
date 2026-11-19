/**
 * Page 1 (`/`) mapping: meta, KPI strip, headline cards, the overview chart,
 * "Cần theo dõi" and the top recommendations.
 */
import type { Card, Meta, Monitor, SectorId } from "../../../lib/monitor/types.ts"
import { indicatorById } from "../../../lib/monitor/lookup.ts"
import { overviewFigure, type FigureModel } from "./chart-block.ts"
import {
  DEFINITIONS_HREF,
  RECOMMENDATIONS_HREF,
  SECTOR_IDS,
  footerModel,
  hasNumber,
  insightCard,
  kpiModel,
  sectorTitle,
  trustFor,
  type FooterModel,
  type InsightCardModel,
  type KpiModel,
  type TrustModel,
} from "./common.ts"

const MAX_KPIS = 6
const MAX_CARDS = 3
const MAX_WATCH = 4
const MAX_RECOMMENDATIONS = 3

export interface OverviewModel {
  level: "overview"
  headline: string
  lead: string[]
  generatedAt: string
  actions: { label: string; href: string }[]
  kpis: KpiModel[]
  kpiTrust: TrustModel | null
  cards: InsightCardModel[]
  figure: FigureModel | null
  watch: { text: string }[]
  recommendations: { id: string; href: string; title: string; meta: string }[]
  footer: FooterModel
}

function resolveCardRef(monitor: Monitor, ref: string): { sector: SectorId; card: Card } | null {
  for (const sector of SECTOR_IDS) {
    const card = monitor.sectors[sector]?.cards.find((item) => item.rule_id === ref)
    if (card) return { sector, card }
  }
  const match = /^([a-z_]+)(?:[#:](\d+))?$/.exec(ref)
  if (!match) return null
  const sector = match[1] as SectorId
  if (!SECTOR_IDS.includes(sector)) return null
  const card = monitor.sectors[sector]?.cards[Number(match[2] ?? 0)]
  return card ? { sector, card } : null
}

/** `meta.headline_card_refs` first (rule id, `<sector>#<index>` or `<sector>`), then every sector in nav order. */
function headlineCards(monitor: Monitor): InsightCardModel[] {
  const explicit = (monitor.meta.headline_card_refs ?? [])
    .map((ref) => resolveCardRef(monitor, ref))
    .filter((entry): entry is { sector: SectorId; card: Card } => Boolean(entry))
  const fallback = SECTOR_IDS.flatMap((sector) =>
    (monitor.sectors[sector]?.cards ?? []).map((card) => ({ sector, card })),
  )
  const cards: InsightCardModel[] = []
  const seen = new Set<string>()
  for (const { sector, card } of [...explicit, ...fallback]) {
    const key = `${sector}|${card.rule_id}|${card.period}`
    if (seen.has(key)) continue
    seen.add(key)
    const model = insightCard(monitor, card, sectorTitle(sector))
    if (model) cards.push(model)
    if (cards.length === MAX_CARDS) break
  }
  return cards
}

/**
 * H1 must be a conclusion with a number and a period. The payload title carries one
 * once the writer emits it; until then fall back to the first numeric card sentence.
 */
export function overviewHeadline(meta: Meta, cards: InsightCardModel[]): string {
  if (hasNumber(meta.title_vi)) return meta.title_vi
  const card = cards.find((item) => hasNumber(item.sentence))
  return card ? card.sentence : meta.title_vi
}

function kpiStrip(monitor: Monitor): KpiModel[] {
  const ids = (monitor.meta.kpi_ids ?? []).slice(0, MAX_KPIS)
  return ids.map((id) => kpiModel(monitor, id)).filter((item): item is KpiModel => Boolean(item))
}

/** Lead sentences that a card already says verbatim are dropped, unless that would empty the lead. */
function leadSentences(monitor: Monitor, headline: string, cards: InsightCardModel[]): string[] {
  const said = new Set(cards.map((card) => card.sentence))
  const unique = (monitor.meta.lead_vi ?? []).filter((sentence) => sentence.trim() && sentence !== headline)
  const fresh = unique.filter((sentence) => !said.has(sentence))
  return fresh.length ? fresh : unique
}

export function overviewPage(monitor: Monitor): OverviewModel {
  const cards = headlineCards(monitor)
  const headline = overviewHeadline(monitor.meta, cards)
  const visibleCards = cards.filter((card) => card.sentence !== headline)
  const kpis = kpiStrip(monitor)
  const kpiSourceIds = kpis
    .map((kpi) => indicatorById(monitor, kpi.id)?.source_id)
    .filter((id): id is string => Boolean(id))
  const figure = overviewFigure(monitor)
  const actions = [{ label: "Xem dữ liệu", href: DEFINITIONS_HREF }]

  return {
    level: "overview",
    headline,
    lead: leadSentences(monitor, headline, visibleCards),
    generatedAt: monitor.meta.generated_at,
    actions,
    kpis,
    kpiTrust: kpis.length ? trustFor(monitor, { sourceIds: [...new Set(kpiSourceIds)], indicatorIds: kpis.map((kpi) => kpi.id) }) : null,
    cards: visibleCards,
    figure: figure ? { ...figure, number: figure.number ?? 1 } : null,
    watch: (monitor.meta.watch_vi ?? [])
      .filter((sentence) => sentence.trim())
      .slice(0, MAX_WATCH)
      .map((text) => ({ text })),
    recommendations: monitor.recommendations.slice(0, MAX_RECOMMENDATIONS).map((item) => ({
      id: item.id,
      href: `${RECOMMENDATIONS_HREF}#${item.id}`,
      title: item.title_vi,
      meta: [item.agency_vi, item.horizon_vi].filter(Boolean).join(" · "),
    })),
    footer: footerModel(monitor),
  }
}
