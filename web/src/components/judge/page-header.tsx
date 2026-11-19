import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "cn"

import { levelLabel, updateBadge, type JudgeLevel } from "./labels"
import { enterClass } from "./motion"

export interface PageHeaderAction {
  label: string
  href: string
}

export interface PageHeaderProps {
  level: JudgeLevel
  /** One conclusion sentence with a number and a period, ≤120 characters. */
  headline: string
  /** 1–3 lead sentences. */
  lead?: string[]
  generatedAt?: string | null
  /** Overrides the "Cập nhật dd/mm/yyyy" badge when a page knows better. */
  updatedLabel?: string | null
  actions?: PageHeaderAction[]
}

export function PageHeader({ level, headline, lead = [], generatedAt, updatedLabel, actions = [] }: PageHeaderProps) {
  const badge = updatedLabel ?? updateBadge(generatedAt)

  return (
    <header className={cn("flex flex-col gap-3", enterClass())}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <p className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">{levelLabel(level)}</p>
        {badge ? (
          <Badge variant="outline" className="font-normal text-muted-foreground">
            {badge}
          </Badge>
        ) : null}
        {actions.length ? (
          <div className="ml-auto flex flex-wrap items-center gap-2">
            {actions.map((action) => (
              <Button
                key={action.label}
                variant="outline"
                size="sm"
                nativeButton={false}
                render={<a href={action.href} />}
              >
                {action.label}
              </Button>
            ))}
          </div>
        ) : null}
      </div>
      <h1 className="text-3xl font-semibold tracking-tight text-balance">{headline}</h1>
      {lead.length ? (
        <div className="flex max-w-3xl flex-col gap-1">
          {lead.map((paragraph) => (
            <p key={paragraph} className="text-base text-muted-foreground">
              {paragraph}
            </p>
          ))}
        </div>
      ) : null}
    </header>
  )
}
