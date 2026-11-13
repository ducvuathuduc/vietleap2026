"use client"

import { AlertCircleIcon, DatabaseIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"

export function ErrorState({ error, title = "Có lỗi xảy ra" }: { error: Error | string; title?: string }) {
  return (
    <div className="px-4 lg:px-6">
      <Alert variant="destructive">
        <AlertCircleIcon />
        <AlertTitle>{title}</AlertTitle>
        <AlertDescription>{typeof error === "string" ? error : error.message}</AlertDescription>
      </Alert>
    </div>
  )
}

export function LoadingState({ rows = 3 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-4 px-4 lg:px-6" aria-busy="true" aria-label="Đang tải">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-32 w-full rounded-xl" />
      ))}
    </div>
  )
}

export function EmptyState({
  title,
  description,
  icon = <DatabaseIcon />,
  children,
}: {
  title: string
  description?: React.ReactNode
  icon?: React.ReactNode
  children?: React.ReactNode
}) {
  return (
    <div className="px-4 lg:px-6">
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">{icon}</EmptyMedia>
          <EmptyTitle>{title}</EmptyTitle>
          {description && <EmptyDescription>{description}</EmptyDescription>}
        </EmptyHeader>
        {children && <EmptyContent>{children}</EmptyContent>}
      </Empty>
    </div>
  )
}

/** Shown when no dataset has been analysed yet (or the API returned an empty list). */
export function NoDatasetState() {
  return (
    <EmptyState
      title="Chưa có dataset"
      description="Tải file lên (nút Upload) hoặc chạy pipeline ở trang Nguồn dữ liệu để bắt đầu."
    />
  )
}

export function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <div className="@container/main flex flex-1 flex-col gap-2">
        <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">{children}</div>
      </div>
    </div>
  )
}

/**
 * Shared loading / error / empty handling for pages that read one dataset resource.
 * Returns the state UI to render, or null when `data` is ready.
 */
export function datasetGate(s: {
  datasetId: string | null
  datasetsLoading: boolean
  datasetsError: string | null
  loading: boolean
  error: Error | undefined
  hasData: boolean
}): React.ReactNode | null {
  if (s.datasetsError) return <ErrorState error={s.datasetsError} title="Không kết nối được API" />
  if (s.datasetsLoading) return <LoadingState />
  if (!s.datasetId) return <NoDatasetState />
  if (s.error) {
    const status = (s.error as Error & { status?: number }).status
    if (status === 404)
      return (
        <EmptyState
          title="Dataset này chưa có kết quả pipeline"
          description="Chạy lại pipeline Data Engineering (trang Nguồn dữ liệu hoặc `python de.py file <đường-dẫn> --serve`)."
        />
      )
    return <ErrorState error={s.error} />
  }
  if (s.loading || !s.hasData) return <LoadingState />
  return null
}
