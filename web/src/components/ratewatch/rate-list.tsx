"use client"

import Link from "next/link"

import { Badge } from "@/components/ui/badge"
import type { TableRow } from "@/lib/ratewatch/view"
import type { Lang } from "@/lib/ratewatch/view"

function channelLabel(channel: string, lang: Lang): string {
  if (channel === "counter") return lang === "vi" ? "quầy" : "counter"
  if (channel === "online") return "online"
  return channel
}

function tierLabel(tier: string, lang: Lang): string {
  if (!tier) return ""
  if (tier === "tu_2_ty") return lang === "vi" ? "bậc từ 2 tỷ" : "from 2 billion"
  return tier
}

export function RateList({ rows, lang, onSelect }: { rows: TableRow[]; lang: Lang; onSelect?: (code: string) => void }) {
  const vi = lang === "vi"
  if (!rows.length) {
    return <p className="text-sm text-muted-foreground">{vi ? "Không có dòng đã có ngày biểu." : "No row with a sheet date."}</p>
  }
  return (
    <ul className="flex flex-col gap-2">
      {rows.map((row) => {
        const tier = tierLabel(row.tier, lang)
        return (
          <li key={`${row.bankCode}-${row.channel}-${row.tier}-${row.term}-${row.grade}`} className="flex flex-col gap-1 rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
            <div className="flex flex-wrap items-center gap-2">
              {onSelect ? (
                <button type="button" className="min-h-11 text-left font-medium underline-offset-4 hover:underline" onClick={() => onSelect(row.bankCode)}>
                  {row.bankName}
                </button>
              ) : (
                <Link href={`/ngan-hang/${row.bankCode}`} className="font-medium underline-offset-4 hover:underline">
                  {row.bankName}
                </Link>
              )}
              {onSelect ? (
                <Link href={`/ngan-hang/${row.bankCode}`} className="inline-flex min-h-11 items-center underline underline-offset-4">
                  {vi ? "Trang ngân hàng" : "Bank page"}
                </Link>
              ) : null}
              <span>
                {row.term} {vi ? "tháng" : "months"} · {channelLabel(row.channel, lang)}
                {tier ? ` · ${tier}` : ""}
              </span>
              <span className="font-medium">{row.rateText}</span>
              <Badge variant={row.grade === "contested" ? "destructive" : row.grade === "verified" ? "default" : "secondary"}>
                {row.gradeLabel}
                {row.gradeDetail ? ` · ${row.gradeDetail}` : ""}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground break-words">
              {vi ? "Ngày biểu" : "Sheet date"} {row.sheetDate}
              {row.sourceUrl ? (
                <>
                  {" · "}
                  <a href={row.sourceUrl} className="underline underline-offset-4" rel="noreferrer">
                    {vi ? "Nguồn" : "Source"}
                  </a>
                </>
              ) : null}
            </p>
          </li>
        )
      })}
    </ul>
  )
}
