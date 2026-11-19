/**
 * URL-state helpers for the data table.
 * Pattern adapted from Kiranism/next-shadcn-dashboard-starter (MIT):
 * https://github.com/Kiranism/next-shadcn-dashboard-starter
 */

export type SortItem = { id: string; desc: boolean }

export const PAGE_SIZES = [10, 20, 50] as const
export const DEFAULT_PAGE_SIZE = PAGE_SIZES[0]

export function parseSortParam(value: string): SortItem[] | null {
  if (!value) return []
  const sorting: SortItem[] = []
  for (const part of value.split(",")) {
    const index = part.lastIndexOf(".")
    const order = part.slice(index + 1)
    if (index <= 0 || (order !== "asc" && order !== "desc")) return null
    sorting.push({ id: part.slice(0, index), desc: order === "desc" })
  }
  return sorting
}

export function serializeSortParam(value: readonly SortItem[]): string {
  return value.map((item) => `${item.id}.${item.desc ? "desc" : "asc"}`).join(",")
}

export function clampPageSize(value: number): number {
  return (PAGE_SIZES as readonly number[]).includes(value) ? value : DEFAULT_PAGE_SIZE
}

export function rowMatchesQuery(row: unknown, query: string): boolean {
  const needle = fold(query)
  if (!needle) return true
  return fold(collect(row)).includes(needle)
}

function collect(value: unknown): string {
  if (value == null) return ""
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value)
  if (Array.isArray(value)) return value.map(collect).join(" ")
  if (typeof value === "object") return Object.values(value).map(collect).join(" ")
  return ""
}

function fold(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
}
