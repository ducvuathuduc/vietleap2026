export function formatPct(value: number, digits = 2, lang: "vi" | "en" = "vi"): string {
  return value.toLocaleString(lang === "en" ? "en-US" : "vi-VN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function formatAmountInput(value: number, lang: "vi" | "en" = "vi"): string {
  return Math.round(value).toLocaleString(lang === "en" ? "en-US" : "vi-VN")
}

export function parseAmountInput(text: string): number | null {
  const digits = text.replace(/\D/g, "")
  if (!digits) return null
  const value = Number(digits)
  return Number.isFinite(value) ? value : null
}

export function formatReadClock(iso: string, lang: "vi" | "en" = "vi"): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const locale = lang === "en" ? "en-GB" : "vi-VN"
  const time = new Intl.DateTimeFormat(locale, {
    timeZone: "Asia/Saigon",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date)
  const day = new Intl.DateTimeFormat(locale, {
    timeZone: "Asia/Saigon",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date)
  return `${time} ${day}`
}

export function formatVnd(value: number, lang: "vi" | "en" = "vi"): string {
  const amount = Math.round(value).toLocaleString(lang === "en" ? "en-US" : "vi-VN")
  return lang === "en" ? `${amount} VND` : `${amount} đ`
}

export function formatSheetDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!match) return iso
  return `${match[3]}/${match[2]}/${match[1]}`
}

export function formatReadAt(iso: string, lang: "vi" | "en" = "vi"): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat(lang === "en" ? "en-GB" : "vi-VN", {
    timeZone: "Asia/Saigon",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}
