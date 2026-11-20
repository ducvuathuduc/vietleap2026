"use client"

import { useState } from "react"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatNumber, sortDataRows, type DataRow, type Lang } from "@/lib/npl/view"

type Key = "bank_code" | "period" | "d_npl_pp" | "adjusted_change_pp" | "npl_pct" | "coverage_pct" | "ldr_pct" | "nim_pct" | "loan_growth_pct"

const BASE: { key: Key; vi: string; en: string }[] = [
  { key: "bank_code", vi: "Ngân hàng", en: "Bank" },
  { key: "period", vi: "Quý", en: "Quarter" },
  { key: "d_npl_pp", vi: "Biến động NPL", en: "NPL change" },
  { key: "adjusted_change_pp", vi: "Sau hiệu ứng quý", en: "After quarter effect" },
]

const RAW: { key: Key; vi: string; en: string }[] = [
  { key: "npl_pct", vi: "NPL", en: "NPL" },
  { key: "coverage_pct", vi: "Bao phủ", en: "Coverage" },
  { key: "ldr_pct", vi: "LDR", en: "LDR" },
  { key: "nim_pct", vi: "NIM", en: "NIM" },
  { key: "loan_growth_pct", vi: "Tăng dư nợ", en: "Loan growth" },
]

function cell(row: DataRow, key: Key, lang: Lang): string {
  const value = row[key]
  if (value == null || value === "") return ""
  if (typeof value === "number") return formatNumber(value, lang, key === "bank_code" || key === "period" ? 0 : 3)
  return value
}

export function DataTable({ rows, raw, lang }: { rows: DataRow[]; raw: boolean; lang: Lang }) {
  const columns = raw ? [...BASE, ...RAW] : BASE
  const [key, setKey] = useState<Key>("bank_code")
  const [dir, setDir] = useState<1 | -1>(1)
  const sorted = sortDataRows(rows, key, dir)

  function choose(next: Key) {
    if (next === key) setDir((current) => (current === 1 ? -1 : 1))
    else {
      setKey(next)
      setDir(1)
    }
  }

  return (
    <div className="w-full min-w-0 overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column.key}>
                <button type="button" className="min-h-11 underline-offset-4 hover:underline" onClick={() => choose(column.key)}>
                  {lang === "vi" ? column.vi : column.en}
                </button>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((row) => (
            <TableRow key={`${row.bank_code}-${row.period}`}>
              {columns.map((column) => (
                <TableCell key={column.key} className="tabular-nums">{cell(row, column.key, lang)}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
