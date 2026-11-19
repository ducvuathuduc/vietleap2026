"use client"

import * as React from "react"

import { formatNumber } from "@/lib/monitor/format"

import { groupToStep, loadErrorText, stepFill } from "./labels"

type GeoFeature = {
  type: "Feature"
  properties: { pcode: string; name: string; name_en?: string }
  geometry: {
    type: "MultiPolygon" | "Polygon"
    coordinates: number[][][][] | number[][][]
  }
}

type GeoCollection = {
  type: "FeatureCollection"
  features: GeoFeature[]
}

export interface ChoroplethRow {
  name: string
  value: number | null
  group: number | null
}

export interface ChoroplethGroup {
  group: number
  label_vi: string
  min: number
  max: number
  count: number
}

export interface ChoroplethProps {
  rows: ChoroplethRow[]
  groups: ChoroplethGroup[]
  unit?: string
  ariaLabel: string
  geoUrl?: string
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

function geometryToPath(geometry: GeoFeature["geometry"]): string {
  const polygons: number[][][][] =
    geometry.type === "MultiPolygon" ? (geometry.coordinates as number[][][][]) : [geometry.coordinates as number[][][]]
  const parts: string[] = []
  for (const polygon of polygons) {
    for (const ring of polygon) {
      if (!ring.length) continue
      const commands: string[] = []
      for (let index = 0; index < ring.length; index += 1) {
        const [x, y] = project(ring[index][0], ring[index][1])
        commands.push(`${index === 0 ? "M" : "L"}${x},${y}`)
      }
      commands.push("Z")
      parts.push(commands.join(""))
    }
  }
  return parts.join(" ")
}

/**
 * 34-province choropleth (§3.1): 5 grey steps by group, missing data stays white,
 * hover changes the fill in 80 ms. Adapted from `province-map.tsx`, which stays untouched.
 */
export function Choropleth({ rows, groups, unit, ariaLabel, geoUrl = "/geo/vn-34.geo.json" }: ChoroplethProps) {
  const [geo, setGeo] = React.useState<GeoCollection | null>(null)
  const [failed, setFailed] = React.useState(false)
  const [hovered, setHovered] = React.useState<string | null>(null)

  React.useEffect(() => {
    let alive = true
    fetch(geoUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<GeoCollection>
      })
      .then((data) => {
        if (!alive) return
        if (!data?.features?.length) throw new Error("Empty GeoJSON")
        setGeo(data)
      })
      .catch(() => {
        if (alive) setFailed(true)
      })
    return () => {
      alive = false
    }
  }, [geoUrl])

  const byName = React.useMemo(() => new Map(rows.map((row) => [row.name, row])), [rows])

  const paths = React.useMemo(() => {
    if (!geo) return []
    return geo.features.map((feature) => ({
      pcode: feature.properties.pcode,
      name: feature.properties.name,
      d: geometryToPath(feature.geometry),
    }))
  }, [geo])

  const legend = React.useMemo(() => [...groups].sort((a, b) => a.group - b.group), [groups])

  if (failed) {
    return <p className="text-xs text-muted-foreground">{loadErrorText("bản đồ tỉnh/thành")}</p>
  }

  if (!geo) {
    return <div className="h-[320px] w-full animate-pulse rounded-lg bg-muted motion-reduce:animate-none" aria-hidden="true" />
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-center">
        <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} role="img" aria-label={ariaLabel} className="max-h-[440px] w-full max-w-[420px] select-none">
          {paths.map((shape) => {
            const row = byName.get(shape.name)
            const step = row ? groupToStep(row.group, groups) : null
            const fill =
              hovered === shape.name && row
                ? "var(--foreground)"
                : step === null
                  ? "var(--background)"
                  : stepFill(step)
            const group = row?.group !== null && row?.group !== undefined ? legend.find((item) => item.group === row.group) : undefined
            return (
              <path
                key={shape.pcode}
                d={shape.d}
                fill={fill}
                stroke="var(--border)"
                strokeWidth={row ? 0.8 : 0.5}
                className="transition-[fill] duration-[80ms] motion-reduce:transition-none"
                onMouseEnter={() => setHovered(shape.name)}
                onMouseLeave={() => setHovered(null)}
              >
                <title>
                  {row
                    ? `${shape.name}: ${formatNumber(row.value)}${unit ? ` ${unit}` : ""}${group ? ` · ${group.label_vi}` : ""}`
                    : `${shape.name}: chưa có dữ liệu`}
                </title>
              </path>
            )
          })}
        </svg>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {legend.map((item) => (
          <span key={item.group} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block size-2.5 rounded-[2px] border border-border"
              style={{ backgroundColor: stepFill(groupToStep(item.group, groups)) }}
              aria-hidden="true"
            />
            {item.label_vi}
            <span className="tabular-nums">
              {formatNumber(item.min)}–{formatNumber(item.max)}
            </span>
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-[2px] border border-border bg-background" aria-hidden="true" />
          Thiếu dữ liệu
        </span>
      </div>
    </div>
  )
}
