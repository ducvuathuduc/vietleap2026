import type { Metadata } from "next"

import { LegalFooter } from "@/components/ratewatch/legal-footer"
import { selectionFromParams } from "@/lib/ratewatch/decide"
import { formatReadAt } from "@/lib/ratewatch/format"
import { loadSnapshot } from "@/lib/ratewatch/load"

export const instant = false

export const metadata: Metadata = {
  title: "Phương pháp",
  description: "Cách đọc biểu lãi suất, chấm nguồn, và những gì bản số liệu không làm.",
}

type Query = Record<string, string | string[] | undefined>

const DICTIONARY = [
  ["bank_code", "Mã ngân hàng trên đường dẫn"],
  ["term_months", "Kỳ hạn, tháng"],
  ["channel", "online hoặc quầy"],
  ["tier", "Bậc số dư, trống nếu biểu không tách"],
  ["rate_pct", "Lãi suất %/năm trên biểu"],
  ["grade", "Đã kiểm hai nguồn, một nguồn, hoặc mâu thuẫn"],
  ["sheet_date", "Ngày in trên biểu"],
  ["source_url", "Trang đã đọc"],
  ["read_at", "Giờ đọc, Asia/Saigon"],
] as const

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const snapshot = loadSnapshot()
  const selection = selectionFromParams(await searchParams, snapshot)
  const vi = selection.lang === "vi"
  const { coverage, quality, sources, generated_at: generatedAt } = snapshot.meta
  const stages = vi
    ? [
        ["Thu thập", "Đọc trang và PDF ngân hàng đã niêm yết. Hai cách đọc khi có. Không vượt captcha, không đăng nhập."],
        ["Lưu", "Giữ đường dẫn, giờ đọc và mức chấm của từng dòng. Không đưa dòng thô của nhà cung cấp dữ liệu vào bản công khai."],
        ["Biến đổi", "Gắn Đã kiểm 2 nguồn, 1 nguồn hoặc Mâu thuẫn. Dòng mâu thuẫn không vào phép tính. Dòng không có ngày biểu không vào màn demo."],
        ["Phục vụ", `${coverage.banks_read} ngân hàng có ngày biểu, ${coverage.rows} dòng (${coverage.verified} đã kiểm, ${coverage.single} một nguồn, ${coverage.contested} mâu thuẫn). CSV công khai ở liên kết dưới.`],
      ]
    : [
        ["Ingestion", "Read the bank's posted page or PDF. A second reader when one exists. No captcha and no login."],
        ["Storage", "Keep the URL, the read time and the grade of each row. Vendor raw rows are not in the public edition."],
        ["Transform", "Mark checked on two sources, one source, or contested. Contested rows stay out of the calculation. Rows with no sheet date stay off the demo."],
        ["Serving", `${coverage.banks_read} banks with a sheet date, ${coverage.rows} rows (${coverage.verified} checked, ${coverage.single} single-source, ${coverage.contested} contested). The public CSV is linked below.`],
      ]
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">
        {vi
          ? `Bản đọc ${formatReadAt(generatedAt, selection.lang)}: ${coverage.banks_read}/${coverage.banks_total} ngân hàng có ngày biểu, ${coverage.verified} dòng hai nguồn khớp.`
          : `Read ${formatReadAt(generatedAt, selection.lang)}: ${coverage.banks_read}/${coverage.banks_total} banks have a sheet date, ${coverage.verified} rows match on two sources.`}
      </h1>
      <ol className="flex list-decimal flex-col gap-3 pl-5 text-sm">
        {stages.map(([title, body]) => (
          <li key={title}>
            <span className="font-medium">{title}. </span>
            {body}
          </li>
        ))}
      </ol>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? `${quality.length} cổng trên lần đọc ${formatReadAt(generatedAt, selection.lang)}.` : `${quality.length} gates on the read at ${formatReadAt(generatedAt, selection.lang)}.`}</h2>
        <ul className="flex flex-col gap-1 text-sm">
          {quality.map((gate) => (
            <li key={gate.id}>
              <span className="font-medium">{gate.name}</span> · {gate.status === "pass" ? (vi ? "đạt" : "pass") : gate.status === "warn" ? (vi ? "cảnh báo" : "warn") : (vi ? "không đạt" : "fail")} · {gate.detail}
            </li>
          ))}
        </ul>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? `${sources.length} nguồn ghi trong bản này.` : `${sources.length} sources recorded in this edition.`}</h2>
        <ul className="flex flex-col gap-1 text-sm">
          {sources.map((source) => (
            <li key={source.id} className="break-words">
              {source.publisher} · {source.method}
              {" · "}
              <a href={source.url} className="underline underline-offset-4" rel="noreferrer">{source.url}</a>
            </li>
          ))}
        </ul>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? `${DICTIONARY.length} cột trong CSV công khai.` : `${DICTIONARY.length} columns in the public CSV.`}</h2>
        <ul className="flex flex-col gap-1 text-sm">
          {DICTIONARY.map(([column, meaning]) => (
            <li key={column}>
              <span className="font-medium">{column}</span> — {meaning}
            </li>
          ))}
        </ul>
        <p>
          <a href="/tai-lieu/lai-suat" className="text-sm underline underline-offset-4">{vi ? "Tải CSV công khai" : "Download the public CSV"}</a>
        </p>
      </section>
      <section className="flex flex-col gap-2 text-sm">
        <h2 className="text-base font-semibold">{vi ? "5 giới hạn của bản này. Không có CPI và không có nợ xấu." : "5 limits of this edition. No CPI and no NPL figure."}</h2>
        <ul className="flex list-disc flex-col gap-2 pl-5">
          <li>{vi ? "Không dự báo lãi suất. Mức hoà vốn là phép tính trên hai kỳ đã niêm yết." : "No rate forecast. The break-even figure is a calculation on two posted terms."}</li>
          <li>{vi ? "Dòng mâu thuẫn hiện trong bảng với các mức đã đọc, và không vào phương án." : "Contested rows appear in the table with the values that were read, and they do not enter a plan."}</li>
          <li>{vi ? "Dòng không có ngày in trên biểu ngân hàng không hiện trên màn demo." : "A row with no date printed on the bank sheet is left off the demo."}</li>
          <li>{vi ? "Bản này chưa gắn số nợ xấu, LDR, ROA, P/B. Ô hồ sơ để trống thay vì điền số không có nguồn." : "This edition has no NPL, LDR, ROA or P/B figures. The profile stays empty rather than filling a number that has no source here."}</li>
          <li>{vi ? "Không có CPI trong bản này, nên không in lãi suất thực." : "This edition has no CPI series, so no real rate is shown."}</li>
        </ul>
      </section>
      <LegalFooter snapshot={snapshot} lang={selection.lang} />
    </>
  )
}
