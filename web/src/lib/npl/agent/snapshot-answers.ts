import { decoderCells, formatNumber, nextPeriod, type DecoderSignal, type Lang, type Snapshot } from "../view.ts"
import type { NplCitation } from "./tools.ts"

function source(period: string | null, n: number | null = null): NplCitation[] {
  return [{ source: "FiinQuant (FiinGroup)", period, n, ci95: null }]
}

export type ScreeningRow = {
  bank: string
  npl_pp: number | null
  group2_pp: number | null
  writeoff_pct: number | null
  coverage_pp: number | null
  flags: DecoderSignal["id"][]
  waterfall: boolean
}

export function screenDeclines(snapshot: Snapshot, { period }: { period: string }) {
  const published = snapshot.decoder
  const cells = decoderCells(published && !Array.isArray(published) && published.rows
    ? { rows: published.rows }
    : published).filter((cell) => cell.period === period)
  const declines = cells.filter((cell) => cell.d_npl_pp != null && cell.d_npl_pp < 0)
  const changes = new Map((snapshot.decomposition?.rows ?? []).filter((row) => row.period === period)
    .map((row) => [row.bank_code, row]))
  const rows: ScreeningRow[] = declines.filter((cell) => cell.signals.some((signal) => signal.id === "S1"))
    .sort((left, right) => left.bank.localeCompare(right.bank))
    .map((cell) => {
      const change = changes.get(cell.bank)
      return {
        bank: cell.bank,
        npl_pp: cell.d_npl_pp,
        group2_pp: cell.inputs.delta_g2_pp ?? change?.d_g2_pp ?? null,
        writeoff_pct: change?.writeoff_pct_loans ?? null,
        coverage_pp: cell.inputs.d_coverage_pp,
        flags: cell.signals.map((signal) => signal.id),
        waterfall: snapshot.meta.publish_bank_series && period.endsWith("Q4") && change?.d_npl_pp != null &&
          change.d_npl_pp < 0 && change.npl_pct != null && change.denominator_pp != null && change.numerator_pp != null,
      }
    })
  const missingGroup2 = declines.filter((cell) => cell.inputs.delta_g2_pp == null &&
    changes.get(cell.bank)?.d_g2_pp == null && !cell.signals.some((signal) => signal.id === "S1")).length
  const banks = rows.map((row) => row.bank).join(", ")
  const vi = rows.length
    ? `${rows.length} ngân hàng có tỷ lệ nợ xấu giảm nhưng tỷ lệ nợ nhóm 2 tăng ở ${period}, gồm ${banks}.`
    : cells.length ? `Không tìm thấy ngân hàng thỏa cả hai điều kiện trong số liệu ${period}.` : `Chưa có số liệu cho ${period}.`
  const en = rows.length
    ? `${rows.length} banks had falling NPL and rising group 2 loans in ${period}. They were ${banks}.`
    : cells.length ? `No bank in the published ${period} data met both conditions.` : `Data for ${period} is unavailable.`
  const tailVi = missingGroup2
    ? `Chưa có số liệu nhóm 2 để kiểm tra ${missingGroup2} trường hợp giảm nợ xấu khác.`
    : rows.length ? "Đây là cờ vàng cần xem xét." : ""
  const tailEn = missingGroup2
    ? `Group 2 data was unavailable for ${missingGroup2} other NPL declines.`
    : rows.length ? "These are flags to review." : ""
  return {
    data_period: period,
    loan_group: 2,
    count: rows.length,
    rows,
    missing_group2: missingGroup2,
    banks_checked: cells.length,
    reading_vi: `${vi} ${tailVi}`.trim(),
    reading_en: `${en} ${tailEn}`.trim(),
    citations: source(period, cells.length),
  }
}

export function q4Drivers(snapshot: Snapshot) {
  const q4 = snapshot.decomposition?.by_quarter.find((row) => row.quarter === "Q4")
  const net = q4?.mean_d_npl_pp ?? null
  const loan = q4?.mean_denominator_pp ?? null
  const share = net != null && net < 0 && loan != null && loan < 0 ? 100 * loan / net : null
  const writeoff = q4?.mean_writeoff_pct_loans ?? null
  const writeoffCount = q4?.writeoff_n ?? null
  const reading = (lang: Lang) => {
    if (net == null || loan == null || share == null) return null
    const vi = lang === "vi"
    const decimal = (value: number, digits = 2) => formatNumber(value, lang, digits)
    const lead = vi
      ? `Khoảng ${decimal(share, 1)}% mức giảm tỷ lệ nợ xấu bình quân quý 4 đến từ dư nợ tăng. Phần này là ${decimal(loan)} trong tổng mức thay đổi ${decimal(net)} điểm %.`
      : `About ${decimal(share, 1)}% of the average Q4 NPL decline came from loan growth. That contributed ${decimal(loan)} of the ${decimal(net)} pp change.`
    const note = writeoff == null || writeoffCount == null ? "" : vi
      ? `Dự phòng sử dụng, chỉ báo gián tiếp về xóa nợ, bình quân bằng ${decimal(writeoff)}% dư nợ ở ${writeoffCount} quan sát có số liệu.`
      : `Provisions used, a proxy for write-offs, averaged ${decimal(writeoff)}% of loans in the ${writeoffCount} observations with data.`
    return `${lead} ${note}`.trim()
  }
  return {
    data_period: snapshot.meta.period_end,
    quarter: 4,
    mean_change_pp: net,
    loan_growth_part_pp: loan,
    share_of_mean_decline_pct: share,
    bad_debt_part_pp: q4?.mean_numerator_pp ?? null,
    writeoff_percent_of_loans: writeoff,
    writeoff_n: writeoffCount,
    n: q4?.n ?? null,
    reading_vi: reading("vi"),
    reading_en: reading("en"),
    citations: source(snapshot.meta.period_end, q4?.n ?? null),
  }
}

export function q1Rebound(snapshot: Snapshot) {
  return {
    data_period: snapshot.meta.period_end,
    quarter: 1,
    previous_quarter: 4,
    rates: snapshot.reversal?.baselines ?? null,
    citations: source(snapshot.meta.period_end, snapshot.reversal?.baselines?.any_q4.n ?? null),
  }
}

export function quarterBreakdown(snapshot: Snapshot, input: { code: string; year: number }) {
  const bank = input.code.trim().toUpperCase()
  const period = `${input.year}Q4`
  const rows = snapshot.meta.publish_bank_series ? snapshot.decomposition?.rows ?? [] : []
  const quarter = rows.find((row) => row.bank_code === bank && row.period === period)
  const change = quarter?.d_npl_pp ?? null
  const q4 = quarter?.npl_pct ?? null
  const next = rows.find((row) => row.bank_code === bank && row.period === nextPeriod(period))
  return {
    data_period: period,
    bank,
    year: input.year,
    q3_period: quarter ? `${input.year}Q3` : null,
    q1_period: next?.period ?? null,
    q3_pct: q4 != null && change != null ? q4 - change : null,
    q4_pct: q4,
    change_pp: change,
    loan_growth_part_pp: quarter?.denominator_pp ?? null,
    bad_debt_part_pp: quarter?.numerator_pp ?? null,
    q1_pct: next?.npl_pct ?? null,
    citations: source(period, quarter ? 1 : null),
  }
}

export function coverageEffect(snapshot: Snapshot) {
  const effect = snapshot.linkage.coverage_q4
  return {
    data_period: snapshot.meta.period_end,
    quarter: 4,
    reference_quarter: 1,
    effect,
    citations: source(snapshot.meta.period_end, effect?.n ?? null),
  }
}

export function rankGap(snapshot: Snapshot, { period }: { period?: string }) {
  const gaps = snapshot.meta.publish_bank_series ? snapshot.scorecard?.rank_gaps : undefined
  const published = gaps?.[period ?? "latest"]
    ?? (period && gaps?.latest?.[0]?.period === period ? gaps.latest : undefined)
  const rows = (published ?? []).filter((row) => row.direction === "npl_looks_better")
  const data_period = period ?? snapshot.meta.period_end
  const banks = rows.map((row) => row.bank_code).join(", ")
  return {
    data_period,
    rows,
    count: rows.length,
    reading_vi: rows.length
      ? `Trong danh sách chênh lệch đáng chú ý ở ${data_period}, ${rows.length} ngân hàng có hạng theo tỷ lệ nợ xấu tốt hơn hạng chất lượng tín dụng tổng hợp, gồm ${banks}.`
      : published ? `Bảng công bố cho ${data_period} không có trường hợp chênh lệch theo hướng này.` : `Chưa có bảng chênh lệch thứ hạng được công bố cho ${data_period}.`,
    reading_en: rows.length
      ? `Among the notable rank gaps in ${data_period}, ${rows.length} banks ranked better on NPL than on composite credit quality. They were ${banks}.`
      : published ? `The published ${data_period} table has no gaps in this direction.` : `Published rank gaps are unavailable for ${data_period}.`,
    citations: source(data_period),
  }
}

export function earlyWarning(snapshot: Snapshot) {
  const early = snapshot.context?.early_warning
  const event = early?.backtests.rise_in_four
  return {
    data_period: snapshot.meta.period_end,
    fits: event?.fits ?? null,
    n: event?.n_test ?? null,
    reading_vi: early?.reading_vi ?? "Chưa có kết quả kiểm tra cảnh báo sớm được công bố.",
    reading_en: early?.reading_en ?? "Early warning results are unavailable.",
    citations: source(snapshot.meta.period_end, event?.n_test ?? null),
  }
}

export type SnapshotAnswers = {
  screen_declines: ReturnType<typeof screenDeclines>
  q4_drivers: ReturnType<typeof q4Drivers>
  q1_rebound: ReturnType<typeof q1Rebound>
  quarter_breakdown: ReturnType<typeof quarterBreakdown>
  coverage_effect: ReturnType<typeof coverageEffect>
  rank_gap: ReturnType<typeof rankGap>
  early_warning: ReturnType<typeof earlyWarning>
}

export type SnapshotAnswer = { [K in keyof SnapshotAnswers]: {
  name: K
  text: string
  input: object
  output: SnapshotAnswers[K]
} }[keyof SnapshotAnswers]

export function answerSnapshot(snapshot: Snapshot, question: string, lang: Lang): SnapshotAnswer | null {
  const vi = lang === "vi"
  const plain = question.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "").replace(/đ/g, "d").trim()
  const q4 = /\b(?:(?:20\d{2})?q4|quy\s+4|fourth quarter)\b/.test(plain)
  const npl = /\b(?:npl|no xau|bad debt|non-performing loans?)\b/.test(plain)
  const fell = /\b(?:giam|fell|fall\w*|decreas\w*|declin\w*|drop\w*)\b/.test(plain)
  const year = /\b(20\d{2})(?=\b|q4\b)/.exec(plain)?.[1]
  const decimal = (value: number, digits = 2) => formatNumber(value, lang, digits)

  if (npl && /\b(?:ngan hang nao|which banks?|xep hang|thu hang|ranks?|ranking)\b/.test(plain) &&
    /\b(?:chat luong tong the|chat luong (?:tai san|tin dung) tong hop|composite (?:asset|credit) quality|overall credit quality|rank gaps?)\b/.test(plain)) {
    const compactPeriod = /\b(20\d{2})\s*q([1-4])\b/.exec(plain)
    const spokenPeriod = /\b(?:q|quy\s+)([1-4])\s+(20\d{2})\b/.exec(plain)
    const period = compactPeriod ? `${compactPeriod[1]}Q${compactPeriod[2]}`
      : spokenPeriod ? `${spokenPeriod[2]}Q${spokenPeriod[1]}` : undefined
    if (year && !period) return null
    const input = { period }
    const output = rankGap(snapshot, input)
    return { name: "rank_gap", input, output, text: output[`reading_${lang}`] }
  }
  if (!year && /\b(?:canh bao som|early[- ]warning)\b/.test(plain)) {
    const output = earlyWarning(snapshot)
    return { name: "early_warning", input: {}, output, text: output[`reading_${lang}`] }
  }
  if (q4 && npl && fell && year && /\b(?:nhom\s*2|group[- ]?2)\b/.test(plain) &&
    /\b(?:tang|rose|ris\w*|increas\w*)\b/.test(plain)) {
    const input = { period: `${year}Q4` }
    const output = screenDeclines(snapshot, input)
    return { name: "screen_declines", input, output, text: output[`reading_${lang}`] }
  }
  if (q4 && npl && fell && /\b(?:why|vi sao|tai sao|giai thich)\b/.test(plain) && !year) {
    const output = q4Drivers(snapshot)
    const text = output[`reading_${lang}`]
    return text ? { name: "q4_drivers", input: {}, output, text } : null
  }
  if (/\b(?:q1|quy\s+1|first quarter)\b/.test(plain) && /\b(?:luon|always)\b/.test(plain)) {
    const output = q1Rebound(snapshot)
    const { any_q4: base, q4_fell: afterFall, q4_not_fell: afterOther } = output.rates ?? {}
    if (base?.share_pct == null || afterFall?.share_pct == null || afterOther?.share_pct == null) return null
    const text = vi
      ? `${decimal(base.share_pct, 1)}% (${base.rises}/${base.n}) trường hợp có tỷ lệ nợ xấu tăng vào quý 1. Tỷ lệ tăng lại là ${decimal(afterFall.share_pct, 1)}% sau quý 4 giảm và ${decimal(afterOther.share_pct, 1)}% sau quý 4 không giảm. Quý 1 vẫn có lúc không tăng.`
      : `NPL rose in ${decimal(base.share_pct, 1)}% (${base.rises} of ${base.n}) of Q1 observations. It rose in ${decimal(afterFall.share_pct, 1)}% after a Q4 fall and ${decimal(afterOther.share_pct, 1)}% after Q4 held steady or rose. That leaves Q1 quarters without a rise.`
    return { name: "q1_rebound", input: {}, output, text }
  }
  const bankYear = /^(?:cho xem|xem|show me|show|let me see)\s+([a-z0-9]{2,5})\s+(20\d{2})[.!?]?$/.exec(plain)
  if (bankYear) {
    const input = { code: bankYear[1].toUpperCase(), year: Number(bankYear[2]) }
    const output = quarterBreakdown(snapshot, input)
    const { q3_pct: q3, q4_pct: finish, loan_growth_part_pp: loan, bad_debt_part_pp: bad } = output
    if (q3 == null || finish == null || loan == null || bad == null) return null
    const text = vi
      ? `${output.bank} có tỷ lệ nợ xấu từ ${decimal(q3)}% ${finish <= q3 ? "xuống" : "lên"} ${decimal(finish)}% vào ${output.data_period}. Biến động dư nợ đóng góp ${decimal(loan)} điểm % và thay đổi số dư nợ xấu đóng góp ${decimal(bad)} điểm %.`
      : `${output.bank}'s NPL moved from ${decimal(q3)}% to ${decimal(finish)}% in ${output.data_period}. The change in loans contributed ${decimal(loan)} pp and the change in bad debt contributed ${decimal(bad)} pp.`
    return { name: "quarter_breakdown", input, output, text }
  }
  if (q4 && /\b(?:bao phu|coverage)\b/.test(plain) && /\b(?:tang|rose|ris\w*|up|increas\w*)\b/.test(plain) && !year) {
    const output = coverageEffect(snapshot)
    const term = output.effect
    if (!term) return null
    const [lo, hi] = term.ci95
    const lead = vi ? `Chênh lệch thay đổi tỷ lệ bao phủ quý 4 so với quý 1 là ${decimal(term.coef_pp)} điểm %.`
      : `The change in coverage in Q4 was ${decimal(term.coef_pp)} pp relative to Q1.`
    const note = lo == null || hi == null ? "" : vi
      ? `Khoảng ước tính từ ${decimal(lo)} đến ${decimal(hi)} điểm %. Đây là kết quả chung của mẫu ngân hàng.`
      : `The estimated range is ${decimal(lo)} to ${decimal(hi)} pp. This is a panel-wide result.`
    return { name: "coverage_effect", input: {}, output, text: `${lead} ${note}`.trim() }
  }
  return null
}
