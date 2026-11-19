import { NextResponse } from "next/server"
import { guardApi } from "@/lib/api-guard"

export function GET(req: Request) {
  const denied = guardApi(req)
  if (denied) return denied
  return NextResponse.json({
    kinds: ["file", "api", "sql", "scrape", "social", "cv"],
    examples: {
      file: { uri: "data/practice/wdi_asia_fiscal_panel.csv" },
      api: {
        uri: "https://api.worldbank.org/v2/country/VN/indicator/NY.GDP.PCAP.CD",
        options: { params: { format: "json", per_page: 100 }, records_path: "1", paging: "worldbank" },
      },
      sql: { uri: "sqlite:///scenarios/demo/demo.sqlite", options: { query: "SELECT * FROM t" } },
      scrape: { uri: "https://vi.wikipedia.org/wiki/Tỉnh_thành_Việt_Nam", options: { table_index: "largest" } },
      social: { uri: "https://vnexpress.net/rss/kinh-doanh.rss" },
      cv: { uri: "scenarios/cv_counting/sample_counts.csv" },
    },
  })
}
