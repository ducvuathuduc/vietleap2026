// Contract (feature 006) for the AI SDK `runSql` tool and its UI rendering. Copied into
// web/src/lib/analyst/tools.ts / types.ts by T606; kept here as the reviewable source of truth.
import { z } from "zod"

export const RunSqlInput = z.object({
  // one read-only statement; the server guard (POST /api/sql, Warehouse.readonly) is authoritative
  query: z.string().min(1).max(5000),
})

export const ChartSpec = z.object({
  kind: z.enum(["bar", "hbar", "line", "scatter"]),
  x: z.array(z.union([z.string(), z.number(), z.null()])),
  series: z.array(z.object({ name: z.string(), data: z.array(z.number().nullable()) })).min(1).max(3),
  x_label: z.string().optional(),
  y_label: z.string().optional(),
})

export const RunSqlOutput = z.object({
  query_id: z.number().int().min(1), // "truy vấn #n" cited in the answer
  query: z.string(), // exactly what was sent to /api/sql
  columns: z.array(z.string()).max(200),
  rows: z.array(z.array(z.union([z.string(), z.number(), z.boolean(), z.null()]))).max(200),
  row_count: z.number().int().min(0),
  chart: ChartSpec.nullable(), // chartFromResult(columns, rows) — values copied, never aggregated
  offline_template: z.enum(["topN", "byTime", "compare"]).optional(),
})

// Error shape surfaced in the tool card (HTTP status from FastAPI)
export const RunSqlError = z.object({
  status: z.union([z.literal(403), z.literal(408), z.literal(429), z.literal(400)]),
  message: z.string(),
})
