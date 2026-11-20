import { loadSnapshot } from "@/lib/npl/load"
import { publicCsv } from "@/lib/npl/view"

export function GET() {
  const body = publicCsv(loadSnapshot())
  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": "attachment; filename=\"npl-public.csv\"",
    },
  })
}
