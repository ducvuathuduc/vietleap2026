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
import { LayoutDashboardIcon, ChartBarIcon, Settings2Icon, CircleHelpIcon, DatabaseIcon, FileChartColumnIcon, FileIcon, LightbulbIcon, SlidersHorizontalIcon, SparklesIcon, PresentationIcon, ChartNoAxesCombinedIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { api } from "@/lib/api/client"

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
      { title: "Overview", url: "/", icon: <LayoutDashboardIcon /> },
      { title: "Data Profile", url: "/profile", icon: <DatabaseIcon /> },
      { title: "Insights", url: "/insights", icon: <LightbulbIcon /> },
      { title: "Drivers & What-if", url: "/drivers", icon: <SlidersHorizontalIcon /> },
      { title: "Segments", url: "/segments", icon: <ChartBarIcon /> },
      { title: "AI Analyst", url: "/analyst", icon: <SparklesIcon /> },
      { title: "Report / Export", url: "/report", icon: <FileChartColumnIcon /> },
    ],
    navSecondary: [
      { title: "API docs", url: "/api-docs", icon: <Settings2Icon /> },
      { title: "Get Help", url: "/report#help", icon: <CircleHelpIcon /> },
    ],
    documents: [
      { name: "Pitch deck (.pptx)", url: file("deck"), icon: <PresentationIcon /> },
      { name: "Static dashboard", url: file("dashboard"), icon: <FileChartColumnIcon /> },
      { name: "Executive summary", url: file("summary_pdf"), icon: <FileIcon /> },
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
