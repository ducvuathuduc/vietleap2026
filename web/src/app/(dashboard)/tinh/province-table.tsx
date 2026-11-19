"use client"

/** Province table. Sort, filter and page stay in the URL via the shared data table. */
import { useMemo } from "react"
import type { ColumnDef } from "@tanstack/react-table"

import { DataTable } from "@/components/data-table/data-table"
import type { DataTableFeatures } from "@/components/data-table/data-table-features"

import type { ProvinceTableRow } from "../_lib/province-view"

const LINK =
  "underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"

export function ProvinceTable({ rows }: { rows: ProvinceTableRow[] }) {
  const columns = useMemo<ColumnDef<DataTableFeatures, ProvinceTableRow>[]>(
    () => [
      {
        id: "name",
        accessorKey: "name",
        header: "Tỉnh",
        cell: ({ row }) => (
          <a href={row.original.href} className={LINK}>
            {row.original.name}
          </a>
        ),
      },
      { id: "group", accessorKey: "group", header: "Nhóm" },
      {
        id: "value",
        accessorKey: "value",
        header: "Giá trị",
        cell: ({ row }) => row.original.valueText,
      },
      {
        id: "gap",
        accessorKey: "gap",
        header: "Chênh trung vị",
        cell: ({ row }) => row.original.gapText,
      },
    ],
    [],
  )
  return <DataTable data={rows} columns={columns} />
}
