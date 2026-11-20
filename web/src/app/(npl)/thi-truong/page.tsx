import type { Metadata } from "next"

import { MarketBands } from "@/components/npl/market-bands"
import { MarketPricePanel } from "@/components/npl/market-price-panel"
import { marketPriceModel } from "@/lib/npl/judge-view"
import { loadSnapshot } from "@/lib/npl/load"
import { langFromQuery, pageHref } from "@/lib/npl/view"

export const instant = false

export const metadata: Metadata = {
  title: "Thị trường",
  description: "Đối chiếu dự báo giá với giá thực tế và xem P/B theo nhóm nợ xấu.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const lang = langFromQuery((await searchParams).lang)
  const { market } = await loadSnapshot()
  const vi = lang === "vi"
  const study = market.m8
  const targets = study ? { basket: marketPriceModel(study.basket), vnindex: marketPriceModel(study.vnindex) } : null
  const comparison = targets?.basket.lowerError ?? null
  const heading = comparison == null ? (vi ? "Nợ xấu và giá cổ phiếu ngân hàng" : "Bad debt and bank stock prices")
    : comparison ? (vi ? "Dự báo từ nợ xấu có sai số thấp hơn" : "Using NPL gave a lower forecast error")
      : (vi ? "Biết nợ xấu chưa giúp dự báo giá tốt hơn" : "Knowing NPL did not improve the price forecast")
  const bands = study?.band_table.map((row) => ({ id: row.band, label: vi ? row.label_vi : row.label_en, median: row.median_pb })) ?? []
  const terms = study?.bands.spec_i?.terms
  const controlled = bands.filter((band) => band.id !== "lt1").map((band) => terms?.[band.id]?.ci95)
  const allUnclear = controlled.length > 0 && controlled.every((ci) =>
    ci?.[0] != null && ci[1] != null && ci[0] <= 0 && ci[1] >= 0,
  )
  const bandReading = allUnclear
    ? (vi ? "Chênh lệch P/B giữa các nhóm không còn rõ khi tính đến tỷ lệ bao phủ và tăng trưởng dư nợ."
      : "The P/B gap between bands is no longer clear after accounting for coverage and loan growth.")
    : (vi ? "Các cột là mức P/B quan sát được của từng nhóm." : "The bars show the observed P/B for each band.")

  return (
    <>
      <header className="flex min-w-0 flex-col gap-2 pt-3">
        <h1 className="max-w-4xl text-balance text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">{heading}</h1>
        <p className="max-w-3xl text-pretty text-sm leading-relaxed text-muted-foreground sm:text-base">
          {vi ? "So sánh giá thực tế với dự báo từng tháng. Mốc đơn giản để đối chiếu là giữ nguyên giá tháng trước."
            : "Compare actual prices with month-by-month forecasts. The baseline holds the previous month’s price."}
        </p>
      </header>
      <div className="grid min-w-0 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
        <section className="flex min-w-0 flex-col gap-2" aria-labelledby="market-price">
          <h2 id="market-price" className="text-lg font-semibold">{vi ? "Giá thực tế và giá dự báo" : "Actual and predicted prices"}</h2>
          {targets?.basket.points.length
            ? <MarketPricePanel targets={targets} lang={lang} />
            : <p className="text-sm text-muted-foreground">{vi ? "Chưa công bố chuỗi giá dự báo." : "The price forecast is unavailable."}</p>}
        </section>
        <section className="flex min-w-0 flex-col gap-2" aria-labelledby="market-bands">
          <h2 id="market-bands" className="text-lg font-semibold">{vi ? "P/B theo nhóm nợ xấu" : "P/B by NPL band"}</h2>
          {bands.length
            ? <MarketBands rows={bands} lang={lang} reading={bandReading} />
            : <p className="text-sm text-muted-foreground">{vi ? "Chưa có số liệu P/B theo nhóm." : "P/B data by band is unavailable."}</p>}
        </section>
      </div>
      <footer className="flex flex-wrap justify-between gap-2 border-t border-border py-2 text-xs text-muted-foreground">
        <p>{vi ? "Nguồn giá và định giá" : "Price and valuation source"} FiinQuant (FiinGroup)</p>
        <a href={pageHref("/phuong-phap", lang)} className="underline underline-offset-4">{vi ? "Xem phương pháp" : "See the method"}</a>
      </footer>
    </>
  )
}
