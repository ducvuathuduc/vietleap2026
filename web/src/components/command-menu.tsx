"use client"

import { useCallback, useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"

import { useDataset } from "@/components/dataset-provider"
import { useInsightInspector } from "@/components/insight-inspector"
import { Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { api } from "@/lib/api/client"
import type { ExportKind } from "@/lib/api/types"
import { commandScore, filterCommands, hrefForIndicatorSector, LAB_NAV, whatIfLink } from "@/lib/nav"

const EXPORTS: [ExportKind, string, string][] = [
  ["deck_vi", "deck_vi", "Deck tiếng Việt"], ["deck", "deck", "Deck tiếng Anh"],
  ["pitch_md", "pitch_md", "Pitch tiếng Việt"], ["pitch_en", "pitch_en", "Pitch tiếng Anh"],
  ["dashboard", "dashboard_html", "Dashboard HTML"], ["summary_pdf", "summary_pdf", "Tóm tắt PDF"],
  ["dictionary_csv", "dictionary_csv", "Từ điển dữ liệu"], ["eda_md", "eda_md", "Báo cáo EDA"],
  ["bundle", "bundle", "Gói ZIP"],
]

export type CommandIndicator = { id: string; name_vi: string; sector: string }

export function CommandMenu(props: { shell: "judge"; indicators: CommandIndicator[] } | { shell: "lab" }) {
  if (props.shell === "judge") return <JudgeCommandMenu indicators={props.indicators} />
  return <LabCommandMenu />
}

function JudgeCommandMenu({ indicators }: { indicators: CommandIndicator[] }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const router = useRouter()
  const show = useCallback(() => {
    setQuery("")
    setOpen(true)
  }, [])
  useCommandHotkey(show)

  function run(action: () => void) {
    setOpen(false)
    requestAnimationFrame(action)
  }
  const pages = filterCommands(query)
  const matchedIndicators = indicators.filter((item) => commandScore(item.name_vi, query) > 0)
  return (
    <CommandDialog open={open} onOpenChange={setOpen} title="Lệnh nhanh" description="Tìm trang hoặc chỉ số.">
      <Command shouldFilter={false}>
        <CommandInput aria-label="Tìm lệnh" placeholder="Tìm trang hoặc chỉ số…" value={query} onValueChange={setQuery} />
        <CommandList>
          {pages.length === 0 && matchedIndicators.length === 0 ? <CommandEmpty>Chưa có lệnh khớp.</CommandEmpty> : null}
          <CommandGroup heading="Trang">
            {pages.map((page) => (
              <CommandItem key={page.url + page.title} value={page.title} onSelect={() => run(() => router.push(page.url))}>
                {page.title}
              </CommandItem>
            ))}
          </CommandGroup>
          {matchedIndicators.length > 0 && (
            <CommandGroup heading="Chỉ số">
              {matchedIndicators.map((item) => (
                <CommandItem
                  key={item.id}
                  value={item.name_vi}
                  onSelect={() => run(() => router.push(hrefForIndicatorSector(item.sector)))}
                >
                  {item.name_vi}
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  )
}

function LabCommandMenu() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const { datasetId, datasets, detail, select } = useDataset()
  const { stopInteractions, startTour, startStory, setInspecting } = useInsightInspector()
  const pathname = usePathname()
  const router = useRouter()

  const show = useCallback(() => {
    stopInteractions()
    setQuery("")
    setOpen(true)
  }, [stopInteractions])
  useCommandHotkey(show)

  function run(action: () => void) {
    setOpen(false)
    requestAnimationFrame(action)
  }
  const shortcut = whatIfLink(query)
  const files = detail?.meta.name === datasetId ? detail.files : {}
  return (
    <CommandDialog open={open} onOpenChange={setOpen} title="Lệnh nhanh" description="Tìm trang, hành động, dataset hoặc file xuất.">
      <Command filter={commandScore}>
        <CommandInput aria-label="Tìm lệnh" placeholder="Tìm trang hoặc nhập câu hỏi…" value={query} onValueChange={setQuery} />
        <CommandList>
          <CommandEmpty>Chưa có lệnh khớp.</CommandEmpty>
          <CommandGroup heading="Trang">
            {LAB_NAV.map((page) => (
              <CommandItem key={page.url} value={page.title} keywords={[...page.keywords]} onSelect={() => run(() => router.push(page.url))}>
                {page.title}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandGroup heading="Hành động">
            <CommandItem value="Câu chuyện" keywords={["story"]} disabled={!datasetId}
              onSelect={() => run(startStory)}>Câu chuyện{!datasetId && " · Chưa chọn dataset"}</CommandItem>
            <CommandItem value="Bật Hỏi AI" keywords={["inspect"]} disabled={!datasetId}
              onSelect={() => run(() => setInspecting(true))}>Bật Hỏi AI{!datasetId && " · Chưa chọn dataset"}</CommandItem>
            <CommandItem value="Hướng dẫn trang này" keywords={["tour"]}
              onSelect={() => run(() => startTour(pathname))}>Hướng dẫn trang này</CommandItem>
            {query.trim() && (
              <CommandItem value={`Hỏi AI Analyst · ${query}`} disabled={!datasetId}
                onSelect={() => run(() => router.push(`/lab/analyst?q=${encodeURIComponent(query.slice(0, 2000))}`))}>
                Hỏi AI Analyst · {query}
              </CommandItem>
            )}
            {shortcut && (
              <CommandItem value={`Mở kịch bản · ${query}`} disabled={!datasetId}
                onSelect={() => run(() => router.push(shortcut))}>Mở kịch bản · {query}</CommandItem>
            )}
          </CommandGroup>
          <CommandGroup heading="Dataset">
            {datasets.map((dataset) => (
              <CommandItem key={dataset.id} value={`Dataset ${dataset.name}`} onSelect={() => run(() => select(dataset.id))}>
                {dataset.name}
              </CommandItem>
            ))}
            {!datasets.length && (
              <CommandItem value="Chưa có dataset — tải dữ liệu" onSelect={() => run(() => router.push("/lab/sources"))}>
                Chưa có dataset — tải dữ liệu
              </CommandItem>
            )}
          </CommandGroup>
          <CommandGroup heading="Xuất file">
            {EXPORTS.filter(([, key]) => files[key]).map(([kind, , title]) => (
              <CommandItem key={kind} value={title} keywords={["export", "download"]}
                onSelect={() => run(() => { if (datasetId) window.open(api.fileUrl(datasetId, kind), "_blank", "noopener,noreferrer") })}>
                {title}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}

function useCommandHotkey(show: () => void) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.isComposing || event.key.toLowerCase() !== "k" || !(event.ctrlKey || event.metaKey)) return
      event.preventDefault()
      show()
    }
    window.addEventListener("keydown", onKey)
    window.addEventListener("vlk:open-command", show)
    return () => {
      window.removeEventListener("keydown", onKey)
      window.removeEventListener("vlk:open-command", show)
    }
  }, [show])
}
