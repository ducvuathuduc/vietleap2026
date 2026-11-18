import crypto from "node:crypto"
import fs from "node:fs"
import path from "node:path"
import type {
  Brief,
  ExportJob,
  IngestJob,
  IngestRequest,
  Job,
  RowsResponse,
  SavedScenario,
  WhatIfScenarioRequest,
} from "@/lib/api/types"
import {
  analyzeDataset,
  computeGeo,
  computeSegments,
  computeTimeSeries,
  computeWhatIf,
  computeWhatIfCurve,
  computeWhatIfMulti,
  type AnalyzedDataset,
  type SourceInputMeta,
} from "./analyzer"
import { loadBriefSamples, parseBrief } from "./brief"
import { discoverStaticOutputs } from "./offline-fallback"
import { executeReadOnlySql, getTableColumns, listWarehouseTables } from "./sql"
import { parseDelimitedBuffer, repoRoot, slug } from "./vn"

export class EngineNotFoundError extends Error {
  status = 404
}

export class EngineBadRequestError extends Error {
  status = 422
}

interface StoreState {
  seeded: boolean
  datasets: Map<string, AnalyzedDataset>
  briefs: Map<string, Brief>
  jobs: Map<string, Job>
  ingestJobs: Map<string, IngestJob>
  exportJobs: Map<string, ExportJob>
  scenarios: Map<string, SavedScenario[]>
}

const g = globalThis as unknown as { __vietleapStore?: StoreState }

function state(): StoreState {
  if (!g.__vietleapStore) {
    g.__vietleapStore = {
      seeded: false,
      datasets: new Map(),
      briefs: new Map(),
      jobs: new Map(),
      ingestJobs: new Map(),
      exportJobs: new Map(),
      scenarios: new Map(),
    }
  }
  const s = g.__vietleapStore
  if (!s.scenarios) s.scenarios = new Map()
  if (!s.seeded) {
    s.seeded = true
    seedInitialDatasets(s)
  }
  return s
}

function seedInitialDatasets(s: StoreState) {
  const root = repoRoot()
  const seeds: {
    id: string
    name: string
    relPath: string
    domain: string
    target?: string
    timeCol?: string
    geoCol?: string
  }[] = [
    {
      id: "wdi_asia_fiscal_panel",
      name: "WDI Asia Fiscal Panel",
      relPath: "data/practice/wdi_asia_fiscal_panel.csv",
      domain: "public_finance",
      // Story anchor: GDP/capita — Vietnam has 25/25 observations
      // (VNM 2024 $4,717, rank 6/10) while tax_revenue_pct_gdp has 0/25
      // for Vietnam, so the old target made /decision unable to speak
      // about Vietnam at all. Matches Evidence Overview + pitch/deck/EDA.
      target: "gdp_per_capita_usd",
      timeCol: "year",
      geoCol: "country",
    },
    {
      id: "provincial_earmarked_transfers_2024_2025",
      name: "Provincial Earmarked Transfers 2024–2025",
      relPath: "data/snapshots/provincial_earmarked_transfers_2024_2025.csv",
      domain: "public_finance",
      target: "earmarked_transfers",
      timeCol: "year",
      geoCol: "province",
    },
    {
      id: "synthetic_messy_bds",
      name: "Vietnam Real Estate Listings (Messy Practice)",
      relPath: "data/practice/synthetic_messy_bds.csv",
      domain: "property",
      target: "price_per_m2",
    },
  ]

  for (const seed of seeds) {
    const abs = path.join(/*turbopackIgnore: true*/ root, seed.relPath)
    if (!fs.existsSync(/*turbopackIgnore: true*/ abs)) continue
    try {
      const buf = fs.readFileSync(/*turbopackIgnore: true*/ abs)
      const parsed = parseDelimitedBuffer(buf)
      if (parsed.rows.length === 0) continue
      const ds = analyzeDataset({
        id: seed.id,
        name: seed.name,
        sourceFile: seed.relPath,
        rawRows: parsed.rows,
        domain: seed.domain,
        target: seed.target,
        timeCol: seed.timeCol,
        geoCol: seed.geoCol,
      })
      s.datasets.set(ds.id, ds)
    } catch {
      /* skip broken seed */
    }
  }

  // Also hydrate any precomputed static outputs from out/<ds>/ so dashboard remains usable when :8000 is down
  const outRoot = path.join(/*turbopackIgnore: true*/ root, "out")
  for (const item of discoverStaticOutputs(outRoot)) {
    if (item.briefRaw && !s.briefs.has(item.id)) {
      s.briefs.set(item.id, item.briefRaw as Brief)
    }
    if (s.datasets.has(item.id) || !item.sampleCsvPath) continue
    try {
      const buf = fs.readFileSync(/*turbopackIgnore: true*/ item.sampleCsvPath)
      const parsed = parseDelimitedBuffer(buf)
      if (parsed.rows.length === 0) continue
      const ds = analyzeDataset({
        id: item.id,
        name: item.id,
        sourceFile: `out/${item.id}/clean_sample.csv`,
        rawRows: parsed.rows,
        domain: item.domain,
        target: item.target,
      })
      s.datasets.set(ds.id, ds)
    } catch {
      /* skip invalid precomputed output */
    }
  }
}

export function listDatasets() {
  return Array.from(state().datasets.values()).map((d) => d.summary)
}

export function getDataset(id: string): AnalyzedDataset {
  const ds = state().datasets.get(id)
  if (!ds) throw new EngineNotFoundError(`dataset '${id}' not found`)
  return ds
}

export function getDatasetDetail(id: string) {
  const ds = getDataset(id)
  const hasBrief = state().briefs.has(id)
  return { ...ds.detail, has_brief: hasBrief }
}

export function getDatasetRows(
  id: string,
  opts: { page?: number; page_size?: number; sort?: string | null; desc?: boolean; q?: string | null; filter_col?: string | null; filter_val?: string | null }
): RowsResponse {
  const ds = getDataset(id)
  const roles = ds.detail.meta.roles
  const cols = Object.keys(ds.silverRows[0] ?? {}).filter((c) => !c.startsWith("_") || c === "_outlier_any" || c === "_segment")
  let rows = ds.silverRows

  if (opts.filter_col && opts.filter_val !== undefined && opts.filter_val !== null) {
    const fc = opts.filter_col
    if (!cols.includes(fc)) throw new EngineBadRequestError(`unknown column ${fc}`)
    rows = rows.filter((r) => String(r[fc] ?? "") === opts.filter_val)
  }
  if (opts.q) {
    const needle = opts.q.toLowerCase()
    const searchCols = cols.filter((c) => ["text", "geo", "category", "id"].includes(roles[c] ?? ""))
    rows = rows.filter((r) => searchCols.some((c) => String(r[c] ?? "").toLowerCase().includes(needle)))
  }
  if (opts.sort) {
    const sc = opts.sort
    if (!cols.includes(sc)) throw new EngineBadRequestError(`unknown sort column ${sc}`)
    const dir = opts.desc ? -1 : 1
    rows = [...rows].sort((a, b) => {
      const va = a[sc]
      const vb = b[sc]
      if (va === vb) return 0
      if (va === null) return 1
      if (vb === null) return -1
      return (typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb))) * dir
    })
  }
  const page = Math.max(1, opts.page ?? 1)
  const pageSize = Math.min(500, Math.max(1, opts.page_size ?? 25))
  const total = rows.length
  const slice = rows.slice((page - 1) * pageSize, page * pageSize)
  return {
    columns: cols.map((name) => ({ name, role: roles[name] ?? (name.startsWith("_") ? "flag" : "?") })),
    rows: slice,
    total,
    page,
    page_size: pageSize,
  }
}

export function createUploadJob(opts: {
  filename: string
  buffer: Buffer
  name?: string | null
  domain?: string
  target?: string | null
  time?: string | null
  geo?: string | null
}): Job {
  const s = state()
  const dsId = slug(opts.name || opts.filename.replace(/\.[^.]+$/, ""))
  const ext = path.extname(opts.filename).toLowerCase()
  const jobId = crypto.randomUUID().slice(0, 12)
  const started = Date.now() / 1000

  let rawRows: Record<string, unknown>[] = []
  if (ext === ".json") {
    const parsed = JSON.parse(opts.buffer.toString("utf-8"))
    if (!Array.isArray(parsed)) throw new EngineBadRequestError("JSON file must contain an array of records")
    rawRows = parsed.filter((x): x is Record<string, unknown> => typeof x === "object" && x !== null)
  } else if (ext === ".csv" || ext === ".tsv" || ext === ".txt") {
    rawRows = parseDelimitedBuffer(opts.buffer).rows
  } else {
    throw new EngineBadRequestError(`Unsupported file extension '${ext}'. Please upload CSV, TSV, or JSON.`)
  }

  if (rawRows.length === 0) throw new EngineBadRequestError("Uploaded file contains no data rows.")

  const ds = analyzeDataset({
    id: dsId,
    name: opts.name || opts.filename.replace(/\.[^.]+$/, ""),
    sourceFile: opts.filename,
    rawRows,
    domain: opts.domain ?? "auto",
    target: opts.target,
    timeCol: opts.time,
    geoCol: opts.geo,
  })
  s.datasets.set(ds.id, ds)

  const job: Job = {
    id: jobId,
    status: "done",
    dataset_id: ds.id,
    error: null,
    started,
    finished: Date.now() / 1000,
  }
  s.jobs.set(jobId, job)
  return job
}

export function getJob(id: string): Job {
  const j = state().jobs.get(id)
  if (!j) throw new EngineNotFoundError("job not found")
  return j
}

export function createIngestJob(req: IngestRequest): IngestJob {
  const s = state()
  const dsId = slug(req.dataset)
  const jobId = crypto.randomUUID().slice(0, 12)
  const started = Date.now() / 1000

  const root = repoRoot()
  let rows: Record<string, unknown>[] = []
  let sourceFile = req.sources[0]?.uri ?? dsId

  // Try reading local file source if it points to data/ or scenarios/
  for (const src of req.sources) {
    if (src.kind === "file" || src.kind === "cv") {
      const candidate = path.resolve(root, src.uri)
      if (candidate.startsWith(root) && fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
        const parsed = parseDelimitedBuffer(fs.readFileSync(candidate))
        if (parsed.rows.length > 0) {
          rows = parsed.rows
          sourceFile = src.uri
          break
        }
      }
    }
  }

  // Fallback to WDI practice dataset sample if external network/SQL source requested offline
  if (rows.length === 0) {
    const fallback = path.join(root, "data/practice/wdi_asia_fiscal_panel.csv")
    if (fs.existsSync(fallback)) {
      rows = parseDelimitedBuffer(fs.readFileSync(fallback)).rows.slice(0, 80)
    }
  }

  const sourcesMeta: SourceInputMeta[] = req.sources.map((x) => ({
    name: x.name,
    kind: x.kind,
    uri: x.uri,
    options: x.options,
    license_note: x.license_note,
  }))

  const ds = analyzeDataset({
    id: dsId,
    name: req.dataset,
    sourceFile,
    rawRows: rows,
    sources: sourcesMeta,
  })
  s.datasets.set(ds.id, ds)

  const job: IngestJob = {
    id: jobId,
    status: "done",
    dataset: ds.id,
    error: null,
    started,
    finished: Date.now() / 1000,
    summary: {
      dataset: ds.id,
      run_id: ds.pipeline.run_id,
      timings: ds.pipeline.timings,
      steps: ds.pipeline.steps,
      gold: ds.pipeline.gold,
      quality: ds.pipeline.quality,
    },
  }
  s.ingestJobs.set(jobId, job)
  return job
}

export function getIngestJob(id: string): IngestJob {
  const j = state().ingestJobs.get(id)
  if (!j) throw new EngineNotFoundError("job not found")
  return j
}

export function startExportJob(dsId: string): { job_id: string } {
  const ds = getDataset(dsId)
  const jobId = crypto.randomUUID().slice(0, 12)
  const now = new Date().toISOString()
  const job: ExportJob = {
    id: jobId,
    dataset: ds.id,
    status: "done",
    progress: 1,
    step: "done",
    warnings: [],
    error: null,
    files: {
      bundle: "export/bundle.zip",
      results: "results.json",
      clean_csv: "clean_sample.csv",
      dictionary_csv: "data_dictionary.csv",
      dictionary_md: "data_dictionary.md",
      eda_md: "eda.md",
      pitch_md: "pitch.md",
      pitch_en: "pitch.en.md",
      dashboard: "dashboard.html",
    },
    started_at: now,
    finished_at: now,
  }
  state().exportJobs.set(jobId, job)
  return { job_id: jobId }
}

export function getExportJob(id: string): ExportJob {
  const j = state().exportJobs.get(id)
  if (!j) throw new EngineNotFoundError("Không tìm thấy lượt xuất báo cáo")
  return j
}

export function analyzeBrief(text: string, datasetId: string | null): Brief {
  let columns: string[] | null = null
  if (datasetId) {
    const ds = getDataset(datasetId)
    columns = Object.keys(ds.detail.meta.roles)
  }
  const b = parseBrief(text, columns)
  b.dataset = datasetId
  if (datasetId) {
    state().briefs.set(datasetId, b)
  }
  return b
}

export function getDatasetBrief(dsId: string): Brief {
  const b = state().briefs.get(dsId)
  if (!b) throw new EngineNotFoundError(`no brief saved for dataset '${dsId}'`)
  return b
}

function scenariosFile(dsId: string): string {
  const safeId = dsId.replace(/[^a-zA-Z0-9_-]/g, "_")
  return path.join(repoRoot(), "out", safeId, "scenarios.json")
}

export function listScenarios(dsId: string): SavedScenario[] {
  getDataset(dsId)
  const mem = state().scenarios.get(dsId)
  if (mem) return mem
  try {
    const fp = scenariosFile(dsId)
    if (fs.existsSync(fp)) {
      const parsed = JSON.parse(fs.readFileSync(fp, "utf-8"))
      if (Array.isArray(parsed)) {
        const list = parsed.slice(0, 4) as SavedScenario[]
        state().scenarios.set(dsId, list)
        return list
      }
    }
  } catch {
    /* fallback to empty */
  }
  return []
}

function persistScenarios(dsId: string, list: SavedScenario[]) {
  state().scenarios.set(dsId, list)
  try {
    const fp = scenariosFile(dsId)
    fs.mkdirSync(path.dirname(fp), { recursive: true })
    fs.writeFileSync(fp, JSON.stringify(list, null, 2), "utf-8")
  } catch {
    /* ignore read-only disk */
  }
}

export function saveScenario(dsId: string, name: string, req: WhatIfScenarioRequest): SavedScenario[] {
  const ds = getDataset(dsId)
  const cleanName = name.trim()
  if (!cleanName || cleanName.length > 60) {
    throw new EngineBadRequestError("Tên kịch bản phải có 1–60 ký tự.")
  }
  const cur = listScenarios(dsId)
  if (cur.length >= 4 && !cur.some((x) => x.name === cleanName)) {
    const err = new Error("Đã đạt tối đa 4 kịch bản lưu cho deck.") as Error & { status?: number }
    err.status = 409
    throw err
  }
  const result = computeWhatIfMulti(ds, req.changes, req.target)
  const next = [...cur.filter((x) => x.name !== cleanName), { name: cleanName, request: req, result }].slice(0, 4)
  persistScenarios(dsId, next)
  return next
}

export function deleteScenario(dsId: string, name: string): SavedScenario[] {
  getDataset(dsId)
  const cur = listScenarios(dsId)
  const next = cur.filter((x) => x.name !== name)
  persistScenarios(dsId, next)
  return next
}

export function getAllDatasets(): AnalyzedDataset[] {
  return Array.from(state().datasets.values())
}

/** In-process backend dispatcher used by AI Analyst (chat/story) without needing port 8000. */
export async function dispatchBackend<T>(rawPath: string, init?: RequestInit): Promise<T> {
  const url = new URL(rawPath, "http://localhost")
  const p = url.pathname
  const body = typeof init?.body === "string" ? JSON.parse(init.body) : undefined

  if (p === "/api/health") {
    return { status: "ok", datasets: listDatasets().length } as T
  }
  if (p === "/api/datasets") {
    return listDatasets() as T
  }
  if (p === "/api/warehouse/tables") {
    return listWarehouseTables(getAllDatasets()) as T
  }
  const colMatch = p.match(/^\/api\/warehouse\/tables\/([^/]+)\/columns$/)
  if (colMatch) {
    return getTableColumns(getAllDatasets(), decodeURIComponent(colMatch[1])) as T
  }
  if (p === "/api/sql") {
    return executeReadOnlySql(getAllDatasets(), body?.query ?? "", body?.limit ?? 200) as T
  }
  if (p === "/api/brief/samples") {
    return loadBriefSamples() as T
  }

  const dsMatch = p.match(/^\/api\/datasets\/([^/]+)(?:\/(.*))?$/)
  if (dsMatch) {
    const dsId = decodeURIComponent(dsMatch[1])
    const sub = dsMatch[2] ?? ""
    const ds = getDataset(dsId)
    if (sub === "") return getDatasetDetail(dsId) as T
    if (sub === "profile") return ds.profile as T
    if (sub === "insights") return ds.insights as T
    if (sub === "drivers") return ds.drivers as T
    if (sub === "pipeline") return ds.pipeline as T
    if (sub === "quality") return ds.quality as T
    if (sub === "lineage") return ds.lineage as T
    if (sub === "models") return ds.models as T
    if (sub === "provenance") return ds.provenance as T
    if (sub === "brief") return getDatasetBrief(dsId) as T
    if (sub === "segments") {
      return computeSegments(ds, url.searchParams.get("by"), url.searchParams.get("metric")) as T
    }
    if (sub === "geo") {
      const rawAgg = (url.searchParams.get("agg") ?? "median") as "median" | "mean" | "sum" | "count"
      return computeGeo(ds, url.searchParams.get("metric"), rawAgg) as T
    }
    if (sub === "timeseries") {
      return computeTimeSeries(
        ds.silverRows,
        ds.detail.meta.time_col,
        url.searchParams.get("metric") ?? ds.detail.meta.target,
        (url.searchParams.get("agg") as "median" | "mean" | "sum" | "count") ?? "median",
        url.searchParams.get("freq"),
        url.searchParams.get("group")
      ) as T
    }
    if (sub === "whatif") {
      return computeWhatIf(ds, body?.feature ?? "", Number(body?.pct_change ?? 0)) as T
    }
    if (sub === "whatif/scenario") {
      return computeWhatIfMulti(ds, body?.changes ?? [], body?.target ?? null) as T
    }
    if (sub === "whatif/scenarios") {
      const method = (init?.method ?? "GET").toUpperCase()
      if (method === "POST") {
        return saveScenario(dsId, String(body?.name ?? ""), body?.request ?? { changes: [] }) as T
      }
      if (method === "DELETE") {
        return deleteScenario(dsId, url.searchParams.get("name") ?? "") as T
      }
      return listScenarios(dsId) as T
    }
    if (sub === "whatif/curve") {
      return computeWhatIfCurve(ds, url.searchParams.get("feature") ?? "") as T
    }
  }

  throw new EngineNotFoundError(`Unknown backend route: ${p}`)
}
