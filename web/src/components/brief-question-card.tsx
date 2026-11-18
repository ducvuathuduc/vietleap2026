"use client"

import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useAsync } from "@/hooks/use-async"
import { storyQuestion, type StoryQuestion } from "@/lib/analyst/story"
import { api } from "@/lib/api/client"

/** The dataset's brief question; only requested when the summary says a brief exists (no 404 in the console). */
function loadQuestion(datasetId: string, hasBrief: boolean): Promise<StoryQuestion | null> {
  return hasBrief ? api.datasetBrief(datasetId).then(storyQuestion) : Promise.resolve(null)
}

const ROWS: [label: string, key: "who" | "what" | "kpi"][] = [
  ["Ai quyết định", "who"],
  ["Quyết định gì", "what"],
  ["KPI thành công", "kpi"],
]

/**
 * "Câu hỏi quyết định" on Tổng quan (feature 002): the brief's question quoted verbatim + who / what / KPI.
 * Brief text is user data — rendered as text only and deliberately not tagged for "Hỏi AI" (never sent to the model).
 * `data-tour="brief-question"` is the first stop of the "Câu chuyện" walkthrough.
 */
export function BriefQuestionCard({ datasetId, hasBrief }: { datasetId: string; hasBrief: boolean }) {
  const q = useAsync(() => loadQuestion(datasetId, hasBrief), [datasetId, hasBrief])
  if (q.loading) return <Skeleton className="h-32 rounded-xl" />
  if (q.error) return null // the overview still works without the brief
  const question = q.data
  return (
    <Card data-tour="brief-question">
      <CardHeader>
        <CardDescription>{question ? "Câu hỏi quyết định · Đề bài (trích nguyên văn)" : "Câu hỏi quyết định"}</CardDescription>
        <CardTitle>{question ? <q>{question.text}</q> : "Bộ dữ liệu chưa có đề bài"}</CardTitle>
      </CardHeader>
      {question ? (
        <CardContent>
          <dl className="grid gap-1 text-sm">
            {ROWS.filter(([, key]) => question[key]).map(([label, key]) => (
              <div key={key} className="flex gap-2">
                <dt className="text-muted-foreground">{label}:</dt>
                <dd>{question[key]}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      ) : (
        <CardFooter>
          <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/brief" />}>
            Dán đề bài
          </Button>
        </CardFooter>
      )}
    </Card>
  )
}
