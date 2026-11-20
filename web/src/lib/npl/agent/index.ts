// Public surface of the NPL assistant library.
export { detectLang, type Lang } from "./lang.ts"
export { makeNplAgent, makeNplTools, nplSystemPrompt } from "./agent.ts"
export { loadNplSnapshot } from "./snapshot.ts"
export { guardNplAnswer, messagesForNplModel } from "./answer-policy.ts"
export * as nplTools from "./tools.ts"
export type { NplCitation } from "./tools.ts"
