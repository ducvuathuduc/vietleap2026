import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

import { frequencyLabel } from "./labels"

export interface KnowBoxProps {
  definition: string
  /** Comparability caveat, e.g. a definition change or a partial period (§7.6). */
  note?: string | null
  unit?: string | null
  frequency?: string | null
  title?: string
}

const LABEL = "text-xs text-muted-foreground sm:w-28 sm:shrink-0"

/** §7.6 "Điều cần biết": definition, comparability, unit, frequency. */
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
    <Collapsible className="rounded-xl border border-border bg-card">
      <CollapsibleTrigger className="flex w-full items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
        {title}
      </CollapsibleTrigger>
      <CollapsibleContent className="px-4 pb-3">
        <dl className="flex flex-col gap-2 text-sm">
          {rows.map((row) => (
            <div key={row.term} className="flex flex-col gap-0.5 sm:flex-row sm:gap-2">
              <dt className={LABEL}>{row.term}</dt>
              <dd className="leading-relaxed">{row.detail}</dd>
            </div>
          ))}
        </dl>
      </CollapsibleContent>
    </Collapsible>
  )
}
