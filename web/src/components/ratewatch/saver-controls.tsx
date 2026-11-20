"use client"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { formatAmountInput, parseAmountInput } from "@/lib/ratewatch/format"
import { addMonths, type Lang } from "@/lib/ratewatch/view"

const TICKS = [1, 3, 6, 9, 12, 18, 24, 36]
const CHIPS = [
  { add: 100_000_000, vi: "+100 tr", en: "+100 million" },
  { add: 500_000_000, vi: "+500 tr", en: "+500 million" },
  { add: 1_000_000_000, vi: "+1 tỷ", en: "+1 billion" },
]

export function SaverControls({
  asOf,
  banks,
  lang,
  amount,
  need,
  online,
  bank,
  compare,
  horizon,
  onChange,
}: {
  asOf: string
  banks: { code: string; label: string; chip: string; ready: boolean }[]
  lang: Lang
  amount: number
  need: string
  online: boolean
  bank: string
  compare: string[]
  horizon: number
  onChange: (patch: { amount?: number; need?: string; online?: boolean; bank?: string; compare?: string[] }) => void
}) {
  const vi = lang === "vi"
  const months = Math.min(36, Math.max(1, horizon || 1))
  const items = banks.map((item) => ({ value: item.code, label: item.label }))
  const grouped = formatAmountInput(amount, lang)
  return (
    <form className="grid gap-3" onSubmit={(event) => event.preventDefault()}>
      <div className="grid gap-1">
        <Label htmlFor="amount">{vi ? "Số tiền" : "Amount"}</Label>
        <div className="flex items-center gap-2">
          <Input
            id="amount"
            className="min-h-11 tabular-nums"
            inputMode="numeric"
            value={grouped}
            onChange={(event) => {
              const next = parseAmountInput(event.target.value)
              onChange({ amount: next ?? 0 })
            }}
          />
          <span className="text-sm text-muted-foreground">{vi ? "đ" : "VND"}</span>
        </div>
        <div className="flex flex-wrap gap-1">
          {CHIPS.map((chip) => (
            <Button key={chip.add} type="button" variant="outline" size="sm" className="min-h-11" onClick={() => onChange({ amount: amount + chip.add })}>
              {vi ? chip.vi : chip.en}
            </Button>
          ))}
        </div>
        {amount <= 0 ? (
          <p className="text-xs text-destructive">{vi ? "Nhập số tiền lớn hơn 0." : "Enter an amount above 0."}</p>
        ) : (
          <p className="text-xs text-muted-foreground">{vi ? "Dấu chấm hiện khi bạn gõ." : "Separators appear as you type."}</p>
        )}
      </div>
      <div className="grid gap-1">
        <Label htmlFor="horizon">{vi ? `Kỳ hạn: ${months} tháng` : `Horizon: ${months} months`}</Label>
        <Slider
          id="horizon"
          min={1}
          max={36}
          step={1}
          value={[months]}
          onValueChange={(next) => {
            const picked = Array.isArray(next) ? next[0] : next
            if (typeof picked === "number") onChange({ need: addMonths(asOf, picked) })
          }}
        />
        <div className="relative h-4 text-[10px] text-muted-foreground" aria-hidden="true">
          {TICKS.map((tick) => (
            <span key={tick} className="absolute -translate-x-1/2" style={{ left: `${((tick - 1) / 35) * 100}%` }}>
              {tick}
            </span>
          ))}
        </div>
      </div>
      <div className="grid gap-1">
        <Label htmlFor="need">{vi ? "hoặc chọn ngày" : "or pick a date"}</Label>
        <Input id="need" className="min-h-11" type="date" value={need} onChange={(event) => event.target.value && onChange({ need: event.target.value })} />
      </div>
      <div className="grid gap-1">
        <Label htmlFor="bank">{vi ? "Ngân hàng trên biểu đồ" : "Bank on the chart"}</Label>
        <Select value={bank} onValueChange={(value) => value && onChange({ bank: value })} items={items}>
          <SelectTrigger id="bank" className="w-full min-h-11 max-w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {items.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>
      <div className="flex min-h-11 items-center gap-2">
        <Checkbox id="online" checked={online} onCheckedChange={(checked) => onChange({ online: checked === true })} />
        <Label htmlFor="online">{vi ? "Gửi online được" : "Online is fine"}</Label>
      </div>
      <fieldset className="grid gap-2">
        <legend className="text-sm font-medium">{vi ? "So sánh thêm, tối đa 3" : "Compare up to 3 more"}</legend>
        <div className="flex flex-wrap gap-2">
          {banks
            .filter((item) => item.code !== bank)
            .map((item) => {
              const on = compare.includes(item.code)
              const full = !on && compare.length >= 3
              const unread = vi ? "chưa đọc được biểu" : "sheet not read"
              return (
                <Label
                  key={item.code}
                  title={item.ready ? undefined : unread}
                  className="min-h-11 gap-2 rounded-lg border border-border px-3 py-2 text-sm font-normal"
                >
                  <Checkbox
                    checked={on}
                    disabled={!item.ready || full}
                    onCheckedChange={(checked) => {
                      if (!item.ready) return
                      const next = checked === true ? [...compare, item.code].slice(0, 3) : compare.filter((code) => code !== item.code)
                      onChange({ compare: next.filter((code) => code !== bank) })
                    }}
                  />
                  {item.chip}
                </Label>
              )
            })}
        </div>
      </fieldset>
    </form>
  )
}
