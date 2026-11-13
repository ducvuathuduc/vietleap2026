// AI-analyst tools (Vercel AI SDK). Every number the model may quote comes from one of these FastAPI calls.
import { tool } from "ai"
import { z } from "zod"

import type {
  DriversResponse,
  Insight,
  LineageResponse,
  ModelsResponse,
  QualityResponse,
  Recommendation,
  SegmentsResponse,
  SqlResult,
  WarehouseTable,
  WhatIfResult,
} from "@/lib/api/types"
import { backend, compact, dsPath, post } from "./backend"

export function topInsights(insights: Insight[], n: number) {
  return insights.slice(0, n).map((i) => ({
    id: i.id,
    rank: i.rank,
    title: i.title_vi,
    finding: i.sentence_vi,
    test: i.test,
    p_value: i.p_value,
    effect: i.effect,
    caveat: i.caveat,
  }))
}

export function makeTools(datasetId: string | null) {
  const needDs = () => {
    if (!datasetId) throw new Error("Chưa chọn dataset nào trên dashboard.")
    return datasetId
  }
  return {
    listTables: tool({
      description: "Liệt kê các bảng trong warehouse DuckDB (layer bronze/silver/gold/meta, số dòng, số cột).",
      inputSchema: z.object({ layer: z.enum(["bronze", "silver", "gold", "meta"]).optional() }),
      execute: async ({ layer }) => {
        const t = await backend<WarehouseTable[]>("/api/warehouse/tables")
        return layer ? t.filter((x) => x.layer === layer) : t
      },
    }),
    getColumns: tool({
      description: "Tên và kiểu cột của một bảng warehouse, ví dụ 'gold.obt_ten_dataset'. Gọi trước khi viết SQL.",
      inputSchema: z.object({ table: z.string().regex(/^(bronze|silver|gold|meta)\.[\w]+$/) }),
      execute: async ({ table }) =>
        backend<{ name: string; type: string }[]>(`/api/warehouse/tables/${encodeURIComponent(table)}/columns`),
    }),
    runSql: tool({
      description:
        "Chạy MỘT câu SQL DuckDB chỉ đọc (SELECT/WITH) trên warehouse. Tên bảng dạng gold.\"ten_bang\". Trả về tối đa 200 dòng.",
      inputSchema: z.object({ query: z.string().min(1).max(5000) }),
      execute: async ({ query }) => compact(await backend<SqlResult>("/api/sql", post({ query, limit: 200 }))),
    }),
    getInsights: tool({
      description: "Các insight đã xếp hạng (kiểm định, p-value, effect size, caveat) và khuyến nghị của dataset đang chọn.",
      inputSchema: z.object({ top: z.number().int().min(1).max(15).default(5) }),
      execute: async ({ top }) => {
        const r = await backend<{ insights: Insight[]; recommendations: Recommendation[] }>(`${dsPath(needDs())}/insights`)
        return compact({
          insights: topInsights(r.insights, top),
          recommendations: r.recommendations.slice(0, top).map((x) => ({
            from_insight: x.from_insight,
            confidence: x.confidence,
            so_what: x.so_what_vi,
            now_what: x.now_what_vi,
            impact: x.impact_vi,
          })),
        })
      },
    }),
    getSegments: tool({
      description: "Trung vị chỉ số mục tiêu theo một cột phân loại + kiểm định khác biệt giữa các nhóm.",
      inputSchema: z.object({ by: z.string().optional(), metric: z.string().optional() }),
      execute: async ({ by, metric }) => {
        const q = new URLSearchParams()
        if (by) q.set("by", by)
        if (metric) q.set("metric", metric)
        const r = await backend<SegmentsResponse>(`${dsPath(needDs())}/segments?${q}`)
        return compact({ by: r.by, metric: r.metric, groups: r.groups.slice(0, 15), groups_total: r.groups_total, test: r.test, options: r.options })
      },
    }),
    getDrivers: tool({
      description: "Yếu tố tác động (hồi quy chuẩn hoá có bootstrap CI, permutation importance, R² kiểm định chéo).",
      inputSchema: z.object({}),
      execute: async () => {
        const r = await backend<DriversResponse>(`${dsPath(needDs())}/drivers`)
        return compact({ target: r.target, drivers: r.drivers, whatif_features: r.whatif_features.map((f) => f.name) })
      },
    }),
    whatIf: tool({
      description: "Mô phỏng: nếu một biến số thay đổi pct_change % thì chỉ số mục tiêu thay đổi bao nhiêu (kèm khoảng 90%).",
      inputSchema: z.object({ feature: z.string().min(1), pct_change: z.number().min(-90).max(300) }),
      execute: async ({ feature, pct_change }) =>
        compact(await backend<WhatIfResult>(`${dsPath(needDs())}/whatif`, post({ feature, pct_change }))),
    }),
    getQuality: tool({
      description: "Báo cáo chất lượng dữ liệu từng bảng silver: điểm trước/sau, missing, duplicate, outlier, nhật ký làm sạch.",
      inputSchema: z.object({}),
      execute: async () => {
        const q = await backend<QualityResponse>(`${dsPath(needDs())}/quality`)
        return Object.fromEntries(
          Object.entries(q).map(([t, v]) => [
            t,
            {
              score_before: v.score_before,
              score_after: v.score_after,
              rows_before: v.before.rows,
              rows_after: v.after.rows,
              missing_cells: [v.before.missing_cells, v.after.missing_cells],
              duplicate_rows: [v.before.duplicate_rows, v.after.duplicate_rows],
              issues_after: v.after.issues.slice(0, 12),
              cleaning_log: v.cleaning_log.slice(0, 12),
            },
          ])
        )
      },
    }),
    getLineage: tool({
      description: "Lineage dữ liệu: nguồn → bronze → silver → gold (các nút và bước biến đổi).",
      inputSchema: z.object({}),
      execute: async () => {
        const l = await backend<LineageResponse>(`${dsPath(needDs())}/lineage`)
        return { nodes: l.nodes, edges: l.edges }
      },
    }),
    getModels: tool({
      description: "Các mô hình dữ liệu đã dựng (OBT, Star, Snowflake, Data Vault): bảng gold, lý do chọn, khuyến nghị.",
      inputSchema: z.object({}),
      execute: async () => {
        const m = await backend<ModelsResponse>(`${dsPath(needDs())}/models`)
        return { models: Object.fromEntries(Object.entries(m.models).map(([k, v]) => [k, v?.tables])), rationale: m.rationale, recommended: m.recommended, column_plan: m.column_plan }
      },
    }),
  }
}

export type AnalystTools = ReturnType<typeof makeTools>
