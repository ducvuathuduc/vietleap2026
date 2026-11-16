import { generateText } from "ai"
import { z } from "zod"

import { rateLimited } from "@/lib/rate-limit"

import type { Brief, DatasetDetail, Insight, Recommendation } from "@/lib/api/types"
import { backend, BackendError, dsPath } from "@/lib/analyst/backend"
import { analystModel } from "@/lib/analyst/model"
import { mergeDraft, offlineStory, parseDraft, pickInsights, STORY_SIZE, storyPrompt } from "@/lib/analyst/story"

export const maxDuration = 60

const Body = z.object({
  datasetId: z.string().regex(/^[\w.-]{1,80}$/),
  n: z.number().int().min(1).max(8).optional(),
})

/**
 * Auto-insight story: top-N engine insights narrated for a driver.js walkthrough.
 * With an LLM key the model writes the narration, but any sentence with a number not found in the engine
 * output is replaced by the engine's own sentence. Without a key (or on any model error) the story is the
 * deterministic engine text — the endpoint never fails because of the LLM.
 * Feature 002: `question` (quoted from the dataset's brief.json, or null) and `limits` (results caveats) frame the
 * story; both are passed through untouched — the brief is user text and never reaches the model prompt.
 */
export async function POST(req: Request) {
  const limited = rateLimited(req)
  if (limited) return limited
  let body: z.infer<typeof Body>
  try {
    body = Body.parse(await req.json())
  } catch (e) {
    const msg = e instanceof z.ZodError ? e.issues.map((i) => `${i.path.join(".") || "body"}: ${i.message}`).join("; ") : (e as Error).message
    return Response.json({ detail: `Yêu cầu không hợp lệ: ${msg}` }, { status: 400 })
  }
  const base = dsPath(body.datasetId)
  let insights: Insight[]
  let recs: Recommendation[]
  let name = body.datasetId
  try {
    const r = await backend<{ insights: Insight[]; recommendations: Recommendation[] }>(`${base}/insights`)
    insights = r.insights
    recs = r.recommendations
  } catch (e) {
    const status = e instanceof BackendError && e.status ? e.status : 502
    return Response.json({ detail: (e as Error).message }, { status })
  }
  let caveats: string[] = []
  try {
    const detail = await backend<DatasetDetail>(base)
    name = detail.meta.name || name
    caveats = detail.caveats
  } catch {
    /* name and limits are optional framing */
  }
  const brief = await backend<Brief>(`${base}/brief`).catch(() => null) // 404 = no brief parsed for this dataset

  const n = body.n ?? STORY_SIZE
  const story = offlineStory(insights, recs, name, n, { brief, caveats })
  const llm = analystModel()
  if (!llm || story.steps.length === 0) return Response.json(story)
  try {
    const top = pickInsights(insights, n)
    const { text } = await generateText({
      model: llm.model,
      prompt: storyPrompt(top, recs, name),
      temperature: 0.3,
      maxOutputTokens: 1500,
      abortSignal: AbortSignal.timeout(40_000),
    })
    return Response.json(mergeDraft(story, parseDraft(text), top, recs, llm.label))
  } catch {
    return Response.json(story)
  }
}
