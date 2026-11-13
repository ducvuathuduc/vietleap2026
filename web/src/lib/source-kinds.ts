// How each ingestion connector (engine/vlkit/de/connectors.py) maps to the workshop's source types,
// and how it handles access rights, API limits and anti-blocking. Descriptive text only — no data.
import type { SourceKind } from "@/lib/api/types"

export const SOURCE_KINDS: Record<SourceKind, { label: string; workshop: string; handling: string; uriHint: string }> = {
  sql: {
    label: "Database / JDBC",
    workshop: "Database/JDBC",
    handling: "SQLAlchemy (sqlite/postgres/mysql), chỉ cho phép SELECT, đọc theo chunk, ẩn mật khẩu trong provenance.",
    uriHint: "sqlite:///scenarios/demo/demo.sqlite",
  },
  api: {
    label: "Public API",
    workshop: "Public API",
    handling: "Phân trang page/offset/next, retry 429/5xx theo Retry-After, giới hạn req/s, cache đĩa; token đọc từ biến môi trường.",
    uriHint: "https://api.worldbank.org/v2/country/VN/indicator/NY.GDP.PCAP.CD",
  },
  file: {
    label: "File tải trực tiếp",
    workshop: "File tải trực tiếp",
    handling: "CSV (tự dò encoding/dấu phân cách), Excel nhiều sheet, JSON, Parquet, ZIP.",
    uriHint: "data/practice/synthetic_messy_bds.csv",
  },
  scrape: {
    label: "Web scraping",
    workshop: "Web Scraping",
    handling: "Tôn trọng robots.txt (dừng nếu bị cấm), delay ngẫu nhiên, User-Agent định danh; Playwright chỉ khi trang cần JS; không vượt captcha/đăng nhập.",
    uriHint: "https://vi.wikipedia.org/wiki/Tỉnh_thành_Việt_Nam",
  },
  social: {
    label: "Social listening",
    workshop: "Social listening",
    handling: "RSS/Atom (báo, diễn đàn); Google Trends tuỳ chọn, bắt lỗi giới hạn 429.",
    uriHint: "https://vnexpress.net/rss/kinh-doanh.rss",
  },
  cv: {
    label: "Computer vision",
    workshop: "Quan sát → dữ liệu (CV)",
    handling: "CSV đếm sẵn, hoặc video → scenarios/cv_counting/count.py (YOLO + ByteTrack) → bảng đếm theo thời gian.",
    uriHint: "scenarios/cv_counting/sample_counts.csv",
  },
}

export function fmtSeconds(s: number | undefined): string {
  return s === undefined ? "–" : `${s.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây`
}
