"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

type Cell = string | number | boolean | null | undefined

function show(v: Cell): string {
  if (v === null || v === undefined || v === "") return "–"
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString("vi-VN") : v.toLocaleString("vi-VN", { maximumFractionDigits: 4 })
  return String(v)
}

/** Generic read-only table for API results (shadcn Table inside a scroll area). */
export function ResultTable({
  columns,
  rows,
  maxHeight = "28rem",
  empty = "Không có dòng nào.",
}: {
  columns: string[]
  rows: Cell[][]
  maxHeight?: string
  empty?: string
}) {
  return (
    <div className="overflow-auto rounded-lg border" style={{ maxHeight }}>
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-muted">
            <TableRow>
              {columns.map((c) => (
                <TableHead key={c} className="whitespace-nowrap">{c}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={Math.max(columns.length, 1)} className="h-20 text-center text-muted-foreground">{empty}</TableCell>
              </TableRow>
            ) : (
              rows.map((r, i) => (
                <TableRow key={i}>
                  {r.map((v, j) => (
                    <TableCell key={j} className="max-w-96 truncate whitespace-nowrap" title={show(v)}>{show(v)}</TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
    </div>
  )
}

/** Monospace code block for generated SQL (plain <pre>, no highlighter dependency). */
export function CodeBlock({ code, label }: { code: string; label: string }) {
  return (
    <pre aria-label={label} className="max-h-[32rem] overflow-auto rounded-lg border bg-muted/50 p-4 font-mono text-xs leading-relaxed">
      {code}
    </pre>
  )
}
