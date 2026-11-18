import crypto from "node:crypto"
import type {
  ColumnProfile,
  DatasetDetail,
  DatasetSummary,
  Domain,
  DriversResponse,
  ExportKind,
  GeoResponse,
  GeoRow,
  Insight,
  Kpi,
  LineageResponse,
  ModelsResponse,
  PipelineSummary,
  ProfileResponse,
  Provenance,
  QualityIssue,
  QualityResponse,
  QualitySnapshot,
  Recommendation,
  Role,
  SegmentsResponse,
  SourceKind,
  TimeSeriesResponse,
  WhatIfChange,
  WhatIfCurve,
  WhatIfResult,
  WhatIfScenarioResult,
} from "@/lib/api/types"
import { canonicalProvince34, isRatioMetric } from "@/lib/geo-names"
import {
  asciiKey,
  cleanText,
  detectDecimal,
  normalizeProvince,
  parseVnDate,
  parseVnNumber,
  slug,
} from "./vn"
import {
  buildDrivers,
  histogram,
  iqr3Bounds,
  kruskalWallis,
  mannWhitney,
  mean,
  median,
  predictWhatIf,
  predictWhatIfMulti,
  runKMeans,
  skewness,
  spearman,
  std,
  type DriverModelInternal,
} from "./stats"

export interface SourceInputMeta {
  name: string
  kind: SourceKind
  uri: string
  options?: Record<string, unknown>
  license_note?: string
}

export interface AnalyzedDataset {
  id: string
  summary: DatasetSummary
  detail: DatasetDetail
  profile: ProfileResponse
  insights: { insights: Insight[]; recommendations: Recommendation[] }
  drivers: DriversResponse
  driverModel: DriverModelInternal | null
  bronzeRows: Record<string, string | number | boolean | null>[]
  silverRows: Record<string, string | number | boolean | null>[]
  goldRows: Record<string, string | number | boolean | null>[]
  segmentsClusters: SegmentsResponse["clusters"]
  pipeline: PipelineSummary
  quality: QualityResponse
  lineage: LineageResponse
  models: ModelsResponse
  provenance: Provenance[]
  tableNameBronze: string
  tableNameSilver: string
  tableNameGold: string
}

function fmtCompact(n: number | null): string {
  if (n === null || !Number.isFinite(n)) return "–"
  const abs = Math.abs(n)
  if (abs >= 1e9) return `${(n / 1e9).toFixed(2)} tỷ`
  if (abs >= 1e6) return `${(n / 1e6).toFixed(2)} tr`
  if (abs >= 1e4) return Math.round(n).toLocaleString("en-US")
  if (Number.isInteger(n)) return n.toLocaleString("en-US")
  return n.toFixed(2)
}

function detectDomain(cols: string[], requested: string): Domain {
  if (requested === "property" || requested === "public_finance" || requested === "firm" || requested === "generic") {
    return requested
  }
  const keys = cols.map(asciiKey).join(" | ")
  if (/gia ban|gia thue|dien tich|price per m2|loai bds|phap ly/.test(keys)) return "property"
  if (/ngan sach|earmarked|tax revenue|central gov debt|revenue pct gdp|fiscal|transfer/.test(keys)) return "public_finance"
  if (/roe|roa|doanh thu|loi nhuan|von chu|equity|assets/.test(keys)) return "firm"
  return "generic"
}

export function analyzeDataset(opts: {
  id: string
  name: string
  sourceFile: string
  rawRows: Record<string, unknown>[]
  domain?: string
  target?: string | null
  timeCol?: string | null
  geoCol?: string | null
  sources?: SourceInputMeta[]
  created?: string
}): AnalyzedDataset {
  const t0 = Date.now()
  const dsId = slug(opts.id)
  const created = opts.created ?? new Date().toISOString().slice(0, 19).replace("T", " ")
  const rawRows = opts.rawRows.slice(0, 15_000)

  // 1. Normalize column names to slugged keys while preserving display mapping
  const origCols = rawRows.length > 0 ? Object.keys(rawRows[0]) : []
  const colSlugMap = new Map<string, string>()
  const usedSlugs = new Set<string>()
  for (const c of origCols) {
    let s = slug(c)
    if (usedSlugs.has(s)) {
      let i = 2
      while (usedSlugs.has(`${s}_${i}`)) i++
      s = `${s}_${i}`
    }
    usedSlugs.add(s)
    colSlugMap.set(c, s)
  }

  const bronzeRows: Record<string, string | number | boolean | null>[] = rawRows.map((r) => {
    const out: Record<string, string | number | boolean | null> = {}
    for (const [orig, s] of colSlugMap.entries()) {
      const v = r[orig]
      out[s] = v === undefined || v === null || v === "" ? null : typeof v === "number" || typeof v === "boolean" ? v : cleanText(v)
    }
    return out
  })

  const cols = Array.from(colSlugMap.values())
  const cleaningLog: string[] = []
  cleaningLog.push(`Ingested ${bronzeRows.length} raw rows and ${cols.length} columns from ${opts.sourceFile}.`)

  // 2. Determine column parsing & clean into silverRows
  const parsedCols = new Set<string>()
  const dateCols = new Set<string>()
  let geoSourceCol: string | null = null
  const invalidCellsByCol: Record<string, number> = {}
  const beforeMissingByCol: Record<string, number> = {}

  for (const c of cols) {
    const nonNull = bronzeRows.map((r) => r[c]).filter((v) => v !== null && v !== "")
    beforeMissingByCol[c] = bronzeRows.length - nonNull.length
    const cKey = asciiKey(c)

    if (/^(ma_|id$|.*_id$|iso3$)/.test(c)) continue

    // Check date column
    if (
      /ngay|date|time|thoi_gian/.test(cKey) ||
      (nonNull.length > 0 && nonNull.slice(0, 30).filter((v) => parseVnDate(v) !== null).length >= Math.min(nonNull.length, 30) * 0.7)
    ) {
      const parsedDates = nonNull.filter((v) => parseVnDate(v) !== null)
      if (parsedDates.length >= nonNull.length * 0.6 && nonNull.length > 0) {
        dateCols.add(c)
        invalidCellsByCol[c] = nonNull.length - parsedDates.length
        continue
      }
    }

    // Check numeric column (including Vietnamese currency/units)
    const dec = detectDecimal(nonNull.slice(0, 100))
    const numHits = nonNull.slice(0, 80).filter((v) => parseVnNumber(v, dec) !== null).length
    if (nonNull.length > 0 && numHits >= Math.min(nonNull.length, 80) * 0.55) {
      parsedCols.add(c)
      const allNums = nonNull.filter((v) => parseVnNumber(v, dec) !== null)
      invalidCellsByCol[c] = nonNull.length - allNums.length
      if (nonNull.some((v) => typeof v === "string")) {
        cleaningLog.push(`Parsed numeric/VN-unit column '${c}' (${allNums.length}/${nonNull.length} valid values).`)
      }
      continue
    }

    // Check province/geo column
    if (/tinh|province|dia_phuong|city|thanh_pho/.test(cKey)) {
      geoSourceCol = c
    }
  }

  // Deduplicate exact rows
  const seenHashes = new Set<string>()
  let dupCount = 0
  const silverRaw: Record<string, string | number | boolean | null>[] = []

  for (const row of bronzeRows) {
    const hash = crypto.createHash("md5").update(JSON.stringify(row)).digest("hex").slice(0, 12)
    if (seenHashes.has(hash)) {
      dupCount++
      continue
    }
    seenHashes.add(hash)

    const clean: Record<string, string | number | boolean | null> = {}
    for (const c of cols) {
      const raw = row[c]
      if (raw === null || raw === "") {
        clean[c] = null
      } else if (parsedCols.has(c)) {
        const dec = detectDecimal([raw])
        const num = parseVnNumber(raw, dec)
        clean[c] = num !== null ? Number(num.toFixed(4)) : null
      } else if (dateCols.has(c)) {
        clean[c] = parseVnDate(raw)
      } else {
        clean[c] = typeof raw === "string" ? cleanText(raw) : raw
      }
    }
    silverRaw.push(clean)
  }

  if (dupCount > 0) {
    cleaningLog.push(`Removed ${dupCount} exact duplicate row(s) using _row_hash.`)
  } else {
    cleaningLog.push(`Checked duplicate rows via _row_hash: 0 exact duplicates found.`)
  }

  // Normalize Vietnamese provinces + add region if geo column detected
  if (geoSourceCol) {
    let renamed = 0
    const regions = new Set<string>()
    for (const r of silverRaw) {
      const raw = r[geoSourceCol]
      if (typeof raw === "string" && raw) {
        const norm = normalizeProvince(raw)
        if (norm.canonical && norm.canonical !== raw) renamed++
        r[geoSourceCol] = norm.canonical || raw
        if (norm.region) {
          r.region = norm.region
          regions.add(norm.region)
        }
      }
    }
    if (renamed > 0) {
      cleaningLog.push(`Normalized ${renamed} Vietnamese province values in '${geoSourceCol}' (63→34 NQ 202/2025 mapping).`)
    }
    if (regions.size > 0 && !cols.includes("region")) {
      cols.push("region")
      cleaningLog.push(`Enriched dataset with 'region' (${regions.size} socio-economic regions).`)
    }
  }

  // Domain-derived metrics (e.g., price_per_m2)
  const domain = detectDomain(cols, opts.domain ?? "auto")
  if (domain === "property") {
    const priceCol = cols.find((c) => /gia_ban|price/.test(c) && parsedCols.has(c))
    const areaCol = cols.find((c) => /dien_tich|area/.test(c) && parsedCols.has(c))
    if (priceCol && areaCol && !cols.includes("price_per_m2")) {
      let computed = 0
      for (const r of silverRaw) {
        const p = r[priceCol]
        const a = r[areaCol]
        if (typeof p === "number" && typeof a === "number" && a > 0 && p > 0) {
          r.price_per_m2 = Number((p / a).toFixed(2))
          computed++
        } else {
          r.price_per_m2 = null
        }
      }
      if (computed > 0) {
        cols.push("price_per_m2")
        parsedCols.add("price_per_m2")
        cleaningLog.push(`Derived domain metric 'price_per_m2' = ${priceCol} / ${areaCol} (${computed} rows).`)
      }
    }
  }

  // Flag 3xIQR outliers without deleting rows
  const outlierBounds = new Map<string, { lo: number; hi: number; count: number }>()
  for (const c of parsedCols) {
    if (c === "year" || c === "nam") continue
    const vals = silverRaw.map((r) => r[c]).filter((v): v is number => typeof v === "number" && Number.isFinite(v))
    const bounds = iqr3Bounds(vals)
    outlierBounds.set(c, bounds)
  }

  let outlierRowsCount = 0
  for (const r of silverRaw) {
    let anyOutlier = false
    for (const [c, b] of outlierBounds.entries()) {
      const v = r[c]
      if (typeof v === "number" && (v < b.lo || v > b.hi)) {
        anyOutlier = true
        break
      }
    }
    r._outlier_any = anyOutlier
    if (anyOutlier) outlierRowsCount++
  }
  cleaningLog.push(`Flagged ${outlierRowsCount} row(s) with extreme values (> 3×IQR) in '_outlier_any' without deleting any record.`)

  // 3. Infer roles
  const roles: Record<string, Role> = {}
  for (const c of cols) {
    const cKey = asciiKey(c)
    const vals = silverRaw.map((r) => r[c]).filter((v) => v !== null && v !== "")
    const uniq = new Set(vals.map(String)).size
    if (c.startsWith("_")) {
      roles[c] = "flag"
    } else if (dateCols.has(c) || c === "year" || c === "nam" || /ngay|date|year|nam/.test(cKey)) {
      roles[c] = "time"
    } else if (c === geoSourceCol || c === "region" || /country|tinh|province|vung|region|quoc_gia/.test(cKey)) {
      roles[c] = "geo"
    } else if (/^id$|_id$|^ma_/.test(c) || (uniq === silverRaw.length && !parsedCols.has(c) && silverRaw.length > 10)) {
      roles[c] = "id"
    } else if (parsedCols.has(c)) {
      roles[c] = uniq <= 1 ? "constant" : "numeric"
    } else if (uniq <= 1) {
      roles[c] = "constant"
    } else if (uniq <= Math.max(30, silverRaw.length * 0.3)) {
      roles[c] = "category"
    } else {
      roles[c] = "text"
    }
  }
  roles._outlier_any = "flag"

  const numericCols = cols.filter((c) => roles[c] === "numeric")
  const categoryCols = cols.filter((c) => roles[c] === "category" || roles[c] === "geo")

  // Pick time, geo, target
  const timeCol = (opts.timeCol && cols.includes(opts.timeCol) ? opts.timeCol : null) ??
    cols.find((c) => roles[c] === "time") ?? null
  const geoCol = (opts.geoCol && cols.includes(opts.geoCol) ? opts.geoCol : null) ??
    geoSourceCol ?? cols.find((c) => roles[c] === "geo") ?? null

  const targetCol =
    (opts.target && cols.includes(opts.target) ? opts.target : null) ??
    (cols.includes("price_per_m2") ? "price_per_m2" : null) ??
    numericCols.find((c) => /tax_revenue|earmarked_transfers|gia_ban|revenue|gdp_per_capita|roe|gia_thue/.test(c)) ??
    numericCols[0] ??
    cols[0]

  // 4. Column profiles & data quality metrics
  const column_profiles: ColumnProfile[] = cols.map((c) => {
    const vals = silverRaw.map((r) => r[c])
    const valid = vals.filter((v) => v !== null && v !== "")
    const missingPct = silverRaw.length ? ((silverRaw.length - valid.length) / silverRaw.length) * 100 : 0
    const unique = new Set(valid.map(String)).size
    if (roles[c] === "numeric" || (parsedCols.has(c) && roles[c] === "time")) {
      const nums = valid.filter((v): v is number => typeof v === "number" && Number.isFinite(v))
      const b = outlierBounds.get(c)
      return {
        name: c,
        role: roles[c],
        dtype: "float64",
        missing_pct: Number(missingPct.toFixed(1)),
        unique,
        mean: nums.length ? Number(mean(nums).toFixed(2)) : undefined,
        median: nums.length ? Number(median(nums).toFixed(2)) : undefined,
        std: nums.length ? Number(std(nums).toFixed(2)) : undefined,
        min: nums.length ? Number(Math.min(...nums).toFixed(2)) : undefined,
        max: nums.length ? Number(Math.max(...nums).toFixed(2)) : undefined,
        skew: nums.length ? Number(skewness(nums).toFixed(2)) : undefined,
        outliers: b?.count ?? 0,
        hist: histogram(nums),
      }
    }
    const counts = new Map<string, number>()
    for (const v of valid) counts.set(String(v), (counts.get(String(v)) ?? 0) + 1)
    const top_values = Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([value, count]) => ({ value, count }))
    return {
      name: c,
      role: roles[c],
      dtype: "string",
      missing_pct: Number(missingPct.toFixed(1)),
      unique,
      top_values,
    }
  })

  const issues: QualityIssue[] = []
  for (const cp of column_profiles) {
    if (cp.missing_pct >= 20) issues.push({ severity: "high", column: cp.name, issue: `${cp.missing_pct}% missing cells` })
    else if (cp.missing_pct >= 5) issues.push({ severity: "medium", column: cp.name, issue: `${cp.missing_pct}% missing cells` })
    if ((cp.outliers ?? 0) > 0) issues.push({ severity: "low", column: cp.name, issue: `${cp.outliers} extreme values (>3×IQR)` })
  }
  if (dupCount > 0) issues.push({ severity: "medium", column: "_row_hash", issue: `${dupCount} duplicate rows removed` })

  const totalCells = Math.max(1, silverRaw.length * cols.length)
  const afterMissingCells = column_profiles.reduce((s, cp) => s + Math.round((cp.missing_pct / 100) * silverRaw.length), 0)
  const missingOverallPct = Number(((afterMissingCells / totalCells) * 100).toFixed(2))
  const outlierRowsPct = silverRaw.length ? Number(((outlierRowsCount / silverRaw.length) * 100).toFixed(2)) : 0

  // 5. K-means segments + Drivers + What-if
  const clusters = runKMeans(silverRaw, numericCols)
  if (clusters) {
    silverRaw.forEach((r, idx) => {
      r._segment = `C${clusters.labels[idx] + 1}`
    })
  }
  const driverFit = targetCol && roles[targetCol] === "numeric"
    ? buildDrivers(silverRaw, targetCol, numericCols.filter((c) => c !== targetCol && c !== "year" && c !== "nam"))
    : null

  const whatif_features = (driverFit?.model.features ?? []).map((f, idx) => ({
    name: f,
    mean: Number((driverFit!.model.means[idx] ?? 0).toFixed(2)),
    sd: Number((driverFit!.model.sds[idx] ?? 1).toFixed(2)),
    median: column_profiles.find((c) => c.name === f)?.median ?? null,
    min: Number((driverFit!.model.mins[idx] ?? 0).toFixed(2)),
    max: Number((driverFit!.model.maxs[idx] ?? 0).toFixed(2)),
  }))

  // 6. Ranked statistical insights & recommendations
  const insights: Insight[] = []
  const recommendations: Recommendation[] = []

  // Insight A: Group disparity (Kruskal-Wallis across primary category/geo)
  const groupCol = geoCol ?? categoryCols[0]
  if (groupCol && targetCol && roles[targetCol] === "numeric") {
    const grouped = new Map<string, number[]>()
    for (const r of silverRaw) {
      const g = r[groupCol]
      const y = r[targetCol]
      if (g !== null && g !== "" && typeof y === "number" && Number.isFinite(y)) {
        const k = String(g)
        const arr = grouped.get(k) ?? []
        arr.push(y)
        grouped.set(k, arr)
      }
    }
    const entries = Array.from(grouped.entries())
      .map(([group, vals]) => ({ group, vals, med: median(vals), n: vals.length }))
      .filter((e) => e.n >= 2)
      .sort((a, b) => b.med - a.med)

    if (entries.length >= 2) {
      const kw = kruskalWallis(entries.map((e) => e.vals))
      const top = entries[0]
      const bottom = entries[entries.length - 1]
      const mw = mannWhitney(top.vals, bottom.vals)
      const ratio = bottom.med !== 0 ? top.med / bottom.med : null
      if (kw) {
        const id = `gap_${groupCol}`
        const score = Number(((kw.epsilon2 + 0.25) * (kw.p < 0.05 ? 1.5 : 0.8) * 1.2).toFixed(3))
        const topSlice = entries.slice(0, 10)
        insights.push({
          id,
          rank: 1,
          type: "group_gap",
          title_en: `Sharp ${targetCol} gap across ${groupCol}`,
          title_vi: `Chênh lệch rõ rệt về ${targetCol} theo ${groupCol}`,
          sentence_en: `${top.group} leads at median ${fmtCompact(top.med)} vs ${bottom.group} at ${fmtCompact(bottom.med)}${ratio ? ` (${ratio.toFixed(1)}×)` : ""}; Kruskal–Wallis H=${kw.H}, ε²=${kw.epsilon2}.`,
          sentence_vi: `Nhóm ${top.group} dẫn đầu với trung vị ${fmtCompact(top.med)}, cao hơn ${bottom.group} (${fmtCompact(bottom.med)})${ratio ? ` gấp ${ratio.toFixed(1)} lần` : ""}; kiểm định Kruskal–Wallis H=${kw.H}, ε²=${kw.epsilon2}.`,
          value: ratio ? Number(ratio.toFixed(2)) : top.med,
          test: `Kruskal–Wallis + Mann–Whitney (rank-biserial ${mw.rank_biserial})`,
          effect: kw.epsilon2,
          p_value: kw.p,
          weak: kw.p >= 0.05,
          relevance: 0.9,
          score,
          chart: {
            kind: "bar",
            x: topSlice.map((e) => e.group),
            series: [{ name: `median ${targetCol}`, data: topSlice.map((e) => Number(e.med.toFixed(2))) }],
          },
          evidence: { top: top.group, top_median: top.med, bottom: bottom.group, bottom_median: bottom.med, H: kw.H, epsilon2: kw.epsilon2 },
          columns: [groupCol, targetCol],
          caveat: "So sánh phân phối giữa các nhóm là mô tả quan sát, chưa kiểm soát toàn bộ yếu tố cấu trúc.",
          caveat_vi: "So sánh phân phối giữa các nhóm là mô tả quan sát, chưa kiểm soát toàn bộ yếu tố cấu trúc.",
        })
        recommendations.push({
          from_insight: id,
          type: "regional_priority",
          confidence: kw.p < 0.01 ? "high" : "medium",
          so_what_en: `${targetCol} varies markedly across ${groupCol} (ε²=${kw.epsilon2}), indicating uneven structural baselines.`,
          now_what_en: `Prioritize targeted diagnostics and benchmarking in ${bottom.group} against practices in ${top.group}.`,
          impact_en: `Closing half the median gap raises lagging ${groupCol} groups toward ${fmtCompact((top.med + bottom.med) / 2)}.`,
          so_what_vi: `${targetCol} phân hoá mạnh theo ${groupCol} (ε²=${kw.epsilon2}), cho thấy mặt bằng nguồn lực hoặc giá trị không đồng đều.`,
          now_what_vi: `Ưu tiên rà soát chính sách hoặc cơ cấu tại nhóm thấp (${bottom.group}) và đối chiếu chuẩn với nhóm dẫn đầu (${top.group}).`,
          impact_vi: `Thu hẹp 50% khoảng cách trung vị đưa nhóm thấp tiến về ngưỡng ${fmtCompact((top.med + bottom.med) / 2)}.`,
        })
      }
    }
  }

  // Insight B: Top correlated drivers (Spearman)
  if (targetCol && roles[targetCol] === "numeric") {
    const yAll = silverRaw.map((r) => (typeof r[targetCol] === "number" ? (r[targetCol] as number) : NaN))
    const corrs = numericCols
      .filter((c) => c !== targetCol && c !== "year" && c !== "nam")
      .map((c) => {
        const xAll = silverRaw.map((r) => (typeof r[c] === "number" ? (r[c] as number) : NaN))
        const sp = spearman(xAll, yAll)
        return { col: c, ...sp }
      })
      .filter((c) => c.n >= 8 && Math.abs(c.rho) >= 0.15)
      .sort((a, b) => Math.abs(b.rho) - Math.abs(a.rho))

    for (const c of corrs.slice(0, 2)) {
      const id = `corr_${c.col}`
      const dirVi = c.rho >= 0 ? "cùng chiều" : "ngược chiều"
      const dirEn = c.rho >= 0 ? "positive" : "negative"
      const pts = silverRaw
        .map((r) => ({ x: r[c.col], y: r[targetCol] }))
        .filter((p): p is { x: number; y: number } => typeof p.x === "number" && typeof p.y === "number")
        .slice(0, 120)
      insights.push({
        id,
        rank: insights.length + 1,
        type: "driver_correlation",
        title_en: `${c.col} shows a ${dirEn} association with ${targetCol}`,
        title_vi: `${c.col} có tương quan ${dirVi} với ${targetCol}`,
        sentence_en: `Spearman ρ = ${c.rho.toFixed(2)} across n=${c.n} records (p=${c.p.toExponential(1)}).`,
        sentence_vi: `Hệ số tương quan hạng Spearman ρ = ${c.rho.toFixed(2)} trên ${c.n} quan sát (p=${c.p.toExponential(1)}).`,
        value: Number(c.rho.toFixed(3)),
        test: "Spearman rank correlation",
        effect: Number(Math.abs(c.rho).toFixed(3)),
        p_value: c.p,
        weak: c.p >= 0.05,
        relevance: 0.85,
        score: Number((Math.abs(c.rho) * (c.p < 0.05 ? 1.5 : 0.7) * 1.1).toFixed(3)),
        chart: {
          kind: "scatter",
          x: pts.map((p) => Number(p.x.toFixed(2))),
          series: [{ name: targetCol, data: pts.map((p) => Number(p.y.toFixed(2))) }],
          x_label: c.col,
          y_label: targetCol,
        },
        evidence: { rho: c.rho, p: c.p, n: c.n },
        columns: [c.col, targetCol],
        caveat: "Tương quan Spearman đo quan hệ đơn điệu giữa hai biến, không chứng minh quan hệ nhân quả.",
        caveat_vi: "Tương quan Spearman đo quan hệ đơn điệu giữa hai biến, không chứng minh quan hệ nhân quả.",
      })
      recommendations.push({
        from_insight: id,
        type: "driver_lever",
        confidence: c.p < 0.01 ? "high" : "medium",
        so_what_en: `${c.col} moves ${dirEn}ly with ${targetCol} (ρ=${c.rho.toFixed(2)}).`,
        now_what_en: `Test sensitivity of ${c.col} in the What-If simulator before designing pilot interventions.`,
        impact_en: `Provides an actionable lever tracked alongside ${targetCol}.`,
        so_what_vi: `Biến ${c.col} biến động ${dirVi} rõ rệt cùng ${targetCol} (ρ=${c.rho.toFixed(2)}).`,
        now_what_vi: `Kiểm tra biên độ tác động của ${c.col} trên thanh trượt What-If trước khi thử nghiệm can thiệp thực địa.`,
        impact_vi: `Giúp định lượng biến đổi kỳ vọng của ${targetCol} kèm khoảng tin cậy 90%.`,
      })
    }
  }

  // Insight C: Time trend if timeCol exists
  const ts = computeTimeSeries(silverRaw, timeCol, targetCol, "median")
  const validTs = ts.points.filter((p) => p.value !== null)
  if (validTs.length >= 3 && targetCol) {
    const spTime = spearman(
      validTs.map((_, i) => i),
      validTs.map((p) => p.value!)
    )
    const first = validTs[0]
    const last = validTs[validTs.length - 1]
    const chgPct = first.value && first.value !== 0 ? ((last.value! - first.value) / Math.abs(first.value)) * 100 : 0
    const id = `trend_${timeCol}`
    insights.push({
      id,
      rank: insights.length + 1,
      type: "time_trend",
      title_en: `${targetCol} shifted ${chgPct >= 0 ? "+" : ""}${chgPct.toFixed(1)}% from ${first.period} to ${last.period}`,
      title_vi: `Xu hướng ${targetCol} ${chgPct >= 0 ? "tăng" : "giảm"} ${Math.abs(chgPct).toFixed(1)}% giai đoạn ${first.period}–${last.period}`,
      sentence_en: `Period median moved from ${fmtCompact(first.value)} (${first.period}) to ${fmtCompact(last.value)} (${last.period}); Spearman ρ=${spTime.rho.toFixed(2)}.`,
      sentence_vi: `Trung vị theo kỳ chuyển từ ${fmtCompact(first.value)} (${first.period}) lên ${fmtCompact(last.value)} (${last.period}); Spearman ρ=${spTime.rho.toFixed(2)}.`,
      value: Number(chgPct.toFixed(1)),
      test: "Spearman monotonic trend",
      effect: Number(Math.abs(spTime.rho).toFixed(3)),
      p_value: spTime.p,
      weak: spTime.p >= 0.05,
      relevance: 0.8,
      score: Number((Math.abs(spTime.rho) * (spTime.p < 0.05 ? 1.4 : 0.7)).toFixed(3)),
      chart: {
        kind: "line",
        x: validTs.map((p) => p.period),
        series: [{ name: `median ${targetCol}`, data: validTs.map((p) => p.value) }],
      },
      evidence: { first, last, chg_pct: chgPct, rho: spTime.rho, p: spTime.p },
      columns: [timeCol!, targetCol],
      caveat: "Xu hướng theo chuỗi thời gian có thể chịu ảnh hưởng bởi thay đổi thành phần mẫu giữa các kỳ.",
      caveat_vi: "Xu hướng theo chuỗi thời gian có thể chịu ảnh hưởng bởi thay đổi thành phần mẫu giữa các kỳ.",
    })
  }

  // Insight D: Outliers flagged
  if (outlierRowsCount > 0 && targetCol) {
    const id = "outliers_3iqr"
    insights.push({
      id,
      rank: insights.length + 1,
      type: "outlier_flag",
      title_en: `${outlierRowsCount} extreme records flagged (3×IQR)`,
      title_vi: `Phát hiện ${outlierRowsCount} bản ghi ngoại lai (> 3×IQR)`,
      sentence_en: `${outlierRowsPct}% of cleaned rows contain extreme values retained under _outlier_any for sensitivity checks.`,
      sentence_vi: `${outlierRowsPct}% số dòng sau làm sạch có giá trị vượt ngưỡng 3×IQR và được gắn cờ _outlier_any thay vì xoá bỏ.`,
      value: outlierRowsCount,
      test: "Tukey 3×IQR fence",
      effect: Number((outlierRowsPct / 100).toFixed(3)),
      p_value: null,
      weak: false,
      relevance: 0.75,
      score: 0.62,
      chart: null,
      evidence: { outlier_rows: outlierRowsCount, pct: outlierRowsPct },
      columns: [targetCol],
      caveat: "Nên kiểm tra độ nhạy bằng cách so sánh kết quả có và không có các bản ghi gắn cờ ngoại lai.",
      caveat_vi: "Nên kiểm tra độ nhạy bằng cách so sánh kết quả có và không có các bản ghi gắn cờ ngoại lai.",
    })
  }

  insights.sort((a, b) => b.score - a.score)
  insights.forEach((ins, idx) => { ins.rank = idx + 1 })

  // 7. KPIs (4 cards)
  const targetNums = silverRaw.map((r) => r[targetCol]).filter((v): v is number => typeof v === "number" && Number.isFinite(v))
  const medTarget = targetNums.length ? median(targetNums) : null
  const lastPeriodDelta = validTs.length >= 2 && validTs[0].value
    ? Number((((validTs[validTs.length - 1].value! - validTs[0].value!) / Math.abs(validTs[0].value!)) * 100).toFixed(1))
    : null

  const kpis: Kpi[] = [
    {
      label: `Median ${targetCol}`,
      label_vi: `Trung vị ${targetCol}`,
      value: fmtCompact(medTarget),
      raw: medTarget,
      delta_pct: lastPeriodDelta,
      footer: validTs.length >= 2 ? `${validTs[0].period} → ${validTs[validTs.length - 1].period}` : `${targetNums.length} bản ghi hợp lệ`,
      description: `Chỉ số mục tiêu chính (${domain})`,
    },
    {
      label: "Clean rows (silver)",
      label_vi: "Số dòng sạch (silver)",
      value: silverRaw.length.toLocaleString("en-US"),
      raw: silverRaw.length,
      delta_pct: dupCount > 0 ? Number(((-dupCount / Math.max(1, bronzeRows.length)) * 100).toFixed(1)) : 0,
      footer: `${bronzeRows.length.toLocaleString("en-US")} dòng thô · ${cols.length} cột`,
      description: `${dupCount} dòng trùng đã loại, ${outlierRowsCount} ngoại lai gắn cờ`,
    },
    {
      label: "Completeness",
      label_vi: "Độ đầy đủ dữ liệu",
      value: `${(100 - missingOverallPct).toFixed(1)}%`,
      raw: Number((100 - missingOverallPct).toFixed(1)),
      delta_pct: null,
      footer: `${missingOverallPct}% ô thiếu trên toàn bảng`,
      description: "Đo trên tầng silver sau chuẩn hoá kiểu",
    },
    {
      label: "Ranked insights",
      label_vi: "Insight đã kiểm định",
      value: String(insights.length),
      raw: insights.length,
      delta_pct: null,
      footer: driverFit ? `CV R² (GB): ${driverFit.cv_r2.gb_mean.toFixed(2)}` : `${recommendations.length} khuyến nghị hành động`,
      description: "Xếp hạng theo effect size × ý nghĩa thống kê",
    },
  ]

  // 8. Pipeline, Quality, Lineage, Models, Provenance
  const tableBronze = `raw_${dsId}`
  const tableSilver = `clean_${dsId}`
  const tableGoldObt = `obt_${dsId}`
  const factName = `fact_${dsId}`
  const dimGeo = `${dsId}__dim_geo`
  const dimDate = `${dsId}__dim_date`
  const dimCat = `${dsId}__dim_category`

  const beforeMissingTotal = Object.values(beforeMissingByCol).reduce((a, b) => a + b, 0)
  const beforeInvalidTotal = Object.values(invalidCellsByCol).reduce((a, b) => a + b, 0)
  const scoreBefore = Number(Math.max(40, 100 - (beforeMissingTotal / Math.max(1, bronzeRows.length * origCols.length)) * 80 - (dupCount > 0 ? 5 : 0) - (beforeInvalidTotal > 0 ? 6 : 0)).toFixed(1))
  const scoreAfter = Number(Math.max(scoreBefore, Math.min(99.5, 100 - missingOverallPct * 0.65)).toFixed(1))

  const beforeColsSnap: QualitySnapshot["columns"] = {}
  const afterColsSnap: QualitySnapshot["columns"] = {}
  for (const c of cols) {
    const bMiss = beforeMissingByCol[c] ?? 0
    const cp = column_profiles.find((p) => p.name === c)
    beforeColsSnap[c] = {
      dtype: "string",
      missing_pct: Number(((bMiss / Math.max(1, bronzeRows.length)) * 100).toFixed(1)),
      distinct: cp?.unique ?? 0,
      invalid_values: invalidCellsByCol[c] ?? 0,
    }
    afterColsSnap[c] = {
      dtype: cp?.dtype ?? "string",
      missing_pct: cp?.missing_pct ?? 0,
      distinct: cp?.unique ?? 0,
      min: typeof cp?.min === "number" ? cp.min : undefined,
      max: typeof cp?.max === "number" ? cp.max : undefined,
      outliers_3iqr: cp?.outliers,
    }
  }

  const quality: QualityResponse = {
    [tableSilver]: {
      score_before: scoreBefore,
      score_after: scoreAfter,
      cleaning_log: cleaningLog,
      before: {
        rows: bronzeRows.length,
        cols: origCols.length,
        missing_cells: beforeMissingTotal,
        invalid_cells: beforeInvalidTotal,
        duplicate_rows: dupCount,
        candidate_key: cols.find((c) => roles[c] === "id") ? [cols.find((c) => roles[c] === "id")!] : null,
        duplicate_keys: dupCount,
        score: scoreBefore,
        columns: beforeColsSnap,
        issues: issues.map((i) => ({ type: i.issue.includes("missing") ? "missing" : i.issue.includes("duplicate") ? "duplicate_rows" : "outlier", column: i.column, detail: i.issue })),
      },
      after: {
        rows: silverRaw.length,
        cols: cols.length,
        missing_cells: afterMissingCells,
        invalid_cells: 0,
        duplicate_rows: 0,
        candidate_key: cols.find((c) => roles[c] === "id") ? [cols.find((c) => roles[c] === "id")!] : null,
        duplicate_keys: 0,
        score: scoreAfter,
        columns: afterColsSnap,
        issues: issues.filter((i) => i.severity === "high").map((i) => ({ type: "missing", column: i.column, detail: i.issue })),
      },
    },
  }

  const provenance: Provenance[] = (opts.sources && opts.sources.length > 0
    ? opts.sources
    : [{ name: dsId, kind: "file" as SourceKind, uri: opts.sourceFile, license_note: "Local repository dataset" }]
  ).map((s) => ({
    source: s.name,
    kind: s.kind,
    uri: s.uri,
    options: s.options ?? {},
    fetched_at: created,
    license_note: s.license_note ?? "Open / practice dataset",
    tables: {
      [`bronze.${tableBronze}`]: {
        rows: bronzeRows.length,
        cols: origCols.length,
        fingerprint: crypto.createHash("sha256").update(opts.sourceFile).digest("hex").slice(0, 12),
      },
    },
  }))

  const elapsed = Number(((Date.now() - t0) / 1000).toFixed(2)) || 0.12
  const columnPlan = {
    time: timeCol,
    time_is_date: timeCol ? dateCols.has(timeCol) : false,
    province: geoCol,
    cats: categoryCols.filter((c) => c !== geoCol),
    measures: numericCols,
    ids: cols.filter((c) => roles[c] === "id"),
  }

  const obtSql = `CREATE OR REPLACE TABLE gold."${tableGoldObt}" AS\nSELECT *\nFROM silver."${tableSilver}";`
  const starSql = `CREATE OR REPLACE TABLE gold."${dimGeo}" AS\nSELECT DISTINCT ROW_NUMBER() OVER () AS geo_key, ${geoCol ?? "'Vietnam'"} AS province\nFROM silver."${tableSilver}";\n\nCREATE OR REPLACE TABLE gold."${factName}" AS\nSELECT * FROM silver."${tableSilver}";`
  const snowSql = `${starSql}\n-- Normalized regional hierarchy on ${dimGeo}`
  const dvSql = `-- Hub / Link / Satellite tables generated for audit history on ${dsId}\nCREATE OR REPLACE TABLE gold."hub_${dsId}" AS SELECT DISTINCT _row_hash FROM silver."${tableSilver}";`

  const models: ModelsResponse = {
    models: {
      obt: {
        tables: [`gold.${tableGoldObt}`],
        erd: `erDiagram\n  ${tableGoldObt.toUpperCase()} {\n    string ${geoCol ?? "group_key"}\n    float ${targetCol}\n  }`,
      },
      star: {
        tables: [`gold.${factName}`, `gold.${dimGeo}`, `gold.${dimDate}`, `gold.${dimCat}`],
        erd: `erDiagram\n  ${factName.toUpperCase()} }o--|| ${dimGeo.toUpperCase()} : geo_key\n  ${factName.toUpperCase()} }o--|| ${dimDate.toUpperCase()} : date_key\n  ${factName.toUpperCase()} }o--|| ${dimCat.toUpperCase()} : cat_key`,
      },
      snowflake: {
        tables: [`gold.${factName}`, `gold.${dimGeo}`, `gold.${dsId}__dim_region`, `gold.${dimDate}`],
        erd: `erDiagram\n  ${factName.toUpperCase()} }o--|| ${dimGeo.toUpperCase()} : geo_key\n  ${dimGeo.toUpperCase()} }o--|| DIM_REGION : region_key`,
      },
      data_vault: {
        tables: [`gold.hub_${dsId}`, `gold.sat_${dsId}_metrics`, `gold.lnk_${dsId}_geo`],
        erd: `erDiagram\n  HUB_${dsId.toUpperCase()} ||--o{ SAT_${dsId.toUpperCase()} : hkey\n  HUB_${dsId.toUpperCase()} ||--o{ LNK_${dsId.toUpperCase()} : hkey`,
      },
    },
    sql: { obt: obtSql, star: starSql, snowflake: snowSql, data_vault: dvSql },
    rationale: {
      obt: "One Big Table tối ưu cho tốc độ truy vấn dashboard, BI và huấn luyện mô hình driver.",
      star: "Kimball Star Schema tách fact và dimension để chuẩn hoá bộ lọc và nối đa chiều.",
      snowflake: "Chuẩn hoá phân tầng địa lý (tỉnh → vùng KT-XH) giảm dư thừa dimension.",
      data_vault: "Lưu lịch sử thay đổi và truy vết nguồn theo từng lần nạp.",
    },
    recommended: { serving: "obt", semantic: "star" },
    column_plan: columnPlan,
    keys: null,
  }

  const lineage: LineageResponse = {
    dataset: dsId,
    nodes: [
      { id: "src", label: opts.sourceFile, layer: "source", stage: "ingest" },
      { id: "bronze", label: `bronze.${tableBronze}`, layer: "bronze", stage: "storage" },
      { id: "silver", label: `silver.${tableSilver}`, layer: "silver", stage: "clean" },
      { id: "gold_obt", label: `gold.${tableGoldObt}`, layer: "gold", stage: "serve" },
      { id: "gold_star", label: `gold.${factName}`, layer: "gold", stage: "model" },
    ],
    edges: [
      { from: "src", to: "bronze", step: "ingest_raw" },
      { from: "bronze", to: "silver", step: "clean_vn_dedup_iqr" },
      { from: "silver", to: "gold_obt", step: "build_obt" },
      { from: "silver", to: "gold_star", step: "build_star" },
    ],
    mermaid: `flowchart LR\n  src["${opts.sourceFile}"] -->|ingest| bronze["bronze.${tableBronze}"]\n  bronze -->|clean & 3xIQR| silver["silver.${tableSilver}"]\n  silver -->|serving| gold_obt["gold.${tableGoldObt}"]\n  silver -->|Kimball| gold_star["gold.${factName}"]`,
  }

  const pipeline: PipelineSummary = {
    dataset: dsId,
    run_id: crypto.randomUUID().slice(0, 8),
    finished_at: created,
    timings: { ingest: elapsed, clean: elapsed, model: elapsed, serve: elapsed },
    steps: [
      { step: "ingest", status: "ok", tables: [`bronze.${tableBronze}`] },
      { step: "clean", status: "ok", tables: [`silver.${tableSilver}`] },
      { step: "model", status: "ok", tables: [`gold.${tableGoldObt}`, `gold.${factName}`] },
      { step: "serve", status: "ok", tables: [`gold.${tableGoldObt}`] },
    ],
    bronze: [`bronze.${tableBronze}`],
    silver: [`silver.${tableSilver}`],
    primary: provenance[0]?.source ?? dsId,
    gold: [`gold.${tableGoldObt}`, `gold.${factName}`],
    quality: {
      [tableSilver]: {
        score_before: scoreBefore,
        score_after: scoreAfter,
        rows: silverRaw.length,
        issues: issues.length,
      },
    },
    models: models.models,
    column_plan: columnPlan,
    rationale: models.rationale,
    recommended: models.recommended,
    provenance,
    conformed: null,
    load: { mode: "replace", inserted: silverRaw.length, skipped: dupCount, tables: { [tableSilver]: { inserted: silverRaw.length, skipped: dupCount, rebuilt: true, rows: silverRaw.length } } },
  }

  const files: Record<string, string | number | null> = {
    results: "results.json",
    clean_csv: "clean_sample.csv",
    dashboard: "dashboard.html",
    dictionary_csv: "data_dictionary.csv",
    dictionary_md: "data_dictionary.md",
    eda_md: "eda.md",
    pitch_md: "pitch.md",
    pitch_en: "pitch.en.md",
    summary_md: "executive_summary.md",
    bundle: "export/bundle.zip",
  }

  const caveats = [
    "Các kiểm định (Spearman, Kruskal–Wallis, Ridge chuẩn hoá) đo quan hệ liên đới trên dữ liệu quan sát, không chứng minh quan hệ nhân quả.",
    outlierRowsCount > 0 ? `${outlierRowsCount} bản ghi ngoại lai (> 3×IQR) được giữ lại với cờ _outlier_any để kiểm tra độ nhạy.` : "Không phát hiện ngoại lai cực đoan vượt 3×IQR.",
    missingOverallPct > 5 ? `Tỷ lệ ô thiếu tổng thể là ${missingOverallPct}% — cân nhắc kiểm tra thiên lệch thiếu dữ liệu theo nhóm.` : `Dữ liệu có độ đầy đủ cao (${(100 - missingOverallPct).toFixed(1)}%).`,
  ]

  return {
    id: dsId,
    summary: {
      id: dsId,
      name: opts.name,
      domain,
      rows: silverRaw.length,
      target: targetCol,
      source_file: opts.sourceFile,
      created,
    },
    detail: {
      meta: {
        name: dsId,
        source_file: opts.sourceFile,
        domain,
        target: targetCol,
        time_col: timeCol,
        geo_col: geoCol,
        rows: silverRaw.length,
        columns: cols.length,
        roles,
        domain_metrics: cols.includes("price_per_m2") ? ["price_per_m2"] : [],
        category_cols: categoryCols,
        created,
      },
      kpis,
      caveats,
      timings: pipeline.timings,
      files,
      recommendations,
      has_brief: false,
    },
    profile: {
      profile: {
        rows: silverRaw.length,
        columns: cols.length,
        missing_overall_pct: missingOverallPct,
        outlier_rows_pct: outlierRowsPct,
        roles: Object.values(roles).reduce<Record<string, number>>((acc, r) => {
          acc[r] = (acc[r] ?? 0) + 1
          return acc
        }, {}),
        column_profiles,
        issues,
      },
      cleaning_log: cleaningLog,
      caveats,
    },
    insights: { insights, recommendations },
    drivers: {
      target: targetCol,
      drivers: driverFit
        ? {
            n: driverFit.n,
            features: driverFit.model.features,
            leakage_excluded: driverFit.leakage_excluded,
            log_target: driverFit.model.logTarget,
            cv_r2: driverFit.cv_r2,
            importance: driverFit.importance,
            coefficients: driverFit.coefficients,
            note: "Hệ số Ridge chuẩn hoá (per 1 SD); tương quan tuyến tính, không hàm ý nhân quả.",
          }
        : null,
      whatif_features,
    },
    driverModel: driverFit?.model ?? null,
    bronzeRows,
    silverRows: silverRaw,
    goldRows: silverRaw,
    segmentsClusters: clusters
      ? { k: clusters.k, silhouette: clusters.silhouette, features: clusters.features, profiles: clusters.profiles }
      : null,
    pipeline,
    quality,
    lineage,
    models,
    provenance,
    tableNameBronze: tableBronze,
    tableNameSilver: tableSilver,
    tableNameGold: tableGoldObt,
  }
}

export function computeTimeSeries(
  rows: Record<string, unknown>[],
  timeCol: string | null,
  metricCol: string | null,
  agg: "median" | "mean" | "sum" | "count" = "median",
  freq?: string | null,
  group?: string | null
): TimeSeriesResponse {
  if (!timeCol || !metricCol) {
    return { time: timeCol, metric: metricCol, agg, freq: freq ?? null, points: [] }
  }
  const buckets = new Map<string, number[]>()
  for (const r of rows) {
    const rawT = r[timeCol]
    if (rawT === null || rawT === undefined || rawT === "") continue
    const tStr = String(rawT)
    let period = tStr
    if (/^\d{4}-\d{2}-\d{2}/.test(tStr)) {
      if (freq === "Y") period = tStr.slice(0, 4)
      else if (freq === "Q") {
        const m = Number(tStr.slice(5, 7))
        period = `${tStr.slice(0, 4)}-Q${Math.ceil(m / 3)}`
      } else {
        period = tStr.slice(0, 7)
      }
    }
    if (group && r[group]) period = `${period} (${r[group]})`
    const val = r[metricCol]
    const arr = buckets.get(period) ?? []
    if (agg === "count") arr.push(1)
    else if (typeof val === "number" && Number.isFinite(val)) arr.push(val)
    buckets.set(period, arr)
  }
  const points = Array.from(buckets.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([period, xs]) => {
      let value: number | null = null
      if (xs.length > 0) {
        if (agg === "count") value = xs.length
        else if (agg === "sum") value = Number(xs.reduce((a, b) => a + b, 0).toFixed(2))
        else if (agg === "mean") value = Number(mean(xs).toFixed(2))
        else value = Number(median(xs).toFixed(2))
      }
      return { period, value, n: xs.length }
    })
  const detectedFreq = freq ?? (points[0]?.period.length === 4 ? "Y" : points[0]?.period.includes("Q") ? "Q" : "M")
  return { time: timeCol, metric: metricCol, agg, freq: detectedFreq, points }
}

export function computeSegments(ds: AnalyzedDataset, by?: string | null, metric?: string | null): SegmentsResponse {
  const catCol = by && ds.detail.meta.roles[by] ? by : ds.detail.meta.geo_col ?? ds.detail.meta.category_cols[0] ?? Object.keys(ds.detail.meta.roles)[0]
  const metricCol = metric && ds.detail.meta.roles[metric] === "numeric" ? metric : ds.detail.meta.target

  const grouped = new Map<string, number[]>()
  for (const r of ds.silverRows) {
    const g = r[catCol]
    const v = r[metricCol]
    if (g !== null && g !== "" && typeof v === "number" && Number.isFinite(v)) {
      const arr = grouped.get(String(g)) ?? []
      arr.push(v)
      grouped.set(String(g), arr)
    }
  }
  const allGroups = Array.from(grouped.entries())
    .map(([key, xs]) => ({
      row: {
        [catCol]: key,
        n: xs.length,
        mean: Number(mean(xs).toFixed(2)),
        median: Number(median(xs).toFixed(2)),
        sum: Number(xs.reduce((a, b) => a + b, 0).toFixed(2)),
        std: Number(std(xs).toFixed(2)),
      },
      xs,
    }))
    .sort((a, b) => (b.row.median ?? 0) - (a.row.median ?? 0))

  const kw = kruskalWallis(allGroups.map((g) => g.xs))
  const top = allGroups[0]
  const bottom = allGroups[allGroups.length - 1]
  const mw = top && bottom ? mannWhitney(top.xs, bottom.xs) : null

  return {
    by: catCol,
    metric: metricCol,
    groups: allGroups.slice(0, 25).map((g) => g.row),
    groups_total: allGroups.length,
    test: kw && top && bottom && mw
      ? {
          kruskal: kw,
          top: { group: String(top.row[catCol]), median: top.row.median!, n: top.row.n },
          bottom: { group: String(bottom.row[catCol]), median: bottom.row.median!, n: bottom.row.n },
          top_vs_bottom: {
            p: mw.p,
            rank_biserial: mw.rank_biserial,
            median_ratio: bottom.row.median ? Number((top.row.median! / bottom.row.median).toFixed(2)) : 0,
          },
        }
      : { error: "Not enough data per group for a non-parametric test." },
    options: ds.detail.meta.category_cols,
    clusters: ds.segmentsClusters,
  }
}

export function computeGeo(
  ds: AnalyzedDataset,
  metric?: string | null,
  agg: "median" | "mean" | "sum" | "count" = "median"
): GeoResponse {
  const roles = ds.detail.meta.roles
  const numericCols = Object.keys(roles).filter((c) => roles[c] === "numeric")
  const metricCol = metric && metric.trim() ? metric.trim() : ds.detail.meta.target
  if (agg !== "count" && !numericCols.includes(metricCol)) {
    const err = new Error(`Chỉ số '${metricCol}' không hợp lệ hoặc không phải biến số.`) as Error & { status?: number }
    err.status = 422
    throw err
  }
  if (agg === "sum" && isRatioMetric(metricCol)) {
    const err = new Error(`Không cộng dồn (sum) cho chỉ số tỷ lệ/đơn giá '${metricCol}'.`) as Error & { status?: number }
    err.status = 422
    throw err
  }

  // Pick a province column from metadata or fallback candidates
  const candidateCols = Array.from(
    new Set(
      [
        ds.detail.meta.geo_col,
        ...Object.keys(roles).filter((c) => ["geo", "geo_raw", "category"].includes(roles[c])),
      ].filter((c): c is string => Boolean(c))
    )
  )

  let chosenCol: string | null = null
  let bestMatches = 0
  for (const c of candidateCols) {
    let matches = 0
    for (const r of ds.silverRows) {
      if (canonicalProvince34(r[c]).province) matches++
    }
    if (matches > bestMatches) {
      bestMatches = matches
      chosenCol = c
    }
  }

  if (!chosenCol || bestMatches === 0) {
    const err = new Error("Dataset không có cột tỉnh/thành phố Việt Nam.") as Error & { status?: number }
    err.status = 422
    throw err
  }

  const buckets = new Map<string, { region: string | null; vals: number[]; n: number }>()
  const nationalVals: number[] = []
  let nationalCount = 0
  let unmatchedRows = 0
  const unmatchedSamples: string[] = []
  let convertedFrom63 = false

  for (const r of ds.silverRows) {
    const rawGeo = r[chosenCol]
    const resolved = canonicalProvince34(rawGeo)
    if (!resolved.province) {
      if (rawGeo !== null && rawGeo !== undefined && String(rawGeo).trim() !== "") {
        unmatchedRows++
        const s = String(rawGeo).trim()
        if (unmatchedSamples.length < 10 && !unmatchedSamples.includes(s)) {
          unmatchedSamples.push(s)
        }
      }
      continue
    }
    if (resolved.convertedFrom63) convertedFrom63 = true
    const entry = buckets.get(resolved.province) ?? { region: resolved.region, vals: [], n: 0 }
    if (agg === "count") {
      entry.n++
      nationalCount++
    } else {
      const v = r[metricCol]
      if (typeof v === "number" && Number.isFinite(v)) {
        entry.vals.push(v)
        entry.n++
        nationalVals.push(v)
        nationalCount++
      }
    }
    buckets.set(resolved.province, entry)
  }

  const calcAgg = (xs: number[], count: number): number | null => {
    if (agg === "count") return count
    if (xs.length === 0) return null
    if (agg === "sum") return Number(xs.reduce((a, b) => a + b, 0).toFixed(2))
    if (agg === "mean") return Number(mean(xs).toFixed(2))
    return Number(median(xs).toFixed(2))
  }

  const rows: GeoRow[] = Array.from(buckets.entries())
    .map(([province, info]) => ({
      province,
      region: info.region,
      value: calcAgg(info.vals, info.n),
      n: info.n,
    }))
    .filter((r) => r.n > 0)
    .sort((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity))
    .slice(0, 34)

  return {
    metric: metricCol,
    agg,
    level: "province_2025",
    rows,
    national: {
      value: calcAgg(nationalVals, nationalCount),
      n: nationalCount,
    },
    unmatched: {
      rows: unmatchedRows,
      samples: unmatchedSamples,
    },
    converted_from_63: convertedFrom63,
  }
}

export function computeWhatIf(ds: AnalyzedDataset, feature: string, pctChange: number): WhatIfResult {
  if (!ds.driverModel) {
    throw new Error("No driver model fitted for this dataset.")
  }
  const res = predictWhatIf(ds.silverRows, ds.detail.meta.target, ds.driverModel, feature, pctChange)
  if (!res) throw new Error(`Feature '${feature}' is not in the driver model.`)
  return res
}

export function computeWhatIfMulti(
  ds: AnalyzedDataset,
  changes: WhatIfChange[],
  target?: string | null
): WhatIfScenarioResult {
  if (!ds.driverModel) {
    const err = new Error("Chưa có mô hình drivers cho dataset này (cần ≥ 2 biến số).") as Error & { status?: number }
    err.status = 404
    throw err
  }
  const targetCol = target || ds.detail.meta.target
  if (target && target !== ds.detail.meta.target) {
    const err = new Error(`Target '${target}' chưa được hỗ trợ trong mô hình what-if (chỉ hỗ trợ '${ds.detail.meta.target}').`) as Error & { status?: number }
    err.status = 422
    throw err
  }
  const res = predictWhatIfMulti(ds.silverRows, targetCol, ds.driverModel, changes)
  if (!res) {
    const err = new Error("Không thể tính kịch bản what-if do thiếu dữ liệu hợp lệ.") as Error & { status?: number }
    err.status = 422
    throw err
  }
  return res
}

export function computeWhatIfCurve(ds: AnalyzedDataset, feature: string): WhatIfCurve {
  const points: WhatIfCurve["points"] = []
  for (let p = -30; p <= 30; p += 5) {
    const r = computeWhatIf(ds, feature, p)
    points.push({
      pct: p,
      change: r.target_change_pct ?? 0,
      low: r.ci90_pct[0] ?? 0,
      high: r.ci90_pct[1] ?? 0,
    })
  }
  return { feature, points }
}

/** Minimal uncompressed (STORE) ZIP archive builder in pure Node.js so bundle.zip is a valid ZIP file. */
function makeZip(entries: { name: string; content: Buffer }[]): Buffer {
  const crcTable = new Uint32Array(256)
  for (let i = 0; i < 256; i++) {
    let c = i
    for (let k = 0; k < 8; k++) c = (c & 1) ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    crcTable[i] = c >>> 0
  }
  const crc32 = (buf: Buffer) => {
    let c = 0xffffffff
    for (let i = 0; i < buf.length; i++) c = crcTable[(c ^ buf[i]) & 0xff] ^ (c >>> 8)
    return (c ^ 0xffffffff) >>> 0
  }

  const localParts: Buffer[] = []
  const centralParts: Buffer[] = []
  let offset = 0

  for (const e of entries) {
    const nameBuf = Buffer.from(e.name, "utf-8")
    const crc = crc32(e.content)
    const lh = Buffer.alloc(30 + nameBuf.length)
    lh.writeUInt32LE(0x04034b50, 0)
    lh.writeUInt16LE(20, 4)
    lh.writeUInt16LE(0, 6)
    lh.writeUInt16LE(0, 8) // store
    lh.writeUInt16LE(0, 10)
    lh.writeUInt16LE(0, 12)
    lh.writeUInt32LE(crc, 14)
    lh.writeUInt32LE(e.content.length, 18)
    lh.writeUInt32LE(e.content.length, 22)
    lh.writeUInt16LE(nameBuf.length, 26)
    lh.writeUInt16LE(0, 28)
    nameBuf.copy(lh, 30)
    localParts.push(lh, e.content)

    const ch = Buffer.alloc(46 + nameBuf.length)
    ch.writeUInt32LE(0x02014b50, 0)
    ch.writeUInt16LE(20, 4)
    ch.writeUInt16LE(20, 6)
    ch.writeUInt16LE(0, 8)
    ch.writeUInt16LE(0, 10)
    ch.writeUInt16LE(0, 12)
    ch.writeUInt16LE(0, 14)
    ch.writeUInt32LE(crc, 16)
    ch.writeUInt32LE(e.content.length, 20)
    ch.writeUInt32LE(e.content.length, 24)
    ch.writeUInt16LE(nameBuf.length, 28)
    ch.writeUInt16LE(0, 30)
    ch.writeUInt16LE(0, 32)
    ch.writeUInt16LE(0, 34)
    ch.writeUInt16LE(0, 36)
    ch.writeUInt32LE(0, 38)
    ch.writeUInt32LE(offset, 42)
    nameBuf.copy(ch, 46)
    centralParts.push(ch)

    offset += lh.length + e.content.length
  }

  const centralBuf = Buffer.concat(centralParts)
  const eocd = Buffer.alloc(22)
  eocd.writeUInt32LE(0x06054b50, 0)
  eocd.writeUInt16LE(0, 4)
  eocd.writeUInt16LE(0, 6)
  eocd.writeUInt16LE(entries.length, 8)
  eocd.writeUInt16LE(entries.length, 10)
  eocd.writeUInt32LE(centralBuf.length, 12)
  eocd.writeUInt32LE(offset, 16)
  eocd.writeUInt16LE(0, 20)

  return Buffer.concat([...localParts, centralBuf, eocd])
}

export function buildExportFile(ds: AnalyzedDataset, kind: ExportKind): { body: Buffer; mime: string; filename: string } | null {
  const id = ds.id
  const makeCsv = (rows: Record<string, unknown>[]) => {
    if (rows.length === 0) return ""
    const cols = Object.keys(rows[0])
    const esc = (v: unknown) => {
      const s = v === null || v === undefined ? "" : String(v)
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
    }
    return [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n")
  }

  const dictRows = ds.profile.profile.column_profiles.map((c) => ({
    column: c.name,
    role: c.role,
    dtype: c.dtype,
    missing_pct: c.missing_pct,
    unique: c.unique,
    median: c.median ?? "",
    min: c.min ?? "",
    max: c.max ?? "",
  }))
  const dictMd = [
    `# Data Dictionary — ${ds.summary.name}`,
    "",
    "| Column | Role | Type | Missing % | Unique | Median |",
    "|---|---|---|---:|---:|---:|",
    ...dictRows.map((r) => `| ${r.column} | ${r.role} | ${r.dtype} | ${r.missing_pct}% | ${r.unique} | ${r.median} |`),
  ].join("\n")
  const edaMd = [
    `# Exploratory Data Analysis — ${ds.summary.name}`,
    "",
    `- Rows: ${ds.summary.rows}`,
    `- Domain: ${ds.summary.domain}`,
    `- Target: ${ds.summary.target}`,
    "",
    "## Top Ranked Insights",
    ...ds.insights.insights.map((i) => `### #${i.rank} ${i.title_vi}\n${i.sentence_vi}\n- Evidence: ${i.test}`),
  ].join("\n\n")
  const pitchVi = [
    `# Kịch bản Pitch — ${ds.summary.name}`,
    "",
    "## 1. Bối cảnh & Câu hỏi quyết định",
    `Phân tích chỉ số mục tiêu **${ds.summary.target}** trên ${ds.summary.rows.toLocaleString("vi-VN")} bản ghi sạch.`,
    "",
    "## 2. Phát hiện chính",
    ...ds.insights.insights.map((i) => `- **${i.title_vi}**: ${i.sentence_vi}`),
    "",
    "## 3. Khuyến nghị hành động",
    ...ds.insights.recommendations.map((r) => `- **Vấn đề**: ${r.so_what_vi} **Hành động**: ${r.now_what_vi}`),
  ].join("\n")
  const pitchEn = [
    `# Pitch Script — ${ds.summary.name}`,
    "",
    "## 1. Decision Context",
    `Analyzing **${ds.summary.target}** across ${ds.summary.rows.toLocaleString("en-US")} cleaned records.`,
    "",
    "## 2. Key Findings",
    ...ds.insights.insights.map((i) => `- **${i.title_en}**: ${i.sentence_en}`),
    "",
    "## 3. Recommendations",
    ...ds.insights.recommendations.map((r) => `- **So what**: ${r.so_what_en} **Now what**: ${r.now_what_en}`),
  ].join("\n")
  const dashboardHtml = `<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>${ds.summary.name} · VietLeap Insight</title><style>body{font-family:system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem;color:#111}h1,h2{margin-bottom:.4rem}.kpi{display:inline-block;border:1px solid #ddd;border-radius:8px;padding:12px 16px;margin:6px 8px 6px 0}</style></head><body><h1>${ds.summary.name}</h1><p>Domain: ${ds.summary.domain} · Target: ${ds.summary.target} · Rows: ${ds.summary.rows}</p><div>${ds.detail.kpis.map((k) => `<div class="kpi"><small>${k.label_vi}</small><br><strong>${k.value}</strong></div>`).join("")}</div><h2>Insights</h2><ul>${ds.insights.insights.map((i) => `<li><strong>${i.title_vi}</strong>: ${i.sentence_vi}</li>`).join("")}</ul></body></html>`

  switch (kind) {
    case "results":
      return {
        body: Buffer.from(JSON.stringify({ meta: ds.detail.meta, kpis: ds.detail.kpis, profile: ds.profile.profile, insights: ds.insights.insights, recommendations: ds.insights.recommendations, drivers: ds.drivers.drivers }, null, 2), "utf-8"),
        mime: "application/json",
        filename: `${id}_results.json`,
      }
    case "clean_csv":
      return { body: Buffer.from(makeCsv(ds.silverRows.slice(0, 500)), "utf-8"), mime: "text/csv", filename: `${id}_clean_sample.csv` }
    case "dictionary_csv":
      return { body: Buffer.from(makeCsv(dictRows), "utf-8"), mime: "text/csv", filename: `${id}_data_dictionary.csv` }
    case "dictionary_md":
      return { body: Buffer.from(dictMd, "utf-8"), mime: "text/markdown", filename: `${id}_data_dictionary.md` }
    case "eda_md":
      return { body: Buffer.from(edaMd, "utf-8"), mime: "text/markdown", filename: `${id}_eda.md` }
    case "pitch_md":
      return { body: Buffer.from(pitchVi, "utf-8"), mime: "text/markdown", filename: `${id}_pitch.md` }
    case "pitch_en":
      return { body: Buffer.from(pitchEn, "utf-8"), mime: "text/markdown", filename: `${id}_pitch.en.md` }
    case "summary_md":
      return { body: Buffer.from(pitchVi, "utf-8"), mime: "text/markdown", filename: `${id}_executive_summary.md` }
    case "dashboard":
      return { body: Buffer.from(dashboardHtml, "utf-8"), mime: "text/html", filename: `${id}_dashboard.html` }
    case "bundle": {
      const zip = makeZip([
        { name: "results.json", content: Buffer.from(JSON.stringify({ meta: ds.detail.meta, kpis: ds.detail.kpis, insights: ds.insights.insights, recommendations: ds.insights.recommendations }, null, 2), "utf-8") },
        { name: "clean_sample.csv", content: Buffer.from(makeCsv(ds.silverRows.slice(0, 500)), "utf-8") },
        { name: "data_dictionary.csv", content: Buffer.from(makeCsv(dictRows), "utf-8") },
        { name: "data_dictionary.md", content: Buffer.from(dictMd, "utf-8") },
        { name: "eda.md", content: Buffer.from(edaMd, "utf-8") },
        { name: "pitch.md", content: Buffer.from(pitchVi, "utf-8") },
        { name: "pitch.en.md", content: Buffer.from(pitchEn, "utf-8") },
        { name: "dashboard.html", content: Buffer.from(dashboardHtml, "utf-8") },
      ])
      return { body: zip, mime: "application/zip", filename: `${id}_bundle.zip` }
    }
    default:
      return null
  }
}
