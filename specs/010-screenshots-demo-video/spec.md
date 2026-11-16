# Feature Specification: Screenshots + demo video script (backup for the live demo)

**Feature Branch**: `010-screenshots-demo-video` (lands on `main`) · **Created**: 2026-11-16 · **Status**: Draft · **Priority**: P2 (risk R4/R5: UEH wifi or laptop failure during pitch; CONTEST_ANALYSIS §4.5 "18/11: record a 90-second demo video")
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T055.

## Context (verified 2026-11-16)
- `docs/screenshots/` does **not** exist; README has no images.
- Playwright (Apache-2.0) + headless Chromium are installed by `make setup` (`tools/setup_env.sh`, `PLAYWRIGHT_BROWSERS_PATH=.tools/ms-playwright`); `tools/env.sh` exports the path.
- The web app selects the dataset from `localStorage` (`web/src/components/dataset-provider.tsx`); 009 adds `?dataset=`. Practice outputs exist locally in `out/` (`bds_practice`, `firms_2021`, `wdi_fiscal`, `demo_multi`) but `out/` is never committed.
- Story mode ("Câu chuyện") and inspect mode ("Hỏi AI") are driven by driver.js in `web/src/components/insight-inspector.tsx`.

## User Scenarios & Testing

### User Story 1 — Reproducible screenshots (Priority: P1)
As the **ST**, I run `make screenshots` and get PNGs of every page for one dataset (light theme, 1440×900, plus 3 dark-theme hero shots), so the README, deck appendix and backup slides use current, real screens.

**Acceptance**
1. **Given** `make api` and `make web` running and dataset `wdi_fiscal` analysed, **When** `python tools/screenshots.py --dataset wdi_fiscal --out docs/screenshots`, **Then** one PNG per route in the nav list (13 + `/whatif`, map, palette when those features exist) is written with stable names (`01-tong-quan.png` …), each < 600 KB (pngquant optional), and a `docs/screenshots/README.md` index with the dataset, commit hash and date.
2. **Given** a page shows an error/empty state, **Then** the script fails with the route name (no silent bad screenshot).
3. **Given** the screenshots, **Then** README §4 shows 4 of them (Tổng quan, Pipeline, Insight, Hỏi AI sheet).

### User Story 2 — Scripted 90-second demo video (Priority: P1)
As the **DE**, I want an automated Playwright recording following a written storyboard (Câu chuyện → Hỏi AI on a chart → Quyết định → Xuất báo cáo), so a backup video exists that matches the pitch timing (§4.6 slide 7, 0:50).

**Acceptance**: `python tools/record_demo.py --dataset <id>` writes `out/demo/demo.webm` (Playwright `record_video_dir`, 1280×720) following `docs/DEMO_SCRIPT.md` step timings (± 3 s); the script waits on real selectors (`[data-tour=…]`), never on fixed sleeps alone; a narration column exists for a voice-over recorded separately.

### User Story 3 — Contest-day refresh (Priority: P2)
**Acceptance**: on 21/11 09:00–10:30 the team re-runs both scripts on the contest dataset in ≤ 5 min total and drops the PNGs into the deck appendix; checklist in `docs/DEMO_SCRIPT.md`.

### Edge cases
- Fonts/diacritics in headless Chromium → verify Vietnamese renders (no tofu) on the contest laptop; install `fonts-noto` if needed (documented).
- Animations/skeletons → wait for `[data-print-ready]` (009) or network idle + no `.animate-pulse` elements.
- Dark mode via `next-themes` → set `localStorage.theme = "dark"` before navigation.
- Sensitive data: never screenshot a dataset with personal data; screenshots only from practice/open datasets; LLM keys never visible (Analyst page shows only "Groq · model" label).
- File size: video ≤ 30 MB (not committed — stored in `out/demo/`, uploaded to Drive by LEAD); PNGs committed (≤ 600 KB each, total ≤ 10 MB).

## Requirements
- **FR-1001**: `tools/screenshots.py` (Playwright sync API): args `--dataset`, `--base` (default `http://127.0.0.1:3000`), `--out`, `--dark`; sets `localStorage` dataset key; route list imported from a JSON mirror of `web/src/lib/nav.ts` (`web/src/lib/nav.json` generated or hand-kept with a parity test).
- **FR-1002**: `tools/record_demo.py` + `docs/DEMO_SCRIPT.md` (storyboard table: time, action, selector, narration VI, narration EN).
- **FR-1003**: Makefile targets `screenshots` and `demo-video` (require running api/web; print a hint otherwise).
- **FR-1004**: README §4 images + `docs/screenshots/README.md` index.

### Non-functional
- **NFR-1001**: Screenshots for 14 routes ≤ 90 s on the 2-CPU laptop; never run concurrently with `npm run build` or pytest.

## Success criteria
- **SC-1001**: `docs/screenshots/` has ≥ 13 PNGs from a real run, index lists commit hash.
- **SC-1002**: `demo.webm` plays ≤ 95 s, follows the storyboard; reviewed by PO on 18/11.
