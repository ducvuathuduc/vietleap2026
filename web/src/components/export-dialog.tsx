"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog"
import { Progress, ProgressLabel } from "@/components/ui/progress"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { api } from "@/lib/api/client"
import type { ExportJob, ReportLang } from "@/lib/api/types"

const LANGUAGES = [["both", "Việt + Anh"], ["vi", "Tiếng Việt"], ["en", "English"]] as const

export function ExportDialog({ datasetId, onDone }: { datasetId: string; onDone: () => void }) {
  const [lang, setLang] = useState<ReportLang>("both")
  const [dashboard, setDashboard] = useState(true)
  const [starting, setStarting] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<ExportJob | null>(null)
  const busy = starting || jobId !== null

  useEffect(() => {
    if (!jobId) return
    let active = true
    let timer: ReturnType<typeof setTimeout> | undefined

    async function poll(id: string) {
      try {
        const state = await api.exportJob(id)
        if (!active) return
        setJob(state)
        if (state.status === "running" || state.status === "queued") {
          timer = setTimeout(() => void poll(id), 1000)
          return
        }
        setJobId(null)
        if (state.status === "error") {
          toast.error(state.error ?? "Xuất báo cáo thất bại")
        } else {
          toast.success("Gói báo cáo đã sẵn sàng", { description: state.warnings.join(" · ") || undefined })
          onDone()
        }
      } catch (error) {
        if (active) {
          setJobId(null)
          toast.error("Không đọc được trạng thái xuất báo cáo", { description: (error as Error).message })
        }
      }
    }
    void poll(jobId)
    return () => { active = false; clearTimeout(timer) }
  }, [jobId, onDone])

  async function start() {
    setStarting(true)
    setJob(null)
    try {
      const response = await api.startExport(datasetId, lang, dashboard)
      setJobId(response.job_id)
      toast.info("Đang dựng báo cáo")
    } catch (error) {
      toast.error("Không bắt đầu được lượt xuất", { description: (error as Error).message })
    } finally {
      setStarting(false)
    }
  }

  return (
    <Dialog>
      <DialogTrigger render={<Button />}>Xuất báo cáo</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Xuất báo cáo</DialogTitle>
          <DialogDescription>Tạo gói ZIP từ kết quả đã phân tích của {datasetId}.</DialogDescription>
        </DialogHeader>
        <ToggleGroup aria-label="Ngôn ngữ deck và pitch" value={[lang]} disabled={busy} onValueChange={(value) => {
          const selected = LANGUAGES.find(([id]) => id === value[0])
          if (selected) setLang(selected[0])
        }}>
          {LANGUAGES.map(([id, label]) => <ToggleGroupItem key={id} value={id}>{label}</ToggleGroupItem>)}
        </ToggleGroup>
        <label className="flex items-center gap-2 text-sm">
          <Checkbox checked={dashboard} onCheckedChange={setDashboard} disabled={busy} />
          Kèm dashboard PDF
        </label>
        {busy && <Progress value={(job?.progress ?? 0) * 100}><ProgressLabel>{job?.status === "queued" ? "Đang chờ" : "Đang dựng báo cáo"}</ProgressLabel></Progress>}
        {job?.warnings.length ? <ul className="text-sm text-muted-foreground">{job.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
        <DialogFooter>
          {job?.files.bundle && <Button variant="outline" render={<a href={api.fileUrl(datasetId, "bundle")} />}>Tải gói ZIP</Button>}
          <Button type="button" onClick={() => void start()} disabled={busy}>Tạo gói ZIP</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
