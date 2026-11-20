// Deterministic tools for the RateWatch assistant. Every tool reads the
// published snapshot only (no network, no user data), takes typed zod
// arguments (prompt-injection surface: none), and returns its values together
// with citations [{bank, term_months, channel, grade, sheet_date, source_url,
// observed_at}] so the model can only speak numbers that carry their source.
import { tool } from "ai"
import type { Tool } from "ai"
import { z } from "zod"

import { breakEvenRenewal, insuredSplit as calcInsuredSplit, plan as calcPlan, type RateRow, type SplitOption } from "../calc.ts"
import { rateOptions } from "../decide.ts"
import type { Snapshot, SnapshotBank, SnapshotRate } from "../types.ts"

// Same lookup as load.ts, inlined so tests never load the bundler-only JSON import.
function bankByCode(snapshot: Snapshot, code: string): SnapshotBank | null {
  const key = code.toUpperCase()
  return snapshot.banks.find((bank) => bank.code === key) ?? null
}

export interface Citation {
  bank: string
  term_months: number | null
  channel: string | null
  grade: string | null
  sheet_date: string | null
  source_url: string
  observed_at: string
}

function fold(value: string): string {
  // diacritic- and case-insensitive: "Cần Thơ" and "can tho" are the same province
  return value
    .trim()
    .toLocaleLowerCase("vi")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
}

function citationFor(bank: SnapshotBank, rate: SnapshotRate): Citation {
  const reader = rate.readers[0]
  return {
    bank: bank.code,
    term_months: rate.term_months,
    channel: rate.channel,
    grade: rate.grade,
    sheet_date: bank.sheet_date,
    source_url: reader?.source_url || bank.sheet_url || "",
    observed_at: reader?.observed_at || bank.read_at,
  }
}

function sheetCitation(bank: SnapshotBank): Citation {
  return {
    bank: bank.code,
    term_months: null,
    channel: null,
    grade: null,
    sheet_date: bank.sheet_date,
    source_url: bank.sheet_url || "",
    observed_at: bank.read_at,
  }
}

function policyCitation(snapshot: Snapshot, legalRef: string, validFrom: string | null): Citation {
  return {
    bank: "policy",
    term_months: null,
    channel: null,
    grade: null,
    sheet_date: validFrom,
    source_url: legalRef,
    observed_at: snapshot.meta.generated_at,
  }
}

function geoCitation(snapshot: Snapshot, source: string | null): Citation {
  return {
    bank: "geo",
    term_months: null,
    channel: null,
    grade: null,
    sheet_date: null,
    source_url: source || snapshot.geo.attribution,
    observed_at: snapshot.meta.generated_at,
  }
}

/** Posted base-tier rate for (bank, channel, term): verified first, then single; contested never feeds a calculation. */
function usableRate(bank: SnapshotBank, channel: string, term: number): SnapshotRate | null {
  const rows = bank.rates.filter((r) => r.channel === channel && (r.tier ?? "") === "" && r.term_months === term)
  return rows.find((r) => r.grade === "verified") ?? rows.find((r) => r.grade === "single") ?? null
}

function rateContested(bank: SnapshotBank, channel: string, term: number): boolean {
  return bank.rates.some((r) => r.channel === channel && (r.tier ?? "") === "" && r.term_months === term && r.grade === "contested")
}

// --- get_curve -------------------------------------------------------------

export interface CurvePoint {
  term_months: number
  rate_pct: number
  grade: string
}

export function getCurve(snapshot: Snapshot, input: { bank: string; channel: string }) {
  const bank = bankByCode(snapshot, input.bank)
  if (!bank) return { found: false as const, citations: [] as Citation[], values_used: {} }
  const points: CurvePoint[] = bank.rates
    .filter((r) => r.channel === input.channel && (r.tier ?? "") === "")
    .sort((a, b) => a.term_months - b.term_months)
    .map((r) => ({ term_months: r.term_months, rate_pct: r.rate_pct, grade: r.grade }))
  return {
    found: true as const,
    bank_code: bank.code,
    bank_name: bank.name_vi,
    channel: input.channel,
    sheet_date: bank.sheet_date,
    sheet_url: bank.sheet_url,
    points,
    citations: points.map((p) => {
      const rate = bank.rates.find((r) => r.term_months === p.term_months && r.channel === input.channel)!
      return citationFor(bank, rate)
    }),
    values_used: { bank: bank.code, channel: input.channel, n_points: points.length },
  }
}

// --- compare_banks ---------------------------------------------------------

export function compareBanks(snapshot: Snapshot, input: { banks: string[]; term: number }) {
  if (input.banks.length > 3) throw new Error("compare at most 3 banks")
  const rows: { bank_code: string; bank_name: string; channel: string; rate_pct: number; grade: string; sheet_date: string | null }[] = []
  const citations: Citation[] = []
  const missing: string[] = []
  for (const code of input.banks) {
    const bank = bankByCode(snapshot, code)
    if (!bank) {
      missing.push(code.toUpperCase())
      continue
    }
    for (const channel of ["counter", "online"]) {
      const rate = bank.rates.find((r) => r.channel === channel && (r.tier ?? "") === "" && r.term_months === input.term)
      if (!rate) continue
      rows.push({
        bank_code: bank.code,
        bank_name: bank.name_vi,
        channel,
        rate_pct: rate.rate_pct,
        grade: rate.grade,
        sheet_date: bank.sheet_date,
      })
      citations.push(citationFor(bank, rate))
    }
  }
  return {
    term_months: input.term,
    rows,
    missing,
    citations,
    values_used: { banks: input.banks.map((b) => b.toUpperCase()), term: input.term },
  }
}

// --- plan_deposit ----------------------------------------------------------

function rowCitation(snapshot: Snapshot, row: RateRow): Citation {
  const bank = bankByCode(snapshot, row.bank_code)
  const rate = bank?.rates.find((r) => r.term_months === row.term_months && r.channel === row.channel && (r.tier ?? "") === (row.tier ?? "") && r.rate_pct === row.rate_pct)
  return rate ? citationFor(bank!, rate) : {
    bank: row.bank_code,
    term_months: row.term_months,
    channel: row.channel,
    grade: row.grade,
    sheet_date: row.sheet_date,
    source_url: row.source_url,
    observed_at: snapshot.meta.generated_at,
  }
}

export function planDeposit(snapshot: Snapshot, input: { amount: number; horizon_months: number; online_ok: boolean; current_bank?: string }) {
  const options = rateOptions(snapshot)
  const plans = calcPlan(input.amount, input.horizon_months, input.online_ok, options, snapshot.policy.cap.vnd, {}, false)
  const top = plans.slice(0, 3).map((p) => ({
    kind: p.kind,
    early_withdrawal: p.early_withdrawal,
    idle_months: p.idle_months,
    second_leg_assumption: p.second_leg_assumption ?? null,
    interest_vnd: p.interest_vnd,
    value_at_horizon: p.value_at_horizon,
    insured_share: p.insured_share,
    rows: p.rows.map((r) => ({ bank_code: r.bank_code, term_months: r.term_months, channel: r.channel, rate_pct: r.rate_pct, grade: r.grade })),
    amounts: p.amounts,
  }))
  const citations = plans.slice(0, 3).flatMap((p) => p.rows.map((r) => rowCitation(snapshot, r)))
  return {
    amount: input.amount,
    horizon_months: input.horizon_months,
    online_ok: input.online_ok,
    current_bank: input.current_bank ?? null,
    cap_vnd: snapshot.policy.cap.vnd,
    plans: top,
    citations,
    values_used: { amount: input.amount, horizon_months: input.horizon_months, online_ok: input.online_ok, cap_vnd: snapshot.policy.cap.vnd },
  }
}

// --- break_even ------------------------------------------------------------

export function breakEven(snapshot: Snapshot, input: { bank: string; channel: string; short_m: number; long_m: number }) {
  const bank = bankByCode(snapshot, input.bank)
  if (!bank) return { error: "unknown_bank" as const, citations: [] as Citation[], values_used: {} }
  const contested = rateContested(bank, input.channel, input.short_m) || rateContested(bank, input.channel, input.long_m)
  const shortRate = usableRate(bank, input.channel, input.short_m)
  const longRate = usableRate(bank, input.channel, input.long_m)
  if (contested || !shortRate || !longRate) {
    return {
      error: contested ? ("contested" as const) : ("missing_row" as const),
      bank_code: bank.code,
      channel: input.channel,
      citations: [shortRate, longRate].filter((r): r is SnapshotRate => r !== null).map((r) => citationFor(bank, r)),
      values_used: { bank: bank.code, channel: input.channel, short_m: input.short_m, long_m: input.long_m },
    }
  }
  const breakEvenPct = breakEvenRenewal(longRate.rate_pct, input.long_m, shortRate.rate_pct, input.short_m)
  return {
    bank_code: bank.code,
    bank_name: bank.name_vi,
    channel: input.channel,
    short_m: input.short_m,
    long_m: input.long_m,
    short_rate: shortRate.rate_pct,
    long_rate: longRate.rate_pct,
    break_even_pct: breakEvenPct,
    note_vi: "Đây là phép tính, không phải dự báo.",
    note_en: "This is a calculation, not a forecast.",
    citations: [citationFor(bank, shortRate), citationFor(bank, longRate)],
    values_used: {
      short_rate: shortRate.rate_pct,
      long_rate: longRate.rate_pct,
      short_m: input.short_m,
      long_m: input.long_m,
      formula: "(1 + r_long * long_m/12) = (1 + r_short * short_m/12) * (1 + f * (long_m - short_m)/12)",
    },
  }
}

// --- insured_split ---------------------------------------------------------

function bestVerifiedOption(bank: SnapshotBank, maxTerm = 12): SplitOption | null {
  let picked: SnapshotRate | null = null
  for (const rate of bank.rates) {
    if ((rate.tier ?? "") !== "" || rate.grade !== "verified") continue
    if (rate.term_months < 1 || rate.term_months > maxTerm) continue
    if (!picked || rate.rate_pct > picked.rate_pct || (rate.rate_pct === picked.rate_pct && rate.term_months < picked.term_months)) picked = rate
  }
  return picked ? { bank_code: bank.code, term_months: picked.term_months, rate_pct: picked.rate_pct } : null
}

export function insuredSplit(snapshot: Snapshot, input: { amount: number; banks?: string[] }) {
  const requested = input.banks?.map((code) => bankByCode(snapshot, code)).filter((b): b is SnapshotBank => b !== null) ?? null
  const banks = (requested ?? snapshot.banks).map((bank) => ({ bank, option: bestVerifiedOption(bank) })).filter((entry) => entry.option !== null)
  const options = banks.map((entry) => entry.option as SplitOption)
  const split = calcInsuredSplit(input.amount, snapshot.policy.cap.vnd, options)
  // calcInsuredSplit keeps the options' order, so allocation i used option i.
  const allocations = split.allocations.map((allocation, index) => ({
    ...allocation,
    term_months: options[index]!.term_months,
    rate_pct: options[index]!.rate_pct,
  }))
  const citations = split.allocations.map((_, index) => {
    const entry = banks[index]!
    const rate = entry.bank.rates.find(
      (r) => r.term_months === entry.option!.term_months && r.rate_pct === entry.option!.rate_pct && (r.tier ?? "") === "",
    )!
    return citationFor(entry.bank, rate)
  })
  return {
    amount: input.amount,
    cap_vnd: snapshot.policy.cap.vnd,
    allocations,
    allocated_vnd: split.allocated_vnd,
    remainder_vnd: split.remainder_vnd,
    fully_insured: split.fully_insured,
    insured_share: split.insured_share,
    citations,
    values_used: { amount: input.amount, cap_vnd: snapshot.policy.cap.vnd, options },
  }
}

// --- bank_profile ----------------------------------------------------------

export function bankProfile(snapshot: Snapshot, input: { bank: string }) {
  const bank = bankByCode(snapshot, input.bank)
  if (!bank) return { found: false as const, citations: [] as Citation[], values_used: {} }
  return {
    found: true as const,
    bank_code: bank.code,
    bank_name: bank.name_vi,
    profile: bank.profile,
    message_vi: bank.profile
      ? `Số liệu quý ${bank.profile.quarter} của ${bank.name_vi} (nguồn: ${bank.profile.source}).`
      : `${bank.name_vi} chưa có số liệu định lượng an toàn trong snapshot hiện tại — không suy diễn.`,
    message_en: bank.profile
      ? `${bank.name_en} figures for quarter ${bank.profile.quarter} (source: ${bank.profile.source}).`
      : `${bank.name_en} has no quantitative safety figures in the current snapshot — none are invented.`,
    citations: [sheetCitation(bank)],
    values_used: { bank: bank.code, has_profile: bank.profile !== null },
  }
}

// --- policy ----------------------------------------------------------------

export function policyParam(snapshot: Snapshot, input: { param: "ceiling" | "cap" | "premium" | "insured_coverage" | "all" }) {
  const policy = snapshot.policy
  const values =
    input.param === "all"
      ? policy
      : policy[input.param]
  const legalRef = input.param === "all" ? `${policy.ceiling.legal_ref}; ${policy.cap.legal_ref}` : (values as { legal_ref?: string }).legal_ref ?? ""
  const validFrom = input.param === "all" ? policy.ceiling.valid_from : (values as { valid_from?: string }).valid_from ?? null
  return {
    param: input.param,
    values,
    citations: [policyCitation(snapshot, legalRef, validFrom)],
    values_used: input.param === "all" ? { ceiling_pct: policy.ceiling.pct, cap_vnd: policy.cap.vnd } : { [input.param]: values },
  }
}

// --- banks_in_province -----------------------------------------------------

export function banksInProvince(snapshot: Snapshot, input: { province: string }) {
  const needle = fold(input.province)
  const province = snapshot.geo.provinces.find(
    (p) => fold(p.pcode) === needle || fold(p.name_vi) === needle || fold(p.name_en) === needle,
  )
  if (!province) return { found: false as const, citations: [] as Citation[], values_used: { province: input.province } }
  const branches = Object.entries(province.branches_by_bank ?? {})
  return {
    found: true as const,
    province: {
      pcode: province.pcode,
      name_vi: province.name_vi,
      name_en: province.name_en,
      branches_by_bank: province.branches_by_bank,
      branches_total: province.branches_total,
      best_counter_12m: province.best_counter_12m,
    },
    note_vi: branches.length
      ? `Số chi nhánh theo nguồn ${province.branch_source ?? "không rõ"}.`
      : `Snapshot chưa có số chi nhánh cho ${province.name_vi} — không suy đoán.`,
    note_en: branches.length ? `Branch counts per ${province.branch_source ?? "unknown source"}.` : `No branch counts for ${province.name_en} in the snapshot — none are invented.`,
    citations: [geoCitation(snapshot, province.branch_source)],
    values_used: { province: province.pcode, n_banks_with_branches: branches.length },
  }
}

// --- explain ---------------------------------------------------------------

const EXPLAIN_VI: Record<string, (snapshot: Snapshot) => string> = {
  break_even: () =>
    "Break-even là phép tính, không phải dự báo: lãi suất kỳ gửi tiếp theo cần để hoà với khoản khoá dài hơn, theo công thức lãi đơn trên biểu niêm yết của ngân hàng.",
  insured_split: (snapshot) =>
    `Chia tiền nhiều ngân hàng để mỗi ngân hàng giữ gốc+lãi dưới hạn mức bảo hiểm ${snapshot.policy.cap.vnd.toLocaleString("vi-VN")} đồng (Thông tư 05/2026). Phép tính trên lãi suất niêm yết, không phải lời khuyên đầu tư.`,
  ceiling: (snapshot) =>
    `Trần lãi suất ${snapshot.policy.ceiling.pct}%/năm áp cho kỳ hạn ${snapshot.policy.ceiling.terms} (${snapshot.policy.ceiling.legal_ref}). Ngân hàng có thể niêm yết đúng trần, không vượt.`,
  cap: (snapshot) =>
    `Hạn mức bảo hiểm tiền gửi ${snapshot.policy.cap.vnd.toLocaleString("vi-VN")} đồng một người một ngân hàng (${snapshot.policy.cap.legal_ref}). Gốc và lãi vượt hạn mức không được bảo hiểm.`,
  grade: () =>
    "verified = hai nguồn đọc độc lập khớp nhau; single = một nguồn; contested = các nguồn mâu thuẫn và không dùng để tính. Mỗi số đều kèm ngày biểu và thời điểm đọc.",
  plan: () =>
    "Kế hoạch gửi so sánh các kỳ hạn niêm yết trong thời gian bạn cần tiền; rút trước chỉ tính lãi không kỳ hạn. Mọi số là phép tính trên biểu đã đọc, không phải dự báo.",
}

const EXPLAIN_EN: Record<string, (snapshot: Snapshot) => string> = {
  break_even: () =>
    "Break-even is a calculation, not a forecast: the next-period rate needed to tie a longer lock, simple interest on the bank's posted sheet.",
  insured_split: (snapshot) =>
    `Split money across banks so principal plus interest stays under the ${snapshot.policy.cap.vnd.toLocaleString("en-US")} VND insured cap per bank (Thong tu 05/2026). A calculation on posted rates, not investment advice.`,
  ceiling: (snapshot) =>
    `The ${snapshot.policy.ceiling.pct}%/year ceiling applies to terms ${snapshot.policy.ceiling.terms} (${snapshot.policy.ceiling.legal_ref}). Banks may post at the ceiling, not above.`,
  cap: (snapshot) =>
    `The deposit insurance cap is ${snapshot.policy.cap.vnd.toLocaleString("en-US")} VND per person per bank (${snapshot.policy.cap.legal_ref}). Principal and interest above it are uninsured.`,
  grade: () =>
    "verified = two independent readers agree; single = one reader; contested = readers disagree and the cell never feeds a calculation. Every number carries its sheet date and read time.",
  plan: () =>
    "The planner compares posted terms within your horizon; early withdrawal earns only the demand rate. Every number is a calculation on read sheets, not a forecast.",
}

export function explainMetric(snapshot: Snapshot, input: { metric: keyof typeof EXPLAIN_VI | string }) {
  const textVi = EXPLAIN_VI[input.metric]?.(snapshot)
  const textEn = EXPLAIN_EN[input.metric]?.(snapshot)
  if (!textVi || !textEn) return { metric: input.metric, error: "unknown_metric" as const, citations: [] as Citation[], values_used: {} }
  const citations =
    input.metric === "ceiling"
      ? [policyCitation(snapshot, snapshot.policy.ceiling.legal_ref, snapshot.policy.ceiling.valid_from)]
      : input.metric === "cap" || input.metric === "insured_split"
        ? [policyCitation(snapshot, snapshot.policy.cap.legal_ref, snapshot.policy.cap.valid_from)]
        : []
  return { metric: input.metric, text_vi: textVi, text_en: textEn, citations, values_used: { metric: input.metric } }
}

// --- AI SDK tool wrappers --------------------------------------------------

export const TOOL_NAMES = [
  "get_curve",
  "compare_banks",
  "plan_deposit",
  "break_even",
  "insured_split",
  "bank_profile",
  "policy",
  "banks_in_province",
  "explain",
] as const

const bankSchema = z.string().min(2).max(40).describe("Bank code, e.g. OCB, STB, AGRIBANK")

/** Bind the deterministic tools to a snapshot for a ToolLoopAgent. */
export function makeRatewatchTools(snapshot: Snapshot): Record<string, Tool> {
  return {
    get_curve: tool({
      description: "Posted rate curve of one bank on one channel (counter/online), every term, with grades and sheet date.",
      inputSchema: z.object({
        bank: bankSchema,
        channel: z.enum(["counter", "online"]),
      }),
      execute: async (input) => getCurve(snapshot, input),
    }),
    compare_banks: tool({
      description: "Compare at most 3 banks on one term; returns both channels per bank with grades; banks missing from the snapshot are listed.",
      inputSchema: z.object({
        banks: z.array(bankSchema).min(1).max(3),
        term: z.number().int().min(1).max(36).describe("Term in months, e.g. 6"),
      }),
      execute: async (input) => compareBanks(snapshot, input),
    }),
    plan_deposit: tool({
      description: "Plan one amount over a horizon: best single terms, a 6-month renewal ladder and an insured split, ranked by value at the horizon.",
      inputSchema: z.object({
        amount: z.number().min(1).max(1e12).describe("Amount in VND"),
        horizon_months: z.number().int().min(1).max(60),
        online_ok: z.boolean().describe("Whether online channel is acceptable"),
        current_bank: bankSchema.optional(),
      }),
      execute: async (input) => planDeposit(snapshot, input),
    }),
    break_even: tool({
      description: "Break-even renewal rate between a short and a long term of one bank/channel: a calculation, not a forecast.",
      inputSchema: z.object({
        bank: bankSchema,
        channel: z.enum(["counter", "online"]),
        short_m: z.number().int().min(1).max(36),
        long_m: z.number().int().min(1).max(36),
      }),
      execute: async (input) => breakEven(snapshot, input),
    }),
    insured_split: tool({
      description: "Split an amount across banks so each stays inside the 350-million insured cap, at each bank's best verified rate.",
      inputSchema: z.object({
        amount: z.number().min(1).max(1e12).describe("Amount in VND"),
        banks: z.array(bankSchema).max(5).optional(),
      }),
      execute: async (input) => insuredSplit(snapshot, input),
    }),
    bank_profile: tool({
      description: "Quarterly safety metrics (NPL, coverage, LDR, NIM...) and flags of one bank, when present in the snapshot.",
      inputSchema: z.object({ bank: bankSchema }),
      execute: async (input) => bankProfile(snapshot, input),
    }),
    policy: tool({
      description: "Policy parameters from the snapshot: rate ceiling, insured cap, insurance premium, insured coverage.",
      inputSchema: z.object({
        param: z.enum(["ceiling", "cap", "premium", "insured_coverage", "all"]),
      }),
      execute: async (input) => policyParam(snapshot, input),
    }),
    banks_in_province: tool({
      description: "Branch presence and best counter rate for one province (by pcode or Vietnamese/English name).",
      inputSchema: z.object({ province: z.string().min(2).max(60) }),
      execute: async (input) => banksInProvince(snapshot, input),
    }),
    explain: tool({
      description: "Explain a metric or rule (break_even, insured_split, ceiling, cap, grade, plan) in Vietnamese and English.",
      inputSchema: z.object({
        metric: z.enum(["break_even", "insured_split", "ceiling", "cap", "grade", "plan"]),
      }),
      execute: async (input) => explainMetric(snapshot, input),
    }),
  }
}
