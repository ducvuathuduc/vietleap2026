const SAIGON = "Asia/Saigon"

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return ""
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 }).format(value)
}

/** Percent values are already in percent points (11,5 means 11,5%), matching the payload unit. */
export function formatPercent(value: number | null | undefined): string {
  const number = formatNumber(value)
  return number ? `${number}%` : ""
}

export function formatWithUnit(value: number | null | undefined, unit: string): string {
  const number = formatNumber(value)
  if (!number) return ""
  if (!unit) return number
  if (unit === "%") return `${number}%`
  return `${number} ${unit}`
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: SAIGON,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date)
}

export function formatPeriod(period: string): string {
  const quarter = /^(\d{4})-Q([1-4])$/.exec(period)
  if (quarter) return `Quý ${quarter[2]}/${quarter[1]}`
  const day = /^(\d{4})-(\d{2})-(\d{2})$/.exec(period)
  if (day) return `${day[3]}/${day[2]}/${day[1]}`
  const month = /^(\d{4})-(\d{2})$/.exec(period)
  if (month) return `${month[2]}/${month[1]}`
  return period
}
