"use client"

/** Sort, page and filter live in the URL (`sort`, `page`, `perPage`, `q`). */
import { useMemo } from "react"
import type { ColumnDef } from "@tanstack/react-table"

import { DataTable } from "@/components/data-table/data-table"
import type { DataTableFeatures } from "@/components/data-table/data-table-features"
import { formatDay } from "@/components/judge/labels"
import { formatNumber } from "@/lib/monitor/format"

export interface JudgeTableColumn {
  key: string
  label: string
  unit?: string
  kind?: "text" | "number" | "percent" | "date"
}

export interface JudgeTableProps {
  columns: JudgeTableColumn[]
  rows: Record<string, unknown>[]
}

/** A missing cell shows a dash, never a fake zero. */
function cellText(value: unknown, column: JudgeTableColumn): string {
  if (value === null || value === undefined || value === "") return "–"
  if (column.kind === "date") return formatDay(String(value)) || "–"
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "–"
    return formatNumber(value)
  }
  return String(value)
}

export function JudgeTable({ columns, rows }: JudgeTableProps) {
  const definitions = useMemo<ColumnDef<DataTableFeatures, Record<string, unknown>>[]>(
    () =>
      columns.map((column) => ({
        id: column.key,
        accessorKey: column.key,
        header: column.unit ? `${column.label} (${column.unit})` : column.label,
        cell: ({ getValue }) => cellText(getValue(), column),
      })),
    [columns],
  )
  return <DataTable data={rows} columns={definitions} />
}
