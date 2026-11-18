import { NextResponse } from "next/server"

export async function GET(_req: Request, context: { params: Promise<{ ds_id: string }> }) {
  const { ds_id } = await context.params
  return NextResponse.json({ detail: `conformed.json not found for single-source dataset '${ds_id}'` }, { status: 404 })
}
