import { frequencyLabel } from "./labels"

export interface KnowBoxProps {
  definition: string
  /** Comparability caveat, e.g. a definition change or a partial period. */
  note?: string | null
  unit?: string | null
  frequency?: string | null
  title?: string
}

const LABEL = "text-xs text-muted-foreground sm:w-28 sm:shrink-0"

/** "Điều cần biết": definition, comparability, unit, frequency. Native `<details>`, no JS. */
export function KnowBox({
  definition,
  note,
  unit,
  frequency,
  title = "Điều cần biết về chỉ số này",
}: KnowBoxProps) {
  const rows: { term: string; detail: string }[] = [{ term: "Định nghĩa", detail: definition }]
  if (note) rows.push({ term: "Lưu ý so sánh", detail: note })
  if (unit) rows.push({ term: "Đơn vị", detail: unit })
  const frequencyText = frequencyLabel(frequency)
  if (frequencyText) rows.push({ term: "Tần suất", detail: frequencyText })

  return (
    <details className="rounded-xl border border-border bg-card">
      <summary className="cursor-pointer list-none px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
        {title}
      </summary>
      <dl className="flex flex-col gap-2 px-4 pb-3 text-sm">
        {rows.map((row) => (
          <div key={row.term} className="flex flex-col gap-0.5 sm:flex-row sm:gap-2">
            <dt className={LABEL}>{row.term}</dt>
            <dd className="leading-relaxed">{row.detail}</dd>
          </div>
        ))}
      </dl>
    </details>
  )
}
