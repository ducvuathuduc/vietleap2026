import type { Lang } from "@/lib/npl/view"

const VI_MARK = /[À-ỹĐđ]/
const VI_WORD = new Set(["nợ", "quy", "quý", "co", "cờ"])
const VI_PHRASE = new Set(["vi sao", "vì sao", "ngan hang", "ngân hàng"])
const ADVICE_ASCII = /\b(buy|sell|mua|bán|khuyến nghị)\b/i
const ADVICE_WORD = /(?:^|[^\p{L}\p{N}_])(buy|sell|mua|bán|khuyến nghị)(?=$|[^\p{L}\p{N}_])/iu

const REFUSAL: Record<Lang, string> = {
  vi: "Trang này không nói mua hay bán. Nó chỉ cho thấy mức giảm nợ xấu có được các số khác chống lại hay không.",
  en: "This page does not say buy or sell. It only shows whether a fall in bad debt is backed by the other figures.",
}

export function questionLang(text: string): Lang {
  if (VI_MARK.test(text)) return "vi"
  const tokens = text.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean)
  for (const token of tokens) {
    if (VI_WORD.has(token)) return "vi"
  }
  for (let i = 0; i < tokens.length - 1; i++) {
    if (VI_PHRASE.has(`${tokens[i]} ${tokens[i + 1]}`)) return "vi"
  }
  return "en"
}

export function isAdvice(text: string): boolean {
  return ADVICE_ASCII.test(text) || ADVICE_WORD.test(text)
}

export function refusalFor(text: string): string | null {
  if (!isAdvice(text)) return null
  return REFUSAL[questionLang(text)]
}

export function promptsFor(pathname: string): { vi: string; en: string } {
  const path = pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname || "/"
  const bank = /^\/ngan-hang\/([^/]+)/.exec(path)
  if (bank?.[1]) {
    const code = bankCode(bank[1])
    return {
      vi: `Vì sao ${code} có cờ vàng quý này?`,
      en: "Is VCB's NPL fall in 2025Q4 seasonal?",
    }
  }
  if (path === "/giai-ma") {
    return {
      vi: "Cờ vàng nào đang bật ở các ngân hàng lớn?",
      en: "Which large banks have a yellow flag?",
    }
  }
  if (path === "/phuong-phap") {
    return {
      vi: "Vì sao mức giảm quý 4 chưa đủ để kết luận?",
      en: "Why is the Q4 dip not enough to conclude?",
    }
  }
  if (path === "/du-lieu") {
    return {
      vi: "Bảng này gồm những cột nào?",
      en: "Which columns are in this table?",
    }
  }
  if (path === "/thi-truong") {
    return {
      vi: "Giá có phản ứng khi nợ xấu thay đổi không?",
      en: "Does the price react when bad debt changes?",
    }
  }
  return {
    vi: "Mức nợ xấu trung vị mới nhất là bao nhiêu?",
    en: "What is the latest median NPL?",
  }
}

export function visibleText(value: string): string {
  return value
    .replace(/[ \t]*\bM[456]\b(?:[ \t]*[–—-][ \t]*\bM[456]\b)?/gi, "")
    .replace(/[ \t]*\bget_ratios\b/gi, "")
    .replace(/[ \t]*\bconsolidated\b/gi, "")
    .replace(/[ \t]*\btool-[a-z0-9_-]+\b/gi, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/^[ \t]+/, "")
}

function bankCode(raw: string): string {
  try {
    return decodeURIComponent(raw).toUpperCase()
  } catch {
    return raw.toUpperCase()
  }
}
