import type { Metadata } from "next"

import { QuarterChart } from "@/components/npl/charts"
import { HowToRead } from "@/components/npl/how-to-read"
import { buttonVariants } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { loadSnapshot } from "@/lib/npl/load"
import {
  formatNumber,
  formatStamp,
  langFromQuery,
  methodModel,
  overviewModel,
  pageHref,
  type Lang,
  type Ownership,
} from "@/lib/npl/view"
import { cn } from "cn"

export const instant = false

export const metadata: Metadata = {
  title: "Phương pháp",
  description: "Câu kết luận, kiểm tra độ vững, các mô hình, lược đồ và nguồn của bản NPL.",
}

type Query = Record<string, string | string[] | undefined>

function one(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? ""
}

function ownershipOf(value: string): Ownership {
  return value === "state" || value === "private" ? value : "all"
}

function readLabel(lang: Lang): string {
  return lang === "vi" ? "Cách đọc" : "How to read"
}

function blocked(value: string): boolean {
  const folded = value.toLowerCase()
  return folded.includes("get" + "_ratios") || folded.includes("consol" + "idated")
}

function sourceTitle(name: string, vi: boolean): string {
  const text = name.toLowerCase()
  if (text.includes("fiin")) {
    return vi
      ? "FiinQuant (FiinGroup), báo cáo tài chính hợp nhất"
      : "FiinQuant (FiinGroup), group financial statements"
  }
  if (text.includes("deadline") || text.includes("article") || text.includes("lịch")) {
    return vi ? "Lịch hạn công bố báo cáo" : "Disclosure deadline calendar"
  }
  if (text.includes("world") || text.includes("fb.ast")) {
    return vi ? "Chỉ số Ngân hàng Thế giới" : "World Bank indicators"
  }
  if (text.includes("sbv") || text.includes("nhnn") || text.includes("hệ thống")) {
    return vi ? "Số liệu hệ thống Ngân hàng Nhà nước" : "State Bank system figures"
  }
  if (text.includes("techcombank")) {
    return vi ? "Báo cáo tài chính Techcombank" : "Techcombank financial statements"
  }
  if (text.includes("legal") || text.includes("văn bản")) {
    return vi ? "Sổ văn bản pháp luật" : "Legal register"
  }
  if (text.includes("filing") || text.includes("công bố")) {
    return vi ? "Ngày công bố báo cáo" : "Filing dates"
  }
  if (text.includes("price") || text.includes("giá") || text.includes("valuation") || text.includes("foreign")) {
    return vi ? "Giá và giao dịch trên thị trường" : "Market prices and trading"
  }
  return vi ? "Nguồn số liệu" : "Data source"
}

function sourceSentence(
  source: { name: string; method: string; retrieved_at: string; rows: number },
  lang: Lang,
): string {
  const vi = lang === "vi"
  const title = sourceTitle(source.name, vi)
  const rows = formatNumber(source.rows, lang, 0)
  const when = formatStamp(source.retrieved_at)
  const how = blocked(source.method)
    ? ""
    : source.method === "api"
      ? vi ? "qua API" : "via the API"
      : source.method === "file"
        ? vi ? "từ tệp" : "from a file"
        : vi ? `bằng ${source.method}` : `via ${source.method}`
  if (vi) return how ? `${title}. ${rows} dòng, lấy lúc ${when}, ${how}.` : `${title}. ${rows} dòng, lấy lúc ${when}.`
  return how ? `${title}. ${rows} rows, retrieved ${when}, ${how}.` : `${title}. ${rows} rows, retrieved ${when}.`
}

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const query = await searchParams
  const lang = langFromQuery(query.lang)
  const ownership = ownershipOf(one(query.own))
  const dropEarly = one(query.drop) === "1"
  const snapshot = await loadSnapshot()
  const baseline = overviewModel(snapshot, lang)
  const selected = overviewModel(snapshot, lang, { ownership, dropEarly })
  const model = methodModel(snapshot, lang)
  const vi = lang === "vi"
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">{baseline.plainHeadline}</h1>
      <p className="text-sm text-muted-foreground">{baseline.evidenceLine} {selected.decision}</p>
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Kiểm tra độ vững" : "Robustness check"}</h2>
        <div className="flex flex-wrap items-center gap-2">
          {(["all", "state", "private"] as const).map((item) => (
            <a
              key={item}
              href={pageHref("/phuong-phap", lang, { own: item === "all" ? undefined : item, drop: dropEarly && selected.dropEnabled ? "1" : undefined })}
              className={cn(buttonVariants({ variant: ownership === item ? "secondary" : "outline", size: "sm" }), "min-h-11")}
              aria-current={ownership === item ? "true" : undefined}
            >
              {item === "all" ? (vi ? "Cả nhóm" : "All") : item === "state" ? (vi ? "Nhà nước" : "State") : (vi ? "Tư nhân" : "Private")}
            </a>
          ))}
          {selected.dropEnabled ? (
            <a
              href={pageHref("/phuong-phap", lang, { own: ownership === "all" ? undefined : ownership, drop: dropEarly ? undefined : "1" })}
              className={cn(buttonVariants({ variant: dropEarly ? "secondary" : "outline", size: "sm" }), "min-h-11")}
              aria-current={dropEarly ? "true" : undefined}
            >
              {vi ? "Bỏ 2021–2022" : "Drop 2021–2022"}
            </a>
          ) : (
            <button type="button" className={cn(buttonVariants({ variant: "outline", size: "sm" }), "min-h-11")} disabled>
              {vi ? "Bỏ 2021–2022" : "Drop 2021–2022"}
            </button>
          )}
        </div>
        {selected.dropReason ? <p className="text-sm text-muted-foreground">{selected.dropReason}</p> : null}
        {dropEarly && selected.dropEnabled && ownership !== "all" ? (
          <p className="text-sm text-muted-foreground">
            {vi ? "Đang dùng mẫu bỏ 2021–2022. Mẫu đó không tách nhà nước và tư nhân." : "Showing the sample that drops 2021–2022. That sample is not split by ownership."}
          </p>
        ) : null}
        <QuarterChart bars={selected.bars} lang={lang} />
        <HowToRead
          label={readLabel(lang)}
          sentences={vi
            ? ["Cột là mức nợ xấu quý 2, 3 và 4 khác quý 1, sau khi trừ phần riêng của từng ngân hàng.", "Râu trên cột là khoảng tin cậy 95%. Quý 1 là mốc 0."]
            : ["The bars are how Q2, Q3 and Q4 differ from Q1 after each bank's own level is removed.", "The whiskers are the 95% confidence interval. Q1 is the zero line."]}
        />
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">{vi ? "Các mô hình, nói bằng lời" : "Models, in words"}</h2>
        <ul className="flex flex-col gap-3 text-sm">
          {model.models.map((item) => (
            <li key={item.id} className="flex flex-col gap-1">
              <p className="font-medium">{item.name}</p>
              <p>{item.reading}</p>
              <p className="text-muted-foreground">{item.doesNotShow}</p>
            </li>
          ))}
        </ul>
      </section>
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Mô hình dữ liệu" : "Data model"}</h2>
        <div className="w-full min-w-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{vi ? "Bảng" : "Table"}</TableHead>
                <TableHead>{vi ? "Khóa" : "Keys"}</TableHead>
                <TableHead>{vi ? "Một dòng là" : "One row is"}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {model.schema.map((table) => (
                <TableRow key={table.table}>
                  <TableCell>{table.table}</TableCell>
                  <TableCell>{table.keys}</TableCell>
                  <TableCell>{table.grain}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Nguồn" : "Sources"}</h2>
        <ul className="flex flex-col gap-2 text-sm">
          {snapshot.meta.sources.map((source) => (
            <li key={source.id}>{sourceSentence(source, lang)}</li>
          ))}
        </ul>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Giới hạn" : "Limitations"}</h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
          {model.limitations.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Việc dùng AI" : "AI use"}</h2>
        <p className="text-sm">{model.ai.join(" ")}</p>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Pháp lý" : "Legal"}</h2>
        {model.legal.map((item) => (
          <p key={item.ref} className="text-sm break-words"><span className="font-medium">{item.ref}. </span>{item.text}</p>
        ))}
      </section>
    </>
  )
}
