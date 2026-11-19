// Typed API client. All calls go through Next.js rewrites (/api/* → FastAPI), so no CORS in the browser.
import type {
  Brief,
  IngestJob,
  IngestRequest,
  LineageResponse,
  ConformedResponse,
  ModelsResponse,
  PipelineSummary,
  Provenance,
  QualityResponse,
  SourceKindsResponse,
  SqlResult,
  WarehouseTable,
  DatasetDetail,
  DatasetSummary,
  ExportKind,
  ExportJob,
  DriversResponse,
  Insight,
  Job,
  ProfileResponse,
  Recommendation,
  ReportLang,
  RowsResponse,
  GeoResponse,
  SavedScenario,
  SegmentsResponse,
  TimeSeriesResponse,
  WhatIfChange,
  WhatIfCurve,
  WhatIfResult,
  WhatIfScenarioRequest,
  WhatIfScenarioResult,
} from "./types"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? ""

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = "ApiError"
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { ...init, cache: "no-store" })
  } catch (e) {
    throw new ApiError(0, `Không kết nối được API phân tích (${(e as Error).message}). Backend đã chạy ở cổng 8000 chưa?`)
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

const q = (params: Record<string, string | number | boolean | null | undefined>) => {
  const s = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") s.set(k, String(v))
  })
  const str = s.toString()
  return str ? `?${str}` : ""
}

const ds = (id: string) => `/api/datasets/${encodeURIComponent(id)}`

export const api = {
  health: () => request<{ status: string; datasets: number }>("/api/health"),
  datasets: () => request<DatasetSummary[]>("/api/datasets"),
  dataset: (id: string) => request<DatasetDetail>(ds(id)),
  profile: (id: string) => request<ProfileResponse>(`${ds(id)}/profile`),
  insights: (id: string) => request<{ insights: Insight[]; recommendations: Recommendation[] }>(`${ds(id)}/insights`),
  timeseries: (id: string, p: { metric?: string; agg?: string; freq?: string } = {}) =>
    request<TimeSeriesResponse>(`${ds(id)}/timeseries${q(p)}`),
  rows: (id: string, p: { page?: number; page_size?: number; sort?: string; desc?: boolean; q?: string } = {}) =>
    request<RowsResponse>(`${ds(id)}/rows${q(p)}`),
  segments: (id: string, p: { by?: string; metric?: string } = {}) => request<SegmentsResponse>(`${ds(id)}/segments${q(p)}`),
  geo: (id: string, p: { metric?: string; agg?: string } = {}) => request<GeoResponse>(`${ds(id)}/geo${q(p)}`),
  drivers: (id: string) => request<DriversResponse>(`${ds(id)}/drivers`),
  whatIf: (id: string, feature: string, pct_change: number) =>
    request<WhatIfResult>(`${ds(id)}/whatif`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feature, pct_change }),
    }),
  whatIfScenario: (id: string, changes: WhatIfChange[], target?: string | null, signal?: AbortSignal) =>
    request<WhatIfScenarioResult>(`${ds(id)}/whatif/scenario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ changes, target: target ?? null }),
      signal,
    }),
  listScenarios: (id: string) => request<SavedScenario[]>(`${ds(id)}/whatif/scenarios`),
  saveScenario: (id: string, name: string, body: WhatIfScenarioRequest) =>
    request<SavedScenario[]>(`${ds(id)}/whatif/scenarios`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, request: body }),
    }),
  deleteScenario: (id: string, name: string) =>
    request<SavedScenario[]>(`${ds(id)}/whatif/scenarios${q({ name })}`, { method: "DELETE" }),
  whatIfCurve: (id: string, feature: string) => request<WhatIfCurve>(`${ds(id)}/whatif/curve${q({ feature })}`),
  upload: (form: FormData) => request<Job>("/api/datasets", { method: "POST", body: form }),
  job: (id: string) => request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  brief: (text: string, dataset: string | null) =>
    request<Brief>("/api/brief", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, dataset }) }),
  briefSamples: () => request<{ name: string; text: string }[]>("/api/brief/samples"),
  datasetBrief: (id: string) => request<Brief>(`${ds(id)}/brief`),
  // data-engineering layer
  sourceKinds: () => request<SourceKindsResponse>("/api/sources/kinds"),
  ingest: (body: IngestRequest) =>
    request<IngestJob>("/api/ingest", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  ingestJob: (id: string) => request<IngestJob>(`/api/ingest/${encodeURIComponent(id)}`),
  tables: () => request<WarehouseTable[]>("/api/warehouse/tables"),
  columns: (fq: string) => request<{ name: string; type: string }[]>(`/api/warehouse/tables/${encodeURIComponent(fq)}/columns`),
  sql: (query: string, limit = 500) =>
    request<SqlResult>("/api/sql", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, limit }) }),
  pipeline: (id: string) => request<PipelineSummary>(`${ds(id)}/pipeline`),
  quality: (id: string) => request<QualityResponse>(`${ds(id)}/quality`),
  lineage: (id: string) => request<LineageResponse>(`${ds(id)}/lineage`),
  models: (id: string) => request<ModelsResponse>(`${ds(id)}/models`),
  conformed: (id: string) => request<ConformedResponse>(`${ds(id)}/conformed`),
  provenance: (id: string) => request<Provenance[]>(`${ds(id)}/provenance`),
  fileUrl: (id: string, kind: ExportKind) => `${BASE}${ds(id)}/files/${kind}`,
  startExport: (id: string, lang: ReportLang, dashboardPdf: boolean) =>
    request<{ job_id: string }>(`${ds(id)}/export`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lang, dashboard_pdf: dashboardPdf }),
    }),
  exportJob: (id: string) => request<ExportJob>(`/api/export/${encodeURIComponent(id)}`),
}
