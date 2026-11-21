export const LANGUAGE_COOKIE = "npl_lang"
export const LANGUAGE_HEADER = "x-npl-lang"

export type Lang = "vi" | "en"

export function parseLanguage(value: string | undefined | null): Lang | undefined {
  return value === "en" || value === "vi" ? value : undefined
}
