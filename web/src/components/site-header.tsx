"use client"

import { usePathname } from "next/navigation"

import { BookOpenTextIcon, CompassIcon, EllipsisVerticalIcon, ScanSearchIcon, SearchIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { useInsightInspector } from "@/components/insight-inspector"
import { ModeToggle } from "@/components/mode-toggle"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Spinner } from "@/components/ui/spinner"
import { Toggle } from "@/components/ui/toggle"

import { NAV } from "@/lib/nav"

export function SiteHeader() {
  const pathname = usePathname()
  const { datasets, datasetId, select, detail } = useDataset()
  const { inspecting, setInspecting, startTour, startStory, storyLoading } = useInsightInspector()
  const items = datasets.map((d) => ({ label: d.name, value: d.id }))
  return (
    <header className="flex min-h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
      <div className="flex w-full flex-wrap items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 h-4 data-vertical:self-auto"
        />
        <h1 className="text-[17px] font-semibold tracking-tight">{NAV.find((item) => item.url === pathname)?.title ?? "VietLeap Insight"}</h1>
        <div className="ml-auto flex max-w-full flex-wrap items-center gap-1 sm:gap-2">
          <div className="hidden items-center gap-1 md:flex">
            <Button variant="ghost" size="sm" data-tour="command-button" aria-label="Mở lệnh nhanh (Ctrl+K)"
              onClick={() => window.dispatchEvent(new Event("vlk:open-command"))}><SearchIcon className="sm:hidden" /><span className="hidden sm:inline">Ctrl+K</span></Button>
            <Button variant="ghost" size="sm" onClick={() => startTour(pathname)} data-tour="tour-button" aria-label="Hướng dẫn">
              <CompassIcon /> <span className="hidden md:inline">Hướng dẫn</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={startStory}
              disabled={storyLoading || !datasetId}
              data-tour="story-button"
              aria-label="Câu chuyện insight: AI kể 5 insight mạnh nhất và làm nổi bật từng thẻ"
            >
              {storyLoading ? <Spinner /> : <BookOpenTextIcon />} <span className="hidden md:inline">Câu chuyện</span>
            </Button>
            <Toggle
              variant="outline"
              size="sm"
              pressed={inspecting}
              onPressedChange={setInspecting}
              aria-label="Chế độ Hỏi AI: bấm vào phần tử để được giải thích"
              data-tour="inspect-toggle"
            >
              <ScanSearchIcon /> <span className="hidden md:inline">Hỏi AI</span>
            </Toggle>
          </div>
          <div className="md:hidden">
            <DropdownMenu>
              <DropdownMenuTrigger
                render={<Button variant="ghost" size="icon-sm" aria-label="Thêm hành động" />}
              >
                <EllipsisVerticalIcon />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => window.dispatchEvent(new Event("vlk:open-command"))}>
                  <SearchIcon /> Lệnh nhanh <span className="ml-auto text-xs text-muted-foreground">Ctrl+K</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => startTour(pathname)}>
                  <CompassIcon /> Hướng dẫn
                </DropdownMenuItem>
                <DropdownMenuItem onClick={startStory} disabled={storyLoading || !datasetId}>
                  {storyLoading ? <Spinner /> : <BookOpenTextIcon />} Câu chuyện
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem checked={inspecting} onCheckedChange={setInspecting}>
                  <ScanSearchIcon /> Hỏi AI
                </DropdownMenuCheckboxItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          {detail && (
            <Badge variant="outline" className="hidden text-muted-foreground sm:inline-flex">
              {detail.meta.domain.replace("_", " ")} · {detail.meta.rows.toLocaleString("vi-VN")} dòng
            </Badge>
          )}
          <Select value={datasetId ?? ""} onValueChange={(v) => v && select(v)} items={items}>
            <SelectTrigger size="sm" className="w-32 lg:w-52 **:data-[slot=select-value]:truncate" aria-label="Dataset" data-tour="dataset-select">
              <SelectValue placeholder="Chọn bộ dữ liệu" />
            </SelectTrigger>
            <SelectContent align="end">
              <SelectGroup>
                {items.map((d) => (
                  <SelectItem key={d.value} value={d.value}>
                    {d.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <ModeToggle />
        </div>
      </div>
    </header>
  )
}
