import { trustText } from "./labels"

export interface TrustLink {
  data?: string
  definition?: string
  csv?: string
}

export interface TrustLineProps {
  sourceName?: string | null
  lastUpdated?: string | null
  nextRelease?: string | null
  links?: TrustLink
  note?: string | null
}

const LINK_CLASS =
  "underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"

/** "Nguồn X · Cập nhật dd/mm/yyyy · Kỳ tới …" plus the three links. Server, no JS. */
export function TrustLine({ sourceName, lastUpdated, nextRelease, links, note }: TrustLineProps) {
  const text = trustText({ sourceName, lastUpdated, nextRelease })
  if (!text) return null

  const anchors: { label: string; href: string; download?: boolean }[] = []
  if (links?.data) anchors.push({ label: "Xem dữ liệu", href: links.data })
  if (links?.definition) anchors.push({ label: "Định nghĩa", href: links.definition })
  if (links?.csv) anchors.push({ label: "Tải CSV", href: links.csv, download: true })

  return (
    <footer className="flex flex-col gap-1 text-xs text-muted-foreground">
      <div className="flex flex-col gap-1 sm:flex-row sm:flex-wrap sm:items-baseline sm:justify-between sm:gap-4">
        <p>{text}</p>
        {anchors.length ? (
          <nav aria-label="Liên kết dữ liệu" className="flex flex-wrap items-center gap-x-2 gap-y-1">
            {anchors.map((anchor, index) => (
              <span key={anchor.label} className="flex items-center gap-2">
                {index > 0 ? <span aria-hidden="true">·</span> : null}
                <a href={anchor.href} download={anchor.download || undefined} className={LINK_CLASS}>
                  {anchor.label}
                </a>
              </span>
            ))}
          </nav>
        ) : null}
      </div>
      {note ? <p>{note}</p> : null}
    </footer>
  )
}
