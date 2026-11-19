import { createReadStream } from "node:fs"
import { stat } from "node:fs/promises"
import path from "node:path"
import { Readable } from "node:stream"
import { connection } from "next/server"

import { defaultMonitorPaths, loadMonitor } from "@/lib/monitor/load"

import { publishedFile } from "../../../_lib/method-view"

const TYPES: Record<string, string> = {
  ".csv": "text/csv; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".mmd": "text/plain; charset=utf-8",
}

export async function GET(_request: Request, { params }: { params: Promise<{ key: string }> }) {
  await connection()
  const { key } = await params
  let full: string | null
  try {
    full = publishedFile(loadMonitor()?.files, key, path.dirname(defaultMonitorPaths().primary))
  } catch {
    return missing()
  }
  if (!full) return missing()

  try {
    const info = await stat(full)
    if (!info.isFile()) return missing()
  } catch {
    return missing()
  }

  const filename = path.basename(full).replace(/["\r\n]/g, "")
  const body = Readable.toWeb(createReadStream(full)) as ReadableStream
  return new Response(body, {
    headers: {
      "Content-Type": TYPES[path.extname(full).toLowerCase()] ?? "application/octet-stream",
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Cache-Control": "no-store",
    },
  })
}

function missing() {
  return new Response("Không tìm thấy tệp.", {
    status: 404,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  })
}
