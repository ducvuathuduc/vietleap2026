import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"

export interface EmptyStateProps {
  message: string
  title?: string
  link?: { label: string; href: string }
}

/** One factual sentence plus the source link, never a fake zero. */
export function EmptyState({ message, title = "Chưa có số liệu", link }: EmptyStateProps) {
  return (
    <Empty className="border border-dashed border-border py-8">
      <EmptyHeader>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{message}</EmptyDescription>
      </EmptyHeader>
      {link ? (
        <EmptyContent>
          <a
            href={link.href}
            className="text-xs underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            {link.label}
          </a>
        </EmptyContent>
      ) : null}
    </Empty>
  )
}
