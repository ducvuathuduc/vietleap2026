"use client"

import * as React from "react"

import { NavDocuments } from "@/components/nav-documents"
import { NavMain } from "@/components/nav-main"
import { NavSecondary } from "@/components/nav-secondary"
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import Link from "next/link"
import { LayoutDashboardIcon, ChartBarIcon, Settings2Icon, DatabaseIcon, FileChartColumnIcon, FileIcon, FileTextIcon, GavelIcon, LightbulbIcon, NetworkIcon, ShieldCheckIcon, SlidersHorizontalIcon, SlidersVerticalIcon, SparklesIcon, PresentationIcon, ChartNoAxesCombinedIcon, TerminalSquareIcon, UploadCloudIcon, WorkflowIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { ExportLangToggle } from "@/components/export-lang-toggle"
import { useStoredExportLang } from "@/hooks/use-export-lang"
import { api } from "@/lib/api/client"
import type { ExportKind } from "@/lib/api/types"
import { availableLangs, exportKinds, pickLang } from "@/lib/export-lang"
import { NAV } from "@/lib/nav"

const rawDocs = process.env.NEXT_PUBLIC_API_DOCS_URL
const API_DOCS = rawDocs || "/api/health"
const PAGE_ICONS = [LayoutDashboardIcon, FileTextIcon, UploadCloudIcon, WorkflowIcon, ShieldCheckIcon, NetworkIcon,
  TerminalSquareIcon, DatabaseIcon, LightbulbIcon, SlidersHorizontalIcon, SlidersVerticalIcon, ChartBarIcon, GavelIcon, SparklesIcon, FileChartColumnIcon]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { datasetId, detail } = useDataset()
  const [storedLang, setStoredLang] = useStoredExportLang()
  const file = (kind: ExportKind) => (datasetId ? api.fileUrl(datasetId, kind) : "#")
  const files = detail?.files
  const lang = pickLang(files, storedLang)
  const langDocuments = (lang ? exportKinds(files, lang) : []).map((kind) =>
    kind.startsWith("deck")
      ? { name: "Pitch deck (.pptx)", url: file(kind), icon: <PresentationIcon /> }
      : { name: "Kịch bản pitch (.md)", url: file(kind), icon: <FileTextIcon /> }
  )
  const data = {
    navMain: NAV.map((page, index) => ({ ...page, icon: React.createElement(PAGE_ICONS[index]) })),
    navSecondary: [
      { title: rawDocs ? "Tài liệu API" : "Trạng thái dịch vụ", url: `${API_DOCS}`, icon: <Settings2Icon /> },
    ],
    documents: [
      ...langDocuments,
      ...(files?.dictionary_csv ? [{ name: "Từ điển dữ liệu (CSV)", url: file("dictionary_csv"), icon: <DatabaseIcon /> }] : []),
      ...(files?.dictionary_md ? [{ name: "Từ điển dữ liệu (Markdown)", url: file("dictionary_md"), icon: <FileTextIcon /> }] : []),
      ...(files?.eda_md ? [{ name: "Phân tích khám phá (EDA)", url: file("eda_md"), icon: <FileChartColumnIcon /> }] : []),
      { name: "Dashboard tĩnh (HTML)", url: file("dashboard"), icon: <FileChartColumnIcon /> },
      { name: "Tóm tắt điều hành (PDF)", url: file("summary_pdf"), icon: <FileIcon /> },
    ],
  }
  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              className="data-[slot=sidebar-menu-button]:p-1.5!"
              render={<Link href="/" />}
            >
              <ChartNoAxesCombinedIcon className="size-5!" />
              <span className="text-base font-semibold">VietLeap Insight</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        <NavDocuments
          items={data.documents}
          toolbar={<ExportLangToggle value={lang} available={availableLangs(files)} onChange={setStoredLang} />}
        />
        <NavSecondary items={data.navSecondary} className="mt-auto" />
      </SidebarContent>
    </Sidebar>
  )
}
