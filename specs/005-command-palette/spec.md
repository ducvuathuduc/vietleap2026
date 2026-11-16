# Feature Specification: Ctrl+K command palette

**Feature Branch**: `005-command-palette` (lands on `main`) · **Created**: 2026-11-16 · **Status**: Draft · **Priority**: P2 (demo polish, rubric E/F; lets non-coders reach every page/action)
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T050.

## Context (verified 2026-11-16)
- shadcn `command` is **not installed** (`web/src/components/ui/` has dialog, sheet, select… but no `command.tsx`); `cmdk` is not in `web/package.json`. `components.json` style `base-nova`.
- Pages: 13 nav entries in `web/src/components/app-sidebar.tsx` (`/`, `/brief`, `/sources`, `/pipeline`, `/quality`, `/model`, `/sql`, `/profile`, `/insights`, `/drivers`, `/segments`, `/decision`, `/analyst`) and page titles in `web/src/components/site-header.tsx TITLES`.
- Actions exist as hooks: `useInsightInspector()` → `setInspecting`, `startTour(pathname)`, `startStory()`; `useDataset()` → `datasets`, `select(id)`; exports via `api.fileUrl(id, kind)`.

## User Scenarios & Testing

### User Story 1 — Jump anywhere (Priority: P1)
As a **teammate presenting**, I press Ctrl+K (⌘K on macOS), type "chat" or "chất lượng" (with or without diacritics) and land on that page, so navigation during the pitch takes one keystroke.

**Acceptance**
1. **Given** any page, **When** I press Ctrl+K, **Then** a shadcn `CommandDialog` opens with groups "Trang", "Hành động", "Dataset", "Xuất file"; focus is in the input.
2. **Given** I type "chat luong", **Then** "Chất lượng dữ liệu" is the first match (diacritic-insensitive matching via the existing `fold()` in `web/src/lib/analyst/explain.ts`).
3. **Given** I press Enter on a page item, **Then** the router navigates and the dialog closes; Esc closes without action.

### User Story 2 — Run actions (Priority: P1)
As the **demo driver**, I want "Câu chuyện", "Hỏi AI (bật/tắt)", "Hướng dẫn trang này", "Hỏi AI Analyst: <câu đã gõ>" in the palette, so the demo flows without hunting for buttons.

**Acceptance**: **Given** a dataset is selected, **When** I choose "Câu chuyện", **Then** `startStory()` runs (same as the header button). **When** no dataset is selected, **Then** dataset-dependent actions are disabled with "Chưa chọn dataset". **When** I type free text and pick "Hỏi AI Analyst", **Then** `/analyst?q=<text>` opens and the question is pre-filled (not auto-sent).

### User Story 3 — Switch dataset & download exports (Priority: P2)
**Acceptance**: dataset items call `select(id)`; export items open `api.fileUrl(id, kind)` for deck / dashboard / summary_pdf (and feature 003/009 kinds when present).

### User Story 4 — What-if shortcut (Priority: P3)
**Acceptance**: typing "what-if <feature> +10%" offers "Mở what-if <feature> +10%" → `/drivers?feature=<f>&pct=10` (or `/whatif` after feature 007), values clamped to the slider range.

### Edge cases
- Shortcut conflicts: Ctrl+K inside a text input/textarea (SQL Explorer, chat) still opens the palette (standard), but not while an IME composition is active (`event.isComposing`).
- Inspect mode ("Hỏi AI") active → opening the palette exits inspect mode first (avoid capturing clicks).
- A driver.js tour/story running → palette opening destroys the tour (`destroy()`), same as route change.
- No datasets → "Dataset" group shows "Chưa có dataset — tải dữ liệu" item linking to `/sources`.
- Free text is never executed or sent to the LLM from the palette; it is only passed as a query string after URL-encoding.

## Requirements
- **FR-501**: Install via `npx shadcn@latest add command` (adds `components/ui/command.tsx` + `cmdk`), no style edits.
- **FR-502**: `web/src/components/command-menu.tsx` mounted once in the dashboard layout; keyboard listener for `k` + (`metaKey`||`ctrlKey`); header gets a small "⌘K" hint button (shadcn `Button` variant ghost + `Kbd` if available, else text).
- **FR-503**: Items are data-driven from a single `NAV` list shared with `app-sidebar.tsx` (move the list to `web/src/lib/nav.ts`) so the palette never drifts from the sidebar.
- **FR-504**: Matching uses `fold()` on label + keywords (VI and EN synonyms, e.g. "quality", "chat luong").
- **FR-505**: `/analyst` reads `?q=` and pre-fills the input.
- **FR-506**: Add a tour step to `web/src/lib/tour-steps.ts` for the ⌘K hint.

### Non-functional
- **NFR-501**: Palette opens < 100 ms after keypress on the 2-CPU laptop (no data fetch on open; datasets already in context).
- **NFR-502**: Accessible: dialog title, `aria-label`, full keyboard navigation (cmdk provides).
- **NFR-503**: Bundle increase ≤ 30 kB gzip.

## Success criteria
- **SC-501**: Unit test: `filterCommands("chat luong")[0].href === "/quality"`; every sidebar URL appears in the palette (test compares lists).
- **SC-502**: Headless Chromium: Ctrl+K opens dialog, Enter navigates, 0 console/CSP errors.
