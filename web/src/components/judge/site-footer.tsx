import { formatDay } from "./labels"

export interface FooterSource {
  name: string
  license: string
}

export interface SiteFooterProps {
  sources: FooterSource[]
  /** `meta.generated_at`. */
  generatedAt?: string | null
  /** Citation access date; defaults to `generatedAt`. */
  accessedAt?: string | null
  title?: string
  methodsHref?: string
  dataHref?: string
}

const LINK_CLASS =
  "underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"

/** Footer: sources + licence, citation, update time, MIT attribution for the table pattern. */
export function SiteFooter({
  sources,
  generatedAt,
  accessedAt,
  title = "Vietnam Macro-Financial Monitor",
  methodsHref = "/phuong-phap",
  dataHref,
}: SiteFooterProps) {
  const generated = formatDay(generatedAt)
  const accessed = formatDay(accessedAt) || generated
  const year = generated ? generated.slice(-4) : ""
  const sourceLine = sources
    .map((source) => (source.license ? `${source.name} (${source.license})` : source.name))
    .join(", ")

  return (
    <footer className="flex flex-col gap-2 border-t border-border pt-4 text-xs text-muted-foreground">
      {sourceLine ? <p>Nguồn: {sourceLine}</p> : null}
      <p>
        Trích dẫn: VietLeap{year ? ` (${year})` : ""}. {title}.
        {accessed ? ` Truy cập ${accessed}.` : ""}
      </p>
      <p className="flex flex-wrap items-center gap-2">
        <a href={methodsHref} className={LINK_CLASS}>
          Dữ liệu &amp; phương pháp
        </a>
        {dataHref ? (
          <>
            <span aria-hidden="true">·</span>
            <a href={dataHref} className={LINK_CLASS}>
              Tải dữ liệu
            </a>
          </>
        ) : null}
      </p>
      {generated ? <p>Dữ liệu cập nhật {generated} (giờ Việt Nam).</p> : null}
      <p>Bảng dựa trên Kiranism starter (MIT).</p>
    </footer>
  )
}
