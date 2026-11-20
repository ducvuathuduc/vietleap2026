import type { Metadata } from "next"

import { ProvinceMap } from "@/components/ratewatch/province-map"
import { selectionFromParams } from "@/lib/ratewatch/decide"
import { loadSnapshot } from "@/lib/ratewatch/load"

export const instant = false

export const metadata: Metadata = {
  title: "Bản đồ",
  description: "34 tỉnh, thành và chỗ nào bản số liệu đã có chi nhánh, tiền gửi.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const snapshot = loadSnapshot()
  const selection = selectionFromParams(await searchParams, snapshot)
  return <ProvinceMap snapshot={snapshot} lang={selection.lang} bankCode={selection.bank} />
}
