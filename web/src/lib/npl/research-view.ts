import { formatNumber, type Lang, type PublishedDecoderRow, type Snapshot } from "./view.ts"
import type { Indicator, ScorecardRow } from "./research-types.ts"

export const RESEARCH_QUESTION = {
  vi: "Khi tỷ lệ nợ xấu được báo cáo giảm, cần xem thêm bằng chứng gì trước khi kết luận chất lượng tín dụng thực sự cải thiện?",
  en: "When the reported NPL ratio falls, what else should we check before concluding that credit quality has improved?",
}

type EvidenceTone = "context" | "watch" | "steady" | "missing"
type EvidenceRow = { id: string; label: string; value: string; verdict: string; why: string; tone: EvidenceTone }

export function scorecardRanks(rows: ScorecardRow[] | undefined, bank: string, period: string) {
  const cohort = (rows ?? []).flatMap((row) => row.period === period && row.values.npl != null && row.composite != null
    ? [{ bank: row.bank_code, npl: row.values.npl, composite: row.composite }] : [])
  const selected = cohort.find((row) => row.bank === bank)
  if (!selected) return null
  return {
    npl: 1 + cohort.filter((row) => row.npl < selected.npl).length,
    composite: 1 + cohort.filter((row) => row.composite > selected.composite).length,
    count: cohort.length,
  }
}

export function indicatorValue(value: number | null | undefined, unit: Indicator["unit"], lang: Lang) {
  if (value == null) return "—"
  return unit === "ratio" ? `${formatNumber(value * 100, lang, 2)}%` : `${formatNumber(value, lang, 2)}×`
}

export function indicatorDirection(direction: Indicator["direction"], lang: Lang) {
  const labels = {
    higher_worse: { vi: "Cao hơn cần chú ý", en: "Higher calls for review" },
    higher_better: { vi: "Cao hơn thuận lợi", en: "Higher is favourable" },
    higher_faster: { vi: "Cao hơn là tăng nhanh hơn", en: "Higher means faster growth" },
    not_scored: { vi: "Tham khảo", en: "Context only" },
  }
  return labels[direction][lang]
}

export function publishedBankQuarter(snapshot: Snapshot, bank: string, period: string): PublishedDecoderRow | undefined {
  const decoder = snapshot.decoder
  if (!decoder || Array.isArray(decoder)) return undefined
  return (decoder.rows ?? decoder.fiinquant_rows ?? decoder.focus ?? [])
    .find((row) => (row.bank_code ?? row.bank) === bank && row.period === period)
}

export function bankCheck(snapshot: Snapshot, bank: string, period: string, lang: Lang) {
  const vi = lang === "vi"
  const score = snapshot.scorecard?.rows?.find((row) => row.bank_code === bank && row.period === period)
  const adjustment = snapshot.context?.seasonal_adjustment?.series.find((row) => row.bank_code === bank && row.period === period)
  const split = snapshot.decomposition?.rows.find((row) => row.bank_code === bank && row.period === period)
  const decoder = publishedBankQuarter(snapshot, bank, period)
  const visibleLevels = snapshot.meta.publish_bank_series
  const flags = decoder?.layers?.accounting ?? decoder?.signals?.map((signal) => signal.id) ?? []
  const season = decoder?.layers?.context ?? decoder?.signals?.map((signal) => signal.id) ?? []
  const reportedChange = decoder?.delta_npl_ratio == null ? split?.d_npl_pp ?? null : decoder.delta_npl_ratio * 100
  const band = decoder?.expected_change_pp != null && decoder.lo80_pp != null && decoder.hi80_pp != null
    ? { lo: decoder.expected_change_pp + decoder.lo80_pp, hi: decoder.expected_change_pp + decoder.hi80_pp }
    : null
  const inSeason = band && reportedChange != null ? reportedChange >= band.lo - 1e-10 && reportedChange <= band.hi + 1e-10
    : season.includes("S4") ? true : null
  const group2 = decoder?.delta_g2_ratio == null ? split?.d_g2_pp ?? null : decoder.delta_g2_ratio * 100
  const used = !visibleLevels ? null : score?.values.writeoff_proxy ??
    (decoder?.writeoff_quarter_flow === false ? null : decoder?.writeoff_ratio ?? null)
  const coverage = decoder?.coverage_contested || decoder?.delta_coverage == null ? null : decoder.delta_coverage * 100
  const provisions = decoder?.delta_provisions_to_loans == null ? null : decoder.delta_provisions_to_loans * 100
  const denominator = split?.denominator_pp ?? null
  const q4 = period.endsWith("Q4")
  const noData = vi ? "Chưa đủ" : "Incomplete"
  const pp = (value: number | null, withUnit = true) => value == null ? "—"
    : `${value > 0 ? "+" : ""}${formatNumber(value, lang, value !== 0 && Math.abs(value) < .01 ? 3 : 2)}${withUnit ? (vi ? " điểm %" : " pp") : ""}`
  const watch = vi ? "Cần xem xét" : "Review"

  const checks: EvidenceRow[] = [
    {
      id: "season", label: vi ? "Thời điểm và mùa vụ" : "Timing and seasonality",
      value: !q4 ? period : band ? `${pp(band.lo, false)} ${vi ? "đến" : "to"} ${pp(band.hi)}` : "—",
      verdict: !q4 ? (vi ? "Ngoài quý 4" : "Outside Q4") : inSeason == null ? noData
        : inSeason ? (vi ? "Trong dải cuối năm" : "Inside year-end range") : (vi ? "Ngoài dải cuối năm" : "Outside year-end range"),
      why: vi ? "Dải biến động thường thấy được tính từ các năm trước của ngân hàng."
        : "The usual range comes from this bank’s earlier years.",
      tone: q4 && inSeason == null ? "missing" : "context",
    },
    {
      id: "loans", label: vi ? "Mẫu số dư nợ" : "Loan denominator",
      value: pp(denominator),
      verdict: denominator == null ? noData : denominator < 0 ? (vi ? "Kéo tỷ lệ xuống" : "Pulls ratio down")
        : denominator > 0 ? (vi ? "Đẩy tỷ lệ lên" : "Pushes ratio up") : (vi ? "Không đổi" : "Unchanged"),
      why: vi ? "Dư nợ tăng có thể làm tỷ lệ giảm dù số dư nợ xấu giữ nguyên."
        : "A growing loan book can lower the ratio while bad debt stays flat.",
      tone: denominator == null ? "missing" : "context",
    },
    {
      id: "writeoffs", label: vi ? "Xóa nợ" : "Write-offs",
      value: indicatorValue(used, "ratio", lang),
      verdict: flags.includes("S2") ? watch : used == null ? noData : vi ? "Đã quan sát" : "Observed",
      why: vi ? "Dự phòng đã dùng so với dư nợ đầu quý là chỉ báo xóa nợ." : "Provisions used over opening loans are a write-off proxy.",
      tone: flags.includes("S2") ? "watch" : used == null ? "missing" : "steady",
    },
    {
      id: "group2", label: vi ? "Nợ nhóm 2" : "Group 2 loans",
      value: pp(group2),
      verdict: group2 == null ? noData : group2 > 0 ? (vi ? "Tăng" : "Rose") : (vi ? "Không tăng" : "Did not rise"),
      why: vi ? "Nợ cần chú ý tăng là tín hiệu rủi ro sớm." : "A growing share of watch-list loans is an early risk signal.",
      tone: group2 == null ? "missing" : group2 > 0 ? "watch" : "steady",
    },
    {
      id: "coverage", label: vi ? "Bao phủ và dự phòng" : "Coverage and provisions",
      value: `${vi ? "Bao phủ" : "Coverage"} ${pp(coverage)}\n${vi ? "Dự phòng / dư nợ" : "Provisions / loans"} ${pp(provisions)}`,
      verdict: coverage == null || provisions == null ? noData : coverage < 0 && provisions < 0
        ? (vi ? "Cùng giảm" : "Both fell") : (vi ? "Không cùng giảm" : "Did not both fall"),
      why: vi ? "Hai tỷ lệ cùng giảm là dấu hiệu lớp đệm dự phòng mỏng đi."
        : "When both ratios fall, the provision buffer may be thinning.",
      tone: coverage == null || provisions == null ? "missing" : coverage < 0 && provisions < 0 ? "watch" : "steady",
    },
  ]
  return {
    reportedChange,
    adjustedChange: adjustment?.adjusted_change_pp ?? null,
    ranks: scorecardRanks(snapshot.scorecard?.rows, bank, period),
    checks,
  }
}

export function latestScorecard(snapshot: Snapshot, bank: string) {
  const source = snapshot.scorecard
  const row = source?.rows?.filter((item) => item.bank_code === bank).sort((a, b) => a.period.localeCompare(b.period)).at(-1)
  if (!source || !row) return null
  return {
    row, indicators: source.indicators, ranks: scorecardRanks(source.rows, bank, row.period),
  }
}
