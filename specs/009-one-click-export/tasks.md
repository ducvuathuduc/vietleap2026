# Tasks: 009 One-click "Xuất báo cáo"

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Engine
- [ ] T901 Test-first `tests/test_export.py`: `rebuild_reports` on a practice `out/` copy reproduces deck/pitch/summary; `bundle()` contains allowlisted names, README hashes match, Chromium-missing → warnings list (monkeypatch Playwright import).
- [ ] T902 `engine/vlkit/report.py rebuild_reports` + `engine/vlkit/export.py bundle` → T901.
- [ ] T903 `export.dashboard_pdf` (Playwright, `/print` route, fallback to static `dashboard.html`) + test with a fake web server serving a page with `data-print-ready` (skipped if Chromium absent).
- [ ] T904 Commit + push "feat(export): T901–T903 rebuild reports, bundle, dashboard PDF".

## Phase B — API
- [ ] T905 Test-first API tests: `POST /export` 202 + idempotent; `GET /export/{job}` states; `files/bundle|pitch_md|dashboard_pdf`; rate limit path.
- [ ] T906 `api/jobs.py`, `api/routes/datasets.py`, `api/security.py`, `api/settings.py WEB_URL`; regenerate OpenAPI → T902, T905.
- [ ] T907 Commit + push "feat(api): T905–T906 export job + bundle download".

## Phase C — Web
- [ ] T908 `dataset-provider.tsx` `?dataset=`; `/print` page with `data-print-ready`; `print:` utilities hide chrome → T906.
- [ ] T909 `export-dialog.tsx` (Dialog + ToggleGroup lang + Checkbox PDF + Progress + sonner) in sidebar + palette item → T908.
- [ ] T910 End-to-end on the laptop: `make api` + `make web`, export both languages + PDF, open zip on another machine; time it (NFR-901); screenshot `docs/screenshots/export.png`.
- [ ] T911 Commit + push "feat(web): T908–T910 one-click Xuất báo cáo"; tick; `specs/README.md`, README export section.

## Dependencies
T901→T902→T903; T905→T906 (needs T902); T906→T908→T909→T910→T911. Uses `lang` from 003 when merged (else EN deck + VI pitch as today).
