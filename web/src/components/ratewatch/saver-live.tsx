"use client"

import { useEffect, useState } from "react"

import { ChartHelp } from "@/components/ratewatch/chart-help"
import { AnimatedPercents, CountUp } from "@/components/ratewatch/count-up"
import { CurveChart } from "@/components/ratewatch/curve-chart"
import { HeatTable } from "@/components/ratewatch/heat-table"
import { LegalFooter } from "@/components/ratewatch/legal-footer"
import { SaverControls } from "@/components/ratewatch/saver-controls"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { saverModel, type Selection } from "@/lib/ratewatch/decide"
import { formatPct, formatReadClock, formatSheetDate, formatVnd } from "@/lib/ratewatch/format"
import type { Snapshot } from "@/lib/ratewatch/types"
import { addMonths, bankMenuLabel, chartPoints, gradeBadge, horizonMonths, personaPresets } from "@/lib/ratewatch/view"

function planLabel(kind: string, vi: boolean): string {
  if (kind === "single") return vi ? "Một kỳ hạn" : "One term"
  if (kind === "ladder_6_renewal") return vi ? "6 tháng rồi gửi tiếp" : "6 months, then renew"
  return vi ? "Tách nhiều ngân hàng" : "Split across banks"
}

function readyFor(bank: Snapshot["banks"][number], channel: string): boolean {
  return Boolean(bank.sheet_date) && bank.rates.some((rate) => rate.channel === channel && (rate.tier ?? "") === "")
}

export function SaverLive({ snapshot, initial }: { snapshot: Snapshot; initial: Selection }) {
  const [selection, setSelection] = useState(() => {
    const months = horizonMonths(initial.asOf, initial.need)
    const clamped = Math.min(36, Math.max(1, months || 1))
    return clamped === months ? initial : { ...initial, need: addMonths(initial.asOf, clamped) }
  })
  const model = saverModel(snapshot, selection)
  const vi = selection.lang === "vi"
  const lang = selection.lang
  const shortName = lang === "en" ? model.bank.name_en : model.bank.name_vi
  const sheetDate = model.bank.sheet_date ? formatSheetDate(model.bank.sheet_date) : ""
  const clock = formatReadClock(model.bank.read_at, lang)
  const channelWord = model.channel === "online" ? "online" : (vi ? "quầy" : "counter")
  const focusRow = model.bank.rates.find((rate) => rate.channel === model.channel && rate.term_months === model.numbers.yourTerm && (rate.tier ?? "") === "")
  const grade = focusRow ? gradeBadge(focusRow.grade, focusRow.grade_note, lang).label : ""
  const personas = personaPresets(selection.asOf)
  const ceilingText = formatPct(snapshot.policy.ceiling.pct, 2, lang)
  const ceilingLabel = snapshot.policy.ceiling.legal_ref.includes("2411/QĐ-NHNN")
    ? (vi ? `Trần ${ceilingText}% · QĐ 2411` : `Ceiling ${ceilingText}% · Decision 2411`)
    : (vi ? `Trần ${ceilingText}%` : `Ceiling ${ceilingText}%`)
  const bandLabel = vi ? `Vùng trần ${ceilingText}%` : `Ceiling band ${ceilingText}%`
  const insuredShare = selection.amount > 0 ? (model.figures.insuredVnd / selection.amount) * 100 : 0

  useEffect(() => {
    const params = new URLSearchParams()
    params.set("amount", String(selection.amount))
    params.set("need", selection.need)
    params.set("online", selection.online ? "1" : "0")
    params.set("bank", selection.bank)
    if (selection.compare.length) params.set("cmp", selection.compare.join(","))
    if (selection.lang === "en") params.set("lang", "en")
    const next = `?${params.toString()}`
    if (window.location.search !== next) window.history.replaceState(null, "", next)
  }, [selection])

  function update(patch: Partial<Pick<Selection, "amount" | "need" | "online" | "bank" | "compare">>) {
    const next = { ...selection, ...patch }
    if (patch.need) {
      const months = horizonMonths(selection.asOf, patch.need)
      const clamped = Math.min(36, Math.max(1, months || 1))
      if (clamped !== months) next.need = addMonths(selection.asOf, clamped)
    }
    setSelection(next)
  }

  function pickBank(code: string) {
    const item = snapshot.banks.find((bank) => bank.code === code)
    const channel = selection.online ? "online" : "counter"
    const other = selection.online ? "counter" : "online"
    const has = item ? chartPoints(item, channel).length > 0 : false
    const otherHas = item ? chartPoints(item, other).length > 0 : false
    setSelection({
      ...selection,
      bank: code,
      compare: selection.compare.filter((entry) => entry !== code),
      online: !has && otherHas ? other === "online" : selection.online,
    })
  }

  return (
    <>
      <header className="grid gap-1">
        <h1 className="line-clamp-2 text-2xl font-semibold leading-snug text-balance">
          <AnimatedPercents text={model.chartTitle} lang={lang} />
        </h1>
        <p className="text-sm text-muted-foreground">
          {vi ? "Biểu" : "Sheet"} {shortName} {channelWord}
          {" · "}
          {vi ? "ngày" : "date"} {sheetDate}
          {" · "}
          {vi ? "đọc lúc" : "read"} {clock}
          {grade ? ` · ${grade}` : ""}
          {" · "}
          <a href={model.bank.sheet_url} className="underline underline-offset-4" rel="noreferrer">{vi ? "nguồn ↗" : "source ↗"}</a>
        </p>
      </header>
      <section aria-label={vi ? "Bốn số chính" : "Four key figures"} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card size="sm">
          <CardHeader>
            <CardTitle>{vi ? "Lãi của bạn" : "Your interest"}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1">
            <p className="text-[2.5rem] leading-none font-semibold tabular-nums">
              {model.numbers.yourRate === null ? "—" : <CountUp value={model.numbers.yourRate} text={(value) => `${formatPct(value, 2, lang)}%/năm`} />}
            </p>
            <p className="text-xs text-muted-foreground">{model.figures.yourSub}</p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardHeader>
            <CardTitle>{vi ? "Trần kỳ dưới 6 tháng" : "Ceiling under 6 months"}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1">
            <p className="text-[2.5rem] leading-none font-semibold tabular-nums">
              <CountUp value={model.numbers.ceilingPct} text={(value) => `${formatPct(value, 2, lang)}%/năm`} />
            </p>
            <p className="text-xs text-muted-foreground">{model.figures.ceilingSub}</p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardHeader>
            <CardTitle>{vi ? "Hòa vốn khi tái tục" : "Break-even on renewal"}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1">
            <p className="text-[2.5rem] leading-none font-semibold tabular-nums">
              {model.breakEven === null ? "—" : <CountUp value={model.breakEven} text={(value) => `${formatPct(value, 2, lang)}%/năm`} />}
            </p>
            <p className="text-xs text-muted-foreground">{vi ? "phép tính, không phải dự báo" : "a calculation, not a forecast"}</p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardHeader>
            <CardTitle>{vi ? "Được bảo hiểm" : "Insured"}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1">
            <p className="text-[1.65rem] leading-none font-semibold tabular-nums">
              <CountUp value={model.figures.insuredVnd} text={(value) => formatVnd(value, lang)} />
              <span className="text-base font-normal text-muted-foreground"> / </span>
              <CountUp value={selection.amount} text={(value) => formatVnd(value, lang)} />
            </p>
            <div className="h-1.5 w-full rounded-full bg-muted" aria-hidden="true">
              <div className="h-full rounded-full bg-foreground" style={{ width: `${Math.min(100, insuredShare)}%` }} />
            </div>
            <p className="text-xs text-muted-foreground">{model.figures.insuredSub}</p>
          </CardContent>
        </Card>
      </section>
      <section className="grid gap-3 lg:grid-cols-3">
        <Card size="sm" className="min-w-0 lg:col-span-2">
          <CardHeader>
            <CardTitle className="line-clamp-2 text-balance">{model.chartTitle}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {model.chart.rows.length ? (
              <CurveChart
                rows={model.chart.rows}
                series={model.chart.series}
                ceiling={snapshot.policy.ceiling.pct}
                horizon={model.horizonMonths}
                bandLabel={bandLabel}
                ceilingLabel={ceilingLabel}
                lang={lang}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                {vi ? "Kênh này không có điểm đã kiểm hoặc một nguồn để vẽ. Dòng mâu thuẫn không lên biểu đồ." : "This channel has no checked or single-source point to plot. Contested rows stay off the chart."}
              </p>
            )}
            <ChartHelp lang={lang}>
              {vi
                ? "Trục ngang là số tháng. Vùng xám là kỳ 1–5 tháng. Vạch ngang là trần. Vạch đứng là kỳ bạn đang chọn. Đưa chuột vào một điểm để xem mức, cách chấm, ngày biểu và tên miền nguồn."
                : "The horizontal axis is months. The shaded band is terms of 1–5 months. The horizontal line is the ceiling. The vertical line is your horizon. Hover a point for the rate, grade, sheet date and source domain."}
            </ChartHelp>
          </CardContent>
        </Card>
        <Card size="sm" className="min-w-0">
          <CardHeader>
            <CardTitle>{vi ? "Kế hoạch của bạn" : "Your plan"}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <div className="flex flex-wrap gap-2">
              {personas.map((persona) => (
                <Button
                  key={persona.id}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-auto min-h-11 max-w-full whitespace-normal text-left"
                  onClick={() => update({ amount: persona.amount, need: persona.needDate, online: persona.onlineOk, bank: persona.bankCode, compare: [] })}
                >
                  {vi ? persona.labelVi : persona.labelEn}
                </Button>
              ))}
            </div>
            <SaverControls
              asOf={selection.asOf}
              lang={lang}
              banks={snapshot.banks.map((bank) => ({
                code: bank.code,
                label: bankMenuLabel(bank.code, lang),
                chip: lang === "en" ? bank.name_en : bank.name_vi,
                ready: readyFor(bank, model.channel),
              }))}
              amount={selection.amount}
              need={selection.need}
              online={selection.online}
              bank={selection.bank}
              compare={model.compare}
              horizon={model.horizonMonths}
              onChange={update}
            />
            <div className="grid gap-3 text-sm">
              {model.plans.slice(0, 3).map((item, index) => (
                <div key={`${item.kind}-${index}`} className="grid gap-1">
                  <p className="font-medium">{planLabel(item.kind, vi)}</p>
                  <p className="tabular-nums">{formatVnd(item.interest_vnd, lang)} {vi ? "lãi đến hạn" : "interest at the horizon"}</p>
                  <div className="h-1.5 w-full rounded-full bg-muted" aria-hidden="true">
                    <div className="h-full rounded-full bg-foreground" style={{ width: `${Math.min(100, item.insured_share * 100)}%` }} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {vi ? "Phần gốc trong hạn mức" : "Principal inside the cap"}: {formatPct(item.insured_share * 100, 1, lang)}%
                  </p>
                  <ul className="grid gap-1">
                    {item.rows.map((row, rowIndex) => (
                      <li key={`${row.bank_code}-${row.term_months}-${rowIndex}`} className="flex flex-wrap items-center gap-1">
                        <span>{bankMenuLabel(row.bank_code, lang)} · {row.term_months} {vi ? "tháng" : "months"}</span>
                        <Badge variant="outline">{gradeBadge(row.grade === "single" || row.grade === "contested" ? row.grade : "verified", "", lang).label}</Badge>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {!model.plans.length ? <p>{vi ? "Không có kỳ đã kiểm khớp ngày cần tiền." : "No checked term matches the date."}</p> : null}
            </div>
          </CardContent>
        </Card>
      </section>
      <section className="min-w-0">
        <h2 className="mb-2 text-base font-semibold">
          {vi ? "Bảng lãi theo kỳ. Bấm tên ngân hàng để vẽ đường của ngân hàng đó." : "Rates by term. Click a bank name to draw that bank."}
        </h2>
        <HeatTable banks={snapshot.banks} channel={model.channel} sortTerm={model.horizonMonths} lang={lang} onSelect={pickBank} />
      </section>
      <LegalFooter snapshot={snapshot} bank={model.bank} lang={lang} />
    </>
  )
}
