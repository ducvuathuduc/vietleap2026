"use client"

import { useState } from "react"

import { ChartHelp } from "@/components/ratewatch/chart-help"
import { Choropleth } from "@/components/ratewatch/choropleth"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { formatPct } from "@/lib/ratewatch/format"
import type { Snapshot } from "@/lib/ratewatch/types"
import { bankMenuLabel, branchCode, gradeBadge, mapHeadline, provinceOffers, quantileSteps, type Lang } from "@/lib/ratewatch/view"

type Metric = "total" | "bank" | "per100k"

const BOUNDARY = "Ranh giới: GSO/OCHA COD-AB v02 (CC BY-IGO) · Bao gồm Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa)."

function bestOnlineBranch(banks: Snapshot["banks"]): string | null {
  let best: { code: string; rate: number } | null = null
  for (const bank of banks) {
    if (!bank.sheet_date) continue
    const row = bank.rates.find((rate) => rate.channel === "online" && (rate.tier ?? "") === "" && rate.term_months === 12 && rate.grade === "verified")
    if (!row) continue
    if (!best || row.rate_pct > best.rate) best = { code: bank.code, rate: row.rate_pct }
  }
  return best ? branchCode(best.code) : null
}

function metricValue(province: Snapshot["geo"]["provinces"][number], metric: Metric, bankCode: string): number | null {
  if (metric === "per100k") {
    if (!province.population || province.branches_total === null) return null
    return (province.branches_total / province.population) * 100_000
  }
  if (metric === "bank") return province.branches_by_bank[branchCode(bankCode)] ?? 0
  return province.branches_total
}

export function ProvinceMap({ snapshot, lang, bankCode }: { snapshot: Snapshot; lang: Lang; bankCode: string }) {
  const vi = lang === "vi"
  const [metric, setMetric] = useState<Metric>("total")
  const [bank, setBank] = useState(bankCode)
  const [selected, setSelected] = useState<string | null>(snapshot.geo.provinces[0]?.pcode ?? null)
  const province = snapshot.geo.provinces.find((item) => item.pcode === selected) ?? null
  const values = snapshot.geo.provinces.map((item) => metricValue(item, metric, bank)).filter((value): value is number => value !== null)
  const groups = quantileSteps(values)
  const rows = snapshot.geo.provinces.map((item) => {
    const value = metricValue(item, metric, bank)
    const group = value === null ? null : (groups.find((entry) => value >= entry.min && value <= entry.max)?.group ?? null)
    return { pcode: item.pcode, name: vi ? item.name_vi : item.name_en, value, group }
  })
  const digits = metric === "per100k" ? 1 : 0
  const formatStep = (value: number) => value.toLocaleString(vi ? "vi-VN" : "en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })
  const steps = groups.map((group) => ({ group: group.group, label: `${formatStep(group.min)}–${formatStep(group.max)}` }))
  const offers = province ? provinceOffers(province, snapshot.banks) : []
  const bankItems = snapshot.banks.map((item) => ({ value: item.code, label: bankMenuLabel(item.code, lang) }))
  const metricItems = [
    { value: "total", label: vi ? "Tổng điểm giao dịch" : "Bank points, all banks" },
    { value: "bank", label: vi ? "Điểm của ngân hàng đang chọn" : "Points of the selected bank" },
    { value: "per100k", label: vi ? "Điểm trên 100.000 dân" : "Points per 100,000 people" },
  ]
  const provinceItems = snapshot.geo.provinces.map((item) => ({ value: item.pcode, label: vi ? item.name_vi : item.name_en }))
  const headline = mapHeadline({ lang, provinces: snapshot.geo.provinces, bestBankCode: bestOnlineBranch(snapshot.banks) })

  return (
    <>
      <h1 className="text-xl font-semibold text-balance">{headline}</h1>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0">
          <Choropleth
            rows={rows}
            lang={lang}
            selected={selected}
            onSelect={setSelected}
            steps={steps}
            ariaLabel={vi ? "Bản đồ 34 tỉnh, thành" : "Map of 34 provinces"}
          />
          <p className="mt-2 text-xs text-muted-foreground">{BOUNDARY}</p>
          <p className="text-xs text-muted-foreground">© OpenStreetMap contributors (ODbL)</p>
        </div>
        <aside className="flex flex-col gap-3 text-sm">
          <div className="grid gap-1">
            <Label htmlFor="map-metric">{vi ? "Số trên bản đồ" : "Figure on the map"}</Label>
            <Select value={metric} items={metricItems} onValueChange={(value) => value && setMetric(value as Metric)}>
              <SelectTrigger id="map-metric" className="min-h-11 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {metricItems.map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            {metric === "per100k" ? (
              <p className="text-xs text-muted-foreground">
                {snapshot.geo.population_basis ?? (vi ? "Chưa có căn cứ dân số." : "No population basis is recorded.")}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">{vi ? "Tỉnh chưa có số để trắng." : "A province with no figure stays blank."}</p>
            )}
          </div>
          <div className="grid gap-1">
            <Label htmlFor="map-bank">{vi ? "Ngân hàng" : "Bank"}</Label>
            <Select value={bank} items={bankItems} onValueChange={(value) => value && setBank(value)}>
              <SelectTrigger id="map-bank" className="min-h-11 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {bankItems.map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1">
            <Label htmlFor="map-province">{vi ? "Tỉnh hoặc thành" : "Province"}</Label>
            <Select value={selected ?? ""} items={provinceItems} onValueChange={(value) => value && setSelected(value)}>
              <SelectTrigger id="map-province" className="min-h-11 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {provinceItems.map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
          {province ? (
            <div className="flex flex-col gap-2">
              <h2 className="text-base font-semibold">
                {vi ? province.name_vi : province.name_en}. {offers.length} {vi ? "ngân hàng có điểm trong bản này." : "banks with a recorded point in this edition."}
              </h2>
              {offers.length ? (
                <ul className="flex flex-col gap-2">
                  {offers.map((offer) => (
                    <li key={offer.code}>
                      <p className="font-medium">{offer.name}. {offer.branches} {vi ? "điểm" : "points"}.</p>
                      <p>
                        {vi ? "Quầy, kỳ 12 tháng, đã kiểm" : "Counter, 12 months, checked"}: {offer.counter ? `${formatPct(offer.counter.rate, 2, lang)}% · ${gradeBadge(offer.counter.grade, "", lang).label}` : (vi ? "chưa có" : "none")}
                      </p>
                      <p>
                        {vi ? "Online, kỳ 12 tháng, đã kiểm" : "Online, 12 months, checked"}: {offer.online ? `${formatPct(offer.online.rate, 2, lang)}% · ${gradeBadge(offer.online.grade, "", lang).label}` : (vi ? "chưa có" : "none")}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{vi ? "Bản này chưa ghi ngân hàng nào có điểm tại tỉnh này." : "This edition does not list a bank point in this province."}</p>
              )}
            </div>
          ) : null}
        </aside>
      </div>
      <ChartHelp lang={lang}>
        {vi
          ? "Năm mức màu là năm nhóm phân vị của số đang chọn: tổng điểm, điểm của một ngân hàng, hoặc điểm trên 100.000 dân. Tỉnh trắng là chưa có số. Bấm tỉnh để xem ngân hàng có mặt và lãi kỳ 12 tháng đã kiểm."
          : "Five shades are five quantile groups of the selected figure: all points, one bank's points, or points per 100,000 people. A blank province has no figure. Click a province to see the banks there and their checked 12-month rates."}
      </ChartHelp>
    </>
  )
}
