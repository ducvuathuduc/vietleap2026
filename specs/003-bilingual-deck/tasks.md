# Tasks: 003 Bilingual deck & pitch

**Status**: ✅ done & pushed 2026-11-17 — `74de518` (Phase A), `5aa4194` (Phase B), `4e098e5` (Phase C). Clarification defaults: [spec.md](spec.md) §Clarifications.

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit as `thanhdicode`, push `origin main`, tick with hash.

## Phase A — String table & caveats
- [x] T301 (`74de518`) Test-first `tests/test_i18n.py`: EN and VI tables have identical keys; no empty values; VI values contain at least one Vietnamese diacritic where the EN value is a sentence.
- [x] T302 (`74de518`) `engine/vlkit/i18n.py` with every fixed string now in `build_deck`/`pitch_md`/`PITCH_TIMING`; ST/PO review the VI column → T301.
- [x] T303 (`74de518`) [P] Test-first `tests/test_i18n.py::test_caveats_vi_parallel` (same length/order as `caveats`, numbers equal).
- [x] T304 (`74de518`) `engine/vlkit/domains.py` CAVEATS → `{en, vi}`; `profile.caveats()` bilingual; `pipeline.py` writes `caveats_vi` → T303.
- [x] T305 (`74de518`) Commit + push "feat(i18n): T301–T304 string table + bilingual caveats".

## Phase B — Report matrix + CLI/API
- [x] T306 (`5aa4194`) Test-first `tests/test_deck.py::test_deck_lang_matrix` (`--lang both` writes deck.pptx, deck.vi.pptx, pitch.md, pitch.en.md; overflow `[]` both; SC-301/SC-302 number parity).
- [x] T307 (`5aa4194`) `engine/vlkit/report.py` + `engine/vlkit/fmt.py p(lang)`; `run.py`/`de.py --lang`; `api/jobs.py`, `api/routes/datasets.py` (`lang` form field, `EXPORTS` += `deck_vi`, `pitch_md`, `pitch_en`), `api/routes/pipeline.py IngestIn.lang` → T302, T304, T306.
- [x] T308 (`5aa4194`) `python tools/export_openapi.py`; contract test for new export kinds (`tests/test_contracts.py`); path-traversal test still passes (`/files/..%2F` → 404).
- [x] T309 (`5aa4194`) Commit + push "feat(deck): T306–T308 --lang vi|en|both".

## Phase C — Web toggle
- [x] T310 (`4e098e5`) `web/src/lib/api/client.ts` kinds, `web/src/components/app-sidebar.tsx` + `nav-documents.tsx` ToggleGroup EN/VI, disabled state from `summary.files` → T307.
- [x] T311 (`4e098e5`) Headless Chromium check: toggle switches link `href`; 0 console/CSP errors; screenshot `docs/screenshots/exports-lang.png` (feature 010).
- [x] T312 (`4e098e5`) Commit + push "feat(web): T310–T311 export language toggle"; update `specs/README.md`.

## Dependencies
T301→T302; T303→T304; (T302,T304,T306)→T307→T308; T307→T310→T311. Phase A strings can be authored by ST while DE does T303/T304.
