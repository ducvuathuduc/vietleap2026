# Tasks: 007 What-if sliders page

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Engine + API
- [x] T701 Test-first `tests/test_whatif_multi.py`: single change == `what_if`; two changes == aligned-draw sum; log target; zero changes → 0/[0,0]; duplicate feature → ValueError; range warning (`py_compile` ok; `pytest` pending Python env).
- [x] T702 `engine/vlkit/models.py what_if_multi` + `min`/`max` persisted by `fit_drivers`; `engine/vlkit/tools.py` wrapper → T701 (+ TS engine `stats.ts`/`analyzer.ts` parity).
- [x] T703 Test-first API tests (same file): `POST /whatif/scenario` 200/422/404; `POST|GET /whatif/scenarios` max 4, name ≤ 60.
- [x] T704 `api/schemas.py`, `api/routes/analysis.py`, `api/security.py` limited paths (+ Next.js routes `/whatif/scenario`, `/whatif/scenarios`); `python tools/export_openapi.py` deferred to full Python env → T702, T703.
- [ ] T705 Commit + push "feat(whatif): T701–T704 multi-driver scenario with joint bootstrap CI90".

## Phase B — Web
- [x] T706 [P] Test-first `web/src/lib/whatif.test.ts` (debounce/abort, localStorage per dataset, ≤ 4 saved) → `web/src/lib/whatif.ts`.
- [x] T707 `web/src/app/(dashboard)/whatif/page.tsx` (sliders, result card with `insightTarget("whatif", …)`, contribution hbar, saved-scenario table, empty states) + client/types → T704, T706.
- [x] T708 [P] VI strings on `/drivers` what-if card; nav entry + tour steps + palette item.
- [x] T709 `engine/vlkit/report.py` Impact slide & pitch list saved scenarios from `scenarios.json` (`py_compile` ok; PPTX render test pending Python env).
- [x] T710 Headless Chromium smoke on `/whatif` & `/drivers` (`synthetic_messy_bds`): slider prediction + CI90, tornado chart, localStorage & `/whatif/scenarios` reload persistence; 0 console/CSP errors.
- [ ] T711 Commit + push "feat(web): T706–T710 what-if sliders page + deck scenarios"; tick; `specs/README.md`.

## Dependencies
T701→T702→T704 ← T703; T706 ∥ Phase A; T704+T706→T707→T710→T711; T709 after T704.
