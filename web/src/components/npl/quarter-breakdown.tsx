"use client"

import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { waterfallModel, type BankBreakdown } from "@/lib/npl/judge-view"
import { formatNumber, pageHref, type Lang } from "@/lib/npl/view"

function Waterfall({ values, lang }: { values: BankBreakdown; lang: Lang }) {
  const steps = waterfallModel(values, lang)
  const top = Math.max(...steps.map((step) => step.end ?? 0), values.before) || 1
  return (
    <ol className="grid min-w-0 grid-cols-5 gap-2" aria-label={lang === "vi" ? "Các bước thay đổi tỷ lệ nợ xấu" : "Steps in the NPL change"}>
      {steps.map((step, index) => {
        const fill = !step.effect ? "bg-chart-5" : (step.value ?? 0) < 0 ? "bg-chart-2" : "bg-destructive/70"
        const amount = step.value == null ? "—" : `${step.effect && step.value > 0 ? "+" : ""}${formatNumber(step.value, lang, 2)}${step.effect ? "" : "%"}`
        return (
          <li key={step.label} className="grid min-w-0 grid-rows-[auto_1fr_auto] text-center">
            <strong className="text-xs font-semibold tabular-nums sm:text-sm">{amount}</strong>
            <div aria-hidden="true" className="relative mx-auto mt-2 h-24 w-full border-b border-border sm:h-32">
              {step.start != null && step.end != null && (
                <div className={`absolute inset-x-2 rounded-t-sm sm:inset-x-4 ${fill}`} style={{
                  bottom: `${Math.min(step.start, step.end) / top * 100}%`,
                  height: `${Math.abs(step.end - step.start) / top * 100}%`,
                  minHeight: "2px",
                }} />
              )}
              {index < 3 && step.end != null && (
                <div className="pointer-events-none absolute -right-4 z-10 w-6 border-t border-dashed border-muted-foreground/60 sm:-right-6 sm:w-10"
                  style={{ bottom: `${step.end / top * 100}%` }} />
              )}
            </div>
            <span className="min-h-8 pt-1.5 text-[10px] leading-tight text-muted-foreground sm:text-xs">{step.label}</span>
          </li>
        )
      })}
    </ol>
  )
}

export function QuarterBreakdown({ rows, lang, initialBank, initialYear }: {
  rows: BankBreakdown[]
  lang: Lang
  initialBank?: string
  initialYear?: string
}) {
  const vi = lang === "vi"
  const banks = [...new Set(rows.map((row) => row.bank))]
  const [bank, setBank] = useState(() => initialBank && banks.includes(initialBank) ? initialBank : banks.includes("MBB") ? "MBB" : banks[0])
  const [year, setYear] = useState<string | null>(initialYear ?? null)
  const choices = rows.filter((row) => row.bank === bank).sort((a, b) => b.year.localeCompare(a.year))
  const values = choices.find((row) => row.year === year) ?? choices[0]

  if (!values) return <p className="text-sm text-muted-foreground">{vi ? "Chưa có đủ số liệu để tách hai phần thay đổi." : "There is not enough data to split the change."}</p>

  return (
    <div className="min-w-0 rounded-xl border border-border bg-card p-4">
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <span id="breakdown-bank" className="text-xs font-medium">{vi ? "Ngân hàng" : "Bank"}</span>
          <Select value={bank} onValueChange={(value) => { if (value) setBank(value) }}>
            <SelectTrigger aria-labelledby="breakdown-bank" className="min-w-24"><SelectValue /></SelectTrigger>
            <SelectContent align="start">
              {banks.map((code) => <SelectItem key={code} value={code}>{code}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <span id="breakdown-year" className="text-xs font-medium">{vi ? "Năm" : "Year"}</span>
          <Select value={values.year} onValueChange={setYear}>
            <SelectTrigger aria-labelledby="breakdown-year" className="min-w-24"><SelectValue /></SelectTrigger>
            <SelectContent align="start">
              {choices.map((row) => <SelectItem key={row.year} value={row.year}>{row.year}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <a href={pageHref(`/ngan-hang/${bank}`, lang)} className="inline-flex min-h-8 items-center text-sm font-medium underline underline-offset-4 sm:ml-auto">
          {vi ? `Xem ngân hàng ${bank}` : `Open bank ${bank}`}
        </a>
      </div>
      <div className="grid min-w-0 gap-5 md:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <div className="min-w-0">
          <p className="mb-2 text-xs text-muted-foreground">
            {vi ? "Mức nợ xấu tính theo %, phần làm tỷ lệ đổi tính theo điểm %." : "NPL levels are in percent. Effects are in percentage points."}
          </p>
          <Waterfall values={values} lang={lang} />
          <p className="mt-2 text-xs text-muted-foreground">
            {vi ? "Xóa nợ ảnh hưởng đến số dư nợ xấu. Dự phòng đã sử dụng là chỉ báo gián tiếp về xóa nợ."
              : "Write-offs affect the balance of bad debts. Provisions used are a proxy for write-offs."}
          </p>
        </div>
        <div className="min-w-0 border-t border-border pt-3 md:border-t-0 md:border-l md:pt-0 md:pl-4">
          <p className="mb-2 text-sm font-semibold">{vi ? "Cờ vàng cần xem xét" : "Yellow flags to review"}</p>
          <ul className="space-y-2" aria-live="polite">
            {values.checks.map((check) => (
              <li key={check.label} className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-xs">
                <Badge variant={check.flagged ? "default" : "outline"}>{check.label}</Badge>
                <span className="text-muted-foreground">{check.text}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
