import { loadSnapshot } from "@/lib/ratewatch/load"

function cell(value: string | number | null): string {
  const text = value === null || value === undefined ? "" : String(value)
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function GET() {
  const snapshot = loadSnapshot()
  const lines = ["bank_code,name,term_months,channel,tier,rate_pct,grade,sheet_date,source_url,read_at"]
  for (const bank of snapshot.banks) {
    for (const rate of bank.rates) {
      lines.push(
        [
          bank.code,
          bank.name_vi,
          rate.term_months,
          rate.channel,
          rate.tier,
          rate.rate_pct,
          rate.grade,
          bank.sheet_date,
          rate.readers[0]?.source_url || bank.sheet_url,
          bank.read_at,
        ].map(cell).join(","),
      )
    }
  }
  return new Response(`${lines.join("\n")}\n`, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": "attachment; filename=lai-suat.csv",
    },
  })
}
