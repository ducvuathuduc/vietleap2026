"use client"

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { EXPORT_LANG_LABEL, EXPORT_LANGS, type ExportLang, isExportLang, NOT_EXPORTED_HINT } from "@/lib/export-lang"

/** EN/VI switch for the deck/pitch exports (feature 003); a language that was not exported is disabled with a hint. */
export function ExportLangToggle({
  value,
  available,
  onChange,
}: {
  value: ExportLang | null
  available: ExportLang[]
  onChange: (lang: ExportLang) => void
}) {
  return (
    <ToggleGroup
      multiple={false}
      value={value ? [value] : []}
      onValueChange={(v) => {
        if (isExportLang(v[0])) onChange(v[0])
      }}
      variant="outline"
      size="sm"
      aria-label="Ngôn ngữ deck và pitch"
      data-testid="export-lang"
    >
      {EXPORT_LANGS.map((lang) =>
        available.includes(lang) ? (
          <ToggleGroupItem key={lang} value={lang}>
            {EXPORT_LANG_LABEL[lang]}
          </ToggleGroupItem>
        ) : (
          <Tooltip key={lang}>
            <TooltipTrigger render={<span />}>
              <ToggleGroupItem value={lang} disabled>
                {EXPORT_LANG_LABEL[lang]}
              </ToggleGroupItem>
            </TooltipTrigger>
            <TooltipContent>{NOT_EXPORTED_HINT}</TooltipContent>
          </Tooltip>
        )
      )}
    </ToggleGroup>
  )
}
