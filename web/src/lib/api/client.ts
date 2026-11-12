// Typed API client. All calls go through Next.js rewrites (/api/* → FastAPI), so no CORS in the browser.
import type {
  AgentConfig,
  AgentEvent,
  ChatMessage,
  DatasetDetail,
  DatasetSummary,
  DriversResponse,
  Insight,
  Job,
  ProfileResponse,
  Recommendation,
  RowsResponse,
  SegmentsResponse,
  TimeSeriesResponse,
  WhatIfCurve,
  WhatIfResult,
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
    throw new ApiError(0, `Cannot reach the analysis API (${(e as Error).message}). Is the backend running on port 8000?`)
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
  drivers: (id: string) => request<DriversResponse>(`${ds(id)}/drivers`),
  whatIf: (id: string, feature: string, pct_change: number) =>
    request<WhatIfResult>(`${ds(id)}/whatif`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feature, pct_change }),
    }),
  whatIfCurve: (id: string, feature: string) => request<WhatIfCurve>(`${ds(id)}/whatif/curve${q({ feature })}`),
  upload: (form: FormData) => request<Job>("/api/datasets", { method: "POST", body: form }),
  job: (id: string) => request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  agentConfig: () => request<AgentConfig>("/api/agent/config"),
  fileUrl: (id: string, kind: "deck" | "dashboard" | "summary_pdf" | "summary_md" | "results" | "clean_csv") => `${BASE}${ds(id)}/files/${kind}`,
}

/** Stream AI-analyst events (Server-Sent Events over a POST). */
export async function streamAgent(
  id: string,
  body: { message: string; history: ChatMessage[]; auto?: boolean; top_n?: number },
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE}${ds(id)}/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) throw new ApiError(res.status, `agent request failed (${res.status})`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ""
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx: number
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const line = chunk.split("\n").find((l) => l.startsWith("data:"))
      if (line) onEvent(JSON.parse(line.slice(5).trim()) as AgentEvent)
    }
  }
}
