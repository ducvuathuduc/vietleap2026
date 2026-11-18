import type { SqlResult, WarehouseTable } from "@/lib/api/types"
import { isReadOnlySql } from "@/lib/analyst/sql-guard"
import type { AnalyzedDataset } from "./analyzer"

function forbiddenError(msg: string): Error {
  const err = new Error(msg) as Error & { status?: number }
  err.status = 403
  return err
}

export interface WarehouseView {
  layer: "bronze" | "silver" | "gold"
  name: string
  rows: Record<string, string | number | boolean | null>[]
}

export function listWarehouseTables(datasets: AnalyzedDataset[]): WarehouseTable[] {
  const out: WarehouseTable[] = []
  for (const ds of datasets) {
    const colsB = ds.bronzeRows[0] ? Object.keys(ds.bronzeRows[0]).length : 0
    const colsS = ds.silverRows[0] ? Object.keys(ds.silverRows[0]).length : 0
    const colsG = ds.goldRows[0] ? Object.keys(ds.goldRows[0]).length : 0
    out.push({ layer: "bronze", name: ds.tableNameBronze, rows: ds.bronzeRows.length, cols: colsB })
    out.push({ layer: "silver", name: ds.tableNameSilver, rows: ds.silverRows.length, cols: colsS })
    out.push({ layer: "gold", name: ds.tableNameGold, rows: ds.goldRows.length, cols: colsG })
  }
  return out
}

export function getTableColumns(datasets: AnalyzedDataset[], fq: string): { name: string; type: string }[] {
  const table = findTable(datasets, fq)
  if (!table || table.rows.length === 0) return []
  const sample = table.rows[0]
  return Object.keys(sample).map((name) => {
    const v = table.rows.find((r) => r[name] !== null)?.[name]
    const type = typeof v === "number" ? "DOUBLE" : typeof v === "boolean" ? "BOOLEAN" : "VARCHAR"
    return { name, type }
  })
}

function findTable(datasets: AnalyzedDataset[], ref: string): WarehouseView | null {
  const cleaned = ref.replace(/"/g, "").trim()
  const parts = cleaned.split(".")
  const layer = parts.length === 2 ? parts[0].toLowerCase() : null
  const name = parts.length === 2 ? parts[1] : parts[0]

  for (const ds of datasets) {
    if ((!layer || layer === "bronze") && ds.tableNameBronze === name) return { layer: "bronze", name, rows: ds.bronzeRows }
    if ((!layer || layer === "silver") && ds.tableNameSilver === name) return { layer: "silver", name, rows: ds.silverRows }
    if ((!layer || layer === "gold") && ds.tableNameGold === name) return { layer: "gold", name, rows: ds.goldRows }
    if (layer === "gold" && (name === `fact_${ds.id}` || name.startsWith(`${ds.id}__dim_`))) {
      return { layer: "gold", name, rows: ds.goldRows }
    }
  }
  return null
}

/** Lightweight safe read-only SQL evaluator supporting warehouse exploration & aggregations. */
export function executeReadOnlySql(datasets: AnalyzedDataset[], query: string, limit = 500): SqlResult {
  const guard = isReadOnlySql(query)
  if (!guard.ok) {
    throw forbiddenError(guard.reason ?? "Câu lệnh bị từ chối bởi chính sách chỉ đọc.")
  }
  const q = query.trim().replace(/;+\s*$/, "")

  // Handle duckdb_tables() metadata query
  if (/duckdb_tables\s*\(\s*\)/i.test(q)) {
    const wt = listWarehouseTables(datasets)
    return {
      columns: ["layer", "name", "rows", "cols"],
      rows: wt.slice(0, limit).map((t) => [t.layer, t.name, t.rows, t.cols]),
      row_count: Math.min(limit, wt.length),
    }
  }

  // Handle DESCRIBE / SUMMARIZE / SHOW TABLES
  if (/^show\s+tables/i.test(q)) {
    const wt = listWarehouseTables(datasets)
    return {
      columns: ["layer", "name", "rows", "cols"],
      rows: wt.slice(0, limit).map((t) => [t.layer, t.name, t.rows, t.cols]),
      row_count: Math.min(limit, wt.length),
    }
  }
  const descMatch = q.match(/^(?:describe|summarize)\s+([^\s;]+)/i)
  if (descMatch) {
    const cols = getTableColumns(datasets, descMatch[1])
    if (cols.length === 0) throw new Error(`Không tìm thấy bảng ${descMatch[1]}`)
    return {
      columns: ["column_name", "column_type"],
      rows: cols.map((c) => [c.name, c.type]),
      row_count: cols.length,
    }
  }

  // Parse basic SELECT ... FROM table [WHERE ...] [GROUP BY ...] [ORDER BY ...] [LIMIT n]
  const fromMatch = q.match(/\bfrom\s+((?:bronze|silver|gold)\s*\.\s*(?:"[^"]+"|[\w]+)|(?:"[^"]+"|[\w]+))(?:\s+(?:as\s+)?([a-zA-Z_]\w*))?/i)
  if (!fromMatch) {
    throw new Error("Cú pháp cần mệnh đề FROM <layer>.<ten_bang>, ví dụ: SELECT * FROM gold.\"obt_...\" LIMIT 50.")
  }
  const tableRef = fromMatch[1].replace(/\s+/g, "")
  const alias = fromMatch[2]
  const tbl = findTable(datasets, tableRef)
  if (!tbl) {
    throw new Error(`Không tìm thấy bảng ${tableRef} trong warehouse.`)
  }

  let rows = tbl.rows

  // Optional WHERE equality / comparison filter
  const whereMatch = q.match(/\bwhere\s+([\s\S]+?)(?=\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)/i)
  if (whereMatch) {
    const cond = whereMatch[1].trim()
    const simpleCond = cond.match(/^(?:[a-zA-Z_]\w*\.)?("[^"]+"|[\w]+)\s*(=|!=|<>|>|<|>=|<=)\s*(.+)$/)
    if (simpleCond) {
      const col = simpleCond[1].replace(/"/g, "")
      const op = simpleCond[2]
      const rawVal = simpleCond[3].trim().replace(/^'|'$/g, "")
      const numVal = Number(rawVal)
      rows = rows.filter((r) => {
        const v = r[col]
        if (v === null || v === undefined) return false
        if (op === "=") return String(v) === rawVal || (Number.isFinite(numVal) && Number(v) === numVal)
        if (op === "!=" || op === "<>") return String(v) !== rawVal
        if (typeof v === "number" && Number.isFinite(numVal)) {
          if (op === ">") return v > numVal
          if (op === "<") return v < numVal
          if (op === ">=") return v >= numVal
          if (op === "<=") return v <= numVal
        }
        return false
      })
    }
  }

  const selectMatch = q.match(/\bselect\s+(?:distinct\s+)?([\s\S]+?)\s+\bfrom\b/i)
  const selectExprs = (selectMatch?.[1] ?? "*").split(",").map((s) => s.trim())

  const groupMatch = q.match(/\bgroup\s+by\s+([\s\S]+?)(?=\border\s+by\b|\blimit\b|$)/i)
  const orderMatch = q.match(/\border\s+by\s+([\s\S]+?)(?=\blimit\b|$)/i)
  const limitMatch = q.match(/\blimit\s+(\d+)/i)
  const effectiveLimit = Math.min(limit, limitMatch ? Number(limitMatch[1]) : limit)

  const stripAlias = (col: string) => {
    const c = col.replace(/"/g, "").trim()
    return alias && c.startsWith(`${alias}.`) ? c.slice(alias.length + 1) : c.replace(/^(?:[a-zA-Z_]\w*)\./, "")
  }

  let outCols: string[] = []
  let outRows: (string | number | boolean | null)[][] = []

  const hasAgg = selectExprs.some((e) => /\b(count|avg|mean|sum|min|max|median)\s*\(/i.test(e))
  if (groupMatch || hasAgg) {
    const groupCols = groupMatch
      ? groupMatch[1].split(",").map((g) => {
          const t = g.trim()
          if (/^\d+$/.test(t)) {
            const idx = Number(t) - 1
            return stripAlias((selectExprs[idx] ?? "").replace(/\s+as\s+.*$/i, ""))
          }
          return stripAlias(t)
        })
      : []

    const buckets = new Map<string, Record<string, string | number | boolean | null>[]>()
    for (const r of rows) {
      const key = JSON.stringify(groupCols.map((gc) => r[gc] ?? null))
      const arr = buckets.get(key) ?? []
      arr.push(r)
      buckets.set(key, arr)
    }

    const parsedSelect = selectExprs.map((expr) => {
      const asMatch = expr.match(/^([\s\S]+?)\s+as\s+("[^"]+"|[\w]+)$/i)
      const body = (asMatch ? asMatch[1] : expr).trim()
      const label = asMatch ? asMatch[2].replace(/"/g, "") : stripAlias(body)
      return { body, label }
    })
    outCols = parsedSelect.map((s) => s.label)

    for (const [, grpRows] of buckets.entries()) {
      const rowOut: (string | number | boolean | null)[] = parsedSelect.map(({ body }) => {
        const agg = body.match(/^(count|avg|mean|sum|min|max|median)\s*\(\s*([^)]+)\s*\)$/i)
        if (!agg) {
          const col = stripAlias(body)
          return grpRows[0]?.[col] ?? null
        }
        const fn = agg[1].toLowerCase()
        const arg = stripAlias(agg[2])
        if (fn === "count") return grpRows.length
        const nums = grpRows.map((r) => r[arg]).filter((v): v is number => typeof v === "number" && Number.isFinite(v))
        if (nums.length === 0) return null
        if (fn === "sum") return Number(nums.reduce((a, b) => a + b, 0).toFixed(2))
        if (fn === "avg" || fn === "mean") return Number((nums.reduce((a, b) => a + b, 0) / nums.length).toFixed(2))
        if (fn === "min") return Math.min(...nums)
        if (fn === "max") return Math.max(...nums)
        if (fn === "median") {
          const s = [...nums].sort((a, b) => a - b)
          const mid = Math.floor(s.length / 2)
          return s.length % 2 ? s[mid] : Number(((s[mid - 1] + s[mid]) / 2).toFixed(2))
        }
        return null
      })
      outRows.push(rowOut)
    }
  } else {
    const allCols = rows[0] ? Object.keys(rows[0]) : []
    const parsedSelect = selectExprs.length === 1 && selectExprs[0] === "*"
      ? allCols.map((c) => ({ col: c, label: c }))
      : selectExprs.map((expr) => {
          const asMatch = expr.match(/^([\s\S]+?)\s+as\s+("[^"]+"|[\w]+)$/i)
          const col = stripAlias(asMatch ? asMatch[1] : expr)
          const label = asMatch ? asMatch[2].replace(/"/g, "") : col
          return { col, label }
        })
    outCols = parsedSelect.map((p) => p.label)
    outRows = rows.map((r) => parsedSelect.map((p) => r[p.col] ?? null))
  }

  // ORDER BY
  if (orderMatch) {
    const firstOrder = orderMatch[1].split(",")[0].trim()
    const desc = /\bdesc\b/i.test(firstOrder)
    const targetTok = stripAlias(firstOrder.replace(/\b(asc|desc)\b/gi, "").trim())
    const colIdx = /^\d+$/.test(targetTok) ? Number(targetTok) - 1 : outCols.indexOf(targetTok)
    if (colIdx >= 0 && colIdx < outCols.length) {
      outRows.sort((a, b) => {
        const va = a[colIdx]
        const vb = b[colIdx]
        if (va === vb) return 0
        if (va === null) return 1
        if (vb === null) return -1
        const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb))
        return desc ? -cmp : cmp
      })
    }
  }

  const sliced = outRows.slice(0, effectiveLimit)
  return { columns: outCols, rows: sliced, row_count: sliced.length }
}
