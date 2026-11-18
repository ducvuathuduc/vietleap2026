import { NextResponse } from "next/server"
import { jsonError } from "@/lib/engine/http"
import { createUploadJob, listDatasets } from "@/lib/engine/store"

export function GET() {
  return NextResponse.json(listDatasets())
}

export async function POST(req: Request) {
  try {
    const form = await req.formData()
    const file = form.get("file")
    if (!(file instanceof File) || file.size === 0) {
      return NextResponse.json({ detail: "empty or missing file" }, { status: 422 })
    }
    const buf = Buffer.from(await file.arrayBuffer())
    const job = createUploadJob({
      filename: file.name || "dataset.csv",
      buffer: buf,
      name: (form.get("name") as string | null) || null,
      domain: (form.get("domain") as string | null) || "auto",
      target: (form.get("target") as string | null) || null,
      time: (form.get("time") as string | null) || null,
      geo: (form.get("geo") as string | null) || null,
    })
    return NextResponse.json(job, { status: 202 })
  } catch (e) {
    return jsonError(e, 400)
  }
}
