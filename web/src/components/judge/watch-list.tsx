import { cn } from "cn"

import { enterClass } from "./motion"

export interface WatchItem {
  /** One sentence; the evidence itself lives in the linked chart. */
  text: string
  href?: string
  evidenceLabel?: string
}

export interface WatchListProps {
  items: WatchItem[]
  title?: string
}

/** §6 "Cần theo dõi": one sentence per line plus a link to the evidence. */
export function WatchList({ items, title = "Cần theo dõi" }: WatchListProps) {
  if (!items.length) return null

  return (
    <section className={cn("flex flex-col gap-2", enterClass())}>
      <h2 className="text-xl font-semibold">{title}</h2>
      <ul className="flex flex-col gap-2">
        {items.map((item, index) => (
          <li key={`${index}-${item.text}`} className="flex flex-col gap-0.5 text-sm">
            <span>{item.text}</span>
            {item.href ? (
              <a
                href={item.href}
                className="w-fit text-xs underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                {item.evidenceLabel ?? "Bằng chứng"}
              </a>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
