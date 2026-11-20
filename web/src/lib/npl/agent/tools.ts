// Deterministic tools for the NPL study assistant. Every tool reads the
// published snapshot only (web/seed/npl/snapshot.json, fixture fallback) and
// returns its values together with citations (source, period, n, CI where
// relevant) so the model can only speak numbers the snapshot carries.
import type { Snapshot, Term } from "../view.ts"

export interface NplCitation {
  source: string
  period: string | null
  n: number | null
  ci95: [number, number] | null
}

function cite(source: string, period: string | null, n: number | null, ci95: [number, number] | null = null): NplCitation {
  return { source, period, n, ci95 }
}

function toCi95(ci: (number | null)[] | null | undefined): [number, number] | null {
  const lo = ci?.[0]
  const hi = ci?.[1]
  return typeof lo === "number" && typeof hi === "number" ? ([lo, hi] as [number, number]) : null
}

function termCitation(prefix: string, term: Term, period: string | null): NplCitation {
  return cite(prefix, period, term.n, toCi95(term.ci95))
}

// --- overview --------------------------------------------------------------

export function overview(snapshot: Snapshot) {
  const last = snapshot.series.median_by_period.at(-1) ?? null
  return {
    headline: snapshot.headline,
    level: snapshot.kpis.level,
    benchmark: snapshot.kpis.benchmark,
    trend: snapshot.kpis.trend,
    last_median: last,
    citations: [
      cite("snapshot headline", snapshot.meta.period_end, snapshot.kpis.benchmark.n, toCi95(snapshot.kpis.benchmark.ci95)),
      cite("FiinQuant get_ratios (consolidated)", snapshot.meta.period_end, snapshot.meta.n_bank_quarters),
    ],
    note_vi: "Đây là liên hệ, không phải nhân quả; dự báo là phép tính, không phải lời hứa.",
    note_en: "M4–M6 results are association, not causation; forecasts are calculation, not a promise.",
  }
}

// --- quarter_effects -------------------------------------------------------

export function quarterEffects(snapshot: Snapshot) {
  return {
    effects: snapshot.quarter_effects,
    citations: snapshot.quarter_effects.map((e) => termCitation("quarter effects (Q2/Q3/Q4 vs Q1)", e, `Q${e.quarter}`)),
    note_vi: "Đây là liên hệ, không phải nhân quả — dữ liệu bảng 2021Q2–2026Q3.",
    note_en: "Association from 2021Q2–2026Q3 panel data, not causation.",
  }
}

// --- bank_profile ----------------------------------------------------------

export function bankProfile(snapshot: Snapshot, input: { code: string }) {
  const code = input.code.trim().toUpperCase()
  const bank = snapshot.banks.find((b) => b.code === code)
  if (!bank) return { found: false as const, citations: [] as NplCitation[] }
  return {
    found: true as const,
    bank,
    citations: [cite("bank profile", bank.latest?.period ?? null, bank.years, null)],
  }
}

// --- adjusted_change -------------------------------------------------------

export function adjustedChange(snapshot: Snapshot, input: { code: string; period?: string }) {
  const code = input.code.trim().toUpperCase()
  const bank = snapshot.banks.find((b) => b.code === code)
  if (!bank) return { found: false as const, citations: [] as NplCitation[] }
  const period = input.period ?? bank.latest?.period
  if (!period) return { found: false as const, citations: [] as NplCitation[] }
  const row = bank.quarters.find((q) => q.period === period.toUpperCase())
  if (!row) return { found: false as const, citations: [] as NplCitation[] }
  return {
    found: true as const,
    row,
    citations: [cite("adjusted change (bank-quarter)", row.period, 1)],
  }
}

// --- compare_banks ---------------------------------------------------------

export function compareBanks(snapshot: Snapshot, input: { codes: string[] }) {
  if (input.codes.length > 4) throw new Error("compare at most 4 banks")
  const rows: {
    code: string
    name_vi: string
    name_en: string
    ownership: "state" | "private"
    q4_change_median_pp: number | null
    q1_rebound_median_pp: number | null
    latest_period: string | null
    adjusted_change_pp: number | null
    forecast_next: { period: string; npl_pct: number; lo80: number; hi80: number } | null
  }[] = []
  const missing: string[] = []
  for (const raw of input.codes) {
    const code = raw.trim().toUpperCase()
    const bank = snapshot.banks.find((b) => b.code === code)
    if (!bank) {
      missing.push(code)
      continue
    }
    rows.push({
      code: bank.code,
      name_vi: bank.name_vi,
      name_en: bank.name_en,
      ownership: bank.ownership,
      q4_change_median_pp: bank.q4_change_median_pp,
      q1_rebound_median_pp: bank.q1_rebound_median_pp,
      latest_period: bank.latest?.period ?? null,
      adjusted_change_pp: bank.latest?.adjusted_change_pp ?? null,
      forecast_next: bank.latest?.forecast_next ?? null,
    })
  }
  return {
    rows,
    missing,
    citations: rows.map((row) => cite("bank medians (FiinQuant panel)", row.latest_period, null)),
  }
}

// --- forecast --------------------------------------------------------------

export function forecast(snapshot: Snapshot, input: { code: string }) {
  const code = input.code.trim().toUpperCase()
  const bank = snapshot.banks.find((b) => b.code === code)
  if (!bank) return { found: false as const, citations: [] as NplCitation[] }
  const next = bank.latest?.forecast_next ?? null
  if (!next) return { found: false as const, citations: [] as NplCitation[] }
  return {
    found: true as const,
    forecast: next,
    mae: snapshot.forecast.mae,
    citations: [cite("forecast (model vs seasonal naive)", next.period, snapshot.forecast.backtest.length, [next.lo80, next.hi80])],
    note_vi: "Đây là phép tính, không phải lời hứa.",
    note_en: "This is a calculation, not a promise.",
  }
}

// --- market_reaction -------------------------------------------------------

export function marketReaction(snapshot: Snapshot) {
  return {
    events_with_car: snapshot.market.events_with_car,
    car_all: snapshot.market.car_by_day.filter((row) => row.group === "all"),
    regressions: snapshot.market.regressions,
    reading_vi: snapshot.market.reading_vi,
    reading_en: snapshot.market.reading_en,
    citations: [cite("market CAR around disclosure events", snapshot.market.period_end ?? null, snapshot.market.events_with_car)],
  }
}

// --- method ----------------------------------------------------------------

export function method(snapshot: Snapshot, input: { model_id: string }) {
  const id = input.model_id.trim().toUpperCase()
  const entry = snapshot.method.find((m) => m.id.toUpperCase() === id)
  if (!entry) return { found: false as const, valid_ids: snapshot.method.map((m) => m.id) }
  return {
    found: true as const,
    entry,
    citations: [cite("study method", snapshot.meta.period_end, entry.n)],
  }
}

// --- limitations -----------------------------------------------------------

export function limitations(snapshot: Snapshot) {
  return {
    items: snapshot.limitations,
    legal: snapshot.legal,
    citations: [cite("snapshot limitations", snapshot.meta.period_end, snapshot.meta.n_bank_quarters)],
  }
}

// --- glossary --------------------------------------------------------------

const GLOSSARY: Record<string, { vi: string; en: string }> = {
  npl: {
    vi: "Nợ xấu (NPL): khoản cho vay mà người vay không trả được đúng hạn theo chuẩn của Ngân hàng Nhà nước.",
    en: "NPL: a loan the borrower is not repaying on schedule (non-performing loan).",
  },
  "adjusted change": {
    vi: "Thay đổi NPL sau khi loại bỏ hiệu ứng quý (so với quý 1) — đọc phần thay đổi sau hiệu ứng quý, không phải mức giảm thô.",
    en: "The NPL change after removing the quarter effect (versus Q1) — read it instead of the raw quarter-over-quarter move.",
  },
  "quarter effect": {
    vi: "Hiệu ứng quý: mức chênh lệch trung vị NPL của quý 2/3/4 so với quý 1 trong cùng năm.",
    en: "How much the median NPL differs in Q2/Q3/Q4 versus Q1 within the same year.",
  },
  "wild bootstrap": {
    vi: "Kiểm định wild cluster bootstrap theo cụm ngân hàng — p-value bền vững khi số ngân hàng ít.",
    en: "A wild cluster bootstrap over bank clusters — a sturdier p-value when banks are few.",
  },
  coverage: {
    vi: "Tỷ lệ bao phủ nợ xấu: dự phòng rủi ro tín dụng chia cho nợ xấu.",
    en: "Loan-loss reserves divided by NPLs.",
  },
  car: {
    vi: "Lợi suất bất thường tích luỹ (CAR) quanh sự kiện công bố báo cáo — so với ngày thường.",
    en: "Cumulative abnormal return around a disclosure event, versus normal days.",
  },
  ldr: {
    vi: "Tỷ lệ cho vay trên tiền gửi (LDR).",
    en: "Loan-to-deposit ratio.",
  },
  nim: {
    vi: "Thu nhập lãi thuần trên tài sản sinh lời (NIM).",
    en: "Net interest margin over earning assets.",
  },
}

export function glossary(snapshot: Snapshot, input: { term: string }) {
  void snapshot
  const aliases: Record<string, string> = {
    "nợ xấu": "npl",
    "no xau": "npl",
    "npl": "npl",
    "hiệu ứng quý": "quarter effect",
    "quarter effect": "quarter effect",
    "wild bootstrap": "wild bootstrap",
    "bao phủ nợ xấu": "coverage",
    "coverage": "coverage",
    "ldr": "ldr",
    "nim": "nim",
    "car": "car",
    "thay đổi đã điều chỉnh": "adjusted change",
    "adjusted change": "adjusted change",
  }
  const key = aliases[input.term.trim().toLowerCase()]
  const entry = key ? GLOSSARY[key] : undefined
  if (!entry) return { found: false as const, terms: Object.keys(GLOSSARY) }
  return {
    found: true as const,
    entry,
    citations: [cite("glossary (in-code dictionary)", null, null)],
  }
}
