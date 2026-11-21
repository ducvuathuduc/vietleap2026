import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3"
import Ajv2020 from "ajv/dist/2020.js"
import addFormats from "ajv-formats"

import seed from "../../../seed/npl/snapshot.json" with { type: "json" }

import schema from "./snapshot.schema.json" with { type: "json" }
import type { MentorRegression, PanelFit } from "./research-types.ts"
import { nextPeriod, type PublishedDecoderRow, type QuarterEffect, type Snapshot, type SnapshotBank, type Term } from "./view.ts"

type WireRegression = PanelFit
type WireDecoderRow = PublishedDecoderRow & { bank_code: string; period: string }
type WireSnapshot = Omit<typeof seed, "banks" | "decoder" | "robustness" | "market" | "decomposition" | "decision_rule" | "context" | "scorecard" | "pdf_audit"> & {
  banks: Omit<SnapshotBank, "quarters" | "quarter_means" | "pairs">[]
  decoder?: {
    rows: WireDecoderRow[]
    fiinquant_rows?: WireDecoderRow[]
    reading_vi?: string
    reading_en?: string
    regression?: { fiinquant?: MentorRegression }
  }
  decomposition?: Snapshot["decomposition"]
  decision_rule?: Snapshot["decision_rule"]
  context?: Snapshot["context"]
  scorecard?: Snapshot["scorecard"]
  pdf_audit?: Snapshot["pdf_audit"]
  robustness: {
    leave_one_bank_out: Snapshot["robustness"]["leave_one_bank_out"]
    drop_2021_2022: WireRegression
    state_vs_private: Partial<Record<"state" | "private", WireRegression>>
    median_regression: WireRegression
  }
  market: Pick<Snapshot["market"], "car_by_day"> & Partial<Omit<Snapshot["market"], "regressions" | "car_by_day">> & {
    regressions: Record<string, WireRegression>
  }
}

// Accept older wire formats for parsing. The reader checks whether an S3
// publication can supply the current pages before serving it.
const readerSchema = {
  ...schema,
  required: schema.required.filter((key) => key !== "decomposition"),
  properties: {
    ...schema.properties,
    market: {
      ...schema.properties.market,
      required: schema.properties.market.required.filter((key) => key !== "m8" && key !== "windows"),
    },
    decision_rule: {
      ...schema.properties.decision_rule,
      required: schema.properties.decision_rule.required.filter((key) => key !== "q4_oos"),
    },
  },
}
const validate = addFormats(new Ajv2020({ strict: false })).compile<WireSnapshot>(readerSchema)
const CACHE_MS = 10 * 60 * 1000
const STAR_SCHEMA = [
  { table: "dim_bank", keys: "bank_code", grain: "Một ngân hàng hoặc chỉ số / bank or index" },
  { table: "dim_period", keys: "period", grain: "Một quý / quarter" },
  { table: "dim_date", keys: "date", grain: "Một ngày giao dịch hoặc mốc công bố / trading or disclosure date" },
  { table: "fact_bank_quarter", keys: "bank_code, period, basis", grain: "Ngân hàng × quý × phạm vi báo cáo / bank × quarter × reporting scope" },
  { table: "fact_bank_market_day", keys: "bank_code, date", grain: "Ngân hàng hoặc chỉ số × phiên / bank or index × session" },
  { table: "fact_report_event", keys: "bank_code, period, basis", grain: "Ngân hàng × quý × phạm vi báo cáo / bank × quarter × reporting scope" },
]
let client: S3Client | undefined
let bundled: Snapshot | undefined
type Selection = { snapshot: Snapshot; source: "s3" | "seed" }
let cached: { uri: string; selection: Selection; expires: number } | undefined
let pending: { uri: string; load: Promise<Selection> } | undefined

function coefficient(fit: WireRegression | undefined, name: string): Term | null {
  const term = fit?.terms[name]
  if (!fit || !term) return null
  return {
    coef_pp: term.coefficient, ci95: term.ci95, p: term.p,
    p_wild_bootstrap: term.wild_p ?? null, n: fit.n, clusters: fit.clusters ?? null,
  }
}

function quarterEffects(fit: WireRegression | undefined): QuarterEffect[] {
  return [2, 3, 4].flatMap((quarter) => {
    const term = coefficient(fit, `Q${quarter}`)
    return term ? [{ quarter, ...term }] : []
  })
}

function bankHistory(bank: WireSnapshot["banks"][number], decoderRows: WireDecoderRow[]) {
  const points = [...(bank.series ?? [])].sort((left, right) => left.period.localeCompare(right.period))
  const quarters = new Map<string, SnapshotBank["quarters"][number]>()
  for (const [index, row] of points.entries()) {
    const previous = points[index - 1]
    const delta = previous?.npl_pct != null && row.npl_pct != null && nextPeriod(previous.period) === row.period
      ? row.npl_pct - previous.npl_pct : null
    quarters.set(row.period, { period: row.period, d_npl_pp: delta, adjusted_change_pp: null })
  }
  for (const row of decoderRows) {
    if (row.bank_code !== bank.code || (points.length && !quarters.has(row.period))) continue
    const delta = row.delta_npl_ratio == null ? quarters.get(row.period)?.d_npl_pp ?? null : row.delta_npl_ratio * 100
    const adjusted = delta == null || row.expected_change_pp == null ? null : delta - row.expected_change_pp
    quarters.set(row.period, { period: row.period, d_npl_pp: delta, adjusted_change_pp: adjusted })
  }
  if (bank.latest) {
    const { period, adjusted_change_pp } = bank.latest
    quarters.set(period, { period, d_npl_pp: quarters.get(period)?.d_npl_pp ?? null, adjusted_change_pp })
  }
  const history = [...quarters.values()].sort((left, right) => left.period.localeCompare(right.period))
  return {
    quarters: history,
    quarter_means: [1, 2, 3, 4].map((quarter) => {
      const changes = history.flatMap((row) => row.period.endsWith(`Q${quarter}`) && row.d_npl_pp != null ? [row.d_npl_pp] : [])
      return { quarter, mean_pp: changes.length ? changes.reduce((sum, change) => sum + change, 0) / changes.length : null }
    }),
    pairs: history.flatMap((row) => {
      const q4 = row.d_npl_pp
      const q1 = quarters.get(nextPeriod(row.period))?.d_npl_pp
      return row.period.endsWith("Q4") && q4 != null && q1 != null
        ? [{ year: Number(row.period.slice(0, 4)), q4_pp: q4, q1_pp: q1, reversed: q4 < 0 && q1 > 0 }] : []
    }),
  }
}

function parseSnapshot(value: unknown): Snapshot {
  if (!validate(value)) throw new Error(`Invalid NPL snapshot schema: ${validate.errors?.[0]?.instancePath || "/"}`)

  const { q4_coef_pp, ...baseline } = value.kpis.benchmark
  const benchmark = { ...baseline, coef_pp: q4_coef_pp }
  const { drop_2021_2022: drop, state_vs_private: groups, median_regression: median, leave_one_bank_out } = value.robustness
  const { seasonal } = value.linkage
  const decoderRows = [...(value.decoder?.fiinquant_rows ?? []), ...(value.decoder?.rows ?? [])]
  const descriptives = value.method.find((entry) => entry.id === "M1")

  return {
    ...value,
    // The view accepts the published decoder object as well as legacy fixture cells.
    decoder: value.decoder,
    meta: {
      ...value.meta, cleaning: [], schema: STAR_SCHEMA,
      eda: { href: "#eda", summary_vi: descriptives?.reading_vi ?? "", summary_en: descriptives?.reading_en ?? "" },
    },
    kpis: { ...value.kpis, benchmark },
    quarter_effects: value.quarter_effects.map((effect) => ({ ...effect, n: baseline.n, clusters: baseline.clusters })),
    banks: value.banks.map((bank) => ({ ...bank, ...bankHistory(bank, decoderRows) })),
    heterogeneity: {
      ...value.heterogeneity,
      q4_high_npl: coefficient(value.heterogeneity.regression, "Q4_high_npl"),
      q4_state: coefficient(value.heterogeneity.regression, "Q4_state"),
    },
    linkage: {
      roa_absent: true, roa_q4: null,
      coverage_q4: coefficient(seasonal.d_coverage_pct, "Q4"), nim_q4: coefficient(seasonal.d_nim_pct, "Q4"),
      loan_growth_q4: coefficient(seasonal.loan_growth_yoy_pct, "Q4"),
    },
    market: {
      ...value.market,
      period_start: value.market.period_start ?? null,
      period_end: value.market.period_end ?? null,
      events_with_car: value.market.events_with_car ?? 0,
      eligible_bank_quarters: value.market.eligible_bank_quarters ?? 0,
      reading_vi: value.market.reading_vi ?? "",
      reading_en: value.market.reading_en ?? "",
      regressions: Object.fromEntries(Object.entries<WireRegression>(value.market.regressions).map(([name, fit]) => [name, {
        ...fit, clusters: fit.clusters ?? null,
        terms: Object.fromEntries(Object.keys(fit.terms).map((term) => [term, coefficient(fit, term)])),
      }])),
    },
    forecast: {
      ...value.forecast, train_through: "", test_period: value.forecast.backtest.map((row) => row.period), reading_vi: "", reading_en: "",
    },
    robustness: {
      leave_one_bank_out, drop_2021_2022: coefficient(drop, "Q4"), drop_effects: quarterEffects(drop),
      state_vs_private: { state: coefficient(groups.state, "Q4"), private: coefficient(groups.private, "Q4") },
      state_vs_private_effects: { state: quarterEffects(groups.state), private: quarterEffects(groups.private) },
      median_regression: coefficient(median, "Q4"), year_fe: null,
    },
    method: value.method.map((entry) => ({ ...entry, spec_vi: entry.spec, spec_en: entry.spec })),
  }
}

function bundledSelection(publishBankSeries = true): Selection {
  const snapshot = bundled ??= parseSnapshot(seed)
  // Switching sources must not override an explicit publication restriction.
  return {
    snapshot: publishBankSeries ? snapshot : { ...snapshot, meta: { ...snapshot.meta, publish_bank_series: false } },
    source: "seed",
  }
}

function hasRows(rows: unknown): boolean {
  return Array.isArray(rows) && rows.length > 0
}

function hasPageData(snapshot: Partial<WireSnapshot>): boolean {
  const decomposition = snapshot.decomposition
  const quarters = decomposition?.by_quarter
  const hasQuarterShares = Array.isArray(quarters) && ["Q1", "Q4"].every((quarter) =>
    quarters.some((row) => row?.quarter === quarter && typeof row.share_falling_pct === "number"),
  )
  const price = snapshot.market?.m8
  const mentor = snapshot.decoder?.regression?.fiinquant
  const publishBankSeries = snapshot.meta?.publish_bank_series !== false
  const seasonal = snapshot.context?.seasonal_adjustment
  const warning = snapshot.context?.early_warning
  const researchReady = Boolean(snapshot.scorecard?.indicators && snapshot.scorecard.disagreement && snapshot.pdf_audit?.headline &&
    warning?.backtests?.rise_in_four?.fits && seasonal?.counts && mentor?.without_writeoff !== undefined &&
    (!publishBankSeries || (hasRows(snapshot.scorecard.rows) && hasRows(seasonal.series))))
  return hasQuarterShares &&
    (!publishBankSeries || hasRows(decomposition?.rows)) &&
    hasRows(price?.basket?.series) && hasRows(price?.vnindex?.series) && hasRows(price?.band_table) &&
    Boolean(snapshot.decision_rule?.q4_oos && snapshot.reversal?.baselines) && hasRows(snapshot.decoder?.rows) && researchReady
}

async function fetchSnapshot(uri: string): Promise<Selection> {
  const match = /^s3:\/\/([^/]+)\/(.+)$/.exec(uri)
  if (!match) throw new Error("NPL_SNAPSHOT_S3_URI must be an s3://bucket/key URI")
  client ??= new S3Client({}) // The SDK resolves credentials from the ECS task role.
  const { Body } = await client.send(new GetObjectCommand({ Bucket: match[1], Key: match[2] }))
  if (!Body) throw new Error("NPL snapshot S3 object has no body")
  const raw: unknown = JSON.parse(await Body.transformToString())
  const candidate = raw as Partial<WireSnapshot> | null
  const generatedAt = Date.parse(candidate?.meta?.generated_at ?? "")
  if (candidate && Number.isFinite(generatedAt)) {
    const reason = generatedAt < Date.parse(seed.meta.generated_at) ? "older" :
      !hasPageData(candidate) ? "incomplete" : null
    if (reason) {
      console.warn(`[npl] Serving bundled snapshot because the S3 publication is ${reason}`)
      return bundledSelection(candidate.meta?.publish_bank_series !== false)
    }
  }
  return { snapshot: parseSnapshot(raw), source: "s3" }
}

export async function readSnapshotSelection(): Promise<Selection> {
  const uri = process.env.NPL_SNAPSHOT_S3_URI
  if (!uri) return bundledSelection()
  if (cached?.uri === uri && cached.expires > Date.now()) return cached.selection
  if (pending?.uri === uri) return pending.load

  const request = { uri, load: fetchSnapshot(uri) }
  pending = request
  try {
    const selection = await request.load
    if (pending === request) cached = { uri, selection, expires: Date.now() + CACHE_MS }
    return selection
  } finally {
    if (pending === request) pending = undefined
  }
}

export async function readSnapshot(): Promise<Snapshot> {
  return (await readSnapshotSelection()).snapshot
}
