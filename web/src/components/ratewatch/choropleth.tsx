"use client"

import boundary from "../../../public/geo/vn-34.geo.json"

import type { Lang } from "@/lib/ratewatch/view"

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
  pcode: string
  name: string
  value: number | null
  group: number | null
}

const SVG_W = 540
const SVG_H = 620
const LON_MIN = 101.6
const LON_MAX = 117.8
const LAT_MIN = 6.5
const LAT_MAX = 23.7
const GREY = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"]

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
        const [x, y] = project(ring[index]![0]!, ring[index]![1]!)
        commands.push(`${index === 0 ? "M" : "L"}${x},${y}`)
      }
      commands.push("Z")
      parts.push(commands.join(""))
    }
  }
  return parts.join(" ")
}

const PATHS = (boundary as GeoCollection).features.map((feature) => ({
  pcode: feature.properties.pcode,
  name: feature.properties.name,
  d: geometryToPath(feature.geometry),
}))

export function Choropleth({
  rows,
  lang,
  ariaLabel,
  selected,
  onSelect,
  steps,
}: {
  rows: ChoroplethRow[]
  lang: Lang
  ariaLabel: string
  selected: string | null
  onSelect: (pcode: string) => void
  steps: { group: number; label: string }[]
}) {
  const vi = lang === "vi"
  const byCode = new Map(rows.map((row) => [row.pcode, row]))
  const blank = rows.some((row) => row.value === null)

  return (
    <div className="grid justify-items-center gap-2">
      <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} role="img" aria-label={ariaLabel} className="max-h-[320px] w-full max-w-[520px] sm:max-h-[440px] lg:max-h-[520px]">
        {PATHS.map((shape) => {
          const row = byCode.get(shape.pcode)
          const step = row?.group ?? null
          const fill = step === null ? "var(--background)" : GREY[Math.min(GREY.length - 1, Math.max(0, step))]!
          const amount = row?.value === null || row?.value === undefined
            ? (vi ? "chưa có số" : "no figure")
            : row.value.toLocaleString(vi ? "vi-VN" : "en-US")
          return (
            <path
              key={shape.pcode}
              d={shape.d}
              fill={fill}
              stroke={selected === shape.pcode ? "var(--foreground)" : "var(--border)"}
              strokeWidth={selected === shape.pcode ? 1.6 : 0.6}
              className="cursor-pointer"
              aria-label={`${shape.name}: ${amount}`}
              onClick={() => onSelect(shape.pcode)}
            />
          )
        })}
      </svg>
      <ul className="flex max-w-full flex-wrap justify-center gap-x-3 gap-y-1 text-xs" aria-label={vi ? "Thang 5 mức" : "Five-step scale"}>
        {steps.map((step) => (
          <li key={step.group} className="flex items-center gap-1">
            <span className="inline-block size-3 border border-border" style={{ background: GREY[Math.min(GREY.length - 1, step.group)] }} />
            {step.label}
          </li>
        ))}
        {blank ? (
          <li className="flex items-center gap-1">
            <span className="inline-block size-3 border border-border bg-background" />
            {vi ? "chưa có số" : "no figure"}
          </li>
        ) : null}
      </ul>
    </div>
  )
}
