/**
 * Client-side table features for URL-state tables.
 * Pattern adapted from Kiranism/next-shadcn-dashboard-starter (MIT):
 * https://github.com/Kiranism/next-shadcn-dashboard-starter
 */
import {
  createPaginatedRowModel,
  createSortedRowModel,
  rowPaginationFeature,
  rowSortingFeature,
  tableFeatures,
} from "@tanstack/react-table"

export const dataTableFeatures = tableFeatures({
  rowPaginationFeature,
  rowSortingFeature,
  paginatedRowModel: createPaginatedRowModel(),
  sortedRowModel: createSortedRowModel(),
})

export type DataTableFeatures = typeof dataTableFeatures
