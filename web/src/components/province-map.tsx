"use client"

import * as React from "react"
import { fmtNum } from "@/lib/format"
import { insightTarget } from "@/lib/insight-target"
import type { GeoRow } from "@/lib/api/types"

type GeoFeature = {
  type: "Feature"
  properties: {
    pcode: string
    name: string
    name_en?: string
  }
  geometry: {
    type: "MultiPolygon" | "Polygon"
    coordinates: number[][][][] | number[][][]
  }
}

type GeoCollection = {
  type: "FeatureCollection"
  features: GeoFeature[]
}

const SVG_W = 540
const SVG_H = 620
const LON_MIN = 101.6
const LON_MAX = 117.8
const LAT_MIN = 6.5
const LAT_MAX = 23.7

function mercX(lonDeg: number): number {
  return (lonDeg * Math.PI) / 180
}

function mercY(latDeg: number): number {
  const rad = (latDeg * Math.PI) / 180
  return Math.log(Math.tan(Math.PI / 4 + rad / 2))
}

const MERC_X_MIN = mercX(LON_MIN)
const MERC_X_MAX = mercX(LON_MAX)
const MERC_Y_MIN = mercY(LAT_MIN)
const MERC_Y_MAX = mercY(LAT_MAX)

function project(lon: number, lat: number): [number, number] {
  const pad = 16
  const usableW = SVG_W - pad * 2
  const usableH = SVG_H - pad * 2
  const xSpan = MERC_X_MAX - MERC_X_MIN
  const ySpan = MERC_Y_MAX - MERC_Y_MIN
  const scale = Math.min(usableW / xSpan, usableH / ySpan)
  const ox = (SVG_W - xSpan * scale) / 2
  const oy = (SVG_H - ySpan * scale) / 2
  const x = ox + (mercX(lon) - MERC_X_MIN) * scale
  const y = oy + (MERC_Y_MAX - mercY(lat)) * scale
  return [Number(x.toFixed(1)), Number(y.toFixed(1))]
}

function geometryToPath(geom: GeoFeature["geometry"]): string {
  const polys: number[][][][] =
    geom.type === "MultiPolygon"
      ? (geom.coordinates as number[][][][])
      : [geom.coordinates as number[][][]]
  const parts: string[] = []
  for (const poly of polys) {
    for (const ring of poly) {
      if (!ring.length) continue
      const cmds: string[] = []
      for (let i = 0; i < ring.length; i++) {
        const [x, y] = project(ring[i][0], ring[i][1])
        cmds.push(`${i === 0 ? "M" : "L"}${x},${y}`)
      }
      cmds.push("Z")
      parts.push(cmds.join(""))
    }
  }
  return parts.join(" ")
}

const QUANTILE_VARS = [
  "var(--chart-5)",
  "var(--chart-4)",
  "var(--chart-3)",
  "var(--chart-2)",
  "var(--chart-1)",
]

function quantileColor(value: number, sortedAsc: number[]): { fill: string; bucket: number } {
  if (!sortedAsc.length) return { fill: "var(--muted)", bucket: -1 }
  if (sortedAsc.length === 1 || sortedAsc[0] === sortedAsc[sortedAsc.length - 1]) {
    return { fill: QUANTILE_VARS[2], bucket: 2 }
  }
  let idx = 0
  for (let i = 0; i < sortedAsc.length; i++) {
    if (sortedAsc[i] <= value) idx = i
  }
  const rank = idx / Math.max(1, sortedAsc.length - 1)
  const bucket = Math.min(4, Math.floor(rank * 5))
  return { fill: QUANTILE_VARS[bucket], bucket }
}

export function ProvinceMap({
  rows,
  metric,
  agg,
  nationalValue,
  onUnavailable,
}: {
  rows: GeoRow[]
  metric: string
  agg: string
  nationalValue: number | null
  onUnavailable?: () => void
}) {
  const [geo, setGeo] = React.useState<GeoCollection | null>(null)
  const [failed, setFailed] = React.useState(false)
  const [hovered, setHovered] = React.useState<{
    name: string
    row: GeoRow | null
    rank: number | null
  } | null>(null)

  React.useEffect(() => {
    let alive = true
    fetch("/geo/vn-34.geo.json")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<GeoCollection>
      })
      .then((data) => {
        if (!alive) return
        if (!data?.features?.length) throw new Error("Empty GeoJSON")
        setGeo(data)
      })
      .catch(() => {
        if (!alive) return
        setFailed(true)
        onUnavailable?.()
      })
    return () => {
      alive = false
    }
  }, [onUnavailable])

  const rowMap = React.useMemo(() => {
    const m = new Map<string, { row: GeoRow; rank: number }>()
    rows.forEach((r, idx) => {
      m.set(r.province, { row: r, rank: idx + 1 })
    })
    return m
  }, [rows])

  const sortedValues = React.useMemo(
    () => rows.map((r) => r.value).filter((v): v is number => v !== null && Number.isFinite(v)).sort((a, b) => a - b),
    [rows]
  )

  const paths = React.useMemo(() => {
    if (!geo) return []
    return geo.features.map((f) => ({
      pcode: f.properties.pcode,
      name: f.properties.name,
      d: geometryToPath(f.geometry),
    }))
  }, [geo])

  const hsBox = React.useMemo(() => {
    const [x1, y1] = project(111.1, 17.4)
    const [x2, y2] = project(113.2, 15.3)
    return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 }
  }, [])

  const tsBox = React.useMemo(() => {
    const [x1, y1] = project(110.2, 13.1)
    const [x2, y2] = project(117.6, 6.6)
    return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 }
  }, [])

  if (failed) return null

  if (!geo) {
    return (
      <div className="flex h-[360px] items-center justify-center rounded-lg border bg-muted/20 text-xs text-muted-foreground">
        Đang tải ranh giới 34 tỉnh/thành (NQ 202/2025/QH15)…
      </div>
    )
  }

  return (
    <div className="relative flex flex-col gap-3">
      <div className="relative flex justify-center rounded-lg border bg-muted/15 p-3">
        <svg
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          role="img"
          aria-label={`Bản đồ 34 tỉnh/thành Việt Nam theo ${agg} ${metric}`}
          className="max-h-[440px] w-full max-w-[420px] select-none"
          data-testid="vn-34-choropleth-svg"
        >
          {/* Dashed sovereignty callout boxes for Hoang Sa (Da Nang) and Truong Sa (Khanh Hoa) */}
          <rect
            x={hsBox.x}
            y={hsBox.y}
            width={hsBox.w}
            height={hsBox.h}
            rx={4}
            fill="none"
            stroke="var(--border)"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
          <text
            x={hsBox.x + hsBox.w / 2}
            y={hsBox.y - 5}
            textAnchor="middle"
            fontSize={9}
            fill="var(--muted-foreground)"
          >
            Hoàng Sa (Đà Nẵng)
          </text>

          <rect
            x={tsBox.x}
            y={tsBox.y}
            width={tsBox.w}
            height={tsBox.h}
            rx={4}
            fill="none"
            stroke="var(--border)"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
          <text
            x={tsBox.x + tsBox.w / 2}
            y={tsBox.y - 5}
            textAnchor="middle"
            fontSize={9}
            fill="var(--muted-foreground)"
          >
            Trường Sa (Khánh Hòa)
          </text>

          {paths.map((feat) => {
            const hit = rowMap.get(feat.name)
            const q =
              hit && hit.row.value !== null && Number.isFinite(hit.row.value)
                ? quantileColor(hit.row.value, sortedValues)
                : { fill: "var(--muted)", bucket: -1 }
            const isHovered = hovered?.name === feat.name
            const targetProps = hit
              ? insightTarget("segment", feat.name, `Tỉnh ${feat.name}`, {
                  province: feat.name,
                  region: hit.row.region,
                  metric,
                  agg,
                  value: hit.row.value,
                  n: hit.row.n,
                  rank: hit.rank,
                  total_provinces: rows.length,
                  national_value: nationalValue,
                })
              : {}

            return (
              <path
                key={feat.pcode}
                d={feat.d}
                data-province={feat.name}
                data-bucket={q.bucket}
                fill={q.fill}
                fillOpacity={hit ? (isHovered ? 1 : 0.88) : 0.4}
                stroke={isHovered ? "var(--foreground)" : "var(--background)"}
                strokeWidth={isHovered ? 1.5 : 0.7}
                className={hit ? "cursor-pointer transition-opacity" : "transition-opacity"}
                onMouseEnter={() =>
                  setHovered({
                    name: feat.name,
                    row: hit?.row ?? null,
                    rank: hit?.rank ?? null,
                  })
                }
                onMouseLeave={() => setHovered(null)}
                {...targetProps}
              >
                <title>
                  {hit
                    ? `${feat.name} (#${hit.rank}): ${fmtNum(hit.row.value)} (n=${hit.row.n.toLocaleString("vi-VN")})`
                    : `${feat.name}: chưa có dữ liệu`}
                </title>
              </path>
            )
          })}
        </svg>

        <div className="pointer-events-none absolute right-3 top-3 rounded-md border bg-background/90 px-2.5 py-1.5 text-xs shadow-xs backdrop-blur-xs">
          {hovered ? (
            <div className="flex flex-col gap-0.5">
              <span className="font-medium text-foreground">
                {hovered.name}
                {hovered.rank ? ` · #${hovered.rank}/${rows.length}` : ""}
              </span>
              {hovered.row ? (
                <span className="tabular-nums text-muted-foreground">
                  {agg}: {fmtNum(hovered.row.value)} (n={hovered.row.n.toLocaleString("vi-VN")})
                </span>
              ) : (
                <span className="text-muted-foreground">Không có dữ liệu</span>
              )}
            </div>
          ) : (
            <span className="text-muted-foreground">Di chuột vào tỉnh để xem trị số</span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <span>Thấp</span>
          {QUANTILE_VARS.map((c, i) => (
            <span
              key={i}
              className="inline-block h-2.5 w-5 rounded-[2px] border border-border/50"
              style={{ backgroundColor: c }}
            />
          ))}
          <span>Cao</span>
          <span className="ml-2 inline-flex items-center gap-1">
            <span
              className="inline-block h-2.5 w-4 rounded-[2px] border border-border/50"
              style={{ backgroundColor: "var(--muted)" }}
            />
            Thiếu
          </span>
        </div>
        <span>Ranh giới: GSO/OCHA COD-AB v02 (CC BY-IGO)</span>
      </div>
    </div>
  )
}
