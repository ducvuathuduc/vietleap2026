"use client"

import * as React from "react"

import { NavDocuments } from "@/components/nav-documents"
import { NavMain } from "@/components/nav-main"
import { NavSecondary } from "@/components/nav-secondary"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import Link from "next/link"
import { LayoutDashboardIcon, ChartBarIcon, Settings2Icon, DatabaseIcon, FileChartColumnIcon, FileIcon, FileTextIcon, GavelIcon, LightbulbIcon, NetworkIcon, ShieldCheckIcon, SlidersHorizontalIcon, SparklesIcon, PresentationIcon, ChartNoAxesCombinedIcon, TerminalSquareIcon, UploadCloudIcon, WorkflowIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { api } from "@/lib/api/client"

const API_DOCS = process.env.NEXT_PUBLIC_API_DOCS_URL ?? "http://localhost:8000/docs"

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { datasetId } = useDataset()
  const file = (kind: Parameters<typeof api.fileUrl>[1]) => (datasetId ? api.fileUrl(datasetId, kind) : "#")
  const data = {
    user: {
      name: "VietLeap Team",
      email: "UEH · 20–21/11/2026",
      avatar: "",
    },
    navMain: [
      { title: "Tổng quan", url: "/", icon: <LayoutDashboardIcon /> },
      { title: "Đề bài", url: "/brief", icon: <FileTextIcon /> },
      { title: "Nguồn dữ liệu", url: "/sources", icon: <UploadCloudIcon /> },
      { title: "Pipeline", url: "/pipeline", icon: <WorkflowIcon /> },
      { title: "Chất lượng dữ liệu", url: "/quality", icon: <ShieldCheckIcon /> },
      { title: "Mô hình dữ liệu", url: "/model", icon: <NetworkIcon /> },
      { title: "SQL Explorer", url: "/sql", icon: <TerminalSquareIcon /> },
      { title: "Hồ sơ dữ liệu", url: "/profile", icon: <DatabaseIcon /> },
      { title: "Insight", url: "/insights", icon: <LightbulbIcon /> },
      { title: "Drivers & What-if", url: "/drivers", icon: <SlidersHorizontalIcon /> },
      { title: "Phân khúc", url: "/segments", icon: <ChartBarIcon /> },
      { title: "Quyết định", url: "/decision", icon: <GavelIcon /> },
      { title: "AI Analyst", url: "/analyst", icon: <SparklesIcon /> },
    ],
    navSecondary: [
      { title: "Tài liệu API", url: `${API_DOCS}`, icon: <Settings2Icon /> },
    ],
    documents: [
      { name: "Pitch deck (.pptx)", url: file("deck"), icon: <PresentationIcon /> },
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
        <NavDocuments items={data.documents} />
        <NavSecondary items={data.navSecondary} className="mt-auto" />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
    </Sidebar>
  )
}
