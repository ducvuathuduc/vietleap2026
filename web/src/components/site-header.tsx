"use client"

import { usePathname } from "next/navigation"

import { useDataset } from "@/components/dataset-provider"
import { ModeToggle } from "@/components/mode-toggle"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"

const TITLES: Record<string, string> = {
  "/": "Tổng quan",
  "/sources": "Nguồn dữ liệu (Ingestion)",
  "/pipeline": "Pipeline: Ingestion → Storage → Transform → Serving",
  "/quality": "Chất lượng dữ liệu",
  "/model": "Mô hình dữ liệu: OBT · Star · Snowflake · Data Vault",
  "/sql": "SQL Explorer",
  "/profile": "Hồ sơ dữ liệu",
  "/insights": "Insight",
  "/drivers": "Drivers & What-if",
  "/segments": "Phân khúc",
  "/decision": "Quyết định & khuyến nghị",
  "/analyst": "AI Analyst",
  "/brief": "Đề bài → kế hoạch phân tích",
}

export function SiteHeader() {
  const pathname = usePathname()
  const { datasets, datasetId, select, detail } = useDataset()
  const items = datasets.map((d) => ({ label: d.name, value: d.id }))
  return (
    <header className="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 h-4 data-vertical:self-auto"
        />
        <h1 className="text-base font-medium">{TITLES[pathname] ?? "VietLeap Insight"}</h1>
        <div className="ml-auto flex items-center gap-2">
          {detail && (
            <Badge variant="outline" className="hidden text-muted-foreground sm:inline-flex">
              {detail.meta.domain.replace("_", " ")} · {detail.meta.rows.toLocaleString("vi-VN")} dòng
            </Badge>
          )}
          <Select value={datasetId ?? ""} onValueChange={(v) => v && select(v)} items={items}>
            <SelectTrigger size="sm" className="w-52 **:data-[slot=select-value]:truncate" aria-label="Dataset">
              <SelectValue placeholder="Chọn dataset" />
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
