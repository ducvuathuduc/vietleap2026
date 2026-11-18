"use client"

import * as React from "react"
import { DownloadIcon, MapPinIcon } from "lucide-react"

import { InsightChart } from "@/components/insight-chart"
import { ProvinceMap } from "@/components/province-map"
import { LoadingState } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/use-async"
import { api, ApiError } from "@/lib/api/client"
import { fmtNum } from "@/lib/format"
import { canonicalProvince34, isRatioMetric } from "@/lib/geo-names"
import { insightTarget } from "@/lib/insight-target"

type GeoAgg = "median" | "mean" | "sum" | "count"

const AGG_OPTIONS: { value: GeoAgg; label: string }[] = [
  { value: "median", label: "Trung vị (median)" },
  { value: "mean", label: "Trung bình (mean)" },
  { value: "sum", label: "Tổng (sum)" },
  { value: "count", label: "Số dòng (count)" },
]

export function ProvinceRankingCard({
  datasetId,
  silentOnMissing = false,
}: {
  datasetId: string
  silentOnMissing?: boolean
}) {
  const [pickedMetric, setPickedMetric] = React.useState<{ ds: string; metric: string } | null>(null)
  const [pickedAgg, setPickedAgg] = React.useState<{ ds: string; agg: GeoAgg }>({ ds: datasetId, agg: "median" })
  const [viewMode, setViewMode] = React.useState<"map" | "bar">("map")
  const [mapUnavailable, setMapUnavailable] = React.useState(false)
  const chartWrapRef = React.useRef<HTMLDivElement>(null)

  const profile = useAsync(() => api.profile(datasetId).catch(() => null), [datasetId])
  const colProfiles = React.useMemo(
    () => profile.data?.profile.column_profiles ?? [],
    [profile.data]
  )
  const numericCols = React.useMemo(
    () => colProfiles.filter((c) => c.role === "numeric").map((c) => c.name),
    [colProfiles]
  )
  const hasVnProvinceCol = React.useMemo(() => {
    if (!profile.data) return false
    const geoCols = colProfiles.filter((c) => c.role === "geo" || c.role === "geo_raw")
    if (geoCols.length === 0) return false
    return geoCols.some(
      (c) =>
        !c.top_values ||
        c.top_values.length === 0 ||
        c.top_values.some((tv) => canonicalProvince34(tv.value).province !== null)
    )
  }, [profile.data, colProfiles])

  const metric = pickedMetric && pickedMetric.ds === datasetId ? pickedMetric.metric : undefined
  const activeAgg = pickedAgg.ds === datasetId ? pickedAgg.agg : "median"
  const ratioBlocked = metric ? isRatioMetric(metric) : false

  const geo = useAsync(
    () =>
      hasVnProvinceCol
        ? api.geo(datasetId, { metric, agg: ratioBlocked && activeAgg === "sum" ? "median" : activeAgg })
        : null,
    [datasetId, hasVnProvinceCol, metric, activeAgg, ratioBlocked]
  )

  const currentMetric = geo.data?.metric ?? metric ?? numericCols[0] ?? ""
  const currentMetricIsRatio = currentMetric ? isRatioMetric(currentMetric) : false

  const downloadPng = () => {
    const svg = chartWrapRef.current?.querySelector("svg")
    if (!svg || !geo.data) return
    const rect = svg.getBoundingClientRect()
    const vb = svg.viewBox?.baseVal
    const width = Math.max(640, Math.round(rect.width) || (vb?.width ? Math.round(vb.width) : 800))
    const chartH = Math.max(360, Math.round(rect.height) || (vb?.height ? Math.round(vb.height) : 440))
    const padTop = 52
    const padBottom = 42
    const height = chartH + padTop + padBottom

    const clone = svg.cloneNode(true) as SVGSVGElement
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg")
    clone.setAttribute("width", String(width))
    clone.setAttribute("height", String(chartH))

    // Resolve CSS custom properties on cloned SVG elements so offline PNG matches theme colors
    const computedRoot = getComputedStyle(document.documentElement)
    const resolveVar = (val: string | null) => {
      if (!val) return val
      const m = val.match(/^var\((--[^)]+)\)$/)
      if (!m) return val
      return computedRoot.getPropertyValue(m[1]).trim() || "#0f766e"
    }
    clone.querySelectorAll("path, rect, text").forEach((el) => {
      const f = resolveVar(el.getAttribute("fill"))
      if (f && f !== "none") el.setAttribute("fill", f)
      const s = resolveVar(el.getAttribute("stroke"))
      if (s && s !== "none") el.setAttribute("stroke", s)
    })

    const svgStr = new XMLSerializer().serializeToString(clone)
    const blob = new Blob([svgStr], { type: "image/svg+xml;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement("canvas")
      canvas.width = width * 2
      canvas.height = height * 2
      const ctx = canvas.getContext("2d")
      if (ctx) {
        ctx.scale(2, 2)
        ctx.fillStyle = "#ffffff"
        ctx.fillRect(0, 0, width, height)
        ctx.fillStyle = "#18181b"
        ctx.font = "600 15px sans-serif"
        ctx.fillText(`Bản đồ 34 tỉnh/thành — ${geo.data!.agg} ${geo.data!.metric}`, 16, 26)
        ctx.fillStyle = "#71717a"
        ctx.font = "12px sans-serif"
        ctx.fillText(`Toàn quốc: ${fmtNum(geo.data!.national.value)} (n=${geo.data!.national.n.toLocaleString("vi-VN")})`, 16, 44)
        ctx.drawImage(img, 0, padTop, width, chartH)
        ctx.fillStyle = "#71717a"
        ctx.font = "11px sans-serif"
        ctx.fillText(
          "Chuẩn 34 tỉnh (NQ 202/2025/QH15) · Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa) · GSO/OCHA COD-AB v02 (CC BY-IGO).",
          16,
          height - 16
        )
        const a = document.createElement("a")
        a.href = canvas.toDataURL("image/png")
        a.download = `${datasetId}_34_tinh_${geo.data!.metric}.png`
        a.click()
      }
      URL.revokeObjectURL(url)
    }
    img.src = url
  }

  if (profile.loading || (geo.loading && !geo.data)) {
    if (silentOnMissing) return null
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPinIcon className="size-4" /> Xếp hạng 34 tỉnh/thành (NQ 202/2025/QH15)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <LoadingState rows={2} />
        </CardContent>
      </Card>
    )
  }

  if (!hasVnProvinceCol || geo.error || !geo.data) {
    if (silentOnMissing) return null
    const isMissingGeo = !hasVnProvinceCol || geo.error instanceof ApiError || String(geo.error ?? "").includes("tỉnh")
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPinIcon className="size-4" /> Xếp hạng 34 tỉnh/thành (NQ 202/2025/QH15)
          </CardTitle>
          <CardDescription>
            {isMissingGeo
              ? "Dataset hiện tại không có cột tỉnh/thành phố Việt Nam để tổng hợp theo chuẩn 34 tỉnh."
              : String(geo.error)}
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const data = geo.data
  const rows = data.rows
  const metricOptions = (numericCols.length > 0 ? numericCols : [data.metric]).map((m) => ({ value: m, label: m }))
  const showMap = viewMode === "map" && !mapUnavailable

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          <MapPinIcon className="size-4" />
          <span>Xếp hạng 34 tỉnh/thành: {data.metric}</span>
          {data.converted_from_63 ? <Badge variant="secondary">đã quy đổi về 34 tỉnh</Badge> : null}
        </CardTitle>
        <CardDescription>
          {data.rows.length} tỉnh/thành có dữ liệu · Toàn quốc ({data.agg}):{" "}
          <span className="font-medium text-foreground tabular-nums">{fmtNum(data.national.value)}</span> (n=
          {data.national.n.toLocaleString("vi-VN")})
          {data.unmatched.rows > 0
            ? ` · Chưa khớp: ${data.unmatched.rows} dòng (${data.unmatched.samples.slice(0, 3).join(", ")})`
            : ""}
        </CardDescription>
        <CardAction className="flex flex-wrap items-center gap-2">
          {metricOptions.length > 1 ? (
            <Select
              value={currentMetric}
              onValueChange={(v) => v && setPickedMetric({ ds: datasetId, metric: v })}
              items={metricOptions}
            >
              <SelectTrigger size="sm" className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent align="end">
                <SelectGroup>
                  {metricOptions.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          ) : null}
          <Select
            value={data.agg}
            onValueChange={(v) => {
              if (!v) return
              const next = v as GeoAgg
              if (next === "sum" && currentMetricIsRatio) return
              setPickedAgg({ ds: datasetId, agg: next })
            }}
            items={AGG_OPTIONS}
          >
            <SelectTrigger size="sm" className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="end">
              <SelectGroup>
                {AGG_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value} disabled={o.value === "sum" && currentMetricIsRatio}>
                    {o.value === "sum" && currentMetricIsRatio ? `${o.label} (chặn tỷ lệ)` : o.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          {!mapUnavailable ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setViewMode((m) => (m === "map" ? "bar" : "map"))}
            >
              {showMap ? "Xem biểu đồ cột" : "Xem bản đồ 34 tỉnh"}
            </Button>
          ) : null}
          <Button variant="outline" size="sm" onClick={downloadPng}>
            <DownloadIcon className="size-3.5" /> Tải PNG
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className={showMap ? "grid gap-4 lg:grid-cols-12" : "flex flex-col gap-4"}>
          <div ref={chartWrapRef} className={showMap ? "lg:col-span-5" : undefined}>
            {showMap ? (
              <ProvinceMap
                rows={rows}
                metric={data.metric}
                agg={data.agg}
                nationalValue={data.national.value}
                onUnavailable={() => setMapUnavailable(true)}
              />
            ) : (
              <InsightChart
                spec={{
                  kind: "hbar",
                  x: rows.map((r) => r.province),
                  series: [{ name: `${data.agg} ${data.metric}`, data: rows.map((r) => r.value) }],
                }}
                height={Math.max(260, Math.min(540, rows.length * 22))}
              />
            )}
          </div>
          <div className={showMap ? "lg:col-span-7 max-h-[500px] overflow-auto rounded-lg border" : "max-h-72 overflow-auto rounded-lg border"}>
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-card">
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>Tỉnh/Thành phố (chuẩn 34)</TableHead>
                  <TableHead>Vùng kinh tế</TableHead>
                  <TableHead className="text-right">{data.agg}</TableHead>
                  <TableHead className="text-right">Số dòng (n)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r, idx) => (
                  <TableRow
                    key={r.province}
                    {...insightTarget("segment", r.province, `Tỉnh ${r.province}`, {
                      province: r.province,
                      region: r.region,
                      metric: data.metric,
                      agg: data.agg,
                      value: r.value,
                      n: r.n,
                      rank: idx + 1,
                      total_provinces: rows.length,
                      national_value: data.national.value,
                    })}
                  >
                    <TableCell className="tabular-nums text-muted-foreground">{idx + 1}</TableCell>
                    <TableCell className="font-medium">{r.province}</TableCell>
                    <TableCell className="text-muted-foreground">{r.region ?? "–"}</TableCell>
                    <TableCell className="text-right font-medium tabular-nums">{fmtNum(r.value)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      <span className="inline-flex items-center gap-1.5">
                        {r.n.toLocaleString("vi-VN")}
                        {r.n < 5 ? <Badge variant="outline">n nhỏ</Badge> : null}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Chuẩn hành chính 34 tỉnh/thành theo Nghị quyết 202/2025/QH15 (bao gồm Hoàng Sa thuộc TP. Đà Nẵng và Trường Sa thuộc tỉnh Khánh Hòa). Bấm vào một tỉnh trên bản đồ hoặc bảng trong chế độ “Hỏi AI” để xem xếp hạng và chênh lệch so với toàn quốc.
        </p>
      </CardContent>
    </Card>
  )
}
