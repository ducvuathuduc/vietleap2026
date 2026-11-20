// Live eval for the NPL study assistant (brief T7 item 3).
// Runs the 24 fixture-grounded cases (12 VI, 12 EN, 5 adversarial) in
// cases.json against the configured provider, and prints pass rates for: tool
// choice, numbers guard clean, citations present. With Langfuse project keys
// the cases are pushed as dataset items and the run is recorded as a Langfuse
// dataset run; without them it runs locally and prints that it was skipped.
// Usage: npm run eval:npl [-- --out results.json]
import { readFileSync, writeFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { type LanguageModel, type ToolLoopAgent } from "ai"

import { makeNplAgent } from "../agent.ts"
import { detectLang } from "../lang.ts"
import { loadRepoEnv } from "../../../ratewatch/agent/env.ts"
import { collectTruthNumbers, guardNumbers } from "../../../ratewatch/agent/guards.ts"
import { providerName, ratewatchModel } from "../../../ratewatch/agent/model.ts"
import type { Snapshot } from "../../view.ts"

const CASES_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "cases.json")
const FIXTURE_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../../seed/npl/snapshot.fixture.json")
const DATASET_NAME = "npl-eval"
const CASE_TIMEOUT_MS = 120_000
const PASS_BAR = 22

interface EvalCase {
  id: string
  lang: "vi" | "en"
  question: string
  /** "none" marks an adversarial case: tool choice is not graded. */
  expect_tool: string
  expect_numbers: number[]
  adversarial?: string
  /** Regex (case-insensitive) the answer must match. */
  expect_regex?: string
  /** Substrings that must not appear in the guarded answer. */
  forbidden?: string[]
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
  forbidden_ok: boolean
  regex_ok: boolean
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

async function runCase(snapshot: Snapshot, model: LanguageModel, c: EvalCase): Promise<CaseResult> {
  const agent = makeNplAgent({ snapshot, model, lang: detectLang(c.question) })
  if (!agent) throw new Error("agent unavailable")
  let result: Awaited<ReturnType<ToolLoopAgent["generate"]>>
  try {
    result = await agent.generate({ prompt: c.question })
  } catch (e) {
    return failResult(c, e instanceof Error ? e.message.slice(0, 300) : String(e))
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
  const answered = (result.text ?? "").trim().length > 0
  const forbiddenOk = (c.forbidden ?? []).every((s) => !guarded.text.includes(s))
  const regexOk = c.expect_regex ? new RegExp(c.expect_regex, "i").test(guarded.text) : true
  const adversarial = c.expect_tool === "none"
  const toolOk = adversarial ? true : c.expect_tool.split("|").some((t) => calls.includes(t.trim()))
  const numbersOk = c.expect_numbers.every((n) => truth.some((t) => close(n, t)))
  const dataOutputs = outputs.filter((o) => (o as { found?: unknown })?.found !== false)
  const citationsOk = dataOutputs.every((o) => Array.isArray((o as { citations?: unknown })?.citations) && (o as { citations: unknown[] }).citations.length > 0)
  // Adversarial cases test the refusal + the guard net: an invented number that
  // the guard caught and replaced is the system working, not a failure.
  const pass = adversarial
    ? answered && forbiddenOk && regexOk
    : toolOk && numbersOk && guarded.flagged.length === 0 && citationsOk && answered
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
    forbidden_ok: forbiddenOk,
    regex_ok: regexOk,
    answer: guarded.text,
    pass,
    usage: { inputTokens: num(u?.inputTokens), outputTokens: num(u?.outputTokens) },
  }
}

function failResult(c: EvalCase, error: string): CaseResult {
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
    forbidden_ok: false,
    regex_ok: false,
    answer: "",
    pass: false,
    usage: { inputTokens: 0, outputTokens: 0 },
    error,
  }
}

function timeoutResult(c: EvalCase): CaseResult {
  return { ...failResult(c, `timeout after ${CASE_TIMEOUT_MS / 1000}s`), guard_clean: true, forbidden_ok: true, regex_ok: false }
}

function runCaseWithTimeout(snapshot: Snapshot, model: Parameters<typeof runCase>[1], c: EvalCase): Promise<CaseResult> {
  const timeout = new Promise<CaseResult>((resolve) => setTimeout(() => resolve(timeoutResult(c)), CASE_TIMEOUT_MS))
  return Promise.race([runCase(snapshot, model, c), timeout])
}

function describe(r: CaseResult): string {
  const tool = r.expect_tool === "none" ? "adversarial" : r.tool_ok ? r.expect_tool : `want ${r.expect_tool}, got [${r.tools_called.join(",") || "none"}]`
  const guard = r.guard_clean ? "clean" : `flagged ${r.flagged.join(",")}`
  return `${r.pass ? "pass" : "FAIL"} ${r.id} tool=${tool} numbers=${r.numbers_ok} guard=${guard} citations=${r.citations_ok} answered=${r.answered}${r.error ? ` (${r.error})` : ""}`
}

function rate(results: CaseResult[], key: (r: CaseResult) => boolean): string {
  return `${results.filter(key).length}/${results.length}`
}

async function main(): Promise<void> {
  loadRepoEnv()
  const outArg = process.argv.indexOf("--out")
  const outPath = outArg >= 0 ? process.argv[outArg + 1] : undefined

  const provider = providerName()
  const chosen = ratewatchModel(process.env, `eval-npl-${new Date().toISOString().slice(0, 10)}`)
  if (!chosen) {
    console.error("eval: offline — no LLM key configured, live eval needs a provider")
    process.exit(1)
  }
  console.log(`eval: provider=${provider} model=${chosen.label}`)

  const snapshot = JSON.parse(readFileSync(FIXTURE_PATH, "utf8")) as Snapshot
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
        const id = (item.input as { id?: string } | undefined)?.id
        const expected = item.expectedOutput as { expect_tool?: unknown } | undefined
        const local = id ? byId.get(id) : undefined
        if (!id || kept.has(id) || !local || expected?.expect_tool !== local.expect_tool) {
          await lf.api.datasetItems.delete(item.id)
          continue
        }
        kept.add(id)
      }
      for (const c of cases) {
        if (kept.has(c.id)) continue
        await lf.dataset.createItem({
          datasetName: DATASET_NAME,
          input: { id: c.id, lang: c.lang, question: c.question },
          expectedOutput: { expect_tool: c.expect_tool, expect_numbers: c.expect_numbers },
        })
      }
      const dataset = await lf.dataset.get(DATASET_NAME)
      const runName = `eval-npl-${provider}-${new Date().toISOString().replace(/[:.]/g, "-")}`
      const run = await dataset.runExperiment({
        name: "NPL study assistant eval",
        runName,
        description: "24 VI/EN cases incl. 5 adversarial: tool choice, grounded numbers, citations (fixture snapshot)",
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
          const r = await runCaseWithTimeout(snapshot, chosen.model, c)
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
      const r = await runCaseWithTimeout(snapshot, chosen.model, c)
      results.push(r)
      console.log(describe(r))
    }
  }

  const inputTokens = results.reduce((s, r) => s + r.usage.inputTokens, 0)
  const outputTokens = results.reduce((s, r) => s + r.usage.outputTokens, 0)

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
    langfuse_experiment_url: experimentUrl,
    results,
  }
  console.log(
    `\ntotals: tool choice ${summary.tool_choice}, numbers guard clean ${summary.numbers_guard_clean}, citations ${summary.citations_present}, answered ${summary.answered}, expected numbers ${summary.expected_numbers_found}, PASS ${summary.pass}`,
  )

  if (outPath) {
    writeFileSync(outPath, JSON.stringify(summary, null, 2))
    console.log(`results written to ${outPath}`)
  }
  if (langfuseShutdown) await langfuseShutdown()
  const passed = results.filter((r) => r.pass).length
  if (passed < PASS_BAR) {
    console.error(`eval: ${passed}/${results.length} below the ${PASS_BAR}/${results.length} acceptance bar`)
    process.exit(1)
  }
}

main().catch((e) => {
  console.error(`eval failed: ${e instanceof Error ? e.stack ?? e.message : String(e)}`)
  process.exit(1)
})
