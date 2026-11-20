import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"

import { LegalFooter } from "@/components/ratewatch/legal-footer"
import { RateList } from "@/components/ratewatch/rate-list"
import { bankByCode, loadSnapshot } from "@/lib/ratewatch/load"
import { formatPct, formatSheetDate } from "@/lib/ratewatch/format"
import { selectionFromParams } from "@/lib/ratewatch/decide"
import { tableRows, type Lang } from "@/lib/ratewatch/view"
import type { BankProfile } from "@/lib/ratewatch/types"

export const instant = false

type Query = Record<string, string | string[] | undefined>

const METRIC_LABEL: Record<string, { vi: string; en: string }> = {
  npl_pct: { vi: "Nợ xấu / dư nợ", en: "NPL / loans" },
  npl_change_pp: { vi: "Nợ xấu thay đổi, điểm phần trăm", en: "NPL change, percentage points" },
  npl_amount_growth_pct: { vi: "Số nợ xấu tăng", en: "NPL amount growth" },
  coverage_pct: { vi: "Bao phủ nợ xấu", en: "NPL coverage" },
  ldr_pct: { vi: "LDR", en: "LDR" },
  roa_pct: { vi: "ROA", en: "ROA" },
  nim_pct: { vi: "NIM", en: "NIM" },
  loan_growth_pct: { vi: "Tăng trưởng cho vay", en: "Loan growth" },
  deposit_growth_pct: { vi: "Tăng trưởng tiền gửi", en: "Deposit growth" },
  pb: { vi: "P/B", en: "P/B" },
  vol60_pct: { vi: "Biến động 60 phiên", en: "60-session volatility" },
  drawdown_pct: { vi: "Mức giảm từ đỉnh", en: "Drawdown" },
  foreign_net_20d_bn: { vi: "Khối ngoại mua ròng 20 phiên, tỷ đồng", en: "Foreign net buy, 20 sessions, billion VND" },
}

export async function generateMetadata({ params }: { params: Promise<{ code: string }> }): Promise<Metadata> {
  const { code } = await params
  const bank = bankByCode(loadSnapshot(), code)
  return { title: bank ? bank.name_vi : "Không thấy ngân hàng" }
}

function ratioStory(profile: BankProfile, lang: Lang): string | null {
  const change = profile.metrics.npl_change_pp
  const amount = profile.metrics.npl_amount_growth_pct
  if (typeof change !== "number" || typeof amount !== "number") return null
  const vi = lang === "vi"
  if (change < 0 && amount > 0) {
    return vi
      ? "Tỷ lệ nợ xấu giảm trong khi số nợ xấu tăng: mẫu số dư nợ lớn hơn, không phải nợ xấu giảm thật."
      : "The NPL ratio fell while the NPL amount rose: the loan book in the denominator grew."
  }
  if (change < 0 && amount <= 0) {
    return vi ? "Nợ xấu giảm cả về tỷ lệ và về số tiền." : "Both the NPL ratio and the NPL amount fell."
  }
  if (change > 0) {
    return vi ? "Tỷ lệ nợ xấu tăng so với quý trước trong bản này." : "The NPL ratio rose versus the previous quarter in this record."
  }
  return null
}

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ code: string }>
  searchParams: Promise<Query>
}) {
  const { code } = await params
  const snapshot = loadSnapshot()
  const bank = bankByCode(snapshot, code)
  if (!bank) notFound()
  const selection = selectionFromParams(await searchParams, snapshot)
  const vi = selection.lang === "vi"
  const rows = tableRows([bank], selection.lang)
  const profile = bank.profile
  const story = profile ? ratioStory(profile, selection.lang) : null
  const metrics = profile
    ? Object.entries({ ...profile.metrics, ...profile.market }).filter((entry): entry is [string, number] => typeof entry[1] === "number")
    : []
  return (
    <>
      <p className="text-sm">
        <Link href="/" className="underline underline-offset-4">{vi ? "Về màn hình gửi tiền" : "Back to the saver screen"}</Link>
      </p>
      <h1 className="text-xl font-semibold text-balance">
        {vi
          ? `${bank.name_vi}. ${bank.rates.length} dòng${bank.sheet_date ? `, biểu ${formatSheetDate(bank.sheet_date)}` : ""}. Nguồn: ${bank.sheet_url}.`
          : `${bank.name_en}. ${bank.rates.length} rows${bank.sheet_date ? `, sheet ${formatSheetDate(bank.sheet_date)}` : ""}. Source: ${bank.sheet_url}.`}
      </h1>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? `${profile ? Object.keys(profile.metrics).length : 0} chỉ tiêu hồ sơ. Nguồn: FiinQuant (FiinGroup) khi bản có số.` : `${profile ? Object.keys(profile.metrics).length : 0} profile figures. Source: FiinQuant (FiinGroup) when this edition has them.`}</h2>
        {profile ? (
          <div className="flex flex-col gap-2 text-sm">
            <p>{vi ? "Quý" : "Quarter"} {profile.quarter}. {vi ? "Nguồn" : "Source"}: {profile.source}</p>
            {story ? <p>{story}</p> : null}
            <ul className="flex flex-wrap gap-2">
              {metrics.map(([key, value]) => (
                <li key={key} className="rounded-full border border-border px-2 py-1 text-xs">
                  {METRIC_LABEL[key]?.[selection.lang] ?? key} {formatPct(value, 2, selection.lang)}
                  {key === "ldr_pct" ? (vi ? " · hạn mức được dẫn 85% (Thông tư 22/2019)" : " · cited limit 85% (Circular 22/2019)") : ""}
                </li>
              ))}
            </ul>
            {profile.flags.map((flag) => (
              <p key={flag.id}>{flag.text} · {flag.rule_ref}</p>
            ))}
            {Object.entries(profile.percentiles).filter((entry) => typeof entry[1] === "number").map(([key, value]) => (
              <p key={key} className="text-xs text-muted-foreground">
                {vi ? "Phân vị" : "Percentile"} {METRIC_LABEL[key]?.[selection.lang] ?? key}: {formatPct(value as number, 0, selection.lang)}
              </p>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            {vi
              ? "Chưa có số nợ xấu, bao phủ, LDR, ROA, P/B hay biến động cho ngân hàng này trong bản số liệu đang mở. Khi có, nguồn ghi là FiinQuant (FiinGroup), chỉ số tổng hợp."
              : "This edition has no NPL, coverage, LDR, ROA, P/B or volatility figure for this bank. When present, the source line is FiinQuant (FiinGroup), aggregates only."}
          </p>
        )}
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? `${rows.length} dòng lãi suất có ngày biểu.` : `${rows.length} posted rows with a sheet date.`}</h2>
        <RateList rows={rows} lang={selection.lang} />
      </section>
      <LegalFooter snapshot={snapshot} bank={bank} lang={selection.lang} />
    </>
  )
}
