"use client"

import * as React from "react"
import { LoaderIcon, UploadIcon } from "lucide-react"
import { toast } from "sonner"

import { useDataset } from "@/components/dataset-provider"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { api, ApiError } from "@/lib/api/client"

const DOMAINS = [
  { label: "Auto-detect", value: "auto" },
  { label: "Property / real estate", value: "property" },
  { label: "Public finance", value: "public_finance" },
  { label: "Firm financials", value: "firm" },
  { label: "Generic", value: "generic" },
]

export function UploadDialog({ trigger }: { trigger: React.ReactElement }) {
  const { refresh, select } = useDataset()
  const [open, setOpen] = React.useState(false)
  const [busy, setBusy] = React.useState(false)
  const [elapsed, setElapsed] = React.useState(0)
  const [domain, setDomain] = React.useState("auto")
  const formRef = React.useRef<HTMLFormElement>(null)

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const file = form.get("file")
    if (!(file instanceof File) || file.size === 0) {
      toast.error("Choose a CSV / XLSX / JSON / Parquet file first")
      return
    }
    form.set("domain", domain)
    setBusy(true)
    setElapsed(0)
    const t0 = Date.now()
    const timer = window.setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000)
    try {
      let job = await api.upload(form)
      while (job.status === "queued" || job.status === "running") {
        await new Promise((r) => setTimeout(r, 1500))
        job = await api.job(job.id)
      }
      if (job.status === "error" || !job.dataset_id) throw new ApiError(500, job.error ?? "analysis failed")
      await refresh()
      select(job.dataset_id)
      toast.success(`Analysed ${file.name} in ${Math.round((Date.now() - t0) / 1000)} s`)
      setOpen(false)
      formRef.current?.reset()
    } catch (err) {
      toast.error((err as Error).message)
    } finally {
      window.clearInterval(timer)
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && setOpen(o)}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-md">
        <form ref={formRef} onSubmit={onSubmit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>Upload a dataset</DialogTitle>
            <DialogDescription>
              CSV, XLSX (all sheets), JSON or Parquet. Vietnamese numbers, units (tỷ, triệu, m²) and dates are parsed automatically.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="file">File</Label>
            <Input id="file" name="file" type="file" accept=".csv,.tsv,.txt,.xlsx,.xls,.xlsm,.json,.parquet" disabled={busy} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-2">
              <Label htmlFor="target">Target column</Label>
              <Input id="target" name="target" placeholder="auto" disabled={busy} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="domain">Domain</Label>
              <Select value={domain} onValueChange={(v) => v && setDomain(v)} items={DOMAINS}>
                <SelectTrigger id="domain" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {DOMAINS.map((d) => (
                      <SelectItem key={d.value} value={d.value}>
                        {d.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="time">Time column</Label>
              <Input id="time" name="time" placeholder="auto" disabled={busy} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="geo">Geo column</Label>
              <Input id="geo" name="geo" placeholder="auto" disabled={busy} />
            </div>
          </div>
          {busy && (
            <div className="grid gap-2 text-sm text-muted-foreground">
              <Progress value={Math.min(95, elapsed * 2)} />
              Cleaning, testing and modelling… {elapsed}s
            </div>
          )}
          <DialogFooter>
            <DialogClose render={<Button variant="outline" type="button" disabled={busy} />}>Cancel</DialogClose>
            <Button type="submit" disabled={busy}>
              {busy ? <LoaderIcon className="animate-spin" /> : <UploadIcon />}
              Analyse
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
