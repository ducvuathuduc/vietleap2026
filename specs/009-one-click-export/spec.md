# Feature Specification: One-click "Xuất báo cáo" (deck + pitch.md + dashboard PDF + bundle)

**Feature Branch**: `009-one-click-export` (lands on `main`) · **Created**: 2026-11-16 · **Status**: Draft · **Priority**: P1 for submission day (21/11 12:40 target, hard deadline 13:00) — risk R8 (numbers drift) and R10 (late submission)
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T054 · **Depends on**: 002 (brief in deck), 003 (`lang`), optional 007 (scenarios), 008 (map PNG).

## Context (verified 2026-11-16)
- Reports are built **only at analysis time**: `engine/vlkit/report.py build_all()` (called by `engine/vlkit/pipeline.py`) writes `deck.pptx`, `executive_summary.md/html/pdf` (PDF via Playwright Chromium, skipped with a warning if missing), `pitch.md`, `dashboard.html`, `charts/*.png`.
- Export endpoint `GET /api/datasets/{id}/files/{kind}` serves `deck, dashboard, summary_pdf, summary_md, results, clean_csv` (`api/routes/datasets.py EXPORTS`); **`pitch.md` is generated but not downloadable**; there is no "rebuild reports now" endpoint and no bundle.
- Sidebar "Exports" (`web/src/components/app-sidebar.tsx`) links deck / static dashboard HTML / summary PDF.
- Playwright + headless Chromium are installed by `make setup` (`tools/setup_env.sh`, `PLAYWRIGHT_BROWSERS_PATH=.tools/ms-playwright`); the dataset selection in the web app is stored in `localStorage` (`dataset-provider.tsx`), not in the URL.

## User Scenarios & Testing

### User Story 1 — One button, every deliverable, same numbers (Priority: P1)
As the **LEAD** at 12:30 on 21/11, I press "Xuất báo cáo" and get a ZIP with `deck.pptx` (+ `deck.vi.pptx`), `pitch.md` (+ `pitch.en.md`), `executive_summary.pdf`, `dashboard.html`, `dashboard.pdf`, `provenance.json`, `README.txt` (what is inside, dataset, run id, timestamp Asia/Saigon, data licences), so the submission is complete and consistent.

**Acceptance**
1. **Given** a selected dataset, **When** I click "Xuất báo cáo" (dialog: language vi/en/both, include dashboard PDF ✓), **Then** a background job rebuilds reports from the current `results.json`/`pipeline.json`/`brief.json`/`scenarios.json` and returns a job id; a progress toast updates; on success a download link `files/bundle` appears.
2. **Given** the bundle, **Then** `README.txt` lists every file with its SHA-256 and the run id; numbers in deck and PDF come from the same `results.json` (checked by a test that parses a KPI from both).
3. **Given** Chromium is missing, **Then** the bundle still builds without PDFs and `README.txt` + the toast say "Thiếu Chromium — chạy make setup"; the job status is `done_with_warnings`, not `error`.

### User Story 2 — Dashboard PDF of the live pages (Priority: P2)
As the **ST**, I want a PDF snapshot of Tổng quan, Pipeline, Insight, Quyết định (and Bản đồ if 008 is done), so judges can read the dashboard offline.

**Acceptance**: **Given** the web app runs at `WEB_URL` (env, default `http://127.0.0.1:3000`), **When** the job runs, **Then** Playwright opens a combined `/print?dataset=<id>` route (sections of Tổng quan, Pipeline, Insight, Quyết định), waits for `[data-print-ready]`, and prints A4 landscape into `dashboard.pdf` (header with dataset + timestamp). **Given** the web app is not running, **Then** fall back to printing the static `dashboard.html` (file URL) and note it in `README.txt`.

### User Story 3 — Pitch markdown & slides PDF (Priority: P3)
**Acceptance**: `pitch.md` downloadable via `files/pitch_md`; if Marp CLI is available (`npx @marp-team/marp-cli`), also `pitch.pdf`; otherwise skipped with a note.

### Edge cases
- Export clicked twice → second request returns the running job (idempotent per dataset).
- Long job on the 2-CPU laptop → hard timeout 180 s; partial bundle with warnings.
- Dataset re-analysed during export → job snapshots `results.json` mtime at start; mismatch at end → warning.
- `?dataset=` URL param must win over `localStorage` only when present (needed by Playwright; harmless for users).
- Fonts: Vietnamese diacritics in PDFs — Chromium uses system fonts; verify no tofu (□) in a test PDF text extraction.
- Bundle size > 20 MB (charts) → still produced in `out/` (not committed); warn if > 50 MB (upload forms often limit).
- Time zone: timestamps Asia/Saigon.

## Requirements
- **FR-901**: `engine/vlkit/report.py rebuild_reports(out, lang, include_pdf) -> dict` re-using `build_all` pieces without re-running analysis (loads `results.json`, `clean.parquet` for dashboard, `whatif.json`).
- **FR-902**: `engine/vlkit/export.py`: `dashboard_pdf(web_url, ds, routes, out) -> path | None` (Playwright), `bundle(out, files) -> zip` with `README.txt` + SHA-256.
- **FR-903**: API `POST /api/datasets/{id}/export {lang, dashboard_pdf: bool}` → 202 `{job_id}`; `GET /api/export/{job_id}` → status/progress/warnings/files; `EXPORTS` += `bundle` (`export/bundle.zip`, `application/zip`), `pitch_md`, `dashboard_pdf`.
- **FR-904**: Web: shadcn `Dialog` (installed) "Xuất báo cáo" in the sidebar Exports + command palette item; sonner toasts for progress; DatasetProvider honours `?dataset=`; pages set `data-print-ready` when their data has loaded; `?print=1` hides sidebar/header via existing Tailwind `print:` utilities (no theme change).
- **FR-905**: Job runs through the existing in-process job runner pattern (`api/jobs.py`), serialized with the warehouse lock; rate-limited (add path to `api/security.py`).

### Non-functional
- **NFR-901**: Full bundle (both languages, dashboard PDF) ≤ 90 s on the 2-CPU laptop with the web app already built (`make web`).
- **NFR-902**: Never run `npm run build` inside the job.

## Success criteria
- **SC-901**: pytest: bundle contains the expected files; README hashes match; Chromium-missing path → warnings; deck/PDF KPI parity.
- **SC-902**: Rehearsal 21/11 morning (or 19/11 dry run): export completes, zip opens on another machine, all files readable.

## Open questions
- [NEEDS CLARIFICATION: submission format (file upload vs link, size limit) — organisers unpublished; bundle covers both.]
- [NEEDS CLARIFICATION: whether `@marp-team/marp-cli` (MIT) should be added as a dev dependency or used via `npx` only on the contest laptop.]
