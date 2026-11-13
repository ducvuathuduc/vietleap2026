// "Explain-anything": any element tagged with data-insight-target can be inspected and explained by the AI analyst.

export type InsightKind =
  | "kpi"
  | "chart"
  | "insight"
  | "table-row"
  | "segment"
  | "driver"
  | "whatif"
  | "pipeline-stage"
  | "quality"
  | "model"
  | "decision"

export interface InsightContext {
  kind: InsightKind
  id: string
  label: string
  data?: unknown
}

const MAX_DATA_CHARS = 4000

/** Props that make an element inspectable. `data` is what the element shows (kept small). */
export function insightTarget(kind: InsightKind, id: string, label: string, data?: unknown): Record<string, string> {
  const props: Record<string, string> = { "data-insight-target": `${kind}:${id}`, "data-insight-label": label }
  if (data !== undefined) {
    const json = JSON.stringify(data)
    props["data-insight-data"] = json.length <= MAX_DATA_CHARS ? json : JSON.stringify({ truncated: true, preview: json.slice(0, MAX_DATA_CHARS) })
  }
  return props
}

/** Read the context back from a tagged DOM element. */
export function readInsightTarget(el: Element): InsightContext | null {
  const raw = el.getAttribute("data-insight-target")
  if (!raw) return null
  const i = raw.indexOf(":")
  if (i <= 0) return null
  let data: unknown
  const json = el.getAttribute("data-insight-data")
  if (json) {
    try {
      data = JSON.parse(json)
    } catch {
      data = undefined
    }
  }
  return { kind: raw.slice(0, i) as InsightKind, id: raw.slice(i + 1), label: el.getAttribute("data-insight-label") ?? raw, data }
}
