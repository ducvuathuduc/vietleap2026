import { collectTruthNumbers, numberCandidates, numbersIn, UNGROUNDED_MARK } from "../../../llm/guards.ts"
import { guardNplAnswer } from "../answer-policy.ts"
import { detectLang } from "../lang.ts"

export interface EvalCase {
  id: string
  lang: "vi" | "en"
  question: string
  expect_tool: string
  expect_numbers: number[]
  adversarial?: string
  mixed?: boolean
  expect_regex?: string
  forbidden?: string[]
}

export function scoreAnswer(
  testCase: EvalCase,
  answer: string,
  calls: string[],
  outputs: unknown[],
) {
  const guarded = guardNplAnswer(answer, outputs)
  const unguarded = guardNplAnswer(guarded.text, outputs).flagged
  const answerNumbers = numbersIn(guarded.text).flatMap(numberCandidates)
  const truth = collectTruthNumbers(outputs)
  const numbersOk = testCase.expect_numbers.every((expected) =>
    truth.some((value) => close(value, expected)) &&
    answerNumbers.some((value) => close(value, Math.abs(expected))),
  )
  const toolOk = testCase.expect_tool === "none" || testCase.expect_tool.split("|").some((tool) => calls.includes(tool))
  const citationsOk = outputs.every((output) => {
    const data = output as { found?: unknown; citations?: unknown } | null
    return data?.found === false || (Array.isArray(data?.citations) && data.citations.length > 0)
  })
  const answered = guarded.text.trim().length > 0
  const languageText = guarded.text.replaceAll(UNGROUNDED_MARK, "")
  const mainText = languageText.replace(/\([^()]+\)/g, "").trim()
  const languageOk = answered && detectLang(mainText || languageText) === testCase.lang
  const forbiddenOk = (testCase.forbidden ?? []).every((word) => !guarded.text.toLowerCase().includes(word.toLowerCase()))
  const regexOk = !testCase.expect_regex || new RegExp(testCase.expect_regex, "is").test(guarded.text)
  const guardClean = guarded.flagged.length === 0
  return {
    tool_ok: toolOk,
    numbers_ok: numbersOk,
    flagged: guarded.flagged,
    unguarded,
    guard_clean: guardClean,
    citations_ok: citationsOk,
    answered,
    language_ok: languageOk,
    forbidden_ok: forbiddenOk,
    regex_ok: regexOk,
    answer: guarded.text,
    pass: toolOk && numbersOk && citationsOk && answered && languageOk && forbiddenOk && regexOk &&
      unguarded.length === 0 && (guardClean || Boolean(testCase.adversarial)),
  }
}

function close(a: number, b: number): boolean {
  return Math.abs(a - b) <= Math.max(0.006, Math.max(Math.abs(a), Math.abs(b)) * 0.006)
}
