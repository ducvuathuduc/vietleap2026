/** Types for specs/001-vietleap-insight-kit/contracts/monitor.schema.json (schema_version 1). */

export type SchemaVersion = 1

export type SectorId = "public_finance" | "fdi" | "banking" | "capital_market" | "real_estate"

export type IndicatorSector = SectorId | "macro" | "asean" | "province"

export type SourceMethod = "db" | "api" | "file" | "scrape" | "social" | "tinyfish" | "pdf"

export type Frequency = "daily" | "weekly" | "monthly" | "quarterly" | "annual" | "snapshot"

export type MeasureType = "level" | "ytd" | "yoy" | "mom" | "share" | "ratio" | "pct_plan" | "index"

export type Direction = "up" | "down" | "flat"

export type Severity = "info" | "watch" | "alert"

export type ChartKind = "line" | "bar" | "stacked_bar" | "map" | "range" | "heatmap" | "scatter" | "table"

export type ChartLevel = "overview" | "drilldown" | "detail"

export type ColumnKind = "text" | "number" | "percent" | "date"

export type ReconciliationVerdict = "match" | "mismatch" | "single_source"

export type ModelLayer = "bronze" | "silver" | "gold"

export interface Point {
  period: string
  value: number | null
  geo?: string
}

export interface Card {
  value: number
  unit: string
  period: string
  sentence_vi: string
  action_vi: string
  source_id: string
  rule_id: string
  indicator_id?: string
  direction?: Direction
  severity?: Severity
}

export interface Chart {
  id: string
  number?: number
  kind: ChartKind
  title_vi: string
  note_vi?: string
  indicator_ids: string[]
  source_ids: string[]
  highlight?: string
  level?: ChartLevel
}

export interface TableColumn {
  key: string
  label_vi: string
  unit?: string
  kind?: ColumnKind
}

export interface MonitorTable {
  id: string
  title_vi: string
  columns: TableColumn[]
  rows: Record<string, unknown>[]
  source_ids: string[]
}

export interface HeatCell {
  period: string
  value: number | null
  pctile: number | null
}

export interface HeatRow {
  indicator_id: string
  cells: HeatCell[]
}

export interface Sector {
  question_vi: string
  headline_vi: string
  cards: Card[]
  watch: string[]
  kpi_ids?: string[]
  heatmap?: HeatRow[]
  charts: Chart[]
  tables: MonitorTable[]
}

export interface Meta {
  generated_at: string
  title_vi: string
  question_vi: string
  lead_vi: string[]
  watch_vi?: string[]
  kpi_ids?: string[]
  headline_card_refs?: string[]
}

export interface Source {
  id: string
  publisher: string
  title_vi: string
  url: string
  method: SourceMethod
  license: string
  robots?: string
  fetched_at: string
  data_cutoff: string
  rows?: number
  next_release?: string | null
}

export interface IndicatorChange {
  vs_period: string
  value: number
  unit: string
}

export interface Indicator {
  id: string
  name_vi: string
  name_en?: string
  sector: IndicatorSector
  unit: string
  frequency: Frequency
  measure_type: MeasureType
  definition_vi: string
  note_vi?: string
  source_id: string
  last_updated: string
  next_release?: string | null
  latest: Point
  change?: IndicatorChange | null
  sparkline: Point[]
  pctile_12m?: number | null
}

export interface ProvinceRow {
  code: string
  name: string
  region: string
  metrics: Record<string, number | null>
  group: number | null
}

export interface ProvinceGroup {
  group: number
  label_vi: string
  min: number
  max: number
  count: number
}

export interface ProvinceStats {
  median?: number
  min?: number
  max?: number
  n?: number
}

export interface Province {
  question_vi?: string
  headline_vi?: string
  metric_ids: string[]
  primary_metric?: string
  rows: ProvinceRow[]
  groups: ProvinceGroup[]
  stats?: Record<string, ProvinceStats>
  source_ids?: string[]
}

export interface AseanRow {
  iso3: string
  name_vi: string
  value: number
  rank: number
}

export interface AseanEntry {
  year: number
  rows: AseanRow[]
  vn_rank: number | null
  n: number
  median?: number
  higher_is_better?: boolean
  source_id: string
}

export interface Evidence {
  rule_id: string
  chart_id: string
  fact_vi: string
}

export interface Recommendation {
  id: string
  title_vi: string
  sector?: string
  evidence: Evidence[]
  so_what_vi: string
  action_vi: string
  agency_vi: string
  horizon_vi: string
  caveat_vi?: string
}

export interface Rule {
  id: string
  name_vi: string
  formula_vi: string
  threshold_vi: string
  fired: boolean
  agency_vi?: string
}

export interface Quality {
  source_id: string
  rows: number
  score_before: number
  score_after: number
  flags: Record<string, number>
}

export interface Reconciliation {
  indicator_id: string
  period: string
  values: Record<string, number>
  diff_pct: number
  tolerance_pct?: number
  verdict: ReconciliationVerdict
  note_vi?: string
}

export interface ModelTable {
  name: string
  layer: ModelLayer
  rows: number
  grain_vi?: string
}

export interface Model {
  erd_mermaid?: string
  tables?: ModelTable[]
}

export interface Monitor {
  schema_version: SchemaVersion
  meta: Meta
  sources: Source[]
  indicators: Indicator[]
  series: Record<string, Point[]>
  sectors: Partial<Record<SectorId, Sector>>
  province: Province
  asean: Record<string, AseanEntry>
  recommendations: Recommendation[]
  rules?: Rule[]
  quality: Quality[]
  reconciliation: Reconciliation[]
  model?: Model
  files?: Record<string, string>
}
