import type { Metadata } from "next"

import { SaverLive } from "@/components/ratewatch/saver-live"
import { selectionFromParams } from "@/lib/ratewatch/decide"
import { loadSnapshot } from "@/lib/ratewatch/load"

export const instant = false

export const metadata: Metadata = {
  title: "Lãi suất hôm nay",
  description: "Kỳ hạn, kênh gửi và phần nằm trong hạn mức bảo hiểm cho một khoản tiền gửi.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const snapshot = loadSnapshot()
  const selection = selectionFromParams(await searchParams, snapshot)
  return <SaverLive snapshot={snapshot} initial={selection} />
}
