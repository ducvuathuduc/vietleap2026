import * as React from "react"

import { LANG_STORAGE_KEY } from "@/lib/export-lang"

const CHANGE = "vlk:export-lang"

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange)
  window.addEventListener(CHANGE, onChange)
  return () => {
    window.removeEventListener("storage", onChange)
    window.removeEventListener(CHANGE, onChange)
  }
}

/** Preferred export language kept in localStorage (`vlk.lang`); null on the server and until chosen. */
export function useStoredExportLang(): [string | null, (lang: string) => void] {
  const stored = React.useSyncExternalStore(subscribe, () => window.localStorage.getItem(LANG_STORAGE_KEY), () => null)
  const store = React.useCallback((lang: string) => {
    window.localStorage.setItem(LANG_STORAGE_KEY, lang)
    window.dispatchEvent(new Event(CHANGE))
  }, [])
  return [stored, store]
}
