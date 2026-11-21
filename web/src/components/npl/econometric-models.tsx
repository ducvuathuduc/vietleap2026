import { q4HoldoutReading } from "@/lib/npl/judge-view"
import { formatNumber, type Lang, type Snapshot } from "@/lib/npl/view"

export function EconometricModels({ snapshot, lang }: { snapshot: Snapshot; lang: Lang }) {
  const vi = lang === "vi"
  const decoder = snapshot.decoder
  const mentor = Array.isArray(decoder) ? undefined : decoder?.regression?.fiinquant
  const fit = mentor?.full
  const early = snapshot.context?.early_warning
  const event = early?.backtests.rise_in_four
  const seasonal = snapshot.context?.seasonal_adjustment
  const counts = seasonal?.counts
  const decision = snapshot.decision_rule
  const holdout = q4HoldoutReading(decision?.q4_oos, lang)
  const baseline = decision?.q4_oos?.q1_rise_baseline ?? decision?.q1_rise_baseline
  const models = [
    { key: "npl_only", label: vi ? "Chỉ tỷ lệ nợ xấu" : "NPL only" },
    { key: "npl_group2", label: vi ? "Thêm nhóm 2" : "Add Group 2" },
    { key: "full", label: vi ? "Đầy đủ chỉ báo" : "Full indicators" },
  ] as const
  const factors = [
    ["writeoff_ratio", vi ? "Tỷ lệ xóa nợ theo quý" : "Quarterly write-off ratio"],
    ["delta_g2_ratio", vi ? "Thay đổi tỷ lệ nợ nhóm 2" : "Change in Group 2 ratio"],
    ["loan_growth", vi ? "Tăng trưởng dư nợ cùng kỳ" : "Year-over-year loan growth"],
    ["lagged_coverage", vi ? "Bao phủ quý trước" : "Prior-quarter coverage"],
  ] as const
  const samples = [
    [fit?.n, vi ? "Đủ bốn chỉ báo" : "All four indicators"],
    [mentor?.without_writeoff?.n, vi ? "Bỏ xóa nợ" : "Exclude write-offs"],
    [mentor?.available?.n, vi ? "Chỉ dư nợ và bao phủ" : "Loan growth and coverage only"],
  ] as const
  const terms = factors.flatMap(([key, label]) => {
    const term = fit?.terms[key]
    return term ? [{ label, term }] : []
  })
  const allIncludeZero = terms.length === factors.length && terms.every(({ term }) => {
    const [lo, hi] = term.ci95
    return lo != null && hi != null && lo <= 0 && hi >= 0
  })

  return (
    <section aria-labelledby="models-title" className="min-w-0">
      <h2 id="models-title" className="mb-2 text-lg font-semibold">{vi ? "Các mô hình kiểm tra bằng chứng" : "Models that test the evidence"}</h2>
      <div className="divide-y divide-border overflow-hidden rounded-xl border border-border">
        <section id="bank-model" className="scroll-mt-4 grid gap-2 p-3 sm:p-4" aria-labelledby="bank-model-title">
          <h3 className="font-semibold" id="bank-model-title">{vi ? "Hồi quy trong từng ngân hàng" : "Within-bank regression"}</h3>
          <p className="text-sm text-muted-foreground">
            {vi
              ? "Thay đổi tỷ lệ nợ xấu = Mức riêng của ngân hàng + Tổng phần đóng góp từ xóa nợ theo quý, thay đổi tỷ lệ nợ nhóm 2, tăng trưởng dư nợ cùng kỳ và bao phủ quý trước."
              : "Change in NPL ratio = Bank-specific baseline + Combined contributions from quarterly write-offs, the change in Group 2 ratio, year-over-year loan growth and prior-quarter coverage."}
          </p>
          <p className="text-sm">
            {vi ? "Hồi quy bình phương tối thiểu ước tính hệ số riêng cho từng chỉ báo sau khi trừ mức riêng cố định của mỗi ngân hàng."
              : "Ordinary least squares estimates a slope for each indicator after accounting for each bank’s fixed baseline."}
          </p>
          {mentor?.without_writeoff !== undefined ? (
            <>
              <dl className="grid gap-1 rounded-lg bg-muted/55 p-2.5 text-sm sm:grid-cols-3 sm:gap-3">
                {samples.map(([n, label]) => <div key={label} className="flex justify-between gap-3 sm:grid">
                  <dt>{label}</dt>
                  <dd className="font-semibold whitespace-nowrap tabular-nums">{n == null ? "—" : vi ? `${n} quan sát` : `${n} observations`}</dd>
                </div>)}
              </dl>
              {allIncludeZero && <p className="text-sm font-medium">
                {vi ? "Trong mẫu đủ bốn chỉ báo, khoảng tin cậy của cả bốn hệ số đều chứa 0."
                  : "In the four-indicator sample, all four confidence intervals include zero."}
              </p>}
              <p className="text-sm text-muted-foreground">
                {mentor[vi ? "does_not_show_vi" : "does_not_show_en"]}
              </p>
              {terms.length > 0 && <details className="text-sm">
                <summary className="cursor-pointer font-medium underline underline-offset-4">
                  {vi ? "Hệ số và khoảng tin cậy 95%" : "Coefficients and 95% confidence intervals"}
                </summary>
                <dl className="mt-2 grid gap-1.5">
                  {terms.map(({ label, term }) => {
                    const [lo, hi] = term.ci95
                    return <div key={label} className="flex flex-wrap justify-between gap-x-4">
                      <dt>{label}</dt>
                      <dd className="tabular-nums">{formatNumber(term.coefficient, lang, 3)}
                        {lo != null && hi != null && ` (${formatNumber(lo, lang, 3)} ${vi ? "đến" : "to"} ${formatNumber(hi, lang, 3)})`}
                      </dd>
                    </div>
                  })}
                </dl>
              </details>}
            </>
          ) : <p className="text-sm text-muted-foreground">{vi ? "Chưa có kết quả cho mô hình này." : "Results for this model are unavailable."}</p>}
        </section>
        <section id="early-warning" className="scroll-mt-4 grid gap-2 p-3 sm:p-4" aria-labelledby="warning-model-title">
          <h3 className="font-semibold" id="warning-model-title">{vi ? "Cảnh báo sớm ngoài mẫu" : "Early warning on held-out quarters"}</h3>
          <p className="text-sm text-muted-foreground">
            {vi
              ? "Xác suất nợ xấu tăng = Mức riêng của ngân hàng + Phần ước tính từ các chỉ báo hiện tại."
              : "Probability of an NPL increase = Bank-specific baseline + Contribution from current indicators."}
          </p>
          {event?.fits.npl_only?.auc?.estimate != null && early ? (
            <>
              <p className="text-sm">
                {vi
                  ? `Mô hình dùng dữ liệu đến ${early.train_through}, rồi kiểm tra dự báo nợ xấu tăng ít nhất ${formatNumber(early.event_threshold_pp, lang, 1)} điểm % trong bốn quý kế tiếp ở ${event.n_test} quan sát giữ lại.`
                  : `The model trains through ${early.train_through} and tests whether NPL rises at least ${formatNumber(early.event_threshold_pp, lang, 1)} pp within four quarters across ${event.n_test} held-out observations.`}
              </p>
              <dl className="grid gap-1 rounded-lg bg-muted/55 p-2.5 text-sm sm:grid-cols-3 sm:gap-3">
                {models.map(({ key, label }) => {
                  const auc = event.fits[key]?.auc?.estimate
                  return <div className="flex justify-between gap-3 sm:grid" key={key}>
                    <dt>{label}</dt><dd className="font-semibold tabular-nums">{auc == null ? "—" : `AUC ${formatNumber(auc, lang, 3)}`}</dd>
                  </div>
                })}
              </dl>
              <p className="text-sm font-medium">
                {early[`reading_${lang}`].split(vi ? " Với biến cố" : " For a rise")[0]}
              </p>
              <p className="text-xs text-muted-foreground">
                {vi ? "AUC đo khả năng xếp trường hợp sẽ tăng nợ xấu cao hơn trường hợp còn lại. Giá trị cao hơn cho thấy khả năng phân biệt tốt hơn."
                  : "AUC measures how well the forecasts rank cases where NPL will rise above other cases. Higher values indicate better separation."}
              </p>
            </>
          ) : <p className="text-sm text-muted-foreground">{vi ? "Chưa có kết quả chấm dự báo cho giai đoạn giữ lại." : "Held-out forecast results are unavailable."}</p>}
        </section>
        <section id="seasonal-models" className="scroll-mt-4 grid gap-2 p-3 sm:p-4" aria-labelledby="seasonal-model-title">
          <h3 className="font-semibold" id="seasonal-model-title">{vi ? "Điều chỉnh mùa vụ theo từng ngân hàng" : "Bank-specific seasonal adjustment"}</h3>
          <p className="text-sm text-muted-foreground">
            {vi
              ? "Nợ xấu sau điều chỉnh = Nợ xấu công bố − Hiệu ứng quý, tính từ các quý trước của chính ngân hàng."
              : "Adjusted NPL = Reported NPL − The bank’s seasonal effect estimated from earlier quarters."}
          </p>
          {counts && <p className="text-sm font-medium">
            {vi
              ? `${counts.seasonal_only} trong ${counts.adjustable} lần giảm quý 4 có thể điều chỉnh không còn giảm sau khi bỏ nhịp mùa vụ.`
              : `${counts.seasonal_only} of ${counts.adjustable} adjustable Q4 declines stopped falling after seasonal adjustment.`}
          </p>}
          {holdout && <div className="mt-1 grid gap-1">
            <h4 className="text-sm font-medium">{vi ? "Thử với dữ liệu chưa dùng để đặt quy tắc" : "Test the rule on unused data"}</h4>
            <p className="text-sm text-muted-foreground">{holdout}</p>
          </div>}
          {baseline?.share_pct != null && (
            <p className="text-sm text-muted-foreground">
              {vi
                ? `Để so sánh, quý 1 tăng sau ${baseline.rises}/${baseline.n} quý 4 có thể theo dõi (${formatNumber(baseline.share_pct, lang, 1)}%).`
                : `For comparison, Q1 rose after ${baseline.rises} of ${baseline.n} trackable Q4 quarters (${formatNumber(baseline.share_pct, lang, 1)}%).`}
            </p>
          )}
        </section>
      </div>
    </section>
  )
}
