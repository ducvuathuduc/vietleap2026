// Number formatting shared by cards, tables and charts (VND-aware, compact).
export function fmtNum(v: number | null | undefined, digits = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–"
  const a = Math.abs(v)
  const units: [number, string][] = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ]
  if (a >= 1e4) {
    for (const [b, u] of units) if (a >= b) return `${Number((v / b).toPrecision(digits))}${u}`
  }
  if (a >= 100) return Math.round(v).toLocaleString("en-US")
  if (a >= 1) return String(Number(v.toPrecision(digits)))
  return String(Number(v.toPrecision(2)))
}

export function fmtPct(v: number | null | undefined, signed = true): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–"
  return `${signed && v > 0 ? "+" : ""}${v.toFixed(1)}%`
}

export function fmtP(p: number | null | undefined): string {
  if (p === null || p === undefined) return "n/a"
  return p < 0.001 ? "p<0.001" : `p=${p.toFixed(3)}`
}
