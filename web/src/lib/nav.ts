import { fold } from "./analyst/explain.ts"

export const SECTORS = [
  { id: "public_finance", slug: "tai-chinh-cong", title: "Tài chính công", keywords: ["tai chinh cong", "ngan sach"] },
  { id: "fdi", slug: "fdi", title: "FDI", keywords: ["fdi", "von nuoc ngoai"] },
  { id: "banking", slug: "ngan-hang", title: "Ngân hàng", keywords: ["ngan hang", "tin dung"] },
  { id: "capital_market", slug: "thi-truong-von", title: "Thị trường vốn", keywords: ["thi truong von", "chung khoan"] },
  { id: "real_estate", slug: "bat-dong-san", title: "Bất động sản", keywords: ["bat dong san", "nha dat"] },
] as const

export type SectorSlug = (typeof SECTORS)[number]["slug"]
export type PublicSectorId = (typeof SECTORS)[number]["id"]

type NavChild = { id?: PublicSectorId; title: string; url: string; keywords: readonly string[] }
type NavItem = { title: string; url: string; keywords: readonly string[]; group?: string; children?: readonly NavChild[] }

const sectorChildren: NavChild[] = SECTORS.map((sector) => ({
  id: sector.id,
  title: sector.title,
  url: `/nganh/${sector.slug}`,
  keywords: sector.keywords,
}))

export const NPL_NAV = [
  { title: "Tổng quan", url: "/", en: "Overview", keywords: ["tong quan", "npl", "no xau"] },
  { title: "Ngân hàng", url: "/ngan-hang", en: "Banks", keywords: ["ngan hang", "bank"] },
  { title: "Thị trường", url: "/thi-truong", en: "Market", keywords: ["thi truong", "car"] },
  { title: "Phương pháp", url: "/phuong-phap", en: "Method", keywords: ["phuong phap", "method"] },
  { title: "Dữ liệu", url: "/du-lieu", en: "Data", keywords: ["du lieu", "csv"] },
] as const

export const RATEWATCH_NAV = [
  { title: "Lãi suất hôm nay", url: "/lai-suat", keywords: ["lai suat", "tien gui", "hom nay"] },
  { title: "Bản đồ", url: "/ban-do", keywords: ["ban do", "tinh"] },
  { title: "Chính sách", url: "/chinh-sach", keywords: ["chinh sach", "tran", "bao hiem"] },
  { title: "Phương pháp", url: "/lai-suat/phuong-phap", keywords: ["phuong phap", "nguon"] },
] as const

export const NAV = [
  { title: "Tổng quan", url: "/", keywords: ["overview", "tong quan"] },
  { title: "Chỉ số & ASEAN", url: "/asean", keywords: ["asean", "chi so", "so sanh"] },
  { title: "Ngành", url: "/nganh/tai-chinh-cong", keywords: ["nganh", "sector"], children: sectorChildren },
  { title: "Tỉnh thành", url: "/tinh", keywords: ["tinh", "province"] },
  { title: "Phân tích & Khuyến nghị", url: "/khuyen-nghi", keywords: ["khuyen nghi", "phan tich"] },
  { title: "Dữ liệu & Phương pháp", url: "/phuong-phap", keywords: ["phuong phap", "du lieu"] },
] as const satisfies readonly NavItem[]

const LAB_PAGES = [
  { title: "Tổng quan", slug: "", group: "Phân tích", keywords: ["overview", "dashboard"] },
  { title: "Đề bài", slug: "brief", group: "Phân tích", keywords: ["brief", "question"] },
  { title: "Nguồn dữ liệu", slug: "sources", group: "Dữ liệu", keywords: ["upload", "sources", "ingestion"] },
  { title: "Pipeline", slug: "pipeline", group: "Dữ liệu", keywords: ["lineage", "etl"] },
  { title: "Chất lượng dữ liệu", slug: "quality", group: "Dữ liệu", keywords: ["quality", "missing"] },
  { title: "Mô hình dữ liệu", slug: "model", group: "Dữ liệu", keywords: ["model", "star", "schema"] },
  { title: "SQL Explorer", slug: "sql", group: "Dữ liệu", keywords: ["query", "truy van"] },
  { title: "Hồ sơ dữ liệu", slug: "profile", group: "Dữ liệu", keywords: ["profile", "eda"] },
  { title: "Insight", slug: "insights", group: "Phân tích", keywords: ["finding", "bang chung"] },
  { title: "Drivers & What-if", slug: "drivers", group: "Phân tích", keywords: ["what-if", "scenario", "kich ban"] },
  { title: "Kịch bản what-if", slug: "whatif", group: "Phân tích", keywords: ["whatif", "scenario", "kich ban nhieu bien"] },
  { title: "Phân khúc", slug: "segments", group: "Phân tích", keywords: ["segments", "groups"] },
  { title: "Quyết định", slug: "decision", group: "Kết quả", keywords: ["decision", "recommendation"] },
  { title: "AI Analyst", slug: "analyst", group: "Phân tích", keywords: ["chat", "hoi ai"] },
  { title: "Xuất báo cáo", slug: "report", group: "Kết quả", keywords: ["export", "zip", "deck", "pitch"] },
] as const

export const LAB_NAV = LAB_PAGES.map((page) => ({
  title: page.title,
  url: page.slug ? `/lab/${page.slug}` : "/lab",
  group: page.group,
  keywords: page.keywords,
}))

export type CommandLink = { title: string; url: string; keywords: readonly string[] }

export function sectorBySlug(slug: string) {
  return SECTORS.find((sector) => sector.slug === slug) ?? null
}

export function hrefForIndicatorSector(sector: string): string {
  const known = SECTORS.find((item) => item.id === sector)
  if (known) return `/nganh/${known.slug}`
  if (sector === "province") return "/tinh"
  if (sector === "asean" || sector === "macro") return "/asean"
  return "/"
}

function commandLinks(pages: readonly { title: string; url: string; keywords: readonly string[]; children?: readonly NavChild[] }[]): CommandLink[] {
  return pages.flatMap((page) => [
    { title: page.title, url: page.url, keywords: page.keywords },
    ...(page.children ?? []).map((child) => ({ title: child.title, url: child.url, keywords: child.keywords })),
  ])
}

export function filterCommands(query: string) {
  return commandLinks(NAV).filter((page) => commandScore(page.title, query, [...page.keywords]) > 0)
}

export function filterLabCommands(query: string) {
  return LAB_NAV.filter((page) => commandScore(page.title, query, [...page.keywords]) > 0)
}

export function commandScore(value: string, query: string, keywords: string[] = []): number {
  const text = fold([value, ...keywords].join(" "))
  return fold(query).split(/\s+/).every((word) => text.includes(word)) ? 1 : 0
}

export function titleForPath(
  pathname: string,
  pages: readonly { title: string; url: string; children?: readonly { title: string; url: string }[] }[] = NAV,
): string {
  const candidates = pages.flatMap((page) =>
    page.children?.length ? page.children.map((child) => ({ title: child.title, url: child.url })) : [{ title: page.title, url: page.url }],
  )
  const matches = candidates.filter((page) =>
    page.url === "/" ? pathname === "/" : pathname === page.url || pathname.startsWith(`${page.url}/`),
  )
  matches.sort((left, right) => right.url.length - left.url.length)
  return matches[0]?.title ?? "VietLeap Insight"
}

export function legacyRedirects(labEnabled: boolean) {
  return LAB_PAGES.filter((page) => page.slug).map((page) => ({
    source: `/${page.slug}`,
    destination: labEnabled ? `/lab/${page.slug}` : "/",
    permanent: true as const,
  }))
}

export function whatIfLink(query: string): string | null {
  const match = /^what-if\s+(.+?)\s+([+-]?\d+(?:[.,]\d+)?)%$/i.exec(query.trim())
  if (!match) return null
  const percent = Math.max(-30, Math.min(30, Number(match[2].replace(",", "."))))
  return `/lab/drivers?feature=${encodeURIComponent(match[1])}&pct=${percent}`
}
