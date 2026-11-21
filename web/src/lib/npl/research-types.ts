export type Indicator = {
  id: string
  name_vi: string
  name_en: string
  unit: "ratio" | "times"
  direction: "higher_worse" | "higher_better" | "higher_faster" | "not_scored"
  scored: boolean
}

export type ScorecardRow = {
  bank_code: string
  period: string
  values: Record<string, number | null>
  percentiles: Record<string, number | null>
  n_asset: number
  composite: number | null
}

export type ScorecardGap = {
  bank_code: string
  period: string
  npl_place: number
  composite_place: number
  places: number
  direction: "npl_looks_better" | "npl_looks_worse"
  drivers: string[]
}

export type Scorecard = {
  indicators: Indicator[]
  rows?: ScorecardRow[]
  by_quarter: { period: string; n: number; spearman: number | null }[]
  rank_gaps: Record<string, ScorecardGap[]>
  disagreement: { n_fell: number; n_worsened: number; share: number | null }
  reading_vi: string
  reading_en: string
}

export type SeasonalRow = {
  bank_code: string
  period: string
  reported_npl_pct: number | null
  adjusted_npl_pct: number | null
  adjusted_change_pp: number | null
}

export type SeasonalAdjustment = {
  series: SeasonalRow[]
  latest: SeasonalRow[]
  q4_declines: { bank_code: string; period: string; seasonal_only: boolean | null }[]
  counts: { reported: number; adjustable: number; seasonal_only: number; seasonal_only_pct: number | null }
  reading_vi: string
  reading_en: string
}

type Metric = { estimate: number | null; ci95: number[] | null }
export type ForecastComparison = {
  n_test: number
  test_events?: number
  fits: Partial<Record<"npl_only" | "npl_group2" | "full", { auc?: Metric; brier?: Metric; mae?: Metric }>>
}

export type EarlyWarning = {
  event_threshold_pp: number
  train_through: string
  backtests: { rise_in_four: ForecastComparison }
  reading_vi: string
  reading_en: string
}

export type ResearchContext = {
  early_warning?: EarlyWarning
  seasonal_adjustment?: SeasonalAdjustment
}

export type PdfAudit = {
  headline: { matched: number; comparable: number; rate: number | null }
  all_rows: { matched: number; rows: number; rate: number | null }
}

export type PanelCoefficient = { coefficient: number; ci95: (number | null)[]; p: number | null; wild_p?: number | null }
export type PanelFit = { n: number; clusters?: number; terms: Record<string, PanelCoefficient>; period?: string[]; unavailable_reason?: string }
export type MentorRegression = {
  full: PanelFit
  without_writeoff?: PanelFit | null
  available: PanelFit | null
  does_not_show_vi?: string
  does_not_show_en?: string
}
