// Live eval for the RateWatch assistant (brief T5 item 7).
// Runs the 20 fixture-grounded cases in cases.json against the configured
// provider, and prints pass rates for: tool choice, numbers guard clean,
// citations present. With Langfuse project keys the cases are pushed as
// dataset items and the run is recorded as a Langfuse dataset run; without
// them it runs locally and prints that the dataset run was skipped.
// Usage: npm run eval:ai [-- --out results.json]  (LLM_PROVIDER=groq for the Groq run)
import { readFileSync, writeFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { type ToolLoopAgent } from "ai"

import { makeRatewatchAgent } from "../agent.ts"
import { loadRepoEnv } from "../env.ts"
import { collectTruthNumbers, guardNumbers } from "../guards.ts"
import { providerName, ratewatchModel } from "../model.ts"
import type { Snapshot } from "../../types.ts"

const CASES_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "cases.json")
const FIXTURE_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../..", "seed/ratewatch/snapshot.fixture.json")
const DATASET_NAME = "ratewatch-eval"
const CASE_TIMEOUT_MS = 120_000
// Groq listed prices (USD per million tokens, 2026-11): gpt-oss-120b 0.15 in / 0.60 out.
const GROQ_USD_PER_MTOK = { input: 0.15, output: 0.6 }

interface EvalCase {
  id: string
  lang: "vi" | "en"
  question: string
  expect_tool: string
  expect_numbers: number[]
}

interface CaseUsage {
  inputTokens: number
  outputTokens: number
}

interface CaseResult {
  id: string
  lang: string
  question: string
  expect_tool: string
  tools_called: string[]
  tool_inputs: unknown[]
  tool_ok: boolean
  expect_numbers: number[]
  numbers_ok: boolean
  flagged: string[]
  guard_clean: boolean
  citations_ok: boolean
  answered: boolean
  answer: string
  pass: boolean
  usage: CaseUsage
  error?: string
}

function close(a: number, b: number): boolean {
  if (a === b) return true
  const scale = Math.max(Math.abs(a), Math.abs(b))
  return Math.abs(a - b) <= Math.max(0.006, scale * 0.006)
}

function num(v: unknown): number {
  return typeof v === "number" && Number.isFinite(v) ? v : 0
}

async function runCase(agent: ToolLoopAgent, c: EvalCase): Promise<CaseResult> {
  let result: Awaited<ReturnType<ToolLoopAgent["generate"]>>
  try {
    result = await agent.generate({ prompt: c.question })
  } catch (e) {
    return {
      id: c.id,
      lang: c.lang,
      question: c.question,
      expect_tool: c.expect_tool,
      tools_called: [],
      tool_inputs: [],
      tool_ok: false,
      expect_numbers: c.expect_numbers,
      numbers_ok: false,
      flagged: [],
      guard_clean: true,
      citations_ok: false,
      answered: false,
      answer: "",
      pass: false,
      usage: { inputTokens: 0, outputTokens: 0 },
      error: e instanceof Error ? e.message.slice(0, 300) : String(e),
    }
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
  const truth = collectTruthNumbers(outputs)
  const guarded = guardNumbers(result.text ?? "", truth)
  const toolOk = calls.includes(c.expect_tool)
  const numbersOk = c.expect_numbers.every((n) => truth.some((t) => close(n, t)))
  // Error outputs (found: false) carry no citations by design; every data-bearing
  // output must cite, and at least one output must cite.
  const dataOutputs = outputs.filter((o) => (o as { found?: unknown })?.found !== false)
  const citationsOk =
    dataOutputs.length > 0 &&
    dataOutputs.every((o) => Array.isArray((o as { citations?: unknown })?.citations) && (o as { citations: unknown[] }).citations.length > 0)
  const answered = (result.text ?? "").trim().length > 0
  const u = result.totalUsage
  return {
    id: c.id,
    lang: c.lang,
    question: c.question,
    expect_tool: c.expect_tool,
    tools_called: calls,
    tool_inputs: inputs,
    tool_ok: toolOk,
    expect_numbers: c.expect_numbers,
    numbers_ok: numbersOk,
    flagged: guarded.flagged,
    guard_clean: guarded.flagged.length === 0,
    citations_ok: citationsOk,
    answered,
    answer: guarded.text,
    pass: toolOk && numbersOk && guarded.flagged.length === 0 && citationsOk && answered,
    usage: { inputTokens: num(u?.inputTokens), outputTokens: num(u?.outputTokens) },
  }
}

function timeoutResult(c: EvalCase): CaseResult {
  return {
    id: c.id,
    lang: c.lang,
    question: c.question,
    expect_tool: c.expect_tool,
    tools_called: [],
    tool_inputs: [],
    tool_ok: false,
    expect_numbers: c.expect_numbers,
    numbers_ok: false,
    flagged: [],
    guard_clean: true,
    citations_ok: false,
    answered: false,
    answer: "",
    pass: false,
    usage: { inputTokens: 0, outputTokens: 0 },
    error: `timeout after ${CASE_TIMEOUT_MS / 1000}s`,
  }
}

function runCaseWithTimeout(agent: ToolLoopAgent, c: EvalCase): Promise<CaseResult> {
  const timeout = new Promise<CaseResult>((resolve) => setTimeout(() => resolve(timeoutResult(c)), CASE_TIMEOUT_MS))
  return Promise.race([runCase(agent, c), timeout])
}

function describe(r: CaseResult): string {
  const tool = r.tool_ok ? r.expect_tool : `want ${r.expect_tool}, got [${r.tools_called.join(",") || "none"}]`
  const guard = r.guard_clean ? "clean" : `flagged ${r.flagged.join(",")}`
  return `${r.pass ? "pass" : "FAIL"} ${r.id} tool=${tool} numbers=${r.numbers_ok} guard=${guard} citations=${r.citations_ok}${r.error ? ` (${r.error})` : ""}`
}

function rate(results: CaseResult[], key: (r: CaseResult) => boolean): string {
  return `${results.filter(key).length}/${results.length}`
}

async function main(): Promise<void> {
  loadRepoEnv()
  const outArg = process.argv.indexOf("--out")
  const outPath = outArg >= 0 ? process.argv[outArg + 1] : undefined

  const provider = providerName()
  const chosen = ratewatchModel(process.env, `eval-${new Date().toISOString().slice(0, 10)}`)
  if (!chosen) {
    console.error("eval: offline — no LLM key configured, live eval needs a provider")
    process.exit(1)
  }
  console.log(`eval: provider=${provider} model=${chosen.label}`)

  const snapshot = JSON.parse(readFileSync(FIXTURE_PATH, "utf8")) as Snapshot
  const agent = makeRatewatchAgent({ snapshot, model: chosen.model })
  if (!agent) {
    console.error("eval: agent unavailable")
    process.exit(1)
  }
  const cases = JSON.parse(readFileSync(CASES_PATH, "utf8")) as EvalCase[]

  const results: CaseResult[] = []
  let experimentUrl: string | null = null
  let langfuseShutdown: (() => Promise<void>) | null = null
  const projectKeys = process.env.LANGFUSE_PUBLIC_KEY?.trim() && process.env.LANGFUSE_SECRET_KEY?.trim()
  // Rate-limited providers (Groq free tier: 8000 TPM) need spacing between cases.
  const delayMs = Number(process.env.EVAL_CASE_DELAY_MS ?? "0") || 0
  const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

  if (projectKeys) {
    try {
      const { LangfuseClient } = await import("@langfuse/client")
      const lf = new LangfuseClient()
      langfuseShutdown = () => lf.shutdown()
      try {
        await lf.api.datasets.create({ name: DATASET_NAME, description: "RateWatch assistant eval cases (fixture snapshot)" })
      } catch {
        // already exists — dedupe and upsert below
      }
      // One item per case id: delete duplicates from earlier runs, create missing ones.
      const existing = await lf.dataset.get(DATASET_NAME)
      const seen = new Set<string>()
      for (const item of existing.items) {
        const id = (item.input as { id?: string } | undefined)?.id
        if (id && seen.has(id)) await lf.api.datasetItems.delete(item.id)
        else if (id) seen.add(id)
      }
      for (const c of cases) {
        if (seen.has(c.id)) continue
        await lf.dataset.createItem({
          datasetName: DATASET_NAME,
          input: { id: c.id, lang: c.lang, question: c.question },
          expectedOutput: { expect_tool: c.expect_tool, expect_numbers: c.expect_numbers },
        })
        seen.add(c.id)
      }
      const dataset = await lf.dataset.get(DATASET_NAME)
      const runName = `eval-${provider}-${new Date().toISOString().replace(/[:.]/g, "-")}`
      const run = await dataset.runExperiment({
        name: "RateWatch assistant eval",
        runName,
        description: "20 VI/EN cases: tool choice, grounded numbers, citations (fixture snapshot)",
        metadata: { provider, model: chosen.label },
        maxConcurrency: 1,
        task: async (raw: unknown) => {
          // Dataset items come back untyped from the Langfuse API: narrow before use.
          const item = raw as { input: { id?: unknown; lang?: unknown; question?: unknown }; expectedOutput?: unknown }
          const expected = (item.expectedOutput ?? null) as { expect_tool?: unknown; expect_numbers?: unknown } | null
          if (
            typeof item.input.id !== "string" ||
            typeof item.input.question !== "string" ||
            (item.input.lang !== "vi" && item.input.lang !== "en") ||
            !expected ||
            typeof expected.expect_tool !== "string" ||
            !Array.isArray(expected.expect_numbers)
          ) {
            return { pass: 0, tool_ok: 0, guard_clean: 0, citations_ok: 0 }
          }
          if (delayMs > 0) await sleep(delayMs)
          const c: EvalCase = {
            id: item.input.id,
            lang: item.input.lang,
            question: item.input.question,
            expect_tool: expected.expect_tool,
            expect_numbers: expected.expect_numbers,
          }
          const r = await runCaseWithTimeout(agent, c)
          results.push(r)
          console.log(describe(r))
          return { pass: r.pass ? 1 : 0, tool_ok: r.tool_ok ? 1 : 0, guard_clean: r.guard_clean ? 1 : 0, citations_ok: r.citations_ok ? 1 : 0 }
        },
        evaluators: [
          async (params: { output: Record<string, number> }) => ({ name: "tool_choice", value: params.output.tool_ok }),
          async (params: { output: Record<string, number> }) => ({ name: "numbers_guard_clean", value: params.output.guard_clean }),
          async (params: { output: Record<string, number> }) => ({ name: "citations_present", value: params.output.citations_ok }),
          async (params: { output: Record<string, number> }) => ({ name: "pass", value: params.output.pass }),
        ],
      })
      experimentUrl = run.experimentUrl ?? null
      console.log(`langfuse: dataset run recorded — ${run.experimentUrl ?? run.experimentId}`)
    } catch (e) {
      console.warn(`langfuse: dataset run skipped (${e instanceof Error ? e.message : String(e)})`)
    }
  } else {
    console.log("langfuse: dataset run skipped (no LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY)")
  }

  if (results.length === 0) {
    for (const c of cases) {
      if (delayMs > 0) await sleep(delayMs)
      const r = await runCaseWithTimeout(agent, c)
      results.push(r)
      console.log(describe(r))
    }
  }

  const inputTokens = results.reduce((s, r) => s + r.usage.inputTokens, 0)
  const outputTokens = results.reduce((s, r) => s + r.usage.outputTokens, 0)
  const costUsd =
    provider === "groq"
      ? (inputTokens / 1e6) * GROQ_USD_PER_MTOK.input + (outputTokens / 1e6) * GROQ_USD_PER_MTOK.output
      : null

  const summary = {
    provider,
    model: chosen.label,
    cases: results.length,
    tool_choice: rate(results, (r) => r.tool_ok),
    numbers_guard_clean: rate(results, (r) => r.guard_clean),
    citations_present: rate(results, (r) => r.citations_ok),
    answered: rate(results, (r) => r.answered),
    expected_numbers_found: rate(results, (r) => r.numbers_ok),
    pass: rate(results, (r) => r.pass),
    usage: { inputTokens, outputTokens },
    cost_usd: costUsd,
    langfuse_experiment_url: experimentUrl,
    results,
  }
  console.log(
    `\ntotals: tool choice ${summary.tool_choice}, numbers guard clean ${summary.numbers_guard_clean}, citations ${summary.citations_present}, answered ${summary.answered}, expected numbers ${summary.expected_numbers_found}, PASS ${summary.pass}`,
  )
  console.log(
    `usage: ${inputTokens} in / ${outputTokens} out tokens${costUsd !== null ? `, cost ~$${costUsd.toFixed(4)}` : " (price for this model unknown — tokens only)"}`,
  )

  if (outPath) {
    writeFileSync(outPath, JSON.stringify(summary, null, 2))
    console.log(`results written to ${outPath}`)
  }
  if (langfuseShutdown) await langfuseShutdown()
  const passed = results.filter((r) => r.pass).length
  if (passed < 18) {
    console.error(`eval: ${passed}/20 below the 18/20 acceptance bar`)
    process.exit(1)
  }
}

main().catch((e) => {
  console.error(`eval failed: ${e instanceof Error ? e.stack ?? e.message : String(e)}`)
  process.exit(1)
})
