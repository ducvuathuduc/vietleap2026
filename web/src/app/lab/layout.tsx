import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { AppSidebar } from "@/components/app-sidebar"
import { CommandMenu } from "@/components/command-menu"
import { DatasetProvider } from "@/components/dataset-provider"
import { InsightInspectorProvider } from "@/components/insight-inspector"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export const metadata: Metadata = {
  robots: { index: false },
}

export default function LabLayout({ children }: { children: React.ReactNode }) {
  if (process.env.ENABLE_LAB !== "1") notFound()
  return (
    <DatasetProvider>
      <InsightInspectorProvider>
        <CommandMenu shell="lab" />
        <SidebarProvider>
          <AppSidebar shell="lab" variant="inset" />
          <SidebarInset>
            <SiteHeader shell="lab" />
            {children}
          </SidebarInset>
        </SidebarProvider>
      </InsightInspectorProvider>
    </DatasetProvider>
  )
}
