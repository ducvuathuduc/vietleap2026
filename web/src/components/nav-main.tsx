"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { CirclePlusIcon, SparklesIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar"
import { UploadDialog } from "@/components/upload-dialog"

export type NavMainItem = {
  group?: string
  title: string
  url: string
  icon?: React.ReactNode
  children?: { title: string; url: string }[]
}

function isItemActive(url: string, pathname: string) {
  if (url === "/" || url === "/lab") return pathname === url
  return pathname === url || pathname.startsWith(`${url}/`)
}

export function NavMain({
  items,
  showTools = false,
}: {
  items: NavMainItem[]
  showTools?: boolean
}) {
  const pathname = usePathname()
  const groups = items.some((item) => item.group) ? [...new Set(items.map((item) => item.group ?? ""))] : [""]
  return (
    <SidebarGroup>
      <SidebarGroupContent className="flex flex-col gap-2">
        {showTools && (
          <SidebarMenu>
            <SidebarMenuItem className="flex items-center gap-2">
              <UploadDialog
                trigger={
                  <SidebarMenuButton
                    tooltip="Tải bộ dữ liệu"
                    className="min-w-8 bg-primary text-primary-foreground duration-200 ease-linear hover:bg-primary/90 hover:text-primary-foreground active:bg-primary/90 active:text-primary-foreground"
                  >
                    <CirclePlusIcon />
                    <span>Tải bộ dữ liệu</span>
                  </SidebarMenuButton>
                }
              />
              <Button
                size="icon"
                className="size-8 group-data-[collapsible=icon]:opacity-0"
                variant="outline"
                nativeButton={false}
                render={<Link href="/lab/analyst" />}
              >
                <SparklesIcon />
                <span className="sr-only">Hỏi AI</span>
              </Button>
            </SidebarMenuItem>
          </SidebarMenu>
        )}
        {groups.map((group) => (
          <section key={group || "dieu-huong"} aria-label={group || undefined}>
            {group ? <SidebarGroupLabel>{group}</SidebarGroupLabel> : null}
            <SidebarMenu>
              {items.filter((item) => (item.group ?? "") === group).map((item) => {
                const childActive = item.children?.some((child) => isItemActive(child.url, pathname)) ?? false
                const active = item.children?.length ? childActive || pathname.startsWith("/nganh/") : isItemActive(item.url, pathname)
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton tooltip={item.title} isActive={active} render={<Link href={item.url} />}>
                      {item.icon}
                      <span>{item.title}</span>
                    </SidebarMenuButton>
                    {item.children?.length ? (
                      <SidebarMenuSub>
                        {item.children.map((child) => (
                          <SidebarMenuSubItem key={child.url}>
                            <SidebarMenuSubButton isActive={pathname === child.url} render={<Link href={child.url} />}>
                              <span>{child.title}</span>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                      </SidebarMenuSub>
                    ) : null}
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </section>
        ))}
      </SidebarGroupContent>
    </SidebarGroup>
  )
}
