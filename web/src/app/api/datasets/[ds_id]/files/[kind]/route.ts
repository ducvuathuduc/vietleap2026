import { NextResponse } from "next/server"
import type { ExportKind } from "@/lib/api/types"
import { buildExportFile } from "@/lib/engine/analyzer"
import { jsonError } from "@/lib/engine/http"
import { getDataset } from "@/lib/engine/store"

export async function GET(_req: Request, context: { params: Promise<{ ds_id: string; kind: string }> }) {
  try {
    const { ds_id, kind } = await context.params
    const ds = getDataset(ds_id)
    const file = buildExportFile(ds, kind as ExportKind)
    if (!file) {
      return NextResponse.json({ detail: `${kind} was not generated for this dataset` }, { status: 404 })
    }
    return new NextResponse(new Uint8Array(file.body), {
      status: 200,
      headers: {
        "Content-Type": file.mime,
        "Content-Disposition": `attachment; filename="${file.filename}"`,
      },
    })
  } catch (e) {
    return jsonError(e)
  }
}
