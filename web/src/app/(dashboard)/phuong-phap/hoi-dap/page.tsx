import type { Metadata } from "next"
import Link from "next/link"

import { PageHeader } from "@/components/judge/page-header"
import { SiteFooter } from "@/components/judge/site-footer"
import { PageShell } from "@/components/state"

import { JudgeEmpty, readMonitor } from "../../judge-screen"
import { askPage } from "../../_lib/method-view"

export const metadata: Metadata = {
  title: "Hỏi đáp về số liệu",
  description: "Câu hỏi gợi ý về các chỉ số trong bản số liệu đã xuất bản.",
}

const FRAME = "mx-auto w-full max-w-[1200px] space-y-6 px-4 md:space-y-8 md:px-6"
const LINK =
  "w-fit underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"

export default async function Page() {
  const monitor = await readMonitor()
  if (!monitor) return <JudgeEmpty />
  const model = askPage(monitor, process.env.ENABLE_CHAT === "1")

  return (
    <PageShell>
      <div className={FRAME}>
        <p className="text-sm text-muted-foreground">{model.label}</p>
        <PageHeader level={model.level} headline={model.headline} generatedAt={model.generatedAt} />
        <p className="max-w-3xl text-sm">{model.note}</p>
        {model.questions.length ? (
          <section className="flex flex-col gap-2">
            <h2 className="text-xl font-semibold">Câu hỏi gợi ý</h2>
            <ul className="flex list-disc flex-col gap-2 pl-5 text-sm">
              {model.questions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
          </section>
        ) : null}
        <Link href="/phuong-phap" className={LINK}>
          Về dữ liệu và phương pháp
        </Link>
        <SiteFooter sources={model.footer.sources} generatedAt={model.footer.generatedAt} />
      </div>
    </PageShell>
  )
}
