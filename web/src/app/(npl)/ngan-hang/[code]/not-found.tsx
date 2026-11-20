"use client"

import { Suspense } from "react"
import { useSearchParams } from "next/navigation"

import { pageHref, type Lang } from "@/lib/npl/view"

function MissingBank({ lang }: { lang: Lang }) {
  const vi = lang === "vi"
  return (
    <section className="mx-auto flex w-full max-w-lg flex-col gap-3 py-12">
      <h1 className="text-xl font-semibold">{vi ? "Không tìm thấy" : "Bank not found"}</h1>
      <p className="text-sm text-muted-foreground">
        {vi ? "Mã ngân hàng này không có trong bộ số liệu." : "That ticker is unavailable in the published data."}
      </p>
      <a href={pageHref("/ngan-hang", lang)} className="w-fit text-sm underline underline-offset-4">
        {vi ? "Xem danh sách ngân hàng" : "Browse listed banks"}
      </a>
    </section>
  )
}

function LocalizedMissingBank() {
  return <MissingBank lang={useSearchParams().get("lang") === "en" ? "en" : "vi"} />
}

export default function NotFound() {
  return (
    <Suspense fallback={<MissingBank lang="vi" />}>
      <LocalizedMissingBank />
    </Suspense>
  )
}
