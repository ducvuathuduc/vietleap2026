import { AppSidebar } from "@/components/app-sidebar"
import { DatasetProvider } from "@/components/dataset-provider"
import { InsightInspectorProvider } from "@/components/insight-inspector"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DatasetProvider>
      <InsightInspectorProvider>
      <SidebarProvider
        style={
          {
            "--sidebar-width": "calc(var(--spacing) * 72)",
            "--header-height": "calc(var(--spacing) * 12)",
          } as React.CSSProperties
        }
      >
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
