export type Grade = "verified" | "single" | "contested"

export interface ReaderQuote {
  reader: string
  value: number
  source_url: string
  observed_at: string
}

export interface SnapshotRate {
  term_months: number
  channel: string
  tier: string
  rate_pct: number
  grade: Grade
  grade_note: string
  readers: ReaderQuote[]
}

export interface BankProfile {
  quarter: string
  metrics: Record<string, number | null>
  percentiles: Record<string, number | null>
  flags: { id: string; text: string; rule_ref: string }[]
  market: Record<string, number | null>
  source: string
}

export interface SnapshotBank {
  code: string
  name_vi: string
  name_en: string
  ticker: string
  ownership: string
  listed: boolean
  sheet_url: string
  sheet_date: string | null
  read_at: string
  rates: SnapshotRate[]
  profile: BankProfile | null
}

export interface Snapshot {
  meta: {
    snapshot_id: string
    generated_at: string
    run_ids: string[]
    coverage: {
      banks_total: number
      banks_read: number
      rows: number
      verified: number
      single: number
      contested: number
    }
    quality: { id: string; name: string; status: "pass" | "warn" | "fail"; detail: string }[]
    sources: { id: string; publisher: string; url: string; licence: string; method: string }[]
  }
  policy: {
    ceiling: { pct: number; terms: string; legal_ref: string; valid_from: string }
    cap: { vnd: number; legal_ref: string; valid_from: string }
    premium: { pct: number; legal_ref: string }
    insured_coverage: { depositors_pct: number; value_pct: number; basis: string; source: string }
  }
  banks: SnapshotBank[]
  market: {
    ceiling_stats: {
      quotes_1_5m: number
      at_ceiling: number
      above: number
      jump_5_6_pp_median: number | null
      n_banks: number
      grade_basis: string
    }
    interbank: unknown[]
    omo: unknown[]
    central_fx: unknown[]
  }
  macro: { cpi_yoy: unknown[]; sbv_monthly: unknown[] }
  changes: unknown[]
  geo: {
    provinces: {
      pcode: string
      name_vi: string
      name_en: string
      branches_total: number | null
      branches_by_bank: Record<string, number>
      branch_source: string | null
      population: number | null
      population_period: string | null
      deposits_bn: number | null
      credit_bn: number | null
      deposit_period: string | null
      deposit_source: string | null
      best_counter_12m: { bank: string; rate_pct: number; grade: Grade } | null
    }[]
    boundary: string
    attribution: string
    population_basis?: string
  }
}
