"use client"

import * as React from "react"
import { PlusIcon, Trash2Icon, UploadCloudIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { ResultTable } from "@/components/result-table"
import { ErrorState, LoadingState, PageShell } from "@/components/state"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { IngestJob, SourceIn, SourceKind, SourceKindsResponse } from "@/lib/api/types"
import { SOURCE_KINDS } from "@/lib/source-kinds"

interface Draft {
  key: number
  name: string
  kind: SourceKind
  uri: string
  options: string
  license_note: string
}

const NAME_RE = /^[A-Za-z0-9_]+$/
const POLL_MS = 2000

function draftFor(kind: SourceKind, key: number, examples: SourceKindsResponse["examples"]): Draft {
  const ex = examples[kind]
  return {
    key,
    name: `${kind}_${key}`,
    kind,
    uri: ex?.uri ?? SOURCE_KINDS[kind].uriHint,
    options: ex?.options ? JSON.stringify(ex.options, null, 2) : "{}",
    license_note: "",
  }
}

/** Returns per-field error messages (Vietnamese) or the parsed SourceIn. */
function validate(d: Draft, all: Draft[]): { errors: Partial<Record<keyof Draft, string>>; value?: SourceIn } {
  const errors: Partial<Record<keyof Draft, string>> = {}
  if (!NAME_RE.test(d.name)) errors.name = "Chỉ dùng chữ không dấu, số, dấu _"
  else if (all.filter((x) => x.name === d.name).length > 1) errors.name = "Tên nguồn bị trùng"
  if (!d.uri.trim()) errors.uri = "Cần URI / đường dẫn"
  let options: Record<string, unknown> = {}
  try {
    const parsed: unknown = JSON.parse(d.options || "{}")
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) throw new Error()
    options = parsed as Record<string, unknown>
  } catch {
    errors.options = "Options phải là một object JSON hợp lệ"
  }
  if (Object.keys(errors).length) return { errors }
  return { errors, value: { name: d.name, kind: d.kind, uri: d.uri.trim(), options, license_note: d.license_note.trim() } }
}

export default function SourcesPage() {
  const { refresh, select } = useDataset()
  const kinds = useAsync(() => api.sourceKinds(), [])
  const [dataset, setDataset] = React.useState("")
  const [drafts, setDrafts] = React.useState<Draft[]>([])
  const [primary, setPrimary] = React.useState<string | null>(null)
  const [impute, setImpute] = React.useState(false)
  const [serve, setServe] = React.useState(true)
  const [job, setJob] = React.useState<IngestJob | null>(null)
  const [submitError, setSubmitError] = React.useState<string | null>(null)
  const nextKey = React.useRef(1)

  // poll the background ingest job until it finishes
  React.useEffect(() => {
    if (!job || job.status === "done" || job.status === "error") return
    const t = window.setTimeout(() => {
      api.ingestJob(job.id).then(
        (j) => {
          setJob(j)
          if (j.status === "done") {
            void refresh().then(() => j.summary && serve && select(j.dataset))
          }
        },
        (e: Error) => setSubmitError(e.message)
      )
    }, POLL_MS)
    return () => window.clearTimeout(t)
  }, [job, refresh, select, serve])

  if (kinds.error) return <PageShell><ErrorState error={kinds.error} title="Không tải được danh sách loại nguồn" /></PageShell>
  if (kinds.loading || !kinds.data) return <PageShell><LoadingState /></PageShell>
  const examples = kinds.data.examples

  const add = (kind: SourceKind) => setDrafts((ds) => [...ds, draftFor(kind, nextKey.current++, examples)])
  const update = (key: number, patch: Partial<Draft>) => setDrafts((ds) => ds.map((d) => (d.key === key ? { ...d, ...patch } : d)))
  const remove = (key: number) => setDrafts((ds) => ds.filter((d) => d.key !== key))

  const checks = drafts.map((d) => validate(d, drafts))
  const datasetError = dataset.trim() === "" ? "Cần tên dataset" : dataset.length > 60 ? "Tối đa 60 ký tự" : null
  const primaryName = primary && drafts.some((d) => d.name === primary) ? primary : null
  const busy = job !== null && (job.status === "queued" || job.status === "running")
  const canSubmit = !busy && !datasetError && drafts.length > 0 && checks.every((c) => c.value)

  const submit = async () => {
    if (!canSubmit) return
    setSubmitError(null)
    try {
      setJob(await api.ingest({
        dataset: dataset.trim(),
        sources: checks.map((c) => c.value!),
        primary: primaryName,
        impute: impute ? "median" : null,
        serve,
      }))
    } catch (e) {
      setSubmitError((e as Error).message)
    }
  }

  return (
    <PageShell>
      <div className="px-4 lg:px-6">
        <Card>
          <CardHeader>
            <CardTitle>5 loại nguồn của workshop — kit xử lý thế nào</CardTitle>
            <CardDescription>Quyền truy cập · giới hạn API · chống bị chặn: được xử lý ngay trong connector.</CardDescription>
          </CardHeader>
          <CardContent>
            <ResultTable
              columns={["Loại nguồn", "kind", "Cách xử lý"]}
              rows={kinds.data.kinds.map((k) => [SOURCE_KINDS[k]?.workshop ?? k, k, SOURCE_KINDS[k]?.handling ?? ""])}
            />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-3">
        <Card className="@5xl/main:col-span-2">
          <CardHeader>
            <CardTitle>Thêm nguồn & chạy pipeline</CardTitle>
            <CardDescription>Nguồn → bronze → silver (làm sạch) → gold (OBT/Star/Snowflake/Data Vault) → insight.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="ds-name">Tên dataset</Label>
              <Input id="ds-name" value={dataset} onChange={(e) => setDataset(e.target.value)} placeholder="vd. bds_hanoi" aria-invalid={dataset !== "" && !!datasetError} />
              {dataset !== "" && datasetError && <span className="text-sm text-destructive">{datasetError}</span>}
            </div>
            <div className="flex flex-wrap gap-2">
              {kinds.data.kinds.map((k) => (
                <Button key={k} variant="outline" size="sm" onClick={() => add(k)}>
                  <PlusIcon /> {SOURCE_KINDS[k]?.label ?? k}
                </Button>
              ))}
            </div>
            {drafts.length === 0 && <p className="text-sm text-muted-foreground">Chưa có nguồn nào — chọn loại nguồn ở trên để thêm.</p>}
            {drafts.map((d, i) => {
              const err = checks[i].errors
              return (
                <div key={d.key} className="flex flex-col gap-3 rounded-lg border p-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{SOURCE_KINDS[d.kind]?.label ?? d.kind}</Badge>
                    <Button variant="ghost" size="icon-sm" className="ml-auto" onClick={() => remove(d.key)} aria-label="Xoá nguồn">
                      <Trash2Icon />
                    </Button>
                  </div>
                  <div className="grid gap-3 @xl/main:grid-cols-2">
                    <div className="flex flex-col gap-1.5">
                      <Label htmlFor={`n${d.key}`}>Tên nguồn</Label>
                      <Input id={`n${d.key}`} value={d.name} onChange={(e) => update(d.key, { name: e.target.value })} aria-invalid={!!err.name} />
                      {err.name && <span className="text-sm text-destructive">{err.name}</span>}
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <Label htmlFor={`l${d.key}`}>Giấy phép / ghi chú nguồn</Label>
                      <Input id={`l${d.key}`} value={d.license_note} onChange={(e) => update(d.key, { license_note: e.target.value })} placeholder="vd. CC BY 4.0" />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor={`u${d.key}`}>URI</Label>
                    <Input id={`u${d.key}`} value={d.uri} onChange={(e) => update(d.key, { uri: e.target.value })} aria-invalid={!!err.uri} />
                    {err.uri && <span className="text-sm text-destructive">{err.uri}</span>}
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor={`o${d.key}`}>Options (JSON)</Label>
                    <Textarea id={`o${d.key}`} value={d.options} onChange={(e) => update(d.key, { options: e.target.value })} className="font-mono text-xs" aria-invalid={!!err.options} />
                    {err.options && <span className="text-sm text-destructive">{err.options}</span>}
                  </div>
                </div>
              )
            })}
          </CardContent>
          <CardFooter className="flex flex-wrap items-center gap-4">
            {drafts.length > 1 && (
              <Select value={primaryName ?? ""} onValueChange={(v) => setPrimary(v || null)} items={drafts.map((d) => ({ label: d.name, value: d.name }))}>
                <SelectTrigger size="sm" className="w-56" aria-label="Nguồn chính"><SelectValue placeholder="Nguồn chính (tuỳ chọn)" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {drafts.map((d) => <SelectItem key={d.key} value={d.name}>{d.name}</SelectItem>)}
                  </SelectGroup>
                </SelectContent>
              </Select>
            )}
            <Label className="flex items-center gap-2">
              <Checkbox checked={impute} onCheckedChange={(v) => setImpute(v === true)} /> Điền thiếu bằng trung vị (có cột cờ)
            </Label>
            <Label className="flex items-center gap-2">
              <Checkbox checked={serve} onCheckedChange={(v) => setServe(v === true)} /> Chạy insight sau pipeline
            </Label>
            <Button className="ml-auto" onClick={() => void submit()} disabled={!canSubmit}>
              {busy ? <Spinner /> : <UploadCloudIcon />} Chạy pipeline
            </Button>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Trạng thái job</CardTitle>
            {job && <CardAction><Badge variant={job.status === "error" ? "destructive" : "outline"}>{job.status}</Badge></CardAction>}
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            {submitError && <ErrorState error={submitError} title="Không gửi được yêu cầu" />}
            {!job && !submitError && <p className="text-muted-foreground">Chưa chạy job nào.</p>}
            {busy && <p className="flex items-center gap-2 text-muted-foreground"><Spinner /> Đang chạy… (tự cập nhật mỗi {POLL_MS / 1000} giây)</p>}
            {job?.status === "error" && (
              <Alert variant="destructive">
                <AlertTitle>Pipeline lỗi</AlertTitle>
                <AlertDescription>{job.error}</AlertDescription>
              </Alert>
            )}
            {job?.summary && (
              <>
                <div>Dataset <span className="font-medium">{job.summary.dataset}</span> · lần chạy {job.summary.run_id}</div>
                <ResultTable
                  columns={["Bảng silver", "Điểm trước", "Điểm sau", "Số dòng"]}
                  rows={Object.entries(job.summary.quality).map(([t, q]) => [t, q.score_before, q.score_after, q.rows])}
                  maxHeight="16rem"
                />
                <div className="text-muted-foreground">{job.summary.gold.length} bảng gold đã tạo · xem trang Pipeline, Chất lượng, Mô hình.</div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </PageShell>
  )
}
