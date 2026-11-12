"use client"

import * as React from "react"
import { CircleCheckIcon, LoaderIcon } from "lucide-react"

import { useDataset } from "@/components/dataset-provider"
import { InsightChart } from "@/components/insight-chart"
import { ErrorState, LoadingState, PageShell } from "@/components/state"
import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useAsync } from "@/hooks/use-async"
import { api } from "@/lib/api/client"
import { fmtP } from "@/lib/format"

export default function InsightsPage() {
  const { datasetId } = useDataset()
  const { data, error, loading } = useAsync(() => (datasetId ? api.insights(datasetId) : null), [datasetId])
  const [lang, setLang] = React.useState<"en" | "vi">("en")
  if (error) return <PageShell><ErrorState error={error} /></PageShell>
  if (loading || !data) return <PageShell><LoadingState /></PageShell>
  const recBy = Object.fromEntries(data.recommendations.map((r) => [r.from_insight, r]))
  return (
    <PageShell>
      <div className="flex items-center justify-between px-4 lg:px-6">
        <p className="text-sm text-muted-foreground">
          Ranked by effect size × statistical significance × business relevance. Associations, not causal effects.
        </p>
        <ToggleGroup multiple={false} value={[lang]} onValueChange={(v) => setLang((v[0] as "en" | "vi") ?? "en")} variant="outline">
          <ToggleGroupItem value="en">English</ToggleGroupItem>
          <ToggleGroupItem value="vi">Tiếng Việt</ToggleGroupItem>
        </ToggleGroup>
      </div>
      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @5xl/main:grid-cols-2">
        {data.insights.map((i) => {
          const rec = recBy[i.id]
          const sig = i.p_value !== null && i.p_value < 0.05
          return (
            <Card key={i.id} className="@container/card">
              <CardHeader>
                <CardDescription>#{i.rank} · {i.type.replace("_", " ")}</CardDescription>
                <CardTitle className="text-lg">{lang === "en" ? i.title_en : i.title_vi}</CardTitle>
                <CardAction>
                  <Badge variant="outline" className="text-muted-foreground">
                    {sig ? <CircleCheckIcon className="fill-green-500 dark:fill-green-400" /> : <LoaderIcon />}
                    score {i.score.toFixed(2)}
                  </Badge>
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <p className="text-sm leading-relaxed">{lang === "en" ? i.sentence_en : i.sentence_vi}</p>
                {i.chart && <InsightChart spec={i.chart} />}
              </CardContent>
              <CardFooter className="flex-col items-start gap-1.5 text-sm">
                <div className="text-muted-foreground">Evidence: {i.test}{i.p_value !== null ? ` · ${fmtP(i.p_value)}` : ""}{i.effect !== null ? ` · effect ${i.effect.toFixed(2)}` : ""}</div>
                {rec && (
                  <div className="mt-1 rounded-lg border p-3">
                    <div><span className="font-medium">So what → </span>{lang === "en" ? rec.so_what_en : rec.so_what_vi}</div>
                    <div className="mt-1"><span className="font-medium">Now what → </span>{lang === "en" ? rec.now_what_en : rec.now_what_vi}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{lang === "en" ? rec.impact_en : rec.impact_vi}</div>
                  </div>
                )}
                {i.caveat && <div className="text-xs text-muted-foreground">Caveat: {i.caveat}</div>}
              </CardFooter>
            </Card>
          )
        })}
      </div>
    </PageShell>
  )
}
