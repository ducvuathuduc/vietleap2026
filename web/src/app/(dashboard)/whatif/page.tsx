"use client"

import * as React from "react"
import Link from "next/link"
import { AlertTriangleIcon, BookmarkPlusIcon, RotateCcwIcon, SendIcon, Trash2Icon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { InsightChart } from "@/components/insight-chart"
import { EmptyState, ErrorState, LoadingState, PageShell } from "@/components/state"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import type { DriversResponse, SavedScenario, WhatIfChange, WhatIfScenarioResult } from "@/lib/api/types"
import { fmtNum, fmtPct } from "@/lib/format"
import { insightTarget } from "@/lib/insight-target"
import {
  MAX_SAVED_SCENARIOS,
  createScenarioRequester,
  defaultTopDrivers,
  formatUnitMode,
  hasZeroCrossing,
  isZeroVector,
  loadLocalScenarios,
  removeLocalScenario,
  saveLocalScenario,
} from "@/lib/whatif"

export default function WhatIfPage() {
  const { datasetId } = useDataset()
  const { data, error, loading } = useAsync(() => (datasetId ? api.drivers(datasetId) : null), [datasetId])

  if (error) return <PageShell><ErrorState error={error} /></PageShell>
  if (loading || !data) return <PageShell><LoadingState /></PageShell>
  if (!datasetId || !data.drivers || data.whatif_features.length < 2) {
    return (
      <PageShell>
        <EmptyState
          title="Chưa có mô hình drivers — cần ≥ 2 biến số"
          description="Dataset cần ít nhất 2 biến số độc lập hợp lệ để ước lượng mô hình tác động đa biến."
        >
          <Button render={<Link href="/drivers" />} variant="outline">Xem trang Yếu tố</Button>
        </EmptyState>
      </PageShell>
    )
  }

  return <WhatIfContent key={datasetId} datasetId={datasetId} data={data} />
}

function WhatIfContent({ datasetId, data }: { datasetId: string; data: DriversResponse }) {
  const topDrivers = React.useMemo(() => defaultTopDrivers(data, 5), [data])
  const categoricalKept = React.useMemo(() => {
    const numSet = new Set(data.whatif_features.map((f) => f.name))
    const rawCats = (data.drivers?.features ?? []).filter((f) => !numSet.has(f))
    return Array.from(new Set(rawCats.map((f) => f.split("=")[0]))).slice(0, 6)
  }, [data])

  const [values, setValues] = React.useState<Record<string, number>>(() =>
    Object.fromEntries(topDrivers.map((d) => [d.name, 0]))
  )
  const [result, setResult] = React.useState<WhatIfScenarioResult | null>(null)
  const [reqErr, setReqErr] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)

  const [scenarioName, setScenarioName] = React.useState("")
  const [localScenarios, setLocalScenarios] = React.useState<SavedScenario[]>(() => loadLocalScenarios(datasetId))
  const [deckScenarios, setDeckScenarios] = React.useState<SavedScenario[]>([])
  const [deckMsg, setDeckMsg] = React.useState<string | null>(null)
  const [deckErr, setDeckErr] = React.useState<string | null>(null)
  const [savingDeck, setSavingDeck] = React.useState(false)

  React.useEffect(() => {
    let active = true
    api.listScenarios(datasetId).then(
      (list) => { if (active) setDeckScenarios(list) },
      () => { if (active) setDeckScenarios([]) }
    )
    return () => { active = false }
  }, [datasetId])

  const requester = React.useMemo(
    () =>
      createScenarioRequester<WhatIfScenarioResult>(
        (changes, signal) => api.whatIfScenario(datasetId, changes, data.target, signal),
        { debounceMs: 250, minIntervalMs: 500 }
      ),
    [datasetId, data.target]
  )

  React.useEffect(() => () => requester.cancel(), [requester])

  const changes: WhatIfChange[] = React.useMemo(
    () => topDrivers.map((d) => ({ feature: d.name, pct_change: values[d.name] ?? 0 })),
    [topDrivers, values]
  )
  const allZero = isZeroVector(changes)

  React.useEffect(() => {
    if (allZero) {
      requester.cancel()
      return
    }
    let alive = true
    requester.trigger(changes).then(
      (res) => {
        if (!alive) return
        if (res) setResult(res)
        setReqErr(null)
        setBusy(false)
      },
      (err: Error) => {
        if (!alive) return
        setReqErr(err.message)
        setBusy(false)
      }
    )
    return () => { alive = false }
  }, [allZero, changes, requester])

  const resetAll = () => {
    requester.cancel()
    setValues(Object.fromEntries(topDrivers.map((d) => [d.name, 0])))
    setResult(null)
    setReqErr(null)
    setBusy(false)
    setDeckMsg(null)
    setDeckErr(null)
  }

  const buildFallbackName = () => {
    const moved = changes.filter((c) => c.pct_change !== 0)
    if (moved.length === 0) return "Kịch bản cơ sở"
    return moved
      .slice(0, 2)
      .map((c) => `${c.feature} ${c.pct_change > 0 ? "+" : ""}${c.pct_change}%`)
      .join(", ")
      .slice(0, 60)
  }

  const handleSaveLocal = () => {
    if (!result) return
    const name = (scenarioName.trim() || buildFallbackName()).slice(0, 60)
    const next = saveLocalScenario(datasetId, {
      name,
      request: { changes, target: data.target },
      result,
    })
    setLocalScenarios(next)
    setScenarioName("")
  }

  const handleDeleteLocal = (name: string) => {
    setLocalScenarios(removeLocalScenario(datasetId, name))
  }

  const handlePushDeck = async () => {
    if (!result || savingDeck) return
    const name = (scenarioName.trim() || buildFallbackName()).slice(0, 60)
    setSavingDeck(true)
    setDeckErr(null)
    setDeckMsg(null)
    try {
      const next = await api.saveScenario(datasetId, name, { changes, target: data.target })
      setDeckScenarios(next)
      setScenarioName("")
      setDeckMsg(`Đã đưa "${name}" vào deck (${next.length}/${MAX_SAVED_SCENARIOS}).`)
    } catch (e) {
      setDeckErr((e as Error).message)
    } finally {
      setSavingDeck(false)
    }
  }

  const handleDeleteDeck = async (name: string) => {
    try {
      const next = await api.deleteScenario(datasetId, name)
      setDeckScenarios(next)
      setDeckErr(null)
    } catch (e) {
      setDeckErr((e as Error).message)
    }
  }

  const activeResult = allZero ? null : result
  const activeErr = allZero ? null : reqErr
  const activeBusy = !allZero && busy
  const ciUncertain = activeResult ? hasZeroCrossing(activeResult.ci90_pct) : false
  const nonZeroContrib = (activeResult?.contributions ?? []).filter((c) => c.pct_change !== 0 && c.target_change_pct !== null)

  return (
    <PageShell>
      <div className="grid gap-4 px-4 lg:px-6 @5xl/main:grid-cols-12">
        <Card className="@5xl/main:col-span-6">
          <CardHeader>
            <CardTitle>Kịch bản đa biến (tối đa 5 yếu tố)</CardTitle>
            <CardDescription>
              Sắp xếp theo độ quan trọng hoán vị (permutation importance) đối với {data.target}. Điều chỉnh đồng thời để xem tác động tổng hợp.
            </CardDescription>
            <CardAction>
              <Button variant="ghost" size="sm" onClick={resetAll} disabled={allZero}>
                <RotateCcwIcon /> Đặt lại
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            {topDrivers.map((feat) => {
              const mode = formatUnitMode(feat)
              const val = values[feat.name] ?? 0
              const minTxt = feat.min !== undefined ? fmtNum(feat.min) : "–"
              const maxTxt = feat.max !== undefined ? fmtNum(feat.max) : "–"
              return (
                <div key={feat.name} className="grid gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <Label htmlFor={`slider-${feat.name}`} className="truncate font-medium">
                        {feat.name}
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        TB: {fmtNum(feat.mean)} · Phạm vi: [{minTxt}, {maxTxt}]
                        {mode.mode !== "pct_mean" ? ` · ${mode.unitLabel}` : ""}
                      </p>
                    </div>
                    <Badge variant={val === 0 ? "outline" : "secondary"} className="shrink-0 font-mono tabular-nums">
                      {val > 0 ? `+${val}%` : `${val}%`}
                    </Badge>
                  </div>
                  <Slider
                    id={`slider-${feat.name}`}
                    aria-label={`Thay đổi ${feat.name}`}
                    min={-30}
                    max={30}
                    step={1}
                    disabled={mode.disabled}
                    value={[val]}
                    onValueChange={(v) => {
                      const nextVal = Array.isArray(v) ? v[0] : v
                      const next = { ...values, [feat.name]: nextVal }
                      setValues(next)
                      if (topDrivers.every((d) => (next[d.name] ?? 0) === 0)) {
                        setResult(null)
                        setReqErr(null)
                        setBusy(false)
                      } else {
                        setReqErr(null)
                        setBusy(true)
                      }
                    }}
                  />
                </div>
              )
            })}
            {categoricalKept.length > 0 && (
              <div className="rounded-lg border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                Biến phân loại giữ nguyên: <span className="font-medium text-foreground">{categoricalKept.join(", ")}</span>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4 @5xl/main:col-span-6">
          <Card
            {...insightTarget("whatif", "multi-scenario", `Kịch bản what-if: ${data.target}`, {
              target: data.target,
              changes,
              result: activeResult,
            })}
          >
            <CardHeader>
              <CardTitle>Dự kiến thay đổi trên {data.target}</CardTitle>
              <CardDescription>
                Ridge chuẩn hoá với khoảng tin cậy 90% đồng bộ theo cùng lượt bootstrap (các lần lấy mẫu khớp nhau).
              </CardDescription>
              {ciUncertain && (
                <CardAction>
                  <Badge variant="outline">Không chắc chắn về chiều tác động</Badge>
                </CardAction>
              )}
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {activeErr ? (
                <Alert variant="destructive">
                  <AlertTriangleIcon />
                  <AlertTitle>Không tính được kịch bản</AlertTitle>
                  <AlertDescription>{activeErr}</AlertDescription>
                </Alert>
              ) : allZero ? (
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Chưa thay đổi</div>
                  <div className="text-3xl font-semibold tabular-nums">0.0%</div>
                  <div className="text-sm text-muted-foreground">KTC 90%: [0.0%, 0.0%] · Kéo ít nhất một thanh trượt để mô phỏng.</div>
                </div>
              ) : activeResult ? (
                <div className="rounded-lg border p-4">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm text-muted-foreground">Thay đổi kỳ vọng của {activeResult.target}</span>
                    {activeBusy && <span className="text-xs text-muted-foreground">Đang cập nhật…</span>}
                  </div>
                  <div className="mt-1 text-3xl font-semibold tabular-nums">{fmtPct(activeResult.target_change_pct)}</div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    KTC 90%: {fmtPct(activeResult.ci90_pct[0])} đến {fmtPct(activeResult.ci90_pct[1])} · ≈ {fmtNum(activeResult.target_change_abs)} trên mức nền TB {fmtNum(activeResult.baseline_target_mean)}
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{activeResult.interpretation}</p>
                </div>
              ) : (
                <div className="rounded-lg border p-4 text-sm text-muted-foreground">Đang tính kịch bản…</div>
              )}

              {(activeResult?.range_warnings?.length || activeResult?.collinearity_warnings?.length) ? (
                <Alert>
                  <AlertTriangleIcon />
                  <AlertTitle>Cảnh báo ngoại suy / đa cộng tuyến</AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc pl-4 text-xs">
                      {activeResult.range_warnings.map((w) => <li key={w}>{w}</li>)}
                      {(activeResult.collinearity_warnings ?? []).map((w) => <li key={w}>{w}</li>)}
                    </ul>
                  </AlertDescription>
                </Alert>
              ) : null}

              {nonZeroContrib.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium text-muted-foreground">Đóng góp riêng lẻ từng yếu tố (Δ% {data.target})</p>
                  <InsightChart
                    spec={{
                      kind: "hbar",
                      x: nonZeroContrib.map((c) => `${c.feature} (${c.pct_change > 0 ? "+" : ""}${c.pct_change}%)`),
                      series: [{ name: `Δ% ${data.target}`, data: nonZeroContrib.map((c) => c.target_change_pct) }],
                    }}
                    height={Math.max(150, nonZeroContrib.length * 42)}
                  />
                </div>
              )}
            </CardContent>
            <CardFooter className="flex flex-col items-stretch gap-3 border-t pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  maxLength={60}
                  placeholder="Tên kịch bản (vd. Gói đầu tư công +10%)"
                  aria-label="Tên kịch bản"
                  className="min-w-48 flex-1"
                />
                <Button variant="outline" size="sm" onClick={handleSaveLocal} disabled={!activeResult}>
                  <BookmarkPlusIcon /> Lưu kịch bản
                </Button>
                <Button
                  size="sm"
                  onClick={() => void handlePushDeck()}
                  disabled={!activeResult || savingDeck || deckScenarios.length >= MAX_SAVED_SCENARIOS}
                >
                  <SendIcon /> Đưa vào deck
                </Button>
              </div>
              {deckMsg && <p className="text-xs text-muted-foreground">{deckMsg}</p>}
              {deckErr && <p className="text-xs text-destructive">{deckErr}</p>}
              <p className="text-xs text-muted-foreground">
                Lưu ý: Liên đới theo mô hình, không phải nhân quả — cần kiểm chứng bằng thí điểm thực địa.
              </p>
            </CardFooter>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>So sánh kịch bản đã lưu ({localScenarios.length}/{MAX_SAVED_SCENARIOS})</CardTitle>
            <CardDescription>Lưu trên trình duyệt (localStorage) cho dataset hiện tại; giữ nguyên số liệu do API tính.</CardDescription>
          </CardHeader>
          <CardContent>
            {localScenarios.length === 0 ? (
              <p className="text-sm text-muted-foreground">Chưa lưu kịch bản nào. Kéo thanh trượt và bấm “Lưu kịch bản” để đối chiếu.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kịch bản</TableHead>
                    <TableHead className="text-right">Δ%</TableHead>
                    <TableHead className="text-right">KTC 90%</TableHead>
                    <TableHead className="w-16 text-right">Xoá</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {localScenarios.map((s) => (
                    <TableRow key={s.name}>
                      <TableCell className="max-w-48 truncate font-medium" title={s.name}>{s.name}</TableCell>
                      <TableCell className="text-right font-mono tabular-nums">{fmtPct(s.result.target_change_pct)}</TableCell>
                      <TableCell className="text-right font-mono text-xs tabular-nums">
                        [{fmtPct(s.result.ci90_pct[0])}, {fmtPct(s.result.ci90_pct[1])}]
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon-sm" aria-label={`Xoá ${s.name}`} onClick={() => handleDeleteLocal(s.name)}>
                          <Trash2Icon className="size-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Kịch bản đưa vào Deck ({deckScenarios.length}/{MAX_SAVED_SCENARIOS})</CardTitle>
            <CardDescription>Được lưu ở backend (scenarios.json) để đưa vào slide Tác động khi xuất pitch deck.</CardDescription>
          </CardHeader>
          <CardContent>
            {deckScenarios.length === 0 ? (
              <p className="text-sm text-muted-foreground">Chưa có kịch bản nào đưa vào deck.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kịch bản</TableHead>
                    <TableHead className="text-right">Δ%</TableHead>
                    <TableHead className="text-right">KTC 90%</TableHead>
                    <TableHead className="w-16 text-right">Xoá</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {deckScenarios.map((s) => (
                    <TableRow key={s.name}>
                      <TableCell className="max-w-48 truncate font-medium" title={s.name}>{s.name}</TableCell>
                      <TableCell className="text-right font-mono tabular-nums">{fmtPct(s.result.target_change_pct)}</TableCell>
                      <TableCell className="text-right font-mono text-xs tabular-nums">
                        [{fmtPct(s.result.ci90_pct[0])}, {fmtPct(s.result.ci90_pct[1])}]
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon-sm" aria-label={`Gỡ khỏi deck ${s.name}`} onClick={() => void handleDeleteDeck(s.name)}>
                          <Trash2Icon className="size-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </PageShell>
  )
}
