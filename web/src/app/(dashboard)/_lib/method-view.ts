/**
 * Page 6 (`/phuong-phap`) and the quiet Q&A page. Artefact links point at files{}
 * keys; technical table names stay on a secondary line.
 */
import path from "node:path"

import { formatDay, frequencyLabel, nextReleaseText } from "../../../components/judge/labels.ts"
import { formatDateTime, formatNumber, formatPeriod, formatWithUnit } from "../../../lib/monitor/format.ts"
import { indicatorById, sourceById } from "../../../lib/monitor/lookup.ts"
import type { MeasureType, Monitor, ReconciliationVerdict, SourceMethod } from "../../../lib/monitor/types.ts"
import { type FooterModel } from "./common.ts"

const METHOD_LABELS: Record<SourceMethod, string> = {
  db: "Cơ sở dữ liệu",
  api: "Giao diện lập trình",
  file: "Tệp đã công bố",
  scrape: "Thu thập trang",
  social: "Mạng xã hội",
  tinyfish: "Thu thập có trình duyệt",
  pdf: "Tài liệu PDF",
}

const MEASURE_LABELS: Record<MeasureType, string> = {
  level: "Mức",
  ytd: "Lũy kế",
  yoy: "Cùng kỳ năm trước",
  mom: "So với tháng trước",
  share: "Tỷ trọng",
  ratio: "Tỷ lệ",
  pct_plan: "So với kế hoạch",
  index: "Chỉ số",
}

const FLAG_LABELS: Record<string, string> = {
  category_normalized: "Chuẩn hoá phân loại",
  negative_trade: "Giao dịch âm",
  ohlc_bounds: "Biên giá",
  outlier: "Giá trị ngoại lai",
  duplicate: "Trùng",
  missing: "Thiếu",
  unit_normalized: "Chuẩn hoá đơn vị",
}

const VERDICT_LABELS: Record<ReconciliationVerdict, string> = {
  match: "Khớp",
  mismatch: "Lệch",
  single_source: "Một nguồn",
}

const NOTE_MEASURES: Record<string, string> = {
  level: "Mức",
  yoy: "Cùng kỳ năm trước",
  mom: "So với tháng trước",
  pct_plan: "So với kế hoạch",
  share: "Tỷ trọng",
  ratio: "Tỷ lệ",
  ytd: "Lũy kế",
}

const NOTE_UNITS: Record<string, string> = {
  "%": "%",
  "triệu đồng": "triệu đồng",
  ty_vnd: "tỷ đồng",
  vnd_bn: "tỷ đồng",
  vnd_trn: "nghìn tỷ đồng",
  nghin_ty_vnd: "nghìn tỷ đồng",
  bn_usd: "tỷ USD",
  tr_vnd_m2: "triệu đồng/m²",
  pct_point: "điểm %",
  points: "điểm",
  units: "đơn vị",
  can: "căn",
}

const DOWNLOAD_LABELS: Record<string, string> = {
  dictionary_md: "Từ điển dữ liệu",
  dictionary_csv: "Từ điển dữ liệu (CSV)",
  eda: "Báo cáo khảo sát dữ liệu",
  erd: "Sơ đồ mô hình",
  monitor: "Bản số liệu đã xuất bản",
  v_budget_execution: "Thu chi ngân sách",
  v_public_investment: "Giải ngân đầu tư công",
  v_fdi: "Vốn đầu tư nước ngoài",
  v_bank_health_quarter: "Sức khoẻ ngân hàng",
  v_capital_market_daily: "Thị trường vốn theo ngày",
  v_real_estate: "Bất động sản",
  v_asean_rank: "Xếp hạng ASEAN",
  v_province_scorecard: "Phiếu tỉnh",
}

const STEPS: { title: string; fileKey: string }[] = [
  { title: "Chọn domain", fileKey: "dictionary_md" },
  { title: "Thu thập", fileKey: "dictionary_csv" },
  { title: "EDA", fileKey: "eda" },
  { title: "Làm sạch & mô hình", fileKey: "erd" },
  { title: "Dashboard", fileKey: "monitor" },
  { title: "Quyết định", fileKey: "monitor" },
]

const GLOSSARY = [
  { term: "SA", detail: "Chuỗi đã điều chỉnh mùa vụ." },
  { term: "yoy", detail: "So với cùng kỳ năm trước." },
  { term: "lũy kế", detail: "Cộng dồn từ đầu năm đến kỳ đang xét." },
  { term: "3mma", detail: "Trung bình của ba tháng gần nhất." },
  { term: "phân vị", detail: "Vị trí của giá trị trong phân bố 12 tháng." },
]

const ASK_TEMPLATES = [
  (name: string) => `${name} đang ở mức nào?`,
  (name: string) => `${name} được định nghĩa thế nào?`,
  (name: string) => `${name} thay đổi so với kỳ trước ra sao?`,
  (name: string) => `Nguồn của ${name} là cơ quan nào?`,
]

export interface MethodStepModel {
  title: string
  href: string | null
}

export interface MethodSourceModel {
  publisher: string
  title: string
  url: string
  method: string
  license: string
  robots: string
  fetched: string
  cutoff: string
  nextRelease: string
}

export interface MethodIndicatorModel {
  anchor: string
  name: string
  definition: string
  unit: string
  frequency: string
  measure: string
  updated: string
  nextRelease: string
}

export interface MethodQualityModel {
  source: string
  rows: string
  before: string
  after: string
  flags: string
}

export interface MethodReconciliationModel {
  name: string
  period: string
  values: string
  diff: string
  tolerance: string
  verdict: string
  note: string | null
}

export interface MethodTableModel {
  description: string
  technicalName: string
  /** Shown only when the technical name is not an internal identifier. */
  detail: string | null
  grain: string
  rows: string
}

export interface MethodDownloadModel {
  label: string
  href: string
}

export interface MethodPageModel {
  level: "detail"
  headline: string
  lead: string[]
  generatedAt: string
  steps: MethodStepModel[]
  sources: MethodSourceModel[]
  indicators: MethodIndicatorModel[]
  quality: MethodQualityModel[]
  reconciliation: MethodReconciliationModel[]
  tables: MethodTableModel[]
  erdHref: string | null
  glossary: { term: string; detail: string }[]
  downloads: MethodDownloadModel[]
  footer: FooterModel
}

export interface AskPageModel {
  level: "detail"
  label: string
  headline: string
  note: string
  input: boolean
  questions: string[]
  generatedAt: string
  footer: FooterModel
}

/** A code-like publisher is an internal id. Show the catalogue title, the site and the cutoff. */
export function publicPublisher(source: { publisher: string; title_vi: string; url: string; data_cutoff?: string | null }): string {
  const publisher = source.publisher.trim()
  if (!publisher.includes("_")) return publisher || source.title_vi.trim() || "Nguồn"
  let host = ""
  try {
    host = new URL(source.url).hostname
  } catch {
    host = ""
  }
  const title = source.title_vi.trim() || "Nguồn công bố"
  const when = source.data_cutoff ? formatDay(source.data_cutoff) : ""
  const suffix = [host, when].filter(Boolean).join(", ")
  return suffix ? `${title} (${suffix})` : title
}

export function publicFooter(monitor: Monitor): FooterModel {
  return {
    sources: monitor.sources.map((source) => ({ name: publicPublisher(source), license: source.license })),
    generatedAt: monitor.meta.generated_at,
  }
}

export function fileHref(files: Record<string, string> | undefined, key: string): string | null {
  const relative = files?.[key]
  if (!relative?.trim() || relative.includes("..")) return null
  return `/phuong-phap/tep/${key}`
}

/** Allowlisted download: own files{} key, then a path that stays inside `root`. */
export function publishedFile(
  files: Record<string, string> | undefined,
  key: string,
  root: string,
): string | null {
  if (!files || !/^[a-z0-9_]+$/i.test(key) || !Object.hasOwn(files, key)) return null
  const relative = files[key]
  if (typeof relative !== "string") return null
  return resolvePublishedFile(root, relative)
}

/** Resolve a files{} value and refuse anything that leaves the monitor directory. */
export function resolvePublishedFile(root: string, relative: string): string | null {
  const trimmed = relative.trim()
  if (
    !trimmed ||
    trimmed.includes("\0") ||
    trimmed.includes("\\") ||
    /^[a-z]:/i.test(trimmed) ||
    path.win32.isAbsolute(trimmed) ||
    path.posix.isAbsolute(trimmed)
  ) {
    return null
  }
  const full = path.resolve(root, trimmed)
  const rel = path.relative(path.resolve(root), full)
  if (!rel || rel === "." || rel.startsWith("..") || path.isAbsolute(rel)) return null
  return full
}

function latestInstant(values: (string | null | undefined)[]): string | null {
  let best: { time: number; value: string } | null = null
  for (const value of values) {
    if (!value) continue
    const time = Date.parse(value)
    if (Number.isNaN(time)) continue
    if (!best || time > best.time) best = { time, value }
  }
  return best?.value ?? null
}

function cutoffLabel(value: string | null | undefined): string {
  if (!value?.trim()) return "–"
  if (/^\d{4}$/.test(value)) return value
  return formatDay(value) || value
}

function flagText(flags: Record<string, number>): string {
  const parts: string[] = []
  let other = 0
  for (const [key, count] of Object.entries(flags)) {
    if (!Number.isFinite(count)) continue
    const label = FLAG_LABELS[key]
    if (!label) {
      other += count
      continue
    }
    parts.push(`${label}: ${formatNumber(count)}`)
  }
  if (other) parts.push(`Cờ khác: ${formatNumber(other)}`)
  return parts.join("; ") || "–"
}

function topicName(id: string): string {
  if (id.startsWith("dtc_")) return "Giải ngân đầu tư công"
  if (id.startsWith("fdi_")) return "Vốn đầu tư nước ngoài"
  if (id.startsWith("bank_")) return "Ngân hàng"
  if (id.startsWith("apartment_")) return "Căn hộ"
  if (id.startsWith("landed_home_") || id.startsWith("landed_")) return "Nhà liền thổ"
  return "Đối chiếu"
}

function subjectName(monitor: Monitor, token: string): string | null {
  const province = monitor.province.rows.find((row) => row.code === token)
  if (province?.name.trim()) return province.name.trim()
  if (/[a-z0-9]+_[a-z0-9_]+/i.test(token)) return null
  return token
}

function parsedNote(monitor: Monitor, note: string | null | undefined): { subject: string | null; measure: string | null; unit: string | null; free: string | null } {
  const text = note?.trim() ?? ""
  if (!text) return { subject: null, measure: null, unit: null, free: null }
  const parts = text.split(" · ").map((part) => part.trim())
  if (parts.length >= 3) {
    return {
      subject: subjectName(monitor, parts[0]),
      measure: NOTE_MEASURES[parts[1]] ?? null,
      unit: NOTE_UNITS[parts[2]] ?? (parts[2].includes("_") ? null : parts[2]),
      free: null,
    }
  }
  if (/[a-z0-9]+_[a-z0-9_]+/i.test(text)) return { subject: null, measure: null, unit: null, free: null }
  return { subject: null, measure: null, unit: null, free: text }
}

function downloadLabel(key: string): string | null {
  if (DOWNLOAD_LABELS[key]) return DOWNLOAD_LABELS[key]
  if (key.startsWith("v_")) return "Tệp số liệu"
  return null
}

export function methodPage(monitor: Monitor): MethodPageModel {
  const files = monitor.files
  const sourceCount = monitor.sources.length
  const indicatorCount = monitor.indicators.length
  const updated = formatDay(latestInstant([monitor.meta.generated_at, ...monitor.sources.map((source) => source.fetched_at)]))
  const sourcePart = sourceCount ? `${formatNumber(sourceCount)} nguồn` : "chưa có nguồn"
  const indicatorPart = indicatorCount ? `${formatNumber(indicatorCount)} chỉ số` : "chưa có chỉ số"
  const headline = updated
    ? `${sourcePart}, ${indicatorPart}, cập nhật gần nhất ${updated}`
    : `${sourcePart}, ${indicatorPart}`

  const downloads: MethodDownloadModel[] = []
  for (const key of Object.keys(files ?? {})) {
    const label = downloadLabel(key)
    const href = fileHref(files, key)
    if (!label || !href) continue
    downloads.push({ label, href })
  }

  return {
    level: "detail",
    headline,
    lead: ["Số này từ đâu, định nghĩa gì, đã làm sạch thế nào, và tải ở đâu?"],
    generatedAt: monitor.meta.generated_at,
    steps: STEPS.map((step) => ({ title: step.title, href: fileHref(files, step.fileKey) })),
    sources: monitor.sources.map((source) => ({
      publisher: publicPublisher(source),
      title: source.title_vi,
      url: source.url,
      method: METHOD_LABELS[source.method] ?? "–",
      license: source.license,
      robots: source.robots?.trim() || "–",
      fetched: formatDateTime(source.fetched_at) || "–",
      cutoff: cutoffLabel(source.data_cutoff),
      nextRelease: source.next_release ? formatDay(source.next_release) || "Chưa có lịch kỳ tới" : "Chưa có lịch kỳ tới",
    })),
    indicators: monitor.indicators.map((indicator) => ({
      anchor: indicator.id,
      name: indicator.name_vi,
      definition: indicator.definition_vi,
      unit: indicator.unit || "–",
      frequency: frequencyLabel(indicator.frequency) || "–",
      measure: MEASURE_LABELS[indicator.measure_type] ?? "–",
      updated: formatDay(indicator.last_updated) || "–",
      nextRelease: indicator.next_release ? formatDay(indicator.next_release) || nextReleaseText(null) : nextReleaseText(null),
    })),
    quality: monitor.quality.map((entry) => ({
      source: (() => {
        const source = sourceById(monitor, entry.source_id)
        return source ? publicPublisher(source) : "Nguồn"
      })(),
      rows: formatNumber(entry.rows),
      before: formatNumber(entry.score_before),
      after: formatNumber(entry.score_after),
      flags: flagText(entry.flags),
    })),
    reconciliation: monitor.reconciliation.map((entry) => {
      const parsed = parsedNote(monitor, entry.note_vi)
      const catalog = indicatorById(monitor, entry.indicator_id)?.name_vi?.trim()
      const topic = catalog || topicName(entry.indicator_id)
      const subject = parsed.subject && parsed.subject !== "Toàn quốc" ? parsed.subject : ""
      const values = Object.entries(entry.values)
        .map(([id, value]) => {
          const source = sourceById(monitor, id)
          if (!source || !Number.isFinite(value)) return null
          const number = parsed.unit ? formatWithUnit(value, parsed.unit) : formatNumber(value)
          if (!number) return null
          return `${publicPublisher(source)}: ${number}`
        })
        .filter((part): part is string => Boolean(part))
      const note = [parsed.free, parsed.measure].filter(Boolean).join(" ") || null
      return {
        name: subject ? `${topic} — ${subject}` : topic,
        period: formatPeriod(entry.period),
        values: values.join("; ") || "–",
        diff: formatWithUnit(entry.diff_pct, "%") || "–",
        tolerance: typeof entry.tolerance_pct === "number" ? formatWithUnit(entry.tolerance_pct, "%") || "–" : "–",
        verdict: VERDICT_LABELS[entry.verdict],
        note,
      }
    }),
    tables: (monitor.model?.tables ?? [])
      .filter((table) => table.layer === "gold")
      .map((table) => ({
        description: table.grain_vi?.trim() || "Bảng đã làm sạch",
        technicalName: table.name,
        detail: table.name.includes("_") || table.name.includes(".") ? null : table.name,
        grain: table.grain_vi?.trim() || "–",
        rows: formatNumber(table.rows),
      })),
    erdHref: fileHref(files, "erd"),
    glossary: GLOSSARY,
    downloads,
    footer: publicFooter(monitor),
  }
}

export function askPage(monitor: Monitor, chatEnabled: boolean): AskPageModel {
  const names = monitor.indicators.map((indicator) => indicator.name_vi.trim()).filter(Boolean)
  const questions = names.length ? ASK_TEMPLATES.map((template, index) => template(names[index % names.length])) : []
  const updated = formatDay(monitor.meta.generated_at)
  const headline = names.length
    ? `${formatNumber(names.length)} chỉ số có thể hỏi${updated ? `, cập nhật ${updated}` : ""}`
    : "Chưa có chỉ số đã xuất bản để hỏi."
  return {
    level: "detail",
    label: "Hỏi đáp về số liệu",
    headline,
    // POST /api/chat reads the analyst dataset, not monitor.json. Keep the input off
    // until that route can answer from the published payload.
    input: false,
    note: chatEnabled
      ? "Kênh hỏi đáp hiện có chưa đọc bản số liệu đã xuất bản, nên trang này không gửi câu hỏi."
      : "Hỏi đáp về số liệu đang tắt. Trang này không nhận câu hỏi.",
    questions,
    generatedAt: monitor.meta.generated_at,
    footer: publicFooter(monitor),
  }
}
