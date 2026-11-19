import type { Metadata } from "next"

import { PageHeader } from "@/components/judge/page-header"
import { SiteFooter } from "@/components/judge/site-footer"
import { PageShell } from "@/components/state"

import { JudgeEmpty, readMonitor } from "../judge-screen"
import { methodPage, type MethodIndicatorModel, type MethodSourceModel } from "../_lib/method-view"

export const metadata: Metadata = {
  title: "Dữ liệu và phương pháp",
  description: "Nguồn, định nghĩa, chất lượng, đối chiếu và tệp tải về của bản số liệu đã xuất bản.",
}

const FRAME = "mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6"
const LINK =
  "underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
const H2 = "text-xl font-semibold"

export default async function Page() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  const model = methodPage(monitor)
  const dictionary = model.downloads.find((item) => item.label.startsWith("Từ điển"))

  return (
    <PageShell>
      <div className={FRAME}>
        <PageHeader
          level={model.level}
          headline={model.headline}
          lead={model.lead}
          generatedAt={model.generatedAt}
          actions={dictionary ? [{ label: "Tải từ điển", href: dictionary.href }] : []}
        />

        <section className="flex flex-col gap-3">
          <h2 className={H2}>Các bước</h2>
          <p className="text-xs text-muted-foreground">Mốc thời gian theo giờ Việt Nam.</p>
          <ol className="flex list-decimal flex-col gap-3 pl-5 text-sm">
            {model.steps.map((step) => (
              <li key={step.title} className="flex flex-wrap items-baseline gap-x-3">
                <span>{step.title}</span>
                {step.href ? (
                  <a href={step.href} className={LINK}>
                    Xem tệp
                  </a>
                ) : null}
              </li>
            ))}
          </ol>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className={H2}>Nguồn</h2>
          <div className="flex flex-col gap-2 md:hidden">
            {model.sources.map((source) => (
              <SourceCard key={source.url} source={source} />
            ))}
          </div>
          <div className="hidden overflow-x-auto md:block">
            <SourceTable sources={model.sources} />
          </div>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className={H2}>Danh mục chỉ số</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="hidden text-left text-xs text-muted-foreground md:table-header-group">
                <tr className="border-b border-border">
                  <th className="py-2 pr-3 font-medium">Tên</th>
                  <th className="py-2 pr-3 font-medium">Định nghĩa</th>
                  <th className="py-2 pr-3 font-medium">Đơn vị</th>
                  <th className="py-2 pr-3 font-medium">Tần suất</th>
                  <th className="py-2 pr-3 font-medium">Thước đo</th>
                  <th className="py-2 pr-3 font-medium">Cập nhật</th>
                  <th className="py-2 font-medium">Kỳ tới</th>
                </tr>
              </thead>
              <tbody>
                {model.indicators.map((indicator) => (
                  <IndicatorRow key={indicator.anchor} indicator={indicator} />
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {model.quality.length ? (
          <section className="flex flex-col gap-3">
            <h2 className={H2}>Chất lượng</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="py-2 pr-3 font-medium">Nguồn</th>
                    <th className="py-2 pr-3 font-medium">Số dòng</th>
                    <th className="py-2 pr-3 font-medium">Trước</th>
                    <th className="py-2 pr-3 font-medium">Sau</th>
                    <th className="py-2 font-medium">Cờ</th>
                  </tr>
                </thead>
                <tbody>
                  {model.quality.map((row) => (
                    <tr key={row.source} className="border-b border-border align-top">
                      <td className="py-2 pr-3">{row.source}</td>
                      <td className="py-2 pr-3 tabular-nums">{row.rows}</td>
                      <td className="py-2 pr-3 tabular-nums">{row.before}</td>
                      <td className="py-2 pr-3 tabular-nums">{row.after}</td>
                      <td className="py-2">{row.flags}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        {model.reconciliation.length ? (
          <section className="flex flex-col gap-3">
            <h2 className={H2}>Đối chiếu</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="py-2 pr-3 font-medium">Chỉ số</th>
                    <th className="py-2 pr-3 font-medium">Kỳ</th>
                    <th className="py-2 pr-3 font-medium">Giá trị</th>
                    <th className="py-2 pr-3 font-medium">Chênh</th>
                    <th className="py-2 pr-3 font-medium">Dung sai</th>
                    <th className="py-2 pr-3 font-medium">Kết luận</th>
                    <th className="py-2 font-medium">Ghi chú</th>
                  </tr>
                </thead>
                <tbody>
                  {model.reconciliation.map((row) => (
                    <tr key={`${row.name}-${row.period}`} className="border-b border-border align-top">
                      <td className="py-2 pr-3">{row.name}</td>
                      <td className="py-2 pr-3">{row.period}</td>
                      <td className="py-2 pr-3">{row.values}</td>
                      <td className="py-2 pr-3 tabular-nums">{row.diff}</td>
                      <td className="py-2 pr-3 tabular-nums">{row.tolerance}</td>
                      <td className="py-2 pr-3">{row.verdict}</td>
                      <td className="py-2">{row.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        {model.tables.length || model.erdHref ? (
          <section className="flex flex-col gap-3">
            <h2 className={H2}>Mô hình dữ liệu</h2>
            {model.tables.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs text-muted-foreground">
                    <tr className="border-b border-border">
                      <th className="py-2 pr-3 font-medium">Mô tả</th>
                      <th className="py-2 pr-3 font-medium">Hạt</th>
                      <th className="py-2 font-medium">Số dòng</th>
                    </tr>
                  </thead>
                  <tbody>
                    {model.tables.map((table) => (
                      <tr key={table.technicalName} className="border-b border-border align-top">
                        <td className="py-2 pr-3">
                          {table.description}
                          {table.detail ? <span className="mt-0.5 block text-xs text-muted-foreground">{table.detail}</span> : null}
                        </td>
                        <td className="py-2 pr-3">{table.grain}</td>
                        <td className="py-2 tabular-nums">{table.rows}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Bản đã xuất bản chưa có bảng vàng. Sơ đồ nằm trong tệp tải về.</p>
            )}
            {model.erdHref ? (
              <a href={model.erdHref} className={LINK}>
                Tải sơ đồ mô hình
              </a>
            ) : null}
          </section>
        ) : null}

        <section className="flex flex-col gap-3">
          <h2 className={H2}>Thuật ngữ</h2>
          <dl className="grid gap-3 sm:grid-cols-2">
            {model.glossary.map((entry) => (
              <div key={entry.term}>
                <dt className="text-sm font-medium">{entry.term}</dt>
                <dd className="text-sm text-muted-foreground">{entry.detail}</dd>
              </div>
            ))}
          </dl>
        </section>

        {model.downloads.length ? (
          <section className="flex flex-col gap-3">
            <h2 className={H2}>Tải xuống</h2>
            <ul className="flex flex-col gap-2 text-sm">
              {model.downloads.map((item) => (
                <li key={item.href}>
                  <a href={item.href} className={LINK}>
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="flex flex-col gap-2">
          <h2 className={H2}>Giấy phép</h2>
          <ul className="flex flex-col gap-2 text-sm">
            {model.sources.map((source) => (
              <li key={source.url}>
                <span className="font-medium">{source.publisher}.</span> {source.license}
              </li>
            ))}
          </ul>
        </section>

        <SiteFooter
          sources={model.footer.sources}
          generatedAt={model.footer.generatedAt}
          dataHref={dictionary?.href}
        />
      </div>
    </PageShell>
  )
}

function SourceCard({ source }: { source: MethodSourceModel }) {
  return (
    <details className="rounded-xl border border-border px-4 py-2">
      <summary className="cursor-pointer text-sm font-medium">{source.publisher}</summary>
      <dl className="mt-2 flex flex-col gap-1 text-sm">
        <div>
          <dt className="text-xs text-muted-foreground">Cách lấy</dt>
          <dd>{source.method}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Giấy phép</dt>
          <dd>{source.license}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Robot</dt>
          <dd>{source.robots}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Đã lấy</dt>
          <dd>{source.fetched}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Kỳ số liệu</dt>
          <dd>{source.cutoff}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Kỳ tới</dt>
          <dd>{source.nextRelease}</dd>
        </div>
      </dl>
    </details>
  )
}

function SourceTable({ sources }: { sources: MethodSourceModel[] }) {
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs text-muted-foreground">
        <tr className="border-b border-border">
          <th className="py-2 pr-3 font-medium">Nhà xuất bản</th>
          <th className="py-2 pr-3 font-medium">Cách lấy</th>
          <th className="py-2 pr-3 font-medium">Giấy phép</th>
          <th className="py-2 pr-3 font-medium">Robot</th>
          <th className="py-2 pr-3 font-medium">Đã lấy</th>
          <th className="py-2 pr-3 font-medium">Kỳ số liệu</th>
          <th className="py-2 font-medium">Kỳ tới</th>
        </tr>
      </thead>
      <tbody>
        {sources.map((source) => (
          <tr key={source.url} className="border-b border-border align-top">
            <td className="py-2 pr-3">
              <a href={source.url} className={LINK}>
                {source.publisher}
              </a>
            </td>
            <td className="py-2 pr-3">{source.method}</td>
            <td className="py-2 pr-3">{source.license}</td>
            <td className="py-2 pr-3">{source.robots}</td>
            <td className="py-2 pr-3">{source.fetched}</td>
            <td className="py-2 pr-3">{source.cutoff}</td>
            <td className="py-2">{source.nextRelease}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function IndicatorRow({ indicator }: { indicator: MethodIndicatorModel }) {
  const cell = "block py-0.5 md:table-cell md:py-2 md:pr-3"
  return (
    <tr id={`indicator-${indicator.anchor}`} className="block scroll-mt-20 border-b border-border py-3 md:table-row">
      <td className={`${cell} font-medium`}>{indicator.name}</td>
      <td className={cell}>{indicator.definition}</td>
      <td className={cell}>{indicator.unit}</td>
      <td className={cell}>{indicator.frequency}</td>
      <td className={cell}>{indicator.measure}</td>
      <td className={cell}>{indicator.updated}</td>
      <td className="block py-0.5 md:table-cell md:py-2">{indicator.nextRelease}</td>
    </tr>
  )
}
