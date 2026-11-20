import type { Metadata } from "next"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { loadSnapshot } from "@/lib/npl/load"
import { formatGenerated, langFromQuery, methodModel } from "@/lib/npl/view"

export const instant = false

export const metadata: Metadata = {
  title: "Phương pháp",
  description: "Nguồn, các bước làm sạch, lược đồ sao và bảy mô hình của bản NPL.",
}

type Query = Record<string, string | string[] | undefined>

export default async function Page({ searchParams }: { searchParams: Promise<Query> }) {
  const query = await searchParams
  const lang = langFromQuery(query.lang)
  const snapshot = loadSnapshot()
  const model = methodModel(snapshot, lang)
  const vi = lang === "vi"
  return (
    <>
      <h1 className="text-xl font-semibold text-balance">
        {vi
          ? `Cách ra câu quyết định, bản ${formatGenerated(snapshot.meta.generated_at, lang)}.`
          : `How the decision was reached, snapshot ${formatGenerated(snapshot.meta.generated_at, lang)}.`}
      </h1>
      <ol className="flex list-decimal flex-col gap-3 pl-5 text-sm">
        {model.stages.map((stage) => (
          <li key={stage.title}>
            <span className="font-medium">{stage.title}. </span>
            <span className="break-words">{stage.body}</span>
          </li>
        ))}
      </ol>
      <section id="eda" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">
          <a href={model.edaHref}>{vi ? "Tóm tắt EDA" : "EDA summary"}</a>
        </h2>
        <p className="text-sm break-words">{model.edaSummary}</p>
        <p className="text-sm text-muted-foreground">{vi ? "Tệp HTML hồ sơ không có trong bản chụp này. Bảng dưới là nhật ký làm sạch." : "The HTML profile file is not in this snapshot. The table below is the cleaning log."}</p>
      </section>
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Các bước làm sạch" : "Cleaning steps"}</h2>
        <div className="w-full min-w-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{vi ? "Bước" : "Step"}</TableHead>
                <TableHead>{vi ? "Trước" : "Before"}</TableHead>
                <TableHead>{vi ? "Sau" : "After"}</TableHead>
                <TableHead>{vi ? "Việc đã làm" : "What was done"}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {model.cleaning.map((step) => (
                <TableRow key={step.step}>
                  <TableCell>{step.step}</TableCell>
                  <TableCell className="tabular-nums">{step.before}</TableCell>
                  <TableCell className="tabular-nums">{step.after}</TableCell>
                  <TableCell className="whitespace-normal break-words">{step.detail}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>
      <section className="flex min-w-0 flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Lược đồ sao" : "Star schema"}</h2>
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
      <section className="grid gap-3 md:grid-cols-2">
        {model.models.map((item) => (
          <Card key={item.id}>
            <CardHeader>
              <CardTitle>{item.id} · {item.name}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              <p>{item.spec}</p>
              <p className="tabular-nums">{vi ? `n = ${item.n}` : `n = ${item.n}`}</p>
              <p>{item.reading}</p>
              <p className="text-muted-foreground">{item.doesNotShow}</p>
            </CardContent>
          </Card>
        ))}
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Kiểm tra độ vững" : "Robustness"}</h2>
        <ul className="flex flex-col gap-1 text-sm">
          {model.robustness.map((item) => (
            <li key={item.label}><span className="font-medium">{item.label}. </span>{item.text}</li>
          ))}
        </ul>
        <p className="text-sm text-muted-foreground">{model.linkageNote}</p>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Giới hạn" : "Limitations"}</h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
          {model.limitations.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Pháp lý" : "Legal"}</h2>
        {model.legal.map((item) => (
          <p key={item.ref} className="text-sm break-words"><span className="font-medium">{item.ref}. </span>{item.text}</p>
        ))}
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{vi ? "Việc dùng AI" : "AI use"}</h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
          {model.ai.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
      <section className="flex flex-col gap-1 text-sm">
        <h2 className="text-base font-semibold">{vi ? "Cổng chất lượng" : "Quality gates"}</h2>
        {model.quality.map((gate) => (
          <p key={gate.id}><span className="font-medium">{gate.name}</span> · {gate.status} · {gate.detail}</p>
        ))}
      </section>
    </>
  )
}
