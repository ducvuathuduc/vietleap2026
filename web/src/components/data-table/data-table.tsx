"use client"

/**
 * Generic data table. Rows come from the server; sort, filter and page live in the URL.
 * Pattern adapted from Kiranism/next-shadcn-dashboard-starter (MIT):
 * https://github.com/Kiranism/next-shadcn-dashboard-starter
 */
import { Suspense } from "react"
import type { ColumnDef, RowData } from "@tanstack/react-table"
import { FlexRender, useTable } from "@tanstack/react-table"
import { ChevronLeftIcon, ChevronRightIcon, ChevronsLeftIcon, ChevronsRightIcon } from "lucide-react"

import { PAGE_SIZES } from "@/components/data-table/search-params"
import { dataTableFeatures, type DataTableFeatures } from "@/components/data-table/data-table-features"
import { useDataTable } from "@/hooks/use-data-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table as TableElement, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

type DataColumns<TData extends RowData> = ColumnDef<DataTableFeatures, TData>[]
type TableInstance<TData extends RowData> = ReturnType<typeof useTable<DataTableFeatures, TData>>

export function DataTable<TData extends RowData>({
  data,
  columns,
}: {
  data: TData[]
  columns: DataColumns<TData>
}) {
  return (
    <Suspense fallback={<StaticDataTable data={data} columns={columns} />}>
      <UrlStateDataTable data={data} columns={columns} />
    </Suspense>
  )
}

/** The query string is only known on the client, so this island needs its own Suspense boundary. */
function UrlStateDataTable<TData extends RowData>({ data, columns }: { data: TData[]; columns: DataColumns<TData> }) {
  const { table, query, setQuery } = useDataTable({ data, columns })
  return <TableView table={table} query={query} onQueryChange={setQuery} />
}

/**
 * Fallback for the boundary above: the same first page with default state, so the rows
 * land in the initial HTML instead of arriving with the client bundle.
 */
function StaticDataTable<TData extends RowData>({ data, columns }: { data: TData[]; columns: DataColumns<TData> }) {
  const table = useTable({ features: dataTableFeatures, data, columns })
  return <TableView table={table} query="" onQueryChange={() => {}} />
}

function TableView<TData extends RowData>({
  table,
  query,
  onQueryChange,
}: {
  table: TableInstance<TData>
  query: string
  onQueryChange: (value: string) => void
}) {
  const pageSize = String(table.state.pagination.pageSize)
  return (
    <div className="flex flex-col gap-3">
      <Input value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Lọc trong bảng" aria-label="Lọc trong bảng" />
      <div className="overflow-hidden rounded-lg border">
        <TableElement>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} colSpan={header.colSpan}>
                    {header.isPlaceholder ? null : header.column.getCanSort() ? (
                      <Button variant="ghost" size="sm" onClick={header.column.getToggleSortingHandler()}>
                        <FlexRender header={header} />
                        <SortMark direction={header.column.getIsSorted()} />
                      </Button>
                    ) : (
                      <FlexRender header={header} />
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getAllCells().map((cell) => (
                    <TableCell key={cell.id}>
                      <FlexRender cell={cell} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={table.getAllColumns().length} className="text-center text-muted-foreground">
                  Không có dòng phù hợp.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </TableElement>
      </div>
      <div className="flex items-center justify-between gap-2">
        <Select
          value={pageSize}
          onValueChange={(value) => {
            if (!value) return
            table.setPageSize(Number(value))
          }}
        >
          <SelectTrigger size="sm" className="w-24" aria-label="Số dòng mỗi trang">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {PAGE_SIZES.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon-sm" onClick={() => table.setPageIndex(0)} disabled={!table.getCanPreviousPage()} aria-label="Tới trang đầu">
            <ChevronsLeftIcon />
          </Button>
          <Button variant="outline" size="icon-sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()} aria-label="Tới trang trước">
            <ChevronLeftIcon />
          </Button>
          <Button variant="outline" size="icon-sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()} aria-label="Tới trang sau">
            <ChevronRightIcon />
          </Button>
          <Button variant="outline" size="icon-sm" onClick={() => table.setPageIndex(table.getPageCount() - 1)} disabled={!table.getCanNextPage()} aria-label="Tới trang cuối">
            <ChevronsRightIcon />
          </Button>
        </div>
      </div>
    </div>
  )
}

function SortMark({ direction }: { direction: false | "asc" | "desc" }) {
  if (direction === "asc") return <span className="text-muted-foreground">tăng dần</span>
  if (direction === "desc") return <span className="text-muted-foreground">giảm dần</span>
  return null
}
