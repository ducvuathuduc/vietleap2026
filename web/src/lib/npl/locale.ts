import type { Metadata } from "next"
import { headers } from "next/headers"

import { LANGUAGE_HEADER, parseLanguage, type Lang } from "./language"
import { SITE_TITLE } from "./view"

export async function requestLanguage(): Promise<Lang> {
  return parseLanguage((await headers()).get(LANGUAGE_HEADER)) ?? "en"
}

export function localizedMetadata(lang: Lang, title: string, description: string): Metadata {
  return {
    title,
    description,
    openGraph: {
      title,
      description,
      siteName: SITE_TITLE[lang],
      locale: lang === "vi" ? "vi_VN" : "en_US",
    },
  }
}
