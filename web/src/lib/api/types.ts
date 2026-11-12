// Types mirroring the FastAPI responses (api/schemas.py + engine results.json).

export type Domain = "property" | "public_finance" | "firm" | "generic"
export type Role = "numeric" | "category" | "geo" | "geo_raw" | "time" | "id" | "text" | "flag" | "constant" | "alias" | "empty" | "?"

export interface DatasetSummary {
  id: string
  name: string
  domain: Domain
  rows: number
  target: string
  source_file: string
  created: string | null
}

export interface Meta {
  name: string
  source_file: string
  domain: Domain
  target: string
  time_col: string | null
  geo_col: string | null
  rows: number
  columns: number
  roles: Record<string, Role>
  domain_metrics: string[]
  category_cols: string[]
  created: string
}

export interface Kpi {
  label: string
  label_vi: string
  value: string
  raw: number | null
  delta_pct: number | null
  footer: string
  description: string
}

export type ChartKind = "bar" | "hbar" | "line" | "scatter"

export interface ChartSpec {
  kind: ChartKind
  x: (string | number | null)[]
  series: { name: string; data: (number | null)[] }[]
  x_label?: string
  y_label?: string
}

export interface Insight {
  id: string
  rank: number
  type: string
  title_en: string
  title_vi: string
  sentence_en: string
  sentence_vi: string
  value: unknown
  test: string
  effect: number | null
  p_value: number | null
  relevance: number | null
  score: number
  chart: ChartSpec | null
  chart_png?: string
  evidence: Record<string, unknown>
  columns: string[]
  caveat: string | null
}

export interface Recommendation {
  so_what_en: string
  now_what_en: string
  impact_en: string
  so_what_vi: string
  now_what_vi: string
  impact_vi: string
  from_insight: string
  type: string
  confidence: "high" | "medium"
}

export interface DatasetDetail {
  meta: Meta
  kpis: Kpi[]
  caveats: string[]
  timings: Record<string, number> | null
  files: Record<string, string | number | null>
  recommendations: Recommendation[]
}

export interface ColumnProfile {
  name: string
  role: Role
  dtype: string
  missing_pct: number
  unique: number
  mean?: number
  median?: number
  std?: number
  min?: number | string
  max?: number | string
  skew?: number
  outliers?: number
  hist?: { counts: number[]; edges: number[] }
  top_values?: { value: string; count: number }[]
}

export interface QualityIssue {
  severity: "high" | "medium" | "low"
  column: string
  issue: string
}

export interface ProfileResponse {
  profile: {
    rows: number
    columns: number
    missing_overall_pct: number
    outlier_rows_pct: number
    roles: Record<string, number>
    column_profiles: ColumnProfile[]
    issues: QualityIssue[]
  }
  cleaning_log: string[]
  caveats: string[]
}

export interface TimePoint {
  period: string
  value: number | null
  n: number
}

export interface TimeSeriesResponse {
  time: string | null
  metric: string | null
  agg: string
  freq: string | null
  points: TimePoint[]
}

export interface RowsResponse {
  columns: { name: string; role: Role }[]
  rows: Record<string, string | number | boolean | null>[]
  total: number
  page: number
  page_size: number
}

export interface GroupRow {
  n: number
  mean: number | null
  median: number | null
  sum: number | null
  std: number | null
  [key: string]: string | number | null
}

export interface ClusterProfile {
  cluster: number
  size: number
  share: number
  medians: Record<string, number | null>
  distinctive: { feature: string; z: number; median: number | null; overall_median: number | null }[]
}

export interface SegmentsResponse {
  by: string
  metric: string
  groups: GroupRow[]
  groups_total: number
  test: Record<string, unknown> & {
    kruskal?: { H: number; p: number; epsilon2: number }
    top?: { group: string; median: number; n: number }
    bottom?: { group: string; median: number; n: number }
    top_vs_bottom?: { p: number; rank_biserial: number; median_ratio: number }
  }
  options: string[]
  clusters: { k: number; silhouette: number; features: string[]; profiles: ClusterProfile[] } | null
}

export interface DriversResponse {
  target: string
  drivers: {
    n: number
    features: string[]
    leakage_excluded: string[]
    log_target: boolean
    cv_r2: { ridge_mean: number; ridge_std: number; gb_mean: number; gb_std: number }
    importance: { feature: string; importance: number; std: number }[]
    coefficients: { feature: string; coef_std: number; ci90: [number, number]; direction: "+" | "-"; stable: boolean }[]
    note: string
  } | null
  whatif_features: { name: string; mean: number; sd: number; median: number | null }[]
}

export interface WhatIfResult {
  feature: string
  pct_change: number
  target: string
  target_change_pct: number | null
  ci90_pct: [number | null, number | null]
  target_change_abs: number | null
  baseline_target_mean: number | null
  interpretation: string
}

export interface WhatIfCurve {
  feature: string
  points: { pct: number; change: number; low: number; high: number }[]
}

export interface Job {
  id: string
  status: "queued" | "running" | "done" | "error"
  dataset_id: string | null
  error: string | null
  started: number
  finished: number | null
}

export interface AgentConfig {
  mode: "llm" | "offline"
  model: string | null
  base_url: string | null
  tools: string[]
}

export type AgentEvent =
  | { type: "status" | "plan"; text: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; ok: boolean; summary: string }
  | { type: "chart"; spec: ChartSpec; source: string }
  | { type: "table"; columns: string[]; rows: (string | number | null)[][]; source: string }
  | { type: "token"; text: string }
  | { type: "replace" }
  | { type: "verification"; verified: string[]; unverified: string[]; ok: boolean; mode: "llm" | "fallback" }
  | { type: "error"; text: string }
  | { type: "done"; text: string }

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
}
