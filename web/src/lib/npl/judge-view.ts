import { decoderCells, nextPeriod, type DecompositionRow, type Lang, type PublishedPriceForecast, type Q4Holdout, type Snapshot } from "./view.ts"

export function q4HoldoutReading(check: Q4Holdout | undefined, lang: Lang) {
  if (!check || !check.improving.n || !check.within_normal_season.n) return null
  const { train_through: trained, scored_period: tested, outcome_period: outcome, improving, within_normal_season: seasonal } = check
  return lang === "vi"
    ? `Dùng dữ liệu đến ${trained} để xác định nhịp mùa vụ, rồi kiểm tra các ngân hàng có tỷ lệ nợ xấu giảm ở ${tested}. Đến ${outcome}, tỷ lệ tăng lại ở ${improving.reversals}/${improving.n} trường hợp xếp là cải thiện và ${seasonal.reversals}/${seasonal.n} trường hợp trong nhịp mùa vụ. Một quý kiểm tra với ít trường hợp chưa đủ để phân biệt hai nhóm.`
    : `We used data through ${trained} to set the seasonal range, then checked banks whose NPL ratio fell in ${tested}. By ${outcome}, it rose again in ${improving.reversals} of ${improving.n} cases classed as improvements and ${seasonal.reversals} of ${seasonal.n} cases inside the seasonal range. One test quarter with few cases gives little evidence that the rule separates the groups.`
}

export type HeatmapCell = { before: number | null; after: number | null; change: number | null }

export function heatmapModel(snapshot: Snapshot, decomposition?: DecompositionRow[]) {
  const periods = snapshot.series.median_by_period.map((row) => row.period).sort()
  const changes = new Map(decomposition?.map((row) => [`${row.bank_code}|${row.period}`, row]))
  const rows = !snapshot.meta.publish_bank_series ? [] : [...snapshot.banks]
    .sort((left, right) => left.code.localeCompare(right.code))
    .map((bank) => {
      const levels = new Map(bank.series?.map((row) => [row.period, row.npl_pct]))
      return {
        bank: bank.code,
        cells: periods.map((period, i): HeatmapCell => {
          if (decomposition?.length) {
            const row = changes.get(`${bank.code}|${period}`)
            if (row?.npl_pct == null || row.d_npl_pp == null) return { before: null, after: null, change: null }
            return { before: row.npl_pct - row.d_npl_pp, after: row.npl_pct, change: row.d_npl_pp }
          }
          const previous = periods[i - 1]
          const before = previous && nextPeriod(previous) === period ? levels.get(previous) ?? null : null
          const after = levels.get(period) ?? null
          return { before, after, change: before != null && after != null ? after - before : null }
        }),
      }
    })
  return { periods, rows }
}

export type BankBreakdown = {
  bank: string
  year: string
  before: number
  after: number
  next: number | null
  denominator: number
  numerator: number
  checks: { label: string; text: string; flagged: boolean }[]
}

export function breakdownModel(snapshot: Snapshot, rows: DecompositionRow[], lang: Lang): BankBreakdown[] {
  if (!snapshot.meta.publish_bank_series) return []
  const vi = lang === "vi"
  const cells = new Map(decoderCells(snapshot.decoder).map((cell) => [`${cell.bank}|${cell.period}`, cell]))
  const rates = new Map(rows.map((row) => [`${row.bank_code}|${row.period}`, row.npl_pct]))
  return rows.flatMap((row) => {
    if (!row.period.endsWith("Q4") || row.d_npl_pp == null || row.d_npl_pp >= 0 ||
      row.npl_pct == null || row.denominator_pp == null || row.numerator_pp == null) return []
    const cell = cells.get(`${row.bank_code}|${row.period}`)
    const flags = new Set(cell?.signals.map((signal) => signal.id))
    const group2 = cell?.inputs.delta_g2_pp ?? row.d_g2_pp
    const writeoff = cell?.inputs.delta_writeoff_pp
    const coverage = cell?.inputs.d_coverage_pp
    const unknown = vi ? "Chưa có số liệu" : "Data unavailable"
    const up = vi ? "Tăng" : "Rose"
    const steady = vi ? "Không tăng" : "Did not rise"
    const seasonal = flags.has("S4")
    const hasSeasonal = cell?.inputs.seasonal_band_available && cell.d_npl_pp != null && cell.d_npl_pp < 0
    const group2Up = flags.has("S1") || (group2 != null && group2 > 0)
    const writeoffUp = flags.has("S2") || (writeoff != null && writeoff > 0)
    const coverageDown = flags.has("S3") || (coverage != null && coverage < 0)
    return [{
      bank: row.bank_code,
      year: row.period.slice(0, 4),
      before: row.npl_pct - row.d_npl_pp,
      after: row.npl_pct,
      next: rates.get(`${row.bank_code}|${nextPeriod(row.period)}`) ?? null,
      denominator: row.denominator_pp,
      numerator: row.numerator_pp,
      checks: [
        { label: vi ? "Nợ nhóm 2" : "Group 2", flagged: group2Up, text: group2Up ? up : group2 == null ? unknown : steady },
        { label: vi ? "Xóa nợ (ước tính)" : "Write-offs (proxy)", flagged: writeoffUp, text: writeoffUp ? up : writeoff == null ? unknown : steady },
        { label: vi ? "Bao phủ" : "Coverage", flagged: coverageDown, text: coverageDown ? (vi ? "Giảm" : "Fell") :
          coverage == null ? unknown : (vi ? "Không giảm" : "Did not fall") },
        { label: vi ? "Dải mùa vụ" : "Year-end range", flagged: seasonal, text: seasonal ? (vi ? "Trong dải" : "Inside the range") :
          hasSeasonal ? (vi ? "Ngoài dải" : "Outside the range") : unknown },
      ],
    }]
  })
}

export function marketPriceModel(forecast: PublishedPriceForecast) {
  const modelMae = forecast.mae_price
  const baselineMae = forecast.mae_price_random_walk ?? null
  return {
    points: forecast.series.map((point) => ({
      month: point.month, actual: point.actual_price, predicted: point.predicted_price, test: point.in_test,
    })),
    modelMae,
    baselineMae,
    lowerError: modelMae == null || baselineMae == null ? null : modelMae < baselineMae,
  }
}

export function waterfallModel(values: BankBreakdown, lang: Lang) {
  const vi = lang === "vi"
  const adjusted = values.before + values.denominator
  return [
    { label: "Q3", value: values.before, start: 0, end: values.before, effect: false },
    { label: vi ? "Tăng dư nợ" : "Loan growth", value: values.denominator, start: values.before, end: adjusted, effect: true },
    { label: vi ? "Biến động nợ xấu" : "Bad-debt change", value: values.numerator, start: adjusted, end: values.after, effect: true },
    { label: "Q4", value: values.after, start: 0, end: values.after, effect: false },
    { label: vi ? "Q1 năm sau" : "Next Q1", value: values.next, start: values.next == null ? null : 0, end: values.next, effect: false },
  ]
}
