"use client"

import { useCallback, useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"

import { useDataset } from "@/components/dataset-provider"
import { useInsightInspector } from "@/components/insight-inspector"
import { Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { api } from "@/lib/api/client"
import type { ExportKind } from "@/lib/api/types"
import { commandScore, NAV, whatIfLink } from "@/lib/nav"

const EXPORTS: [ExportKind, string, string][] = [
  ["deck_vi", "deck_vi", "Deck tiếng Việt"], ["deck", "deck", "Deck tiếng Anh"],
  ["pitch_md", "pitch_md", "Pitch tiếng Việt"], ["pitch_en", "pitch_en", "Pitch tiếng Anh"],
  ["dashboard", "dashboard_html", "Dashboard HTML"], ["summary_pdf", "summary_pdf", "Tóm tắt PDF"],
  ["dictionary_csv", "dictionary_csv", "Từ điển dữ liệu"], ["eda_md", "eda_md", "Báo cáo EDA"],
  ["bundle", "bundle", "Gói ZIP"],
]

export function CommandMenu() {
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

  function run(action: () => void) {
    setOpen(false)
    // Allow the dialog to release its focus trap before opening another surface.
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
            {NAV.map((page) => <CommandItem key={page.url} value={page.title} keywords={[...page.keywords]}
              onSelect={() => run(() => router.push(page.url))}>{page.title}</CommandItem>)}
          </CommandGroup>
          <CommandGroup heading="Hành động">
            <CommandItem value="Câu chuyện" keywords={["story"]} disabled={!datasetId}
              onSelect={() => run(startStory)}>Câu chuyện{!datasetId && " · Chưa chọn dataset"}</CommandItem>
            <CommandItem value="Bật Hỏi AI" keywords={["inspect"]} disabled={!datasetId}
              onSelect={() => run(() => setInspecting(true))}>Bật Hỏi AI{!datasetId && " · Chưa chọn dataset"}</CommandItem>
            <CommandItem value="Hướng dẫn trang này" keywords={["tour"]}
              onSelect={() => run(() => startTour(pathname))}>Hướng dẫn trang này</CommandItem>
            {query.trim() && <CommandItem value={`Hỏi AI Analyst · ${query}`} disabled={!datasetId}
              onSelect={() => run(() => router.push(`/analyst?q=${encodeURIComponent(query.slice(0, 2000))}`))}>Hỏi AI Analyst · {query}</CommandItem>}
            {shortcut && <CommandItem value={`Mở kịch bản · ${query}`} disabled={!datasetId}
              onSelect={() => run(() => router.push(shortcut))}>Mở kịch bản · {query}</CommandItem>}
          </CommandGroup>
          <CommandGroup heading="Dataset">
            {datasets.map((dataset) => <CommandItem key={dataset.id} value={`Dataset ${dataset.name}`}
              onSelect={() => run(() => select(dataset.id))}>{dataset.name}</CommandItem>)}
            {!datasets.length && <CommandItem value="Chưa có dataset — tải dữ liệu" onSelect={() => run(() => router.push("/sources"))}>Chưa có dataset — tải dữ liệu</CommandItem>}
          </CommandGroup>
          <CommandGroup heading="Xuất file">
            {EXPORTS.filter(([, key]) => files[key]).map(([kind, , title]) => <CommandItem key={kind} value={title}
              keywords={["export", "download"]} onSelect={() => run(() => { if (datasetId) window.open(api.fileUrl(datasetId, kind), "_blank", "noopener,noreferrer") })}>{title}</CommandItem>)}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
