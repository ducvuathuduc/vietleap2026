// Automatic chart selection from a SQL result shape.
// Pure function: never aggregates or alters row values; returns null when the shape isn't chartable.
import type { ChartSpec } from "@/lib/api/types"

type Cell = string | number | boolean | null | undefined

const TIME_NAME_RE = /^(?:year|nam|ngay|date|period|thang|quy|quarter|month|day|created|posted)$/i
const TIME_VAL_RE = /^(?:\d{4}(?:-(?:0[1-9]|1[0-2])(?:-\d{2})?|-Q[1-4])?)$/i

function isNumericCol(rows: Cell[][], idx: number): boolean {
  let seen = 0
  for (const r of rows) {
    const v = r[idx]
    if (v === null || v === undefined || v === "") continue
    if (typeof v !== "number" || !Number.isFinite(v)) return false
    seen++
  }
  return seen > 0
}

function isTimeCol(name: string, rows: Cell[][], idx: number): boolean {
  const clean = name.toLowerCase().trim()
  if (TIME_NAME_RE.test(clean) || /(_year|_date|_month|_time|nam_|ngay_|thang_)/i.test(clean)) return true
  let total = 0
  let hits = 0
  for (const r of rows.slice(0, 20)) {
    const v = r[idx]
    if (v === null || v === undefined || v === "") continue
    total++
    if (typeof v === "string" && TIME_VAL_RE.test(v.trim())) hits++
    else if (typeof v === "number" && Number.isInteger(v) && v >= 1900 && v <= 2100) hits++
  }
  return total > 0 && hits / total >= 0.8
}

export function chartFromResult(columns: string[], rows: Cell[][]): ChartSpec | null {
  if (!Array.isArray(columns) || !Array.isArray(rows) || columns.length === 0 || rows.length === 0) return null
  if (columns.length > 10) return null

  const numericIdx: number[] = []
  const timeIdx: number[] = []
  const textIdx: number[] = []

  for (let c = 0; c < columns.length; c++) {
    if (isTimeCol(columns[c], rows, c)) timeIdx.push(c)
    else if (isNumericCol(rows, c)) numericIdx.push(c)
    else textIdx.push(c)
  }

  // 1. Time column + 1..3 numeric columns → line sorted ascending by x
  if (timeIdx.length === 1 && textIdx.length === 0 && numericIdx.length >= 1 && numericIdx.length <= 3) {
    const ti = timeIdx[0]
    const indexed = rows.map((r, pos) => ({ r, pos, k: r[ti] }))
    indexed.sort((a, b) => {
      if (typeof a.k === "number" && typeof b.k === "number") return a.k - b.k
      return String(a.k ?? "").localeCompare(String(b.k ?? "")) || a.pos - b.pos
    })
    return {
      kind: "line",
      x: indexed.map(({ r }) => (r[ti] === null || r[ti] === undefined ? "" : String(r[ti]))),
      series: numericIdx.map((ni) => ({
        name: columns[ni],
        data: indexed.map(({ r }) => (typeof r[ni] === "number" ? (r[ni] as number) : null)),
      })),
      x_label: columns[ti],
      y_label: columns[numericIdx[0]],
    }
  }

  // 2. Exactly 2 numeric columns and >= 10 rows (no text/time col) → scatter
  if (columns.length === 2 && textIdx.length === 0 && timeIdx.length === 0 && numericIdx.length === 2 && rows.length >= 10) {
    const [xi, yi] = numericIdx
    return {
      kind: "scatter",
      x: rows.map((r) => (typeof r[xi] === "number" ? (r[xi] as number) : null)),
      series: [
        {
          name: columns[yi],
          data: rows.map((r) => (typeof r[yi] === "number" ? (r[yi] as number) : null)),
        },
      ],
      x_label: columns[xi],
      y_label: columns[yi],
    }
  }

  // 3. 1 text/category column + 1..3 numeric columns, <= 30 rows → bar (or hbar if any label > 12 chars)
  if (textIdx.length === 1 && timeIdx.length === 0 && numericIdx.length >= 1 && numericIdx.length <= 3 && rows.length <= 30) {
    const xi = textIdx[0]
    const labels = rows.map((r) => (r[xi] === null || r[xi] === undefined ? "–" : String(r[xi])))
    const longLabel = labels.some((s) => s.length > 12)
    return {
      kind: longLabel ? "hbar" : "bar",
      x: labels,
      series: numericIdx.map((ni) => ({
        name: columns[ni],
        data: rows.map((r) => (typeof r[ni] === "number" ? (r[ni] as number) : null)),
      })),
      x_label: columns[xi],
      y_label: columns[numericIdx[0]],
    }
  }

  return null
}
