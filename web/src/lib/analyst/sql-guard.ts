// Client-side UX pre-check for read-only SQL (server guard in DuckDB / FastAPI remains authoritative).
// Pure functions: no Node/browser globals, safe for unit tests and client components.

const START_ALLOW = /^(?:select|with|describe|summarize|show)\b/i
const FORBIDDEN =
  /\b(?:insert|update|delete|drop|alter|create|replace|truncate|attach|copy|pragma|install|load|call|export|import|set|read_csv|read_parquet|read_json|sniff_csv|parquet_scan|glob)\b/i

/** Strip SQL single/double quoted literals and comments while preserving statement separators (`;`) outside quotes. */
function stripCommentsAndStrings(sql: string): string {
  let out = ""
  let i = 0
  while (i < sql.length) {
    const ch = sql[i]
    const next = sql[i + 1]
    // Line comment
    if (ch === "-" && next === "-") {
      while (i < sql.length && sql[i] !== "\n") i++
      out += " "
      continue
    }
    // Block comment
    if (ch === "/" && next === "*") {
      i += 2
      while (i < sql.length && !(sql[i] === "*" && sql[i + 1] === "/")) i++
      i += 2
      out += " "
      continue
    }
    // Single-quoted string literal (handles '' escape)
    if (ch === "'") {
      i++
      while (i < sql.length) {
        if (sql[i] === "'" && sql[i + 1] === "'") {
          i += 2
          continue
        }
        if (sql[i] === "'") {
          i++
          break
        }
        i++
      }
      out += " '' "
      continue
    }
    // Double-quoted identifier
    if (ch === '"') {
      i++
      while (i < sql.length) {
        if (sql[i] === '"' && sql[i + 1] === '"') {
          i += 2
          continue
        }
        if (sql[i] === '"') {
          i++
          break
        }
        i++
      }
      out += " _ident_ "
      continue
    }
    out += ch
    i++
  }
  return out
}

export function isReadOnlySql(query: string): { ok: boolean; reason?: string } {
  const cleaned = stripCommentsAndStrings(query).trim()
  if (!cleaned) {
    return { ok: false, reason: "Câu truy vấn SQL trống." }
  }
  const withoutTrailingSemi = cleaned.replace(/;+\s*$/, "").trim()
  if (!withoutTrailingSemi) {
    return { ok: false, reason: "Câu truy vấn SQL trống." }
  }
  if (withoutTrailingSemi.includes(";")) {
    return { ok: false, reason: "Chỉ cho phép một câu lệnh SQL duy nhất (không dùng nhiều câu lệnh cách nhau bởi `;`)." }
  }
  if (!START_ALLOW.test(withoutTrailingSemi)) {
    return { ok: false, reason: "Chỉ cho phép câu lệnh bắt đầu bằng SELECT, WITH, DESCRIBE, SUMMARIZE hoặc SHOW." }
  }
  const match = withoutTrailingSemi.match(FORBIDDEN)
  if (match) {
    return { ok: false, reason: `Từ khóa '${match[1]}' bị chặn bởi chính sách chỉ đọc.` }
  }
  return { ok: true }
}

/** Double-quote a SQL identifier safely (escapes internal quotes). */
export function quoteIdent(name: string): string {
  return `"${name.replace(/"/g, '""')}"`
}
