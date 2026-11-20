"use client"

import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatNumber, pageHref, type Lang, decoderModel } from "@/lib/npl/view"

type Model = ReturnType<typeof decoderModel>
type Cell = NonNullable<Model["rows"][number]["cells"][number]>

const INPUTS = [
  ["loans", "Dư nợ khách hàng (L)", "Customer loans (L)"],
  ["group2", "Nợ nhóm 2 (G2)", "Group 2 loans (G2)"],
  ["npl", "Nợ nhóm 3–5 (N)", "NPL groups 3–5 (N)"],
  ["provision", "Dự phòng cuối kỳ (P)", "Provision balance (P)"],
  ["writeoff", "Xóa nợ trong kỳ (W)", "Write-offs (W)"],
] as const

const RATIOS = [
  ["npl_ratio", "Tỷ lệ nợ xấu N/L", "NPL ratio N/L"],
  ["g2_ratio", "Tỷ lệ nhóm 2 G2/L", "Group 2 ratio G2/L"],
  ["coverage", "Bao phủ P/N", "Coverage P/N"],
  ["writeoff_ratio", "Tỷ lệ xóa nợ W/L quý trước", "Write-off ratio W/L prior quarter"],
] as const

function amount(value: number | null, missing: string, lang: Lang): string {
  return value == null ? missing : formatNumber(value, lang, 2)
}

function visibleCell(item: Cell | null, quarter: string, status: string): Cell | null {
  if (!item) return null
  if (quarter !== "all" && item.period !== quarter) return null
  if (status !== "all" && item.label !== status) return null
  return item
}

export function DecoderTable({ model, lang }: { model: Model; lang: Lang }) {
  const vi = lang === "vi"
  const missing = vi ? "Thiếu dữ liệu" : "Missing data"
  const [picked, setPicked] = useState<{ bank: string; period: string } | null>(null)
  const [quarter, setQuarter] = useState("all")
  const [status, setStatus] = useState("all")
  const quarterItems = [
    { value: "all", label: vi ? "Mọi quý" : "All quarters" },
    ...model.periods.map((period) => ({ value: period, label: period })),
  ]
  const statusItems = [
    { value: "all", label: vi ? "Mọi trạng thái" : "All statuses" },
    ...model.legend.map((item) => ({ value: item.label, label: item.label })),
  ]
  const rows = status === "all" ? model.rows : model.rows.filter((row) => row.cells.some((item) => visibleCell(item, quarter, status)))
  const cell = picked
    ? model.rows.find((row) => row.bank === picked.bank)?.cells.find((item) => item?.period === picked.period) ?? null
    : null
  return (
    <section className="flex min-w-0 flex-col gap-3">
      <h2 className="text-base font-semibold">{model.title}</h2>
      <p className="text-sm text-muted-foreground">{model.note}</p>
      <div className="flex min-w-0 flex-wrap gap-3">
        <div className="grid w-full min-w-0 max-w-56 gap-1">
          <Label htmlFor="decoder-quarter">{vi ? "Quý" : "Quarter"}</Label>
          <Select value={quarter} items={quarterItems} onValueChange={(value) => { if (value) setQuarter(value) }}>
            <SelectTrigger id="decoder-quarter" className="w-full min-h-11 max-w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="start" className="w-56 max-w-[calc(100vw-2rem)]">
              <SelectGroup>
                {quarterItems.map((item) => (
                  <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
        <div className="grid w-full min-w-0 max-w-56 gap-1">
          <Label htmlFor="decoder-status">{vi ? "Trạng thái" : "Status"}</Label>
          <Select value={status} items={statusItems} onValueChange={(value) => { if (value) setStatus(value) }}>
            <SelectTrigger id="decoder-status" className="w-full min-h-11 max-w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="start" className="w-80 max-w-[calc(100vw-2rem)]">
              <SelectGroup>
                {statusItems.map((item) => (
                  <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="w-full min-w-0 overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{vi ? "Mã" : "Ticker"}</TableHead>
              {model.periods.map((period) => (
                <TableHead key={period}>{period}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.bank}>
                <TableCell>
                  <a className="underline underline-offset-4" href={pageHref(`/ngan-hang/${row.bank}`, lang)}>{row.bank}</a>
                </TableCell>
                {row.cells.map((item, index) => {
                  const visible = visibleCell(item, quarter, status)
                  return (
                    <TableCell key={model.periods[index]} className="align-top">
                      {visible ? (
                        <button
                          type="button"
                          className="flex min-h-11 w-full min-w-28 flex-col items-start gap-1 text-left"
                          aria-pressed={picked?.bank === row.bank && picked.period === visible.period}
                          onClick={() => setPicked({ bank: row.bank, period: visible.period })}
                        >
                          <span className="tabular-nums">{visible.dNplText}</span>
                          {visible.label ? (
                            <Badge variant={visible.status === "clean" ? "default" : visible.status === "seasonal" ? "secondary" : "outline"} className="h-auto overflow-visible whitespace-normal">
                              {visible.label}
                            </Badge>
                          ) : null}
                        </button>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {model.moreHref && model.moreLabel ? (
        <p><a className="text-sm underline underline-offset-4" href={model.moreHref}>{model.moreLabel}</a></p>
      ) : null}
      <p className="text-sm text-muted-foreground">{model.attribution}</p>
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">{vi ? "Chú giải" : "Legend"}</h3>
        <ul className="flex flex-col gap-1 text-sm">
          {model.legend.map((item) => (
            <li key={item.label}><span className="font-medium">{item.label}.</span> {item.sentence}</li>
          ))}
        </ul>
        <p className="text-sm">{model.disclaimer}</p>
      </div>
      <Sheet open={cell != null} onOpenChange={(open) => { if (!open) setPicked(null) }}>
        <SheetContent side="right" className="w-full overflow-y-auto p-4 sm:max-w-md">
          {cell && picked ? <Panel cell={cell} bank={picked.bank} lang={lang} missing={missing} disclaimer={model.disclaimer} attribution={model.attribution} /> : null}
        </SheetContent>
      </Sheet>
    </section>
  )
}

function Panel({ cell, bank, lang, missing, disclaimer, attribution }: { cell: Cell; bank: string; lang: Lang; missing: string; disclaimer: string; attribution: string }) {
  const vi = lang === "vi"
  const stock = cell.inputs
  return (
    <>
      <SheetHeader>
        <SheetTitle>{bank} {cell.period}</SheetTitle>
      </SheetHeader>
      <p>{cell.reading}</p>
      <h3 className="font-semibold">{vi ? "5 đầu vào" : "Five inputs"}</h3>
      <ul className="flex flex-col gap-1">
        {INPUTS.map(([key, labelVi, labelEn]) => (
          <li key={key}>{vi ? labelVi : labelEn}: {amount(stock[key], missing, lang)}</li>
        ))}
      </ul>
      <h3 className="font-semibold">{vi ? "Bốn tỷ lệ" : "Four ratios"}</h3>
      <ul className="flex flex-col gap-1">
        {RATIOS.map(([key, labelVi, labelEn]) => {
          const ratio = stock.ratios[key]
          const page = ratio.page == null ? "—" : String(ratio.page)
          return (
            <li key={key}>
              {vi ? labelVi : labelEn}: {amount(ratio.value, missing, lang)}. {vi ? "Nguồn" : "Source"}: {ratio.source ?? "—"}. {vi ? "Trang" : "Page"}: {page}.
            </li>
          )
        })}
      </ul>
      <p>{vi ? "Thay đổi bao phủ" : "Coverage change"}: {amount(stock.d_coverage_pp, missing, lang)}</p>
      <p>{disclaimer}</p>
      <p className="text-muted-foreground">{attribution}</p>
    </>
  )
}
