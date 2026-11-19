import { AppSidebar } from "@/components/app-sidebar"
import { CommandMenu } from "@/components/command-menu"
import { DatasetProvider } from "@/components/dataset-provider"
import { InsightInspectorProvider } from "@/components/insight-inspector"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DatasetProvider>
      <InsightInspectorProvider>
      <CommandMenu />
      <SidebarProvider>
        <AppSidebar variant="inset" />
        <SidebarInset>
          <SiteHeader />
          {children}
        </SidebarInset>
      </SidebarProvider>
      </InsightInspectorProvider>
    </DatasetProvider>
  )
}
