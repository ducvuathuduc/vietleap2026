// Feature 003 (US2): which deck/pitch exports exist per language, read from results.json `files`
// (GET /api/datasets/{id} → DatasetDetail.files). File names are fixed per language by the engine:
// deck.pptx (EN) · deck.vi.pptx (VI) · pitch.md (VI) · pitch.en.md (EN).

export type ExportLang = "vi" | "en"
export type LangExportKind = "deck" | "deck_vi" | "pitch_md" | "pitch_en"

export const EXPORT_LANGS: readonly ExportLang[] = ["vi", "en"]
export const EXPORT_LANG_LABEL: Record<ExportLang, string> = { vi: "Tiếng Việt", en: "English" }
export const NOT_EXPORTED_HINT = "Chưa xuất — chạy lại với --lang both"
export const LANG_STORAGE_KEY = "vlk.lang"

const KINDS: Record<ExportLang, readonly LangExportKind[]> = { vi: ["deck_vi", "pitch_md"], en: ["deck", "pitch_en"] }

type Files = Record<string, string | number | null> | null | undefined

export function isExportLang(v: unknown): v is ExportLang {
  return v === "vi" || v === "en"
}

/** Export kinds of `lang` whose file was generated (deck first, then pitch). */
export function exportKinds(files: Files, lang: ExportLang): LangExportKind[] {
  return KINDS[lang].filter((kind) => Boolean(files?.[kind]))
}

export function availableLangs(files: Files): ExportLang[] {
  return EXPORT_LANGS.filter((lang) => exportKinds(files, lang).length > 0)
}

/** The stored preference when that language was exported, else the first exported language (VI first). */
export function pickLang(files: Files, preferred: string | null): ExportLang | null {
  const available = availableLangs(files)
  return isExportLang(preferred) && available.includes(preferred) ? preferred : (available[0] ?? null)
}
