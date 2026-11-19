import { Suspense } from "react"
import { connection } from "next/server"

import { AppSidebar } from "@/components/app-sidebar"
import { CommandMenu } from "@/components/command-menu"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { loadMonitor } from "@/lib/monitor/load"
import type { CommandIndicator } from "@/components/command-menu"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar shell="judge" variant="inset" />
      <SidebarInset>
        <SiteHeader shell="judge" />
        <Suspense fallback={null}>
          <JudgeCommands />
        </Suspense>
        {children}
      </SidebarInset>
    </SidebarProvider>
  )
}

async function JudgeCommands() {
  await connection()
  let indicators: CommandIndicator[] = []
  try {
    const monitor = loadMonitor()
    indicators = monitor?.indicators.map((item) => ({
      id: item.id,
      name_vi: item.name_vi,
      sector: item.sector,
    })) ?? []
  } catch {
    indicators = []
  }
  return <CommandMenu shell="judge" indicators={indicators} />
}
