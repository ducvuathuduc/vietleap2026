import { connection } from "next/server"

import { loadSnapshot } from "@/lib/npl/load"
import { publicCsv } from "@/lib/npl/view"

export async function GET() {
  await connection()
  const body = publicCsv(await loadSnapshot())
  return new Response(body, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": "attachment; filename=\"npl-public.csv\"",
    },
  })
}
