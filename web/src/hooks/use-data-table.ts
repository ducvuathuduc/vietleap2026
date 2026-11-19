"use client"

/**
 * URL-state data table hook.
 * Pattern adapted from Kiranism/next-shadcn-dashboard-starter (MIT):
 * https://github.com/Kiranism/next-shadcn-dashboard-starter
 * Keys: page, perPage, sort (`id.asc|desc`), q. Client-side sort, filter and pagination.
 */
import { useMemo } from "react"
import { useTable, type ColumnDef, type RowData, type Updater } from "@tanstack/react-table"
import { createParser, parseAsInteger, parseAsString, useQueryState } from "nuqs"

import { dataTableFeatures, type DataTableFeatures } from "@/components/data-table/data-table-features"
import {
  DEFAULT_PAGE_SIZE,
  clampPageSize,
  parseSortParam,
  rowMatchesQuery,
  serializeSortParam,
  type SortItem,
} from "@/components/data-table/search-params"

const queryOptions = { history: "replace" as const, shallow: true, scroll: false, clearOnDefault: true }

const sortParser = createParser<SortItem[]>({
  parse: (value) => parseSortParam(value),
  serialize: (value) => serializeSortParam(value),
  eq: (left, right) => serializeSortParam(left) === serializeSortParam(right),
})
  .withDefault([])
  .withOptions(queryOptions)

function applyUpdate<T>(updater: Updater<T>, current: T): T {
  return typeof updater === "function" ? (updater as (old: T) => T)(current) : updater
}

export function useDataTable<TData extends RowData>({
  data,
  columns,
}: {
  data: TData[]
  columns: ColumnDef<DataTableFeatures, TData>[]
}) {
  const [page, setPage] = useQueryState("page", parseAsInteger.withDefault(1).withOptions(queryOptions))
  const [perPage, setPerPage] = useQueryState("perPage", parseAsInteger.withDefault(DEFAULT_PAGE_SIZE).withOptions(queryOptions))
  const [sort, setSort] = useQueryState("sort", sortParser)
  const [query, setQueryState] = useQueryState("q", parseAsString.withDefault("").withOptions(queryOptions))

  const filtered = useMemo(() => data.filter((row) => rowMatchesQuery(row, query)), [data, query])
  const pagination = useMemo(
    () => ({ pageIndex: Math.max(page, 1) - 1, pageSize: clampPageSize(perPage) }),
    [page, perPage],
  )

  const table = useTable({
    features: dataTableFeatures,
    data: filtered,
    columns,
    state: { pagination, sorting: sort },
    onPaginationChange: (updater) => {
      const next = applyUpdate(updater, pagination)
      void setPage(next.pageIndex + 1)
      void setPerPage(next.pageSize)
    },
    onSortingChange: (updater) => {
      void setSort(applyUpdate(updater, sort))
      void setPage(1)
    },
  })

  function setQuery(value: string) {
    void setQueryState(value.trim() ? value : null)
    void setPage(1)
  }

  return { table, query, setQuery }
}
