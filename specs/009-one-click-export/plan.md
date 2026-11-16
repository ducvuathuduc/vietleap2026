# Implementation Plan: One-click "Xuất báo cáo"

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 5 h · **Owner role**: DE (ST checks the bundle)

## Technical context
- Engine: `engine/vlkit/report.py` (`build_all`, `build_deck`, `pitch_md`, `summary_md`, `md_to_html`, `html_to_pdf` [Playwright], `static_dashboard`, `load_de`), `engine/vlkit/pipeline.py`.
- API: `api/routes/datasets.py` (`EXPORTS`, `files/{kind}`), `api/jobs.py` (`submit`, `_jobs`), `api/security.py` (rate-limited paths), `api/settings.py` (env).
- Web: `web/src/components/app-sidebar.tsx`, `nav-documents.tsx`, `dataset-provider.tsx` (localStorage key), `web/src/components/ui/{dialog,toggle-group,checkbox,sonner,progress}.tsx` (installed), pages under `web/src/app/(dashboard)/`.
- Tools: Playwright (Apache-2.0, in `requirements.txt`), headless Chromium via `tools/setup_env.sh`; optional Marp CLI (MIT).

## Constitution check
| Principle | Compliance |
|---|---|
| I | bundle is a re-render of stored engine outputs; parity test deck ↔ PDF |
| II/III | unchanged content rules (deck already carries tests/caveats) |
| IV | Dialog/ToggleGroup/Checkbox/Progress/sonner from shadcn; print mode uses Tailwind `print:` utilities only |
| V | Playwright Apache-2.0, Marp MIT (optional) |
| VI | `WEB_URL` from env only (never request input) → no SSRF; Playwright navigates only to `WEB_URL` + fixed route list; zip entries from a fixed allowlist (no path traversal / zip-slip); job timeout; rate limit |
| VII | works offline; Chromium optional with graceful degradation |
| VIII | test-first bundle + endpoint tests |

## Design
1. `report.rebuild_reports(out, lang="both", include_pdf=True)` — loads `results.json`, `clean.parquet` (fallback `clean_sample.csv`), `whatif.json`, calls `build_all` (which already writes charts/deck/summary/pitch/dashboard). With 003, passes `lang`.
2. `export.dashboard_pdf(web_url, ds, routes=("/","/pipeline","/insights","/decision"), out)` — one Chromium context, `page.goto(f"{web_url}{r}?dataset={ds}&print=1")`, `wait_for_selector("[data-print-ready]", timeout=20000)`, `page.pdf(landscape=True)` per route, merge with `pypdf` (BSD-3) — or print a single combined route `/print?dataset=` that stacks the four sections (preferred: no extra dependency). Decision at T903: prefer the `/print` route.
3. `export.bundle(out)` — `zipfile` with fixed names, `README.txt` (dataset, run id, timestamps Asia/Saigon, SHA-256, licences from `provenance.json`).
4. API: `POST /datasets/{id}/export` → `jobs.submit_export(...)`; `GET /export/{job_id}`; `EXPORTS` additions.
5. Web: `export-dialog.tsx` (new) + sidebar button + palette item; polling `GET /api/export/{job}` every 1 s with toast; `/print` page (new, `web/src/app/(dashboard)/print/page.tsx`) rendering existing cards of the four pages with `data-print-ready` when all `useAsync` loads finish.

## Files to touch
`engine/vlkit/report.py`, `engine/vlkit/export.py` (new), `api/jobs.py`, `api/routes/datasets.py`, `api/security.py`, `api/settings.py` (`WEB_URL`), `tests/test_export.py` (new),
`web/src/components/export-dialog.tsx` (new), `web/src/components/app-sidebar.tsx`, `web/src/components/dataset-provider.tsx` (`?dataset=`), `web/src/app/(dashboard)/print/page.tsx` (new), `web/src/lib/api/{client,types}.ts`, `README.md` (export section), `specs/001-vietleap-insight-kit/contracts/openapi.json`.

## Security considerations
- **A10 SSRF**: Playwright target = `WEB_URL` env + allowlisted routes; request body has no URL field.
- **A01 / zip-slip**: archive names fixed; no user-provided names; download through `EXPORTS` allowlist.
- **A04/A05 DoS**: one export job per dataset, 180 s timeout, rate limit, Chromium closed in `finally`.
- **A09 Logging**: job log records warnings (missing Chromium, mismatched mtime) in `meta.runs` for audit.
- **Data**: `README.txt` lists licences so the submission respects CC BY / CC BY-SA attribution.
