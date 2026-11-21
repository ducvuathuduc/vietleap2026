// Live eval for the NPL study assistant.
// Runs the fixture cases and current-publication cases against the
// configured provider and grades tool choice, grounding, citations and language.
// With Langfuse project keys
// the cases are pushed as dataset items and the run is recorded as a Langfuse
// dataset run; without them it runs locally and prints that it was skipped.
// Usage: npm run eval:npl [-- --out results.json]
import { readFileSync, writeFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { type LanguageModel, type ToolLoopAgent } from "ai"

import { makeNplAgent } from "../agent.ts"
import { investmentAdviceNotice } from "../answer-policy.ts"
import { detectLang } from "../lang.ts"
import { loadNplSnapshot } from "../snapshot.ts"
import { loadRepoEnv } from "../../../llm/env.ts"
import { filterInput, redactPii } from "../../../llm/guards.ts"
import { providerName, createAssistantModel } from "../../../llm/model.ts"
import type { Snapshot } from "../../view.ts"
import { scoreAnswer, type EvalCase } from "./score.ts"

const CASES_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "cases.json")
const FIXTURE_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../../seed/npl/snapshot.fixture.json")
const DECODER_PATH = path.join(path.dirname(FIXTURE_PATH), "decoder.fixture.json")
const DATASET_NAME = "npl-eval"
const CASE_TIMEOUT_MS = 120_000
const PASS_RATE = 0.9

interface CaseUsage {
  inputTokens: number
  outputTokens: number
}

interface CaseResult extends ReturnType<typeof scoreAnswer> {
  id: string
  lang: string
  question: string
  expect_tool: string
  tools_called: string[]
  tool_inputs: unknown[]
  expect_numbers: number[]
  mixed: boolean
  usage: CaseUsage
  error?: string
}

function num(v: unknown): number {
  return typeof v === "number" && Number.isFinite(v) ? v : 0
}

async function runCase(snapshot: Snapshot, model: LanguageModel, c: EvalCase): Promise<CaseResult> {
  const lang = detectLang(c.question)
  const pii = filterInput(c.question)
  const notice = pii.ok ? investmentAdviceNotice(c.question, lang) : lang === "vi" ? pii.notice_vi : pii.notice_en
  if (notice) return caseResult(c, notice, [], [], [], { inputTokens: 0, outputTokens: 0 })

  const agent = makeNplAgent({ snapshot, model, lang })
  if (!agent) throw new Error("agent unavailable")
  let result: Awaited<ReturnType<ToolLoopAgent["generate"]>>
  const abortSignal = AbortSignal.timeout(CASE_TIMEOUT_MS)
  try {
    result = await agent.generate({ prompt: c.question, abortSignal })
  } catch (e) {
    const error = abortSignal.aborted ? `timeout after ${CASE_TIMEOUT_MS / 1000}s` :
      e instanceof Error ? e.message.slice(0, 300) : String(e)
    return { ...caseResult(c, "", [], [], [], { inputTokens: 0, outputTokens: 0 }), error }
  }
  const calls: string[] = []
  const inputs: unknown[] = []
  const outputs: unknown[] = []
  for (const step of result.steps) {
    for (const part of step.content) {
      if (part.type === "tool-call") {
        calls.push((part as { toolName: string }).toolName)
        inputs.push((part as { input: unknown }).input)
      } else if (part.type === "tool-result") outputs.push((part as { output: unknown }).output)
    }
  }
  const u = result.totalUsage
  return caseResult(c, result.text, calls, inputs, outputs, { inputTokens: num(u?.inputTokens), outputTokens: num(u?.outputTokens) })
}

function caseResult(
  c: EvalCase,
  text: string,
  calls: string[],
  inputs: unknown[],
  outputs: unknown[],
  usage: CaseUsage,
): CaseResult {
  return {
    id: c.id,
    lang: c.lang,
    question: String(redactPii(c.question)),
    expect_tool: c.expect_tool,
    tools_called: calls,
    tool_inputs: inputs,
    expect_numbers: c.expect_numbers,
    mixed: c.mixed === true,
    usage,
    ...scoreAnswer(c, text, calls, outputs),
  }
}

function describe(r: CaseResult): string {
  const tool = r.expect_tool === "none" ? "adversarial" : r.tool_ok ? r.expect_tool : `want ${r.expect_tool}, got [${r.tools_called.join(",") || "none"}]`
  const guard = r.guard_clean ? "clean" : `flagged ${r.flagged.join(",")}`
  return `${r.pass ? "pass" : "FAIL"} ${r.id} tool=${tool} numbers=${r.numbers_ok} guard=${guard} citations=${r.citations_ok} language=${r.language_ok} format=${r.regex_ok}${r.error ? ` (${r.error})` : ""}`
}

function rate(results: CaseResult[], key: (r: CaseResult) => boolean): string {
  return `${results.filter(key).length}/${results.length}`
}

async function main(): Promise<void> {
  loadRepoEnv()
  const outArg = process.argv.indexOf("--out")
  const outPath = outArg >= 0 ? process.argv[outArg + 1] : undefined

  const provider = providerName()
  const chosen = createAssistantModel(process.env, `eval-npl-${new Date().toISOString().slice(0, 10)}`)
  if (!chosen) {
    console.error("eval: offline — no LLM key configured, live eval needs a provider")
    process.exit(1)
  }
  console.log(`eval: provider=${provider} model=${chosen.label}`)

  const snapshot = JSON.parse(readFileSync(FIXTURE_PATH, "utf8")) as Snapshot
  const { decoder } = JSON.parse(readFileSync(DECODER_PATH, "utf8")) as Pick<Snapshot, "decoder">
  snapshot.decoder = decoder
  const cases = JSON.parse(readFileSync(CASES_PATH, "utf8")) as EvalCase[]
  const passBar = Math.ceil(cases.length * PASS_RATE)
  const published = await loadNplSnapshot()
  const dataFor = (c: EvalCase) => c.published ? published : snapshot

  const results: CaseResult[] = []
  let experimentUrl: string | null = null
  let langfuseShutdown: (() => Promise<void>) | null = null
  const projectKeys = process.env.LANGFUSE_PUBLIC_KEY?.trim() && process.env.LANGFUSE_SECRET_KEY?.trim()
  // Rate-limited providers (Groq free tier: 8000 TPM) need spacing between cases.
  const delayMs = Number(process.env.EVAL_CASE_DELAY_MS ?? "0") || 0
  const concurrency = Math.min(8, Math.max(1, Math.floor(Number(process.env.EVAL_CONCURRENCY) || 1)))
  const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

  if (projectKeys && !process.argv.includes("--local")) {
    try {
      const { LangfuseClient } = await import("@langfuse/client")
      const lf = new LangfuseClient()
      langfuseShutdown = () => lf.shutdown()
      try {
        await lf.api.datasets.create({ name: DATASET_NAME, description: "NPL study assistant eval cases (fixture snapshot)" })
      } catch {
        // already exists — dedupe and upsert below
      }
      // One item per case id: delete duplicates and items whose expected
      // output no longer matches the local cases, create the missing ones.
      const existing = await lf.dataset.get(DATASET_NAME)
      const byId = new Map(cases.map((c) => [c.id, c]))
      const kept = new Set<string>()
      for (const item of existing.items) {
        const input = item.input as { id?: string; question?: string } | undefined
        const id = input?.id
        const expected = item.expectedOutput as { expect_tool?: unknown } | undefined
        const local = id ? byId.get(id) : undefined
        if (!id || kept.has(id) || !local || expected?.expect_tool !== local.expect_tool ||
          input?.question !== redactPii(local.question)) {
          await lf.api.datasetItems.delete(item.id)
          continue
        }
        kept.add(id)
      }
      for (const c of cases) {
        if (kept.has(c.id)) continue
        await lf.dataset.createItem({
          datasetName: DATASET_NAME,
          input: { id: c.id, lang: c.lang, question: redactPii(c.question) as string },
          expectedOutput: { expect_tool: c.expect_tool, expect_numbers: c.expect_numbers },
        })
      }
      const dataset = await lf.dataset.get(DATASET_NAME)
      const runName = `eval-npl-${provider}-${new Date().toISOString().replace(/[:.]/g, "-")}`
      const run = await dataset.runExperiment({
        name: "NPL study assistant eval",
        runName,
        description: "VI/EN cases with fixture and published data, tool choice, grounded numbers, citations and language",
        metadata: { provider, model: chosen.label },
        maxConcurrency: 1,
        task: async (raw: unknown) => {
          const item = raw as { input: { id?: string } }
          const c = item.input.id ? byId.get(item.input.id) : undefined
          if (!c) return { pass: 0, tool_ok: 0, guard_clean: 0, citations_ok: 0, language_ok: 0 }
          if (delayMs > 0) await sleep(delayMs)
          const r = await runCase(dataFor(c), chosen.model, c)
          results.push(r)
          console.log(describe(r))
          return { pass: Number(r.pass), tool_ok: Number(r.tool_ok), guard_clean: Number(r.guard_clean), citations_ok: Number(r.citations_ok), language_ok: Number(r.language_ok) }
        },
        evaluators: [
          async (params: { output: Record<string, number> }) => ({ name: "tool_choice", value: params.output.tool_ok }),
          async (params: { output: Record<string, number> }) => ({ name: "numbers_guard_clean", value: params.output.guard_clean }),
          async (params: { output: Record<string, number> }) => ({ name: "citations_present", value: params.output.citations_ok }),
          async (params: { output: Record<string, number> }) => ({ name: "language_matched", value: params.output.language_ok }),
          async (params: { output: Record<string, number> }) => ({ name: "pass", value: params.output.pass }),
        ],
      })
      experimentUrl = run.experimentUrl ?? null
      console.log(`langfuse: dataset run recorded — ${run.experimentUrl ?? run.experimentId}`)
    } catch (e) {
      console.warn(`langfuse: dataset run skipped (${e instanceof Error ? e.message : String(e)})`)
    }
  } else {
    console.log("langfuse: dataset run skipped (local mode or no project keys)")
  }

  const completed = new Set(results.map((r) => r.id))
  const remaining = cases.filter((c) => !completed.has(c.id))
  for (let index = 0; index < remaining.length; index += concurrency) {
    if (delayMs > 0) await sleep(delayMs)
    await Promise.all(remaining.slice(index, index + concurrency).map(async (c) => {
      const r = await runCase(dataFor(c), chosen.model, c)
      results.push(r)
      console.log(describe(r))
    }))
  }

  const mixed = results.filter((r) => r.mixed)
  const publishedIds = new Set(cases.filter((c) => c.published).map((c) => c.id))
  const publishedResults = results.filter((result) => publishedIds.has(result.id))
  const hardCases = results.filter((result) => result.id.startsWith("b26-"))
  const inputTokens = results.reduce((s, r) => s + r.usage.inputTokens, 0)
  const outputTokens = results.reduce((s, r) => s + r.usage.outputTokens, 0)
  const unguardedNumbers = results.reduce((count, r) => count + r.unguarded.length, 0)

  const summary = {
    provider,
    model: chosen.label,
    cases: results.length,
    tool_choice: rate(results, (r) => r.tool_ok),
    numbers_guard_clean: rate(results, (r) => r.guard_clean),
    citations_present: rate(results, (r) => r.citations_ok),
    answered: rate(results, (r) => r.answered),
    expected_numbers_answered: rate(results, (r) => r.numbers_ok),
    language_matched: rate(results, (r) => r.language_ok),
    mixed_language_matched: rate(mixed, (r) => r.language_ok),
    published_pass: rate(publishedResults, (r) => r.pass),
    hard_cases_pass: rate(hardCases, (r) => r.pass),
    unguarded_numbers: unguardedNumbers,
    pass: rate(results, (r) => r.pass),
    usage: { inputTokens, outputTokens },
    langfuse_experiment_url: experimentUrl,
    results,
  }
  console.log(
    `\ntotals: tool choice ${summary.tool_choice}, numbers guard clean ${summary.numbers_guard_clean}, unguarded numbers ${unguardedNumbers}, citations ${summary.citations_present}, answered ${summary.answered}, expected numbers ${summary.expected_numbers_answered}, language ${summary.language_matched}, mixed language ${summary.mixed_language_matched}, hard cases ${summary.hard_cases_pass}, PASS ${summary.pass}`,
  )

  if (outPath) {
    writeFileSync(outPath, JSON.stringify(summary, null, 2))
    console.log(`results written to ${outPath}`)
  }
  if (langfuseShutdown) await langfuseShutdown()
  const passed = results.filter((r) => r.pass).length
  if (results.length !== cases.length || passed < passBar || unguardedNumbers !== 0 ||
    mixed.length !== 6 || mixed.some((r) => !r.language_ok)) {
    console.error(`eval: acceptance requires ${passBar}/${cases.length} passes, no unguarded numbers and all six mixed languages matched`)
    process.exitCode = 1
  }
}

main().catch((e) => {
  console.error(`eval failed: ${e instanceof Error ? e.stack ?? e.message : String(e)}`)
  process.exit(1)
})
