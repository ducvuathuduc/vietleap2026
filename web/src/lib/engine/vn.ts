import fs from "node:fs"
import path from "node:path"

/** Find workspace root (whether cwd is / or /web). */
export function repoRoot(): string {
  const cwd = process.cwd()
  if (fs.existsSync(path.join(cwd, "data")) && fs.existsSync(path.join(cwd, "scenarios"))) {
    return cwd
  }
  const parent = path.resolve(cwd, "..")
  if (fs.existsSync(path.join(parent, "data")) && fs.existsSync(path.join(parent, "scenarios"))) {
    return parent
  }
  return cwd
}

export function nfc(s: string): string {
  return s.normalize("NFC")
}

const VI_MAP: Record<string, string> = {
  à: "a", á: "a", ạ: "a", ả: "a", ã: "a", â: "a", ầ: "a", ấ: "a", ậ: "a", ẩ: "a", ẫ: "a",
  ă: "a", ằ: "a", ắ: "a", ặ: "a", ẳ: "a", ẵ: "a",
  è: "e", é: "e", ẹ: "e", ẻ: "e", ẽ: "e", ê: "e", ề: "e", ế: "e", ệ: "e", ể: "e", ễ: "e",
  ì: "i", í: "i", ị: "i", ỉ: "i", ĩ: "i",
  ò: "o", ó: "o", ọ: "o", ỏ: "o", õ: "o", ô: "o", ồ: "o", ố: "o", ộ: "o", ổ: "o", ỗ: "o",
  ơ: "o", ờ: "o", ớ: "o", ợ: "o", ở: "o", ỡ: "o",
  ù: "u", ú: "u", ụ: "u", ủ: "u", ũ: "u", ư: "u", ừ: "u", ứ: "u", ự: "u", ử: "u", ữ: "u",
  ỳ: "y", ý: "y", ỵ: "y", ỷ: "y", ỹ: "y", đ: "d",
}

export function unidecodeVi(s: string): string {
  return nfc(s)
    .toLowerCase()
    .replace(/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/g, (ch) => VI_MAP[ch] ?? ch)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
}

export function asciiKey(s: string): string {
  return unidecodeVi(String(s))
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
}

export function slug(s: string): string {
  return asciiKey(s).replace(/\s+/g, "_") || "col"
}

export function cleanText(v: unknown): string {
  if (v === null || v === undefined) return ""
  return nfc(String(v)).replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim()
}

const NULL_WORDS = new Set([
  "", "nan", "none", "null", "n/a", "na", "-", "--", "thoa thuan", "lien he",
  "khong ro", "chua co", "dang cap nhat", "x", "..", "...", "#n/a", "#value!", "#div/0!",
])

function toFloat(tok: string, decimal: "," | "."): number | null {
  let s = tok.trim().replace(/\s+/g, "")
  const neg = s.startsWith("(") && s.endsWith(")")
  s = s.replace(/^\(|\)$/g, "")
  if (!s) return null
  const sign = s.startsWith("-") ? -1 : 1
  s = s.replace(/^[+-]/, "")
  const hasDot = s.includes(".")
  const hasComma = s.includes(",")
  let dec: "." | "," = "."
  if (hasDot && hasComma) {
    dec = s.lastIndexOf(".") > s.lastIndexOf(",") ? "." : ","
  } else if (hasComma) {
    const parts = s.split(",")
    if (parts.length > 2) dec = "."
    else if (parts[1].length === 3 && decimal === ".") dec = "."
    else dec = parts[1].length !== 3 || decimal === "," ? "," : "."
  } else if (hasDot) {
    const parts = s.split(".")
    if (parts.length > 2) dec = ","
    else if (parts[1].length === 3 && decimal === ",") dec = ","
    else dec = "."
  }
  s = dec === "," ? s.replace(/\./g, "").replace(",", ".") : s.replace(/,/g, "")
  const v = Number(s)
  if (!Number.isFinite(v)) return null
  return neg ? -v : sign * v
}

export function detectDecimal(values: unknown[]): "," | "." {
  let comma = 0
  let dot = 0
  for (const v of values) {
    if (typeof v !== "string") continue
    const s = v.replace(/\s+/g, "")
    if (/\d,\d{1,2}(?!\d)|\d\.\d{3}\.\d{3}|\d\.\d{3},\d/.test(s)) comma++
    if (/\d\.\d{1,2}(?!\d)|\d,\d{3},\d{3}|\d,\d{3}\.\d/.test(s)) dot++
  }
  return comma > dot ? "," : "."
}

export function parseVnNumber(raw: unknown, decimal: "," | "." = ","): number | null {
  if (typeof raw === "number") return Number.isFinite(raw) ? raw : null
  if (raw === null || raw === undefined) return null
  const text = cleanText(raw)
  const key = asciiKey(text)
  if (!text || NULL_WORDS.has(key)) return null

  const lower = unidecodeVi(text)
  // Handle compound VN units like "5 ty 763 trieu"
  const compound = lower.match(/(\d[\d.,]*)\s*(?:ty|ti)\s*(\d[\d.,]*)\s*(?:trieu|tr)/)
  if (compound) {
    const a = toFloat(compound[1], decimal)
    const b = toFloat(compound[2], decimal)
    if (a !== null && b !== null) return a * 1e9 + b * 1e6
  }

  const numMatch = text.match(/\(?[-+]?\d[\d.,\s]*\)?/)
  if (!numMatch) return null
  // Reject dates like 13/11/2023 or 2024-01-05
  if (/^\d{1,4}[/-]\d{1,2}[/-]\d{1,4}$/.test(text.trim())) return null

  const base = toFloat(numMatch[0], decimal)
  if (base === null) return null

  // Check unit multipliers (skip m2 / m² unit suffixes so area stays in m²)
  if (/\b(?:ty|ti)\b/.test(lower)) return base * 1e9
  if (/\b(?:trieu|tr)\b/.test(lower)) return base * 1e6
  if (/\b(?:nghin|ngan)\b/.test(lower)) return base * 1e3
  return base
}

export function parseVnDate(raw: unknown): string | null {
  if (raw === null || raw === undefined) return null
  const s = cleanText(raw)
  if (!s) return null
  // YYYY
  if (/^(19|20)\d{2}$/.test(s)) return `${s}-01-01`
  // DD/MM/YYYY or DD-MM-YYYY
  const dmy = s.match(/^(\d{1,2})[/-](\d{1,2})[/-]((?:19|20)\d{2})$/)
  if (dmy) {
    const d = Number(dmy[1])
    const m = Number(dmy[2])
    const y = Number(dmy[3])
    if (m >= 1 && m <= 12 && d >= 1 && d <= 31) {
      return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`
    }
  }
  // YYYY-MM-DD or YYYY/MM/DD
  const ymd = s.match(/^((?:19|20)\d{2})[/-](\d{1,2})[/-](\d{1,2})/)
  if (ymd) {
    return `${ymd[1]}-${ymd[2].padStart(2, "0")}-${ymd[3].padStart(2, "0")}`
  }
  return null
}

let _provinceCache: { map63to34: Map<string, string>; regionMap: Map<string, string> } | null = null

function loadProvinceMaps() {
  if (_provinceCache) return _provinceCache
  const map63to34 = new Map<string, string>()
  const regionMap = new Map<string, string>()
  try {
    const root = repoRoot()
    const p63 = path.join(root, "engine/vlkit/resources/province_63_to_34.csv")
    if (fs.existsSync(p63)) {
      const lines = fs.readFileSync(p63, "utf-8").split(/\r?\n/).slice(1)
      for (const l of lines) {
        const cols = l.split(",")
        if (cols.length >= 2) {
          const oldName = cleanText(cols[0])
          const newName = cleanText(cols[1])
          if (oldName && newName) {
            map63to34.set(asciiKey(oldName), newName)
            map63to34.set(asciiKey(newName), newName)
          }
        }
      }
    }
    const preg = path.join(root, "engine/vlkit/resources/province_region.csv")
    if (fs.existsSync(preg)) {
      const lines = fs.readFileSync(preg, "utf-8").split(/\r?\n/).slice(1)
      for (const l of lines) {
        const cols = l.split(",")
        if (cols.length >= 2) {
          const prov = cleanText(cols[0])
          const reg = cleanText(cols[1])
          if (prov && reg) regionMap.set(asciiKey(prov), reg)
        }
      }
    }
  } catch {
    /* optional resource */
  }
  // Common English/unaccented aliases aligned with province_63_to_34.csv
  map63to34.set("ha noi", "Hà Nội")
  map63to34.set("hanoi", "Hà Nội")
  map63to34.set("tp ho chi minh", "Hồ Chí Minh")
  map63to34.set("ho chi minh", "Hồ Chí Minh")
  map63to34.set("ho chi minh city", "Hồ Chí Minh")
  map63to34.set("hcm", "Hồ Chí Minh")
  map63to34.set("hcmc", "Hồ Chí Minh")
  map63to34.set("sai gon", "Hồ Chí Minh")
  map63to34.set("hue", "Huế")
  map63to34.set("thua thien hue", "Huế")
  map63to34.set("da nang", "Đà Nẵng")
  map63to34.set("hai phong", "Hải Phòng")
  map63to34.set("can tho", "Cần Thơ")
  _provinceCache = { map63to34, regionMap }
  return _provinceCache
}

export function normalizeProvince(raw: unknown): { canonical: string; region: string | null } {
  const text = cleanText(raw)
  if (!text) return { canonical: "", region: null }
  const { map63to34, regionMap } = loadProvinceMaps()
  const key = asciiKey(text).replace(/^(tinh|thanh pho|tp)\s+/, "")
  const canonical = map63to34.get(key) ?? map63to34.get(asciiKey(text)) ?? text
  const region = regionMap.get(asciiKey(canonical)) ?? regionMap.get(key) ?? null
  return { canonical, region }
}

/** Decode buffer (UTF-16LE/BE with BOM or UTF-8) and parse CSV/TSV into headers + row objects. */
export function parseDelimitedBuffer(buf: Buffer): { headers: string[]; rows: Record<string, string>[]; delimiter: string; preambleLines: number } {
  let text: string
  if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) {
    text = buf.slice(2).toString("utf16le")
  } else if (buf.length >= 2 && buf[0] === 0xfe && buf[1] === 0xff) {
    // Swap bytes for UTF-16BE
    const swapped = Buffer.alloc(buf.length - 2)
    for (let i = 2; i < buf.length - 1; i += 2) {
      swapped[i - 2] = buf[i + 1]
      swapped[i - 1] = buf[i]
    }
    text = swapped.toString("utf16le")
  } else {
    text = buf.toString("utf-8").replace(/^\uFEFF/, "")
  }

  const rawLines = text.split(/\r?\n/).filter((l) => l.trim().length > 0)
  if (rawLines.length === 0) return { headers: [], rows: [], delimiter: ",", preambleLines: 0 }

  // Detect delimiter from first 10 lines
  const sample = rawLines.slice(0, 10)
  const candidates = ["\t", ",", ";", "|"]
  let bestDelim = ","
  let bestScore = -1
  for (const d of candidates) {
    const counts = sample.map((l) => l.split(d).length)
    const maxC = Math.max(...counts)
    const multi = counts.filter((c) => c > 1).length
    const score = multi * 10 + maxC
    if (maxC > 1 && score > bestScore) {
      bestScore = score
      bestDelim = d
    }
  }

  // Skip title/preamble lines (lines with fewer columns than the header line)
  const colCounts = rawLines.slice(0, 10).map((l) => splitCsvLine(l, bestDelim).length)
  const targetCols = Math.max(...colCounts)
  let headerIdx = colCounts.findIndex((c) => c >= targetCols && c > 1)
  if (headerIdx < 0) headerIdx = 0

  const rawHeaders = splitCsvLine(rawLines[headerIdx], bestDelim).map((h, i) => cleanText(h) || `col_${i + 1}`)
  // Ensure unique headers
  const seen = new Map<string, number>()
  const headers = rawHeaders.map((h) => {
    const n = (seen.get(h) ?? 0) + 1
    seen.set(h, n)
    return n === 1 ? h : `${h}_${n}`
  })

  const rows: Record<string, string>[] = []
  for (let i = headerIdx + 1; i < rawLines.length; i++) {
    const vals = splitCsvLine(rawLines[i], bestDelim)
    if (vals.every((v) => !v.trim())) continue
    const rec: Record<string, string> = {}
    headers.forEach((h, idx) => {
      rec[h] = cleanText(vals[idx] ?? "")
    })
    rows.push(rec)
  }
  return { headers, rows, delimiter: bestDelim, preambleLines: headerIdx }
}

function splitCsvLine(line: string, delim: string): string[] {
  if (delim === "\t") return line.split("\t")
  const out: string[] = []
  let cur = ""
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"'
        i++
      } else {
        inQuotes = !inQuotes
      }
    } else if (ch === delim && !inQuotes) {
      out.push(cur)
      cur = ""
    } else {
      cur += ch
    }
  }
  out.push(cur)
  return out
}
