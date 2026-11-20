"use client"

import type { Lang } from "@/lib/npl/view"

const TERMS = {
  vi: [
    ["NPL", "Nợ xấu là các khoản nợ nhóm 3 đến nhóm 5, tính trên dư nợ cho khách hàng."],
    ["Nợ nhóm 2", "Nợ cần chú ý. Nếu nhóm 2 tăng trong lúc nợ xấu giảm, rủi ro có thể chỉ mới chuyển chỗ."],
    ["Bao phủ", "Dự phòng chia cho nợ xấu. Bao phủ giảm có nghĩa là đệm dự phòng mỏng hơn."],
  ],
  en: [
    ["NPL", "Non-performing loans are loans in groups 3 to 5, divided by customer loans."],
    ["Group 2", "Loans that need attention. If group 2 rises while NPL falls, the risk may only have moved."],
    ["Coverage", "Provisions divided by NPL. Lower coverage means a thinner provision buffer."],
  ],
} as const

export function Glossary({ lang }: { lang: Lang }) {
  const rows = TERMS[lang]
  return (
    <details className="max-w-3xl text-sm">
      <summary className="min-h-11 cursor-pointer">{lang === "vi" ? "NPL, nợ nhóm 2 và bao phủ nghĩa là gì" : "What NPL, group 2 and coverage mean"}</summary>
      <div className="flex flex-col gap-2 pt-2 text-muted-foreground">
        {rows.map(([name, text]) => (
          <p key={name}><span className="font-medium text-foreground">{name}. </span>{text}</p>
        ))}
      </div>
    </details>
  )
}
