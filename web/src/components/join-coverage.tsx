"use client"

// Join coverage of the conformed layer (engine/vlkit/de/conformed.py): how many rows of each source found a row in
// the shared dimension, and how many rows of the integrated OBT got a match from each joined source.
// Every number is read from pipeline.json / conformed.json — nothing computed beyond display formatting.
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { ConformedDiagnostics } from "@/lib/api/types"
import { insightTarget } from "@/lib/insight-target"

export const KEY_LABEL: Record<string, string> = {
  geo: "Tỉnh/quận",
  year: "Năm",
  date: "Ngày",
  ticker: "Mã CK",
  country: "Quốc gia",
  district: "Quận/huyện",
}

const STATUS_LABEL: Record<string, string> = {
  joined: "đã ghép",
  grain_mismatch: "không ghép — nhiều dòng/khoá",
  no_shared_key: "không có khoá chung",
}

const n = (x: number | undefined | null) => (typeof x === "number" ? x.toLocaleString("vi-VN") : "–")
const pct = (x: number | undefined | null) => (typeof x === "number" ? `${x.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%` : "–")

export function JoinCoverageCard({ c }: { c: ConformedDiagnostics }) {
  const rows = c.sources.flatMap((s) => Object.entries(s.keys).map(([key, k]) => ({ s, key, k })))
  return (
    <Card data-tour="join-coverage">
      <CardHeader>
        <CardTitle>Độ phủ ghép nối (join coverage)</CardTitle>
        <CardDescription>
          Khoá chung {c.shared_keys.map((k) => KEY_LABEL[k] ?? k).join(", ")} → bảng tích hợp {c.integrated} ({n(c.integrated_rows)} dòng
          {c.row_explosion ? ", CẢNH BÁO: số dòng khác bảng gốc" : ", không nhân dòng"}).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="overflow-auto rounded-lg border">
          <Table>
            <TableHeader className="bg-muted">
              <TableRow>
                <TableHead>Nguồn</TableHead>
                <TableHead>Khoá</TableHead>
                <TableHead className="w-48">Khớp dim chung</TableHead>
                <TableHead className="text-right">Khớp</TableHead>
                <TableHead className="text-right">Không khớp</TableHead>
                <TableHead className="text-right">Khoá trống</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-muted-foreground">Không có nguồn nào trỏ vào dimension chung.</TableCell>
                </TableRow>
              )}
              {rows.map(({ s, key, k }) => (
                <TableRow
                  key={`${s.table}-${key}`}
                  {...insightTarget("join", `${s.source}:${key}`, `Độ phủ khoá ${KEY_LABEL[key] ?? key} của ${s.source}`, {
                    source: s.source, key, column: k.column, rows: s.rows, matched_rows: k.matched_rows,
                    unmatched_rows: k.unmatched_rows, null_key_rows: k.null_key_rows, match_pct: k.match_pct,
                  })}
                >
                  <TableCell className="font-medium">{s.source}</TableCell>
                  <TableCell>{KEY_LABEL[key] ?? key}{k.column ? <span className="text-muted-foreground"> · {k.column}</span> : null}</TableCell>
                  <TableCell>
                    <Progress value={k.match_pct} aria-label={`Tỉ lệ khớp ${pct(k.match_pct)}`} />
                    <span className="text-xs text-muted-foreground">{pct(k.match_pct)}</span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{n(k.matched_rows)}</TableCell>
                  <TableCell className="text-right tabular-nums">{n(k.unmatched_rows)}</TableCell>
                  <TableCell className="text-right tabular-nums">{n(k.null_key_rows)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {c.joins.length > 0 && (
          <div className="overflow-auto rounded-lg border">
            <Table>
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead>Ghép vào bảng tích hợp</TableHead>
                  <TableHead>Trên khoá</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead className="w-48">Dòng được ghép</TableHead>
                  <TableHead>Mẫu chưa khớp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {c.joins.map((j) => (
                  <TableRow
                    key={j.source}
                    {...insightTarget("join", `integration:${j.source}`, `Ghép nguồn ${j.source} vào bảng tích hợp`, {
                      source: j.source, keys: j.keys, status: j.status, matched_rows: j.matched_rows, unmatched_rows: j.unmatched_rows,
                      match_pct: j.match_pct, unmatched_samples: j.unmatched_samples, hint: j.hint,
                    })}
                  >
                    <TableCell className="font-medium">{j.source}</TableCell>
                    <TableCell>{j.keys.map((k) => KEY_LABEL[k] ?? k).join(", ") || "–"}</TableCell>
                    <TableCell>
                      <Badge variant={j.status === "joined" ? "outline" : "secondary"}>{STATUS_LABEL[j.status] ?? j.status}</Badge>
                      {j.aggregated ? <span className="ml-1 text-xs text-muted-foreground">gộp {j.aggregated}</span> : null}
                    </TableCell>
                    <TableCell>
                      {j.status === "joined" ? (
                        <>
                          <Progress value={j.match_pct ?? 0} aria-label={`Tỉ lệ ghép ${pct(j.match_pct)}`} />
                          <span className="text-xs text-muted-foreground">{n(j.matched_rows)} dòng · {pct(j.match_pct)}</span>
                        </>
                      ) : (
                        <span className="text-xs text-muted-foreground">{j.hint ?? "–"}</span>
                      )}
                    </TableCell>
                    <TableCell className="max-w-64 truncate text-xs text-muted-foreground">{(j.unmatched_samples ?? []).join(" · ") || "–"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
