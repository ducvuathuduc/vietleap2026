/**
 * Pure copy/format helpers for the judge component kit.
 * Number formatting stays in `@/lib/monitor/format`; this file only adds the
 * label and date rules the components need.
 */

const SAIGON = "Asia/Saigon"

export type JudgeLevel = "overview" | "drilldown" | "detail"

export const LEVEL_LABELS: Record<JudgeLevel, string> = {
  overview: "Tổng quan · Overview",
  drilldown: "Đào sâu · Drill-down",
  detail: "Chi tiết · Detail",
}

const FREQUENCY_LABELS: Record<string, string> = {
  daily: "hàng ngày",
  weekly: "hàng tuần",
  monthly: "hàng tháng",
  quarterly: "hàng quý",
  annual: "hàng năm",
  snapshot: "một lần",
}

/** 5 grey steps: --chart-1 is the lightest, --chart-5 the darkest. */
export const GREY_STEPS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
] as const

export function levelLabel(level: JudgeLevel): string {
  return LEVEL_LABELS[level]
}

export function frequencyLabel(frequency: string | null | undefined): string {
  if (!frequency) return ""
  return FREQUENCY_LABELS[frequency] ?? ""
}

/** dd/mm/yyyy in Asia/Saigon; period strings keep their period shape. */
export function formatDay(value: string | null | undefined): string {
  if (!value) return ""
  const quarter = /^(\d{4})-Q([1-4])$/.exec(value)
  if (quarter) return `Quý ${quarter[2]}/${quarter[1]}`
  const month = /^(\d{4})-(\d{2})$/.exec(value)
  if (month) return `${month[2]}/${month[1]}`
  const day = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (day) return `${day[3]}/${day[2]}/${day[1]}`
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: SAIGON,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date)
}

/** A 12m percentile maps onto the 5 grey steps; null stays blank (no grey at all). */
export function pctileToStep(pctile: number | null | undefined): number | null {
  if (pctile === null || pctile === undefined || !Number.isFinite(pctile)) return null
  const clamped = Math.min(100, Math.max(0, pctile))
  return Math.min(4, Math.floor(clamped / 20))
}

/** Province groups are ranked onto the same 5 steps; an unknown group stays blank. */
export function groupToStep(group: number | null | undefined, groups: { group: number }[]): number | null {
  if (group === null || group === undefined || groups.length === 0) return null
  const ordered = groups.map((item) => item.group).sort((a, b) => a - b)
  const index = ordered.indexOf(group)
  if (index < 0) return null
  if (ordered.length === 1) return 0
  return Math.round((index / (ordered.length - 1)) * 4)
}

export function stepFill(step: number | null | undefined): string {
  if (step === null || step === undefined) return ""
  return GREY_STEPS[Math.min(4, Math.max(0, step))]
}

/** Dark steps carry light text so the cell stays readable (≥4,5:1). */
export function stepTextClass(step: number | null | undefined): string {
  if (step === null || step === undefined) return ""
  return step >= 3 ? "text-background" : "text-foreground"
}

export function nextReleaseText(nextRelease: string | null | undefined): string {
  const day = formatDay(nextRelease)
  return day ? `Kỳ tới ${day}` : "Chưa có lịch kỳ tới"
}

/** TrustLine copy; an empty source means the caller must not render the block. */
export function trustText(input: {
  sourceName?: string | null
  lastUpdated?: string | null
  nextRelease?: string | null
}): string {
  const source = input.sourceName?.trim()
  if (!source) return ""
  const parts = [`Nguồn ${source}`]
  const updated = formatDay(input.lastUpdated)
  if (updated) parts.push(`Cập nhật ${updated}`)
  parts.push(nextReleaseText(input.nextRelease))
  return parts.join(" · ")
}

export function updateBadge(generatedAt: string | null | undefined): string {
  const day = formatDay(generatedAt)
  return day ? `Cập nhật ${day}` : ""
}

export function emptyPeriodText(frequency?: string | null): string {
  const label = frequencyLabel(frequency)
  return label ? `Chưa có số liệu kỳ này. Nguồn công bố: ${label}.` : "Chưa có số liệu kỳ này."
}

export function partialPeriodText(months: number): string {
  return `Số liệu ${months} tháng, chưa gồm ước tính tháng ${months + 1}.`
}

export function loadErrorText(block: string): string {
  return `Không tải được ${block}. Thử lại.`
}

/** Fail closed: a chart needs at least one source and at least one point. */
export function canRenderChart(input: { sourceIds?: string[]; pointCount?: number }): boolean {
  if (!input.sourceIds?.length) return false
  return (input.pointCount ?? 0) > 0
}

export function figureLabel(number: number | null | undefined, title: string): string {
  return typeof number === "number" && Number.isFinite(number) ? `Hình ${number} · ${title}` : title
}
