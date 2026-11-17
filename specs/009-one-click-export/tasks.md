# Tasks: 009 One-click "Xuất báo cáo"

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Engine
- [x] T901–T904 `3c02c26` Rebuild reports, verify ZIP hashes, print the live dashboard with HTML fallback, and test graceful handling without Chromium.

## Phase B — API
- [x] T905–T907 `3c02c26` Export job and allowlisted downloads with OpenAPI, deduplication and rate limiting.

## Phase C — Web
- [x] T908 `3c02c26` Dataset URL and standalone `/print` with `data-print-ready` marker.
- [x] T909 `3c02c26` `/report` and Exports link with shadcn export dialog. Command palette entry follows feature 005.
- [ ] T910 `3c02c26` Local browser exported and reopened the bilingual ZIP in 39.01 s. All 12 required archive members found, hashes checked, PDF/deck KPI matched. [Screenshot](../../docs/screenshots/export.png). Second-machine rehearsal is pending.
- [x] T911 `3c02c26` Publish one-click export and update docs.

## Dependencies
T901→T902→T903; T905→T906 (needs T902); T906→T908→T909→T910→T911. Uses `lang` from 003 when merged (else EN deck + VI pitch as today).
