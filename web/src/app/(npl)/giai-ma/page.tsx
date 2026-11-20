import type { Metadata } from "next"

import { DecoderTable } from "@/components/npl/decoder-table"
import { loadSnapshot } from "@/lib/npl/load"
import { decoderModel, langFromQuery, pageHref } from "@/lib/npl/view"

export const instant = false

export const metadata: Metadata = {
  title: "Giải mã nợ xấu",
  description: "Cờ nợ xấu của mọi ngân hàng niêm yết, mọi quý trong bản chụp.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const lang = langFromQuery((await searchParams).lang)
  const model = decoderModel(loadSnapshot(), lang, "all")
  const vi = lang === "vi"
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">{vi ? "Mọi ngân hàng, mọi quý" : "Every bank, every quarter"}</h1>
      <p className="text-sm text-muted-foreground">{model.note}</p>
      <p><a className="text-sm underline underline-offset-4" href={pageHref("/", lang)}>{vi ? "Về tám ngân hàng lớn" : "Back to the eight large banks"}</a></p>
      <DecoderTable model={model} lang={lang} />
    </>
  )
}
