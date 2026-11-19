import type { Card, Indicator, Monitor, SectorId, Source } from "./types.ts"

export function indicatorById(monitor: Monitor, id: string): Indicator | null {
  return monitor.indicators.find((item) => item.id === id) ?? null
}

export function sourceById(monitor: Monitor, id: string): Source | null {
  return monitor.sources.find((item) => item.id === id) ?? null
}

export function cardsBySector(monitor: Monitor, sector: SectorId): Card[] {
  return monitor.sectors[sector]?.cards ?? []
}
