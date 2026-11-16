# Feature Specification: Bilingual deck & pitch (`--lang vi|en`)

**Feature Branch**: `003-bilingual-deck` (lands on `main`) · **Created**: 2026-11-16 · **Status**: Draft · **Priority**: P1 (contest risk R6 — pitch language unconfirmed; foreign judges/speakers)
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T081 · **Depends on**: 002 (slide layout) — can start in parallel on the string table.

## Context (verified in code, 2026-11-16)
- `engine/vlkit/report.py build_deck()` writes **English only**: slide headers/kickers are hard-coded English strings ("Problem & question", "WHAT WE FOUND", "Recommendations", "LIKELY JUDGE QUESTIONS", …) and bodies use `title_en`, `sentence_en`, `so_what_en`, `now_what_en`, `impact_en`.
- `pitch_md()` writes **Vietnamese only** (`title_vi`, `sentence_vi`, `*_vi`, headings "Dữ liệu & pipeline", `PITCH_TIMING`).
- Engine output is already bilingual for insights (`title_en/vi`, `sentence_en/vi`) and recommendations (`so_what_en/vi`, `now_what_en/vi`, `impact_en/vi`),
  **but `results.caveats` are English-only strings** (`engine/vlkit/profile.py caveats()`, `engine/vlkit/domains.py CAVEATS`), and the static `dashboard.html` / `executive_summary.md` mix both.
- CLIs: `run.py` and `de.py file|run` have no language flag; the web sidebar links `files/deck` (single file).

## User Scenarios & Testing

### User Story 1 — Choose the deck language at build time (Priority: P1)
As the **storyteller (ST)**, I want `python run.py <file> --lang vi` (or `en`, or `both`) to produce a fully Vietnamese or fully English deck and pitch, so we can follow whatever language the organisers require without retyping slides.

**Acceptance**
1. **Given** `--lang vi`, **When** reports build, **Then** `deck.pptx` has no English slide titles/kickers (except technical names: OBT, Star, Snowflake, Data Vault, p-value, test names) and bodies use `*_vi` fields; `pitch.md` is VI.
2. **Given** `--lang en`, **Then** `deck.pptx` and `pitch.md` (new `pitch.en.md` … see FR-303) are English.
3. **Given** `--lang both` (default), **Then** `deck.pptx` (EN, unchanged default for backward compatibility) + `deck.vi.pptx`, `pitch.md` (VI) + `pitch.en.md` are written; `results.json.files` lists all.

### User Story 2 — Switch language on Export in the web (Priority: P2)
As a **non-coder teammate**, I want an EN/VI toggle next to the deck/pitch links in the sidebar Exports, so I download the right file without the CLI.

**Acceptance**: **Given** both files exist, **When** I pick "Tiếng Việt", **Then** the links point to `files/deck_vi` / `files/pitch_vi`; **Given** only one exists, **Then** the other option is disabled with tooltip "Chưa xuất — chạy lại với --lang both".

### User Story 3 — Caveats and judge-question hints in both languages (Priority: P2)
As the **PO**, I want caveats and the "likely judge questions" card in the deck language, so the Limitations slide reads naturally to judges.

**Acceptance**: every string produced by `profile.caveats()` and `domains.CAVEATS` exists as `{en, vi}`; `results.json` gains `caveats_vi` (parallel list, same order, same numbers); the deck uses the list of its language.

### Edge cases
- A `*_vi` field missing on an older `results.json` → fall back to `*_en` and log once "missing VI text: <field>" (never machine-translate silently).
- Numbers formatting: VI uses `1.234,5` and `p<0,001`; EN uses `1,234.5` and `p<0.001` (reuse `fmt` helpers / `fmtP` style already in web `explain.ts`). Numbers must remain equal after parsing (test).
- Text length: VI strings are ~15–25% longer → `fit_text` shrink; `deck_overflow()` must stay `[]` for both languages.
- Diacritics/fonts: python-pptx default font must render Vietnamese (use the theme font already used; test that no "?" replacement chars appear by reading XML text).
- Brief language differs from deck language → brief question is shown as-written (feature 002), with "(original language)" marker.

## Requirements
- **FR-301**: `report.py` MUST use a single string table `engine/vlkit/i18n.py` (`T[lang][key]`) for every fixed deck/pitch string; no inline English/Vietnamese literals remain in `build_deck`/`pitch_md` (lint test greps for capitalised literals in `header(` calls).
- **FR-302**: `build_all(res, df, whatif, out, lang="both")`; `run.py`, `de.py file|run` gain `--lang {vi,en,both}`; API upload/ingest accept optional `lang` (pydantic `Literal`).
- **FR-303**: Output names: `deck.pptx` (EN), `deck.vi.pptx`; `pitch.md` (VI — current behaviour), `pitch.en.md`; `EXPORTS` in `api/routes/datasets.py` gains `deck_vi`, `pitch_md`, `pitch_en`.
- **FR-304**: `results.json.caveats_vi` produced in `engine/vlkit/pipeline.py` from bilingual caveat sources.
- **FR-305**: Number formatting per language through the existing helpers in `engine/vlkit/fmt.py` (`num(v, col, lang)`, `pct(v, lang)` already take `lang`; add `lang` to `p(pv)`).
- **FR-306**: Web Exports: shadcn `ToggleGroup` (already installed: `web/src/components/ui/toggle-group.tsx`) EN/VI controlling deck/pitch links in `web/src/components/app-sidebar.tsx` / `nav-documents.tsx`.

### Non-functional
- **NFR-301**: `both` adds ≤ 3 s build time (charts reused; only pptx text differs).
- **NFR-302**: No machine-translation dependency; all VI strings authored and reviewed (PO/ST).

## Success criteria
- **SC-301**: For 3 practice datasets × {vi, en}: `deck_overflow()==[]`; VI deck has 0 slide titles from the EN table; EN deck has 0 from the VI table (test).
- **SC-302**: Numbers on matching slides of `deck.pptx` and `deck.vi.pptx` parse to identical values (test).
- **SC-303**: ST can switch language in the web without the CLI (manual check, screenshot in `docs/screenshots/`).

## Open questions
- [NEEDS CLARIFICATION: pitch language required by organisers (VI, EN or either) — ask on the Zalo group; default both.]
- [NEEDS CLARIFICATION: whether the submission form takes .pptx, .pdf or a link — affects 009 more than this feature.]
