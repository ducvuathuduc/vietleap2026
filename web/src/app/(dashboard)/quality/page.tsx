"use client"

import * as React from "react"

import { useDataset } from "@/components/dataset-provider"
import { InsightChart } from "@/components/insight-chart"
import { ResultTable } from "@/components/result-table"
import { StatCards } from "@/components/stat-cards"
import { EmptyState, PageShell, datasetGate } from "@/components/state"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { DqIssue, QualitySnapshot } from "@/lib/api/types"

/** Workshop cleaning categories → engine issue types (engine/vlkit/de/quality.py). */
const CATEGORY: Record<string, string> = {
  missing: "Thiếu dữ liệu (missing)",
  duplicate_rows: "Trùng lặp (duplicate)",
  duplicate_key: "Trùng lặp (duplicate)",
  outlier: "Ngoại lai (outlier)",
  wrong_type: "Sai kiểu / định dạng",
  impossible_negative: "Giá trị âm vô lý",
  constant: "Cột hằng",
}

function issueRow(i: DqIssue): (string | number | null)[] {
  const amount = i.count ?? (i.pct !== undefined ? `${i.pct}%` : null)
  const col = i.column ?? (Array.isArray(i.key) ? (i.key as string[]).join(" + ") : "toàn bảng")
  const detail = i.detail ? `${i.detail}${i.unparseable ? ` · ${i.unparseable} ô không đọc được` : ""}` : ""
  return [CATEGORY[i.type] ?? i.type, col, amount, detail]
}

const sumOutliers = (s: QualitySnapshot) =>
  s.issues.filter((i) => i.type === "outlier").reduce((a, i) => a + (i.count ?? 0), 0)

export default function QualityPage() {
  const { datasetId, loading: dsLoading, error: dsError } = useDataset()
  const r = useAsync(() => (datasetId ? api.quality(datasetId) : null), [datasetId])
  const [picked, setPicked] = React.useState<string | null>(null)
  const gate = datasetGate({ datasetId, datasetsLoading: dsLoading, datasetsError: dsError, loading: r.loading, error: r.error, hasData: !!r.data })
  if (gate || !r.data) return <PageShell>{gate}</PageShell>

  const names = Object.keys(r.data)
  if (names.length === 0)
    return (
      <PageShell>
        <EmptyState title="Chưa có báo cáo chất lượng" description="Pipeline chưa tạo bảng silver nào cho dataset này." />
      </PageShell>
    )
  const table = picked && r.data[picked] ? picked : names[0]
  const q = r.data[table]
  const { before, after } = q
  const missingCols = Object.entries(before.columns)
    .map(([c, v]) => ({ c, b: v.missing_pct, a: after.columns[c]?.missing_pct ?? null }))
    .filter((x) => x.b > 0 || (x.a ?? 0) > 0)
    .sort((x, y) => y.b - x.b)
    .slice(0, 15)
  const opts = names.map((n) => ({ label: n, value: n }))

  return (
    <PageShell>
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 lg:px-6">
        <p className="text-sm text-muted-foreground">
          Bronze → silver: xử lý <span className="font-medium text-foreground">missing, duplicate, outlier</span>; outlier chỉ gắn cờ (3×IQR), không xoá.
        </p>
        <Select value={table} onValueChange={(v) => v && setPicked(v)} items={opts}>
          <SelectTrigger size="sm" className="w-72" aria-label="Chọn bảng silver"><SelectValue /></SelectTrigger>
          <SelectContent align="end">
            <SelectGroup>
              {opts.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>
      <StatCards
        items={[
          { label: "Điểm chất lượng (0–100)", value: `${q.score_before.toFixed(1)} → ${q.score_after.toFixed(1)}`, badge: `${q.score_after - q.score_before >= 0 ? "+" : ""}${(q.score_after - q.score_before).toFixed(1)}`, footer: `${before.rows.toLocaleString("vi-VN")} → ${after.rows.toLocaleString("vi-VN")} dòng`, hint: "Trước / sau làm sạch" },
          { label: "Ô thiếu (missing)", value: `${before.missing_cells.toLocaleString("vi-VN")} → ${after.missing_cells.toLocaleString("vi-VN")}`, footer: `${before.invalid_cells.toLocaleString("vi-VN")} → ${after.invalid_cells.toLocaleString("vi-VN")} ô sai định dạng`, hint: "Ô không đọc được thành missing, không đoán" },
          { label: "Dòng trùng (duplicate)", value: `${before.duplicate_rows.toLocaleString("vi-VN")} → ${after.duplicate_rows.toLocaleString("vi-VN")}`, footer: after.candidate_key ? `Khoá ứng viên: ${after.candidate_key.join(" + ")}` : "Không tìm thấy khoá ứng viên", hint: after.duplicate_keys !== null ? `${after.duplicate_keys} khoá trùng sau làm sạch` : undefined },
          { label: "Ngoại lai gắn cờ (outlier)", value: sumOutliers(after).toLocaleString("vi-VN"), footer: "Quy tắc 3×IQR theo cột số", hint: "Giữ lại để phân tích độ nhạy" },
        ]}
      />
      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>% thiếu theo cột</CardTitle>
            <CardDescription>Trước và sau làm sạch (tối đa 15 cột thiếu nhiều nhất).</CardDescription>
          </CardHeader>
          <CardContent>
            {missingCols.length === 0 ? (
              <p className="text-sm text-muted-foreground">Không cột nào thiếu dữ liệu.</p>
            ) : (
              <InsightChart
                height={Math.max(200, missingCols.length * 28)}
                spec={{
                  kind: "hbar",
                  x: missingCols.map((m) => m.c),
                  series: [
                    { name: "% thiếu trước", data: missingCols.map((m) => m.b) },
                    { name: "% thiếu sau", data: missingCols.map((m) => m.a) },
                  ],
                }}
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Vấn đề phát hiện (bronze)</CardTitle>
            <CardDescription>{before.issues.length} vấn đề trước · {after.issues.length} còn lại sau làm sạch</CardDescription>
          </CardHeader>
          <CardContent>
            <ResultTable columns={["Loại", "Cột", "Số lượng", "Chi tiết"]} rows={before.issues.map(issueRow)} maxHeight="20rem" empty="Không phát hiện vấn đề." />
          </CardContent>
        </Card>
      </div>
      <div className="px-4 lg:px-6">
        <Card>
          <CardHeader>
            <CardTitle>Nhật ký làm sạch (cleaning log)</CardTitle>
            <CardDescription>Mọi biến đổi bronze → silver, theo thứ tự đã chạy — để giám khảo audit.</CardDescription>
            <CardAction className="text-sm text-muted-foreground">{q.cleaning_log.length} bước</CardAction>
          </CardHeader>
          <CardContent>
            <ResultTable columns={["#", "Bước"]} rows={q.cleaning_log.map((l, i) => [i + 1, l])} maxHeight="24rem" empty="Không có bước làm sạch nào." />
          </CardContent>
        </Card>
      </div>
    </PageShell>
  )
}
