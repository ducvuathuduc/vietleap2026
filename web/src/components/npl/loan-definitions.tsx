import type { Lang } from "@/lib/npl/view"

export function LoanDefinitions({ lang }: { lang: Lang }) {
  const vi = lang === "vi"
  const groups = vi
    ? ["Nợ đủ tiêu chuẩn", "Nợ cần chú ý", "Nợ dưới tiêu chuẩn", "Nợ nghi ngờ", "Nợ có khả năng mất vốn"]
    : ["Standard", "Watch-list", "Substandard", "Doubtful", "Potential loss"]
  return (
    <section className="rounded-xl border border-border bg-muted/40 p-3 sm:p-4" aria-labelledby="loan-definitions">
      <h2 id="loan-definitions" className="text-lg font-semibold">{vi ? "Hiểu tỷ lệ nợ xấu" : "Understand the NPL ratio"}</h2>
      <p className="mt-1 text-sm font-medium">
        {vi ? "Tỷ lệ nợ xấu = Dư nợ nhóm 3–5 / Tổng dư nợ." : "NPL ratio = Loans in groups 3–5 / Total loans."}
      </p>
      <div className="mt-2 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <ol className="list-decimal space-y-0.5 pl-5 text-sm">
          {groups.map((name) => <li key={name}>{name}</li>)}
        </ol>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {vi
            ? "Xóa nợ bằng dự phòng đưa khoản nợ ra khỏi số dư nợ xấu trên bảng cân đối. Người vay vẫn có nghĩa vụ trả. Thu hồi nợ là thu được tiền từ khoản vay."
            : "A provision-funded write-off removes the loan from the reported NPL balance. The borrower still owes the debt. Recovery is money actually collected."}
        </p>
      </div>
    </section>
  )
}
