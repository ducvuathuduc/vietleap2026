import type { Snapshot, SnapshotBank } from "@/lib/ratewatch/types"
import { formatReadAt } from "@/lib/ratewatch/format"
import type { Lang } from "@/lib/ratewatch/view"

export function LegalFooter({
  snapshot,
  bank,
  lang,
}: {
  snapshot: Snapshot
  bank?: SnapshotBank | null
  lang: Lang
}) {
  const vi = lang === "vi"
  const read = bank?.read_at ? formatReadAt(bank.read_at, lang) : formatReadAt(snapshot.meta.generated_at, lang)
  const lines = vi
    ? [
        "Thông tin tham khảo. Đây là phép tính trên lãi suất đã niêm yết, không phải tư vấn đầu tư chứng khoán theo Điều 4 khoản 32 Luật Chứng khoán số 54/2019/QH14, và không phải lãi suất ngân hàng hứa khi số đó là lãi suất kỳ hạn suy ra.",
        "Hạn mức: Thông tư 05/2026/TT-NHNN, Điều 3, hiệu lực 13/7/2026: tối đa 350.000.000 đồng gốc và lãi, mọi khoản tiền gửi được bảo hiểm của một người tại một tổ chức. Luật 111/2025/QH15, Điều 17, Điều 18, Điều 23. Nghĩa vụ trả phát sinh theo Điều 21 luật đó, không phải khi ngân hàng gặp sự cố nói chung.",
        "Quyết định 32/2021/QĐ-TTg hết hiệu lực 13/7/2026 theo Nghị định 280/2026/NĐ-CP, Điều 36 khoản 2 điểm c. Ngân hàng chính sách không tham gia bảo hiểm tiền gửi: Luật 111, Điều 6.",
        "Trần: Quyết định 2411/QĐ-NHNN, Điều 1, hiệu lực 20/11/2024: 0,5%/năm với không kỳ hạn và dưới 1 tháng; 4,75%/năm với 1 tháng đến dưới 6 tháng. Từ 6 tháng trở lên không có trần này: Thông tư 48/2024/TT-NHNN, Điều 3 khoản 2. Khuyến mại nằm trong trần và phải quy đổi về trả lãi cuối kỳ: khoản 3. Niêm yết tại điểm giao dịch và trên website nếu có: khoản 4.",
        "Phí bảo hiểm do ngân hàng nộp, không thu của người gửi: Luật 111, Điều 19 khoản 7; mức 0,15%/năm: Thông tư 04/2026/TT-NHNN, Điều 4 khoản 1.",
        "Màn hình này không gọi mô hình ngôn ngữ. Mức hoà vốn ghi «phép tính, không phải dự báo».",
      ]
    : [
        "Reference information. This is a calculation on posted rates, not securities-investment advice under Article 4 clause 32 of Securities Law 54/2019/QH14, and not a rate the bank promised when the figure is an implied forward.",
        "Cap: Circular 05/2026/TT-NHNN, Article 3, in force 13/7/2026: at most 350,000,000 VND of principal and interest, all insured deposits of one person at one institution. Law 111/2025/QH15, Articles 17, 18 and 23. The payout obligation arises under Article 21 of that law.",
        "Decision 32/2021/QĐ-TTg expired on 13/7/2026 under Decree 280/2026/NĐ-CP, Article 36 clause 2 point c. Policy banks do not join deposit insurance: Law 111, Article 6.",
        "Ceiling: Decision 2411/QĐ-NHNN, Article 1, in force 20/11/2024: 4.75%/year from 1 month to under 6 months. Terms of 6 months and longer are outside that ceiling: Circular 48/2024/TT-NHNN, Article 3 clause 2.",
        "The insurance premium is paid by the bank, not the depositor: Law 111, Article 19 clause 7; 0.15%/year under Circular 04/2026/TT-NHNN, Article 4 clause 1.",
        "This screen does not call a language model. The renewal figure is a calculation, not a forecast.",
      ]
  return (
    <footer className="flex flex-col gap-2 border-t border-border pt-4 text-xs text-muted-foreground break-words">
      {bank ? (
        <p>
          {vi ? "Đọc lúc" : "Read at"} {read}
          {bank.sheet_url ? (
            <>
              {" · "}
              <a href={bank.sheet_url} className="underline underline-offset-4" rel="noreferrer">
                {bank.sheet_url}
              </a>
            </>
          ) : null}
          {bank.sheet_date ? ` · ${vi ? "ngày biểu" : "sheet"} ${bank.sheet_date}` : ""}
        </p>
      ) : (
        <p>
          {vi ? "Bản số liệu" : "Snapshot"} {formatReadAt(snapshot.meta.generated_at)}
        </p>
      )}
      {lines.map((line) => (
        <p key={line}>{line}</p>
      ))}
      <p>
        <a href="/phuong-phap" className="underline underline-offset-4">
          {vi ? "Phương pháp" : "Method"}
        </a>
        {" · "}
        <a href="/tai-lieu/lai-suat" className="underline underline-offset-4">
          {vi ? "Tải CSV" : "Download CSV"}
        </a>
      </p>
    </footer>
  )
}
